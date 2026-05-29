"""
Product table listener — polls public.products every 60s for stock restocks.
When a product transitions 0 → non-zero, notifies all users who requested it.
"""
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Dict

from supabase import create_client

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
POLL_INTERVAL = 60  # seconds
SNAPSHOT_FILE = "product_stock_snapshot.json"


@dataclass
class StockSnapshot:
    """In-memory + disk-backed stock state tracker."""
    stocks: Dict[str, int] = field(default_factory=dict)

    def load(self):
        import json
        if os.path.exists(SNAPSHOT_FILE):
            try:
                with open(SNAPSHOT_FILE, "r") as f:
                    self.stocks = json.load(f)
                logger.info("Loaded product stock snapshot: %d products", len(self.stocks))
            except Exception as e:
                logger.warning("Could not load snapshot: %s", e)

    def save(self):
        import json
        try:
            with open(SNAPSHOT_FILE, "w") as f:
                json.dump(self.stocks, f)
        except Exception as e:
            logger.warning("Could not save snapshot: %s", e)

    def update(self, product_id: str, stock: int) -> bool:
        """
        Returns True if product transitioned from 0 → non-zero (restocked).
        Sets stock for new products (no prior record = not a restock event).
        """
        old = self.stocks.get(product_id, -1)  # -1 = never seen
        self.stocks[product_id] = stock
        self.save()
        return old == 0 and stock > 0


def _fetch_products(supabase_client) -> Dict[str, int]:
    """Fetch current stock for all products. Returns {product_id: stock}."""
    try:
        response = supabase_client.table("products").select("id, stock").execute()
        return {row["id"]: row["stock"] for row in response.data}
    except Exception as e:
        logger.error("Failed to fetch products: %s", e)
        return {}


def _notify_user(bot_token: str, user_id: str, product_id: str, product_name: str, stock: int):
    """
    Send Telegram message to user that their wanted product is back.
    Import bot lazily to avoid circular imports at module scope.
    """
    import asyncio
    try:
        from aiogram import Bot
        from aiogram.types import FSInputFile

        async def _send():
            async with Bot(token=bot_token) as bot:
                msg = (
                    f"✅ Good news! *{product_name}* is back in stock ({stock} available).\n\n"
                    "Tap /start to browse or buy now!"
                )
                await bot.send_message(chat_id=user_id, text=msg, parse_mode="Markdown")

        asyncio.run(_send())
    except Exception as e:
        logger.error("Failed to notify user %s for product %s: %s", user_id, product_id, e)


class ProductListener:
    """
    Background daemon polling product table.
    Start via .start(), stop via .stop().
    """

    def __init__(self):
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._snapshot = StockSnapshot()
        self._snapshot.load()
        self._supabase = None

    def _init_supabase(self):
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in environment"
            )
        return create_client(SUPABASE_URL, SUPABASE_KEY)

    def _notify_watching_users(self, product_id: str, product_name: str, new_stock: int):
        """Send notifications to all users watching this product."""
        from ai.user_store import user_store

        for user_id, profile in user_store.profiles.items():
            if product_id in profile.notify_when_available:
                # Try all known bot tokens — notifying user on their first active bot
                bot_tokens_str = os.getenv("BOT_TOKENS", "")
                tokens = [t.strip() for t in bot_tokens_str.split(",") if t.strip()]
                for token in tokens:
                    _notify_user(token, user_id, product_id, product_name, new_stock)
                # Remove from waitlist after notifying (one-shot notification)
                profile.notify_when_available.remove(product_id)
        user_store.save()

    def _poll(self):
        """Single poll iteration. Checked every POLL_INTERVAL seconds."""
        try:
            if self._supabase is None:
                self._supabase = self._init_supabase()

            # Fetch product name map
            try:
                resp = self._supabase.table("products").select("id, name, stock").execute()
                id_to_name = {r["id"]: r["name"] for r in resp.data}
                products_stock = {r["id"]: r["stock"] for r in resp.data}
            except Exception as e:
                logger.error("Product listener: fetch error: %s", e)
                return

            for product_id, stock in products_stock.items():
                if self._snapshot.update(product_id, stock):
                    name = id_to_name.get(product_id, product_id)
                    logger.info(
                        "RESTOCK detected: product=%s name=%s stock=%d",
                        product_id, name, stock
                    )
                    self._notify_watching_users(product_id, name, stock)

        except Exception as e:
            logger.exception("Product listener poll iteration failed: %s", e)

    def _loop(self):
        logger.info("Product listener started (interval=%ds)", POLL_INTERVAL)
        while not self._stop_event.is_set():
            self._poll()
            # Wait for interval or stop signal, whichever comes first
            self._stop_event.wait(POLL_INTERVAL)
        logger.info("Product listener stopped")

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            logger.warning("Product listener already running")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, name="ProductListener", daemon=True)
        self._thread.start()
        logger.info("Product listener thread started")

    def stop(self):
        if self._thread is None:
            return
        self._stop_event.set()
        self._thread.join(timeout=10)
        self._thread = None
        logger.info("Product listener thread stopped")


# ---------------------------------------------------------------------------
# Module-level singleton exposed for lifecycle management in main.py
# ---------------------------------------------------------------------------
_listener: ProductListener | None = None


def start_listener():
    global _listener
    if _listener is None:
        _listener = ProductListener()
    _listener.start()


def stop_listener():
    global _listener
    if _listener is not None:
        _listener.stop()
        _listener = None