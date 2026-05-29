from ai.ai_service import generate_chat_response, generate_stateful_response
from ai.user_store import user_store
from bot_store import store
from bot_state.conversation_state import ConversationState, Signal, get_next_state, parse_state
from bot_state.mock_shop_data import (
    SHOP_INFO, PRODUCTS, get_product_by_id, get_bestsellers, 
    get_new_arrivals, format_product_card, format_shop_intro
)
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from typing import Dict, Any, List, Optional
import logging
import datetime
import os
import time
import re
from aiogram import Bot

logger = logging.getLogger(__name__)

# Project root for resolving image paths
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# =============================================================================
# INACTIVITY TIMER CONSTANTS
# =============================================================================
INACTIVITY_THRESHOLD_SECONDS = 3600  # 1 hour

PRODUCT_INTENT_KEYWORDS = (
    "price", "cost", "cheapest", "lowest", "expensive", "budget",
    "ဈေး", "စျေး", "တန်ဖိုး", "အပေါဆုံး", "အသက်သာဆုံး", "ဘယ်လောက်",
    "သဘောကျ", "ကြိုက်", "ယူ", "ဝယ်",
)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _format_product_summary(product: Dict[str, Any]) -> str:
    stock_text = f"{product['stock']} available" if product.get("stock", 0) > 0 else "out of stock"
    return (
        f"{product['name']} - {product['price']:,} MMK\n"
        f"Stock: {stock_text}\n"
        f"{product['description']}"
    )


def _find_product_in_text(text: str) -> Optional[Dict[str, Any]]:
    normalized = _normalize_text(text)
    if not normalized:
        return None

    best_match = None
    best_score = 0
    for product in PRODUCTS:
        product_terms = [
            product["name"],
            product.get("category", ""),
            *product["name"].replace("(", " ").replace(")", " ").split(),
        ]
        score = sum(1 for term in product_terms if term and _normalize_text(term) in normalized)
        if score > best_score:
            best_match = product
            best_score = score

    return best_match if best_score >= 1 else None


def _answer_catalog_question(user_id: str, text: str) -> Optional[Dict[str, Any]]:
    """Answer simple catalog questions locally so repeated AI text cannot drift."""
    normalized = _normalize_text(text)
    if not any(keyword in normalized for keyword in PRODUCT_INTENT_KEYWORDS):
        return None

    profile = user_store.get_profile(user_id)
    mentioned_product = _find_product_in_text(text)
    current_product = get_product_by_id(profile.browsing_product_id)

    if "အပေါဆုံး" in normalized or "အသက်သာဆုံး" in normalized or "cheapest" in normalized or "lowest" in normalized:
        cheapest = min(PRODUCTS, key=lambda p: p["price"])
        profile.browsing_product_id = cheapest["id"]
        user_store.save()
        return {
            "text": (
                f"ဈေးအပေါဆုံးက {cheapest['name']} ပါရှင့်။\n"
                f"ဈေးနှုန်း: {cheapest['price']:,} MMK\n"
                f"Stock: {cheapest['stock']} available\n\n"
                "ကြည့်ချင်ရင် အောက်က button လေးနှိပ်နိုင်ပါတယ်ရှင့်။"
            ),
            "reply_markup": InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"View {cheapest['name']}", callback_data=f"view_{cheapest['id']}")],
                [InlineKeyboardButton(text="Browse More", callback_data="browse_products")]
            ])
        }

    product = mentioned_product or current_product
    if product and ("ဈေး" in normalized or "စျေး" in normalized or "price" in normalized or "cost" in normalized or "ဘယ်လောက်" in normalized):
        profile.browsing_product_id = product["id"]
        user_store.save()
        return {
            "text": (
                f"{product['name']} ရဲ့ ဈေးနှုန်းက {product['price']:,} MMK ပါရှင့်။\n"
                f"Stock: {product['stock']} available\n\n"
                f"{product['description']}"
            ),
            "reply_markup": InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"View {product['name']}", callback_data=f"view_{product['id']}")],
                [InlineKeyboardButton(text=f"Add {product['name']}", callback_data=f"add_{product['id']}")]
            ])
        }

    if mentioned_product:
        profile.browsing_product_id = mentioned_product["id"]
        profile.current_step = ConversationState.SHOW_PRODUCT.value
        user_store.save()
        return {
            "text": (
                f"{mentioned_product['name']} လေး သဘောကျတယ်ဆိုရင် အရမ်းကောင်းတဲ့ရွေးချယ်မှုပါရှင့်။\n\n"
                f"{_format_product_summary(mentioned_product)}\n\n"
                "ဝယ်ယူချင်ရင် Add button လေးနှိပ်နိုင်ပါတယ်ရှင့်။"
            ),
            "reply_markup": InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"Add {mentioned_product['name']}", callback_data=f"add_{mentioned_product['id']}")],
                [InlineKeyboardButton(text="View Details", callback_data=f"view_{mentioned_product['id']}")]
            ])
        }

    return None


# =============================================================================
# STATE MACHINE ORCHESTRATOR
# =============================================================================

async def handle_message(
    bot_token: str, 
    user_id: str, 
    user_name: str,
    text: str
) -> Dict[str, Any]:
    """
    Main entry point for stateful message handling.
    Checks for inactivity, determines current state, and dispatches to state handlers.
    """
    profile = user_store.get_profile(user_id)
    profile.user_name = user_name
    
    now = time.time()
    
    # Check inactivity - if >= 1 hour, reset to INTRODUCTION
    if now - profile.last_activity_ts >= INACTIVITY_THRESHOLD_SECONDS:
        logger.info(f"User {user_id} inactive for >= 1 hour, resetting to INTRODUCTION")
        profile.current_step = ConversationState.INTRODUCTION.value
        # Send intro first, then process the user's message
        intro_response = await _send_introduction(user_id)
        user_store.save()
    
    # Always update last_activity_ts
    profile.last_activity_ts = now
    
    # Parse current state
    current_state = parse_state(profile.current_step)

    direct_response = _answer_catalog_question(user_id, text)
    if direct_response:
        return direct_response
    
    # Dispatch to state handler
    if current_state == ConversationState.INTRODUCTION:
        # First interaction - just send intro and wait for response
        return await _handle_introduction(bot_token, user_id, text)
    elif current_state == ConversationState.INTENT_CLASSIFICATION:
        return await _handle_intent_classification(bot_token, user_id, text)
    elif current_state == ConversationState.ADVERTISE:
        return await _handle_advertise(bot_token, user_id, text)
    elif current_state == ConversationState.SHOW_PRODUCT:
        return await _handle_show_product(bot_token, user_id, text)
    elif current_state == ConversationState.WILL_IT_BUY:
        return await _handle_will_it_buy(bot_token, user_id, text)
    elif current_state == ConversationState.STOCK_CHECK:
        return await _handle_stock_check(user_id, text)
    elif current_state == ConversationState.TRANSACTION:
        # Hand off to existing payment flow
        return await handle_start(bot_token, user_id, profile.user_name, "Shwe Thitsar Fashion House")
    elif current_state == ConversationState.TERMINATE_WARM:
        return await _handle_terminate_warm(bot_token, user_id, text)
    elif current_state == ConversationState.TERMINATE_NOTIFY:
        return await _handle_terminate_notify(user_id, text)
    else:
        # Default/BROWSING - treat as intent classification
        return await _handle_intent_classification(bot_token, user_id, text)


async def handle_callback_data(
    bot_token: str,
    user_id: str,
    callback_data: str
) -> Dict[str, Any]:
    """
    Handle callback queries from inline buttons.
    Maps callback data to state transitions.
    """
    profile = user_store.get_profile(user_id)
    current_state = parse_state(profile.current_step)
    
    logger.info(f"Callback: {callback_data} from state {current_state.value}")
    
    # Map callback_data to signals and states
    if callback_data == "browse_products":
        # User wants to browse - go to advertise
        _transition_to(user_id, ConversationState.ADVERTISE)
        return await _handle_advertise(bot_token, user_id, "I want to browse products")
    
    elif callback_data == "specific_request":
        # User has specific request - go to classification
        _transition_to(user_id, ConversationState.INTENT_CLASSIFICATION)
        return await _handle_intent_classification(bot_token, user_id, "I want to find something specific")
    
    elif callback_data.startswith("view_"):
        # View specific product
        product_id = callback_data.replace("view_", "")
        profile.browsing_product_id = product_id
        _transition_to(user_id, ConversationState.SHOW_PRODUCT)
        return _build_product_detail_response(product_id)
    
    elif callback_data.startswith("buy_"):
        # User clicks buy - go to stock check
        product_id = callback_data.replace("buy_", "")
        profile.browsing_product_id = product_id
        _transition_to(user_id, ConversationState.STOCK_CHECK)
        return await _handle_stock_check(user_id, f"I want to buy product {product_id}")
    
    elif callback_data.startswith("notify_"):
        # User wants notification for out-of-stock product
        product_id = callback_data.replace("notify_", "")
        profile.notify_when_available.append(product_id)
        user_store.save()
        return {
            "text": "✅ I'll notify you when the product becomes available! 💚",
            "reply_markup": None
        }
    
    elif callback_data == "browse_more":
        # Browse more products
        _transition_to(user_id, ConversationState.ADVERTISE)
        return await _handle_advertise(bot_token, user_id, "Browse more")
    
    elif callback_data == "no_thanks":
        # User declines - terminate warm
        _transition_to(user_id, ConversationState.TERMINATE_WARM)
        return await _handle_terminate_warm(bot_token, user_id, "No thanks")
    
    # Legacy callback handling - hand off to existing handle_callback
    return await handle_callback(bot_token, user_id, callback_data)


def _transition_to(user_id: str, new_state: ConversationState) -> None:
    """Helper to update user's current state."""
    profile = user_store.get_profile(user_id)
    profile.current_step = new_state.value
    user_store.save()
    logger.info(f"User {user_id} transitioned to {new_state.value}")


def _build_product_detail_response(product_id: str) -> Dict[str, Any]:
    """Build a product detail response directly from catalog data."""
    product = get_product_by_id(product_id)
    if not product:
        return {
            "text": "Product not found.",
            "reply_markup": None
        }

    keyboard_buttons = []
    if product["stock"] > 0:
        keyboard_buttons.append([
            InlineKeyboardButton(text=f"Add {product['name']}", callback_data=f"add_{product['id']}")
        ])
    else:
        keyboard_buttons.append([
            InlineKeyboardButton(text="Notify Me When Available", callback_data=f"notify_{product['id']}")
        ])

    keyboard_buttons.append([
        InlineKeyboardButton(text="View Another Product", callback_data="browse_products")
    ])

    image_path = product.get("image_path", "")
    return {
        "text": format_product_card(product, compact=False),
        "reply_markup": InlineKeyboardMarkup(inline_keyboard=keyboard_buttons),
        "photo_path": image_path if os.path.exists(image_path) else None,
        "photo_caption": f"{product['name']} - {product['price']:,} MMK"
    }


# =============================================================================
# STATE HANDLERS
# =============================================================================

async def _send_introduction(user_id: str) -> Dict[str, Any]:
    """Send the shop introduction message."""
    intro_text = format_shop_intro()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 Browse Products", callback_data="browse_products")],
        [InlineKeyboardButton(text="🔍 I'm looking for something specific", callback_data="specific_request")]
    ])
    
    return {
        "text": intro_text,
        "reply_markup": keyboard
    }


async def _handle_introduction(bot_token: str, user_id: str, text: str) -> Dict[str, Any]:
    """Handle INTRODUCTION state: send intro, then classify user intent."""
    # Send introduction
    intro_response = await _send_introduction(user_id)
    
    # Transition to intent classification
    _transition_to(user_id, ConversationState.INTENT_CLASSIFICATION)
    
    # Get AI response for the user's actual message
    ai_result = await generate_stateful_response(
        bot_token=bot_token,
        user_id=user_id,
        user_message=text
    )
    
    # Determine signal based on AI-intent
    if ai_result.get("intent") == "specific_request":
        _transition_to(user_id, ConversationState.SHOW_PRODUCT)
    else:
        _transition_to(user_id, ConversationState.ADVERTISE)
    
    # Return combined response
    response_text = intro_response["text"] + "\n\n" + ai_result.get("text", "")
    
    return {
        "text": response_text,
        "reply_markup": intro_response.get("reply_markup")
    }


async def _handle_intent_classification(bot_token: str, user_id: str, text: str) -> Dict[str, Any]:
    """Handle INTENT_CLASSIFICATION state: AI classifies exploring vs specific request."""
    profile = user_store.get_profile(user_id)
    
    # Get AI to classify intent
    ai_result = await generate_stateful_response(
        bot_token=bot_token,
        user_id=user_id,
        user_message=text
    )
    
    intent = ai_result.get("intent")
    product_id = ai_result.get("product_id")
    
    if intent == "specific_request" or product_id:
        # User has specific request - go to show product
        if product_id:
            profile.browsing_product_id = product_id
        _transition_to(user_id, ConversationState.SHOW_PRODUCT)
        return await _handle_show_product(bot_token, user_id, text)
    else:
        # User is exploring - go to advertise
        _transition_to(user_id, ConversationState.ADVERTISE)
        return await _handle_advertise(bot_token, user_id, text)


async def _handle_advertise(bot_token: str, user_id: str, text: str) -> Dict[str, Any]:
    """Handle ADVERTISE state: show bestsellers and new arrivals."""
    profile = user_store.get_profile(user_id)
    
    # Get bestsellers and new arrivals
    bestsellers = get_bestsellers()
    new_arrivals = get_new_arrivals()
    
    # Get AI response
    ai_result = await generate_stateful_response(
        bot_token=bot_token,
        user_id=user_id,
        user_message=text
    )
    
    # Check if user mentioned specific product
    if ai_result.get("product_id"):
        profile.browsing_product_id = ai_result["product_id"]
        _transition_to(user_id, ConversationState.SHOW_PRODUCT)
        return await _handle_show_product(bot_token, user_id, text)
    
    # Build response with product cards
    response_text = ai_result.get("text", "Here are our popular products:")
    
    keyboard_buttons = []
    
    # Add bestsellers
    for product in bestsellers[:3]:
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"🔥 {product['name']} ({product['price']:,} MMK)",
                callback_data=f"view_{product['id']}"
            )
        ])
    
    # Add new arrivals
    for product in new_arrivals[:3]:
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"🆕 {product['name']} ({product['price']:,} MMK)",
                callback_data=f"view_{product['id']}"
            )
        ])
    
    # Add browse more button
    keyboard_buttons.append([
        InlineKeyboardButton(text="🔄 Browse More", callback_data="browse_products")
    ])
    
    return {
        "text": response_text,
        "reply_markup": InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    }


async def _handle_show_product(bot_token: str, user_id: str, text: str) -> Dict[str, Any]:
    """Handle SHOW_PRODUCT state: show specific product with image and details."""
    profile = user_store.get_profile(user_id)
    
    product_id = profile.browsing_product_id
    product = get_product_by_id(product_id)
    
    # Get AI response
    ai_result = await generate_stateful_response(
        bot_token=bot_token,
        user_id=user_id,
        user_message=text
    )
    
    # Check for intent changes
    intent = ai_result.get("intent")
    if intent == "wants_to_buy":
        _transition_to(user_id, ConversationState.STOCK_CHECK)
        return await _handle_stock_check(user_id, text)
    elif intent == "not_buying" or intent == "stopped_asking":
        _transition_to(user_id, ConversationState.TERMINATE_WARM)
        return await _handle_terminate_warm(bot_token, user_id, text)
    elif intent == "exploring":
        _transition_to(user_id, ConversationState.ADVERTISE)
        return await _handle_advertise(bot_token, user_id, text)
    
    if not product:
        return {
            "text": ai_result.get("text", "Product not found."),
            "reply_markup": None
        }
    
    # Format product card
    product_text = format_product_card(product, compact=False)
    
    # Build response with image and buttons
    keyboard_buttons = []
    
    if product["stock"] > 0:
        keyboard_buttons.append([
            InlineKeyboardButton(text="🛒 Add to Cart", callback_data=f"add_{product['id']}")
        ])
    
    keyboard_buttons.append([
        InlineKeyboardButton(text="👀 View Another Product", callback_data="browse_products"),
        InlineKeyboardButton(text="❓ Ask AI", callback_data="specific_request")
    ])
    
    if product["stock"] == 0:
        keyboard_buttons.append([
            InlineKeyboardButton(text="🔔 Notify Me When Available", callback_data=f"notify_{product['id']}")
        ])
    
    # Get image path
    image_path = product.get("image_path", "")
    
    response_text = product_text + "\n\n" + ai_result.get("text", "")
    
    return {
        "text": response_text,
        "reply_markup": InlineKeyboardMarkup(inline_keyboard=keyboard_buttons),
        "photo_path": image_path if os.path.exists(image_path) else None,
        "photo_caption": f"✨ {product['name']}"
    }


async def _handle_will_it_buy(bot_token: str, user_id: str, text: str) -> Dict[str, Any]:
    """Handle WILL_IT_BUY state: AI detects purchase intent."""
    ai_result = await generate_stateful_response(
        bot_token=bot_token,
        user_id=user_id,
        user_message=text
    )
    
    intent = ai_result.get("intent")
    
    if intent == "wants_to_buy":
        _transition_to(user_id, ConversationState.STOCK_CHECK)
        return await _handle_stock_check(user_id, text)
    elif intent == "not_buying" or intent == "stopped_asking":
        _transition_to(user_id, ConversationState.TERMINATE_WARM)
        return await _handle_terminate_warm(bot_token, user_id, text)
    
    return {
        "text": ai_result.get("text", "Let me know if you'd like to proceed!"),
        "reply_markup": None
    }


async def _handle_stock_check(user_id: str, text: str) -> Dict[str, Any]:
    """Handle STOCK_CHECK state: check if product is in stock."""
    profile = user_store.get_profile(user_id)
    product_id = profile.browsing_product_id
    product = get_product_by_id(product_id)
    
    if not product:
        return {
            "text": "Product not found.",
            "reply_markup": None
        }
    
    if product["stock"] > 0:
        # In stock - go to transaction
        _transition_to(user_id, ConversationState.TRANSACTION)
        # Add to cart
        existing = next((item for item in profile.cart if item["productId"] == product_id), None)
        if existing:
            existing["quantity"] += 1
        else:
            profile.cart.append({
                "productId": product_id,
                "name": product["name"],
                "price": product["price"],
                "quantity": 1
            })
        user_store.save()
        
        return {
            "text": f"✅ **{product['name']}** is in stock! ({product['stock']} available)\n\nReady to checkout? Choose your payment method below:",
            "reply_markup": InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💵 Cash on Delivery", callback_data="payment_cod")],
                [InlineKeyboardButton(text="💳 Mobile Prepay", callback_data="payment_prepay")],
                [InlineKeyboardButton(text="🛍 Browse More", callback_data="browse_products")]
            ])
        }
    else:
        # Out of stock - go to terminate notify
        _transition_to(user_id, ConversationState.TERMINATE_NOTIFY)
        return await _handle_terminate_notify(user_id, text)


async def _handle_terminate_warm(bot_token: str, user_id: str, text: str) -> Dict[str, Any]:
    """Handle TERMINATE_WARM state: warm goodbye with follow-up question."""
    ai_result = await generate_stateful_response(
        bot_token=bot_token,
        user_id=user_id,
        user_message=text
    )
    
    response_text = ai_result.get("text", "")
    
    # Add warm goodbye follow-up
    response_text += "\n\n💕 **We hope to see you again soon!**\n" + \
                    "Let us know if there's anything else we can help you with. 😊"
    
    return {
        "text": response_text,
        "reply_markup": InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛍 Browse Products", callback_data="browse_products")],
            [InlineKeyboardButton(text="🔍 Search Products", callback_data="specific_request")]
        ])
    }


async def _handle_terminate_notify(user_id: str, text: str) -> Dict[str, Any]:
    """Handle TERMINATE_NOTIFY state: out of stock - offer notification."""
    profile = user_store.get_profile(user_id)
    product_id = profile.browsing_product_id
    product = get_product_by_id(product_id)
    
    if not product:
        return {
            "text": "Product not found.",
            "reply_markup": None
        }
    
    arrival_date = product.get("arrival_date", "soon")
    product_name = product["name"]
    
    response_text = (
        f"😔 Sorry, **{product_name}** is currently **out of stock**.\n\n"
        f"📅 Expected arrival: **{arrival_date}**\n\n"
        f"Would you like me to notify you when it becomes available?"
    )
    
    return {
        "text": response_text,
        "reply_markup": InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔔 Yes, Notify Me!", callback_data=f"notify_{product_id}")],
            [InlineKeyboardButton(text="🛍 Browse Other Products", callback_data="browse_products")],
            [InlineKeyboardButton(text="👋 Maybe Later", callback_data="no_thanks")]
        ])
    }


# =============================================================================
# LEGACY FUNCTIONS (kept for backward compatibility)
# =============================================================================

async def handle_start(bot_token: str, user_id: str, user_name: str, bot_name: str) -> Dict[str, Any]:
    """Handle the /start command with interactive menu."""
    bot_state = store.get_state(bot_token)
    profile = user_store.get_profile(user_id)
    profile.user_name = user_name

    # Reset session for fresh start
    profile.cart = []
    profile.current_step = "browsing"
    user_store.save()

    welcome_text = (
        f"Mingalabar {user_name}! 🙏 Welcome to **{bot_state.persona_name}'s Shop**! "
        f"I am your AI Assistant, happy to help you today. 💕\n\n"
        f"Here is our product list. What can I pack for you?\n\n"
    )

    for idx, p in enumerate(bot_state.products):
        welcome_text += f"{idx + 1}️⃣ **{p['name']}** - {p['price']:,} MMK\n_{p['description']}_\n\n"

    welcome_text += "✨ You can tap the buttons below to add items to your cart or ask me any questions!"

    keyboard = []
    for p in bot_state.products:
        keyboard.append([InlineKeyboardButton(text=f"🛒 Add {p['name']}", callback_data=f"add_{p['id']}")])

    return {
        "text": welcome_text,
        "reply_markup": InlineKeyboardMarkup(inline_keyboard=keyboard)
    }

async def handle_callback(bot_token: str, user_id: str, callback_data: str) -> Dict[str, Any]:
    """Handle button clicks and state transitions."""
    bot_state = store.get_state(bot_token)
    profile = user_store.get_profile(user_id)

    # 1. Add to Cart
    if callback_data.startswith("add_"):
        prod_id = callback_data.replace("add_", "")
        product = next((p for p in bot_state.products if p["id"] == prod_id), None)

        if product:
            existing = next((item for item in profile.cart if item["productId"] == prod_id), None)
            if existing:
                existing["quantity"] += 1
            else:
                profile.cart.append({"productId": prod_id, "name": product["name"], "price": product["price"], "quantity": 1})

            user_store.save()

            cart_text = "Perfect choice! 🌸 I've added that to your basket.\n\n🛒 **Current Basket:**\n"
            total = 0
            for item in profile.cart:
                subtotal = item["price"] * item["quantity"]
                total += subtotal
                cart_text += f"- {item['name']} x {item['quantity']} ({subtotal:,} MMK)\n"

            cart_text += f"\n💰 **Total: {total:,} MMK**\n\nWould you like to checkout now?"

            keyboard = [
                [
                    InlineKeyboardButton(text="💵 Cash on Delivery", callback_data="payment_cod"),
                    InlineKeyboardButton(text="💳 Mobile Prepay", callback_data="payment_prepay")
                ],
                [InlineKeyboardButton(text="🛍 Browse More", callback_data="browse_more")]
            ]

            return {
                "text": cart_text,
                "reply_markup": InlineKeyboardMarkup(inline_keyboard=keyboard)
            }

    # 2. Payment Selection
    elif callback_data in ["payment_cod", "payment_prepay"]:
        profile.temp_pay_method = "cod" if callback_data == "payment_cod" else "prepay"
        profile.current_step = "selecting_township"
        user_store.save()

        township_text = (
            f"Sweet choice! 🌸 You chose: **{profile.temp_pay_method.upper()}**.\n\n"
            "Now, please select your township for delivery calculation:"
        )

        # Fetch live delivery zones from the Delivery Matrix API
        # Use static fallback immediately without API call for fast response
        _static_fallback = [
            {"township_name": z["township"], "rate": z["rate"],
             "estimated_transit_timeline": z.get("deliveryTime", "N/A")}
            for z in bot_state.delivery_zones
        ]
        
        try:
            import asyncio
            from api.delivery_client import fetch_all_zones
            all_zones = await asyncio.wait_for(
                fetch_all_zones(fallback_zones=_static_fallback),
                timeout=3.0  # Max 3 seconds wait for API
            )
        except (asyncio.TimeoutError, Exception) as _fetch_err:
            logger.warning("Delivery zone fetch failed in checkout: %s. Using static fallback.", _fetch_err)
            all_zones = _static_fallback

        keyboard = []
        for zone in all_zones[:10]:
            keyboard.append([InlineKeyboardButton(
                text=f"🛵 {zone['township_name']}",
                callback_data=f"township_{zone['township_name']}"
            )])
        if len(all_zones) > 10:
            keyboard.append([InlineKeyboardButton(
                text="🔍 Other Township (type name)",
                callback_data="township_other"
            )])

        return {
            "text": township_text,
            "reply_markup": InlineKeyboardMarkup(inline_keyboard=keyboard)
        }

    # 3. Township Selection
    elif callback_data.startswith("township_"):
        township_name = callback_data.replace("township_", "")

        # Fetch live delivery zones from the Delivery Matrix API for rate lookup
        _static_fallback = [
            {"township_name": z["township"], "rate": z["rate"],
             "estimated_transit_timeline": z.get("deliveryTime", "N/A")}
            for z in bot_state.delivery_zones
        ]
        
        try:
            import asyncio
            from api.delivery_client import fetch_single_zone
            zone = await asyncio.wait_for(
                fetch_single_zone(township_name, fallback_zones=_static_fallback),
                timeout=3.0  # Max 3 seconds wait for API
            )
        except (asyncio.TimeoutError, Exception) as _fetch_err:
            logger.warning("Delivery zone fetch failed in township selection: %s", _fetch_err)
            zone = next((z for z in _static_fallback if z["township_name"] == township_name), None)

        if zone:
            cart_total = sum(item["price"] * item["quantity"] for item in profile.cart)
            total_amount = cart_total + zone["rate"]

            order_id = f"ORD-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"
            profile.active_order_id = order_id

            order_data = {
                "id": order_id,
                "township": township_name,
                "delivery_fee": zone["rate"],
                "total_amount": total_amount,
                "items": profile.cart.copy(),
                "payment_method": profile.temp_pay_method,
                "status": "pending",
                "created_at": datetime.datetime.now().isoformat()
            }

            if profile.temp_pay_method == "cod":
                order_data["status"] = "confirmed"
                user_store.add_order(user_id, order_data)
                profile.cart = []
                profile.current_step = "completed"
                user_store.save()

                return {
                    "text": (
                        f"🎉 **Order Placed Successfully!**\n\n"
                        f"Invoice ID: `{order_id}`\n"
                        f"Total: **{total_amount:,} MMK** (Delivery: {zone['rate']:,} MMK)\n"
                        f"📍 Township: {township_name}\n"
                        f"🚀 Delivery: {zone['estimated_transit_timeline']}\n\n"
                        f"Thank you for your order! We will deliver it soon. 🙏"
                    )
                }
            else:
                profile.current_step = "awaiting_payment"
                user_store.save()

                return {
                    "text": (
                        f"💳 **Please complete Prepayment**\n\n"
                        f"Total: **{total_amount:,} MMK**\n"
                        f"📍 Township: {township_name} (+{zone['rate']:,} MMK)\n\n"
                        f"👇 **Payment Methods:**\n"
                        f"📱 KPAY: 09971234567 (Shop Owner)\n"
                        f"📱 WAVE: 09971234567 (Shop Owner)\n\n"
                        f"*Please send the receipt screenshot here!* ✨"
                    )
                }

    elif callback_data == "browse_more":
        return await handle_start(bot_token, user_id, profile.user_id, bot_state.persona_name)

    return None

async def handle_receipt_photo(bot_token: str, user_id: str, file_id: str) -> str:
    """Handle uploaded payment receipt photos."""
    profile = user_store.get_profile(user_id)

    if profile.current_step == "awaiting_payment":
        # In a real app, we'd download the file. Here we just update order status.
        # Find the pending order in history or store it properly
        profile.current_step = "verifying"
        user_store.save()

        return (
            "👍 **Receipt received!**\n\n"
            "Our team will verify your payment and confirm your order shortly. "
            "You will receive an alert once confirmed! 💚"
        )

    return "Thank you for the photo! How can I help you with it? 😊"

async def generate_start_reply(channel: str, user_name: str, bot_name: str, user_id: str) -> str:
    """Legacy start reply, kept for compatibility."""
    return (
        f"🚀 Shared Logic Working!\n\n"
        f"You are talking to: **{bot_name}** via {channel.capitalize()}\n"
        f"Your ID: `{user_id}`"
    )

async def send_broadcast_message(bot_token: str, message_text: str) -> Dict[str, Any]:
    """
    Send a broadcast message to all users who have talked with the bot.
    Returns summary dict with sent/failed counts.
    """
    from bot_store import store
    from aiogram.enums import ParseMode

    bot_state = store.get_state(bot_token)
    all_profiles = user_store.profiles

    sent = 0
    failed = 0
    results = []

    async with Bot(token=bot_token) as bot:
        for uid, profile in all_profiles.items():
            try:
                await bot.send_message(
                    chat_id=int(uid),
                    text=message_text,
                    parse_mode=ParseMode.MARKDOWN
                )
                sent += 1
                results.append({"user_id": uid, "status": "sent"})
                logger.info(f"Broadcast: sent to user {uid}")
            except Exception as e:
                failed += 1
                results.append({"user_id": uid, "status": "failed", "error": str(e)})
                logger.warning(f"Broadcast: failed for user {uid}: {e}")

    logger.info(f"Broadcast complete for {bot_state.persona_name}. Sent={sent}, Failed={failed}")
    return {
        "bot_persona": bot_state.persona_name,
        "total_users": len(all_profiles),
        "sent": sent,
        "failed": failed,
        "details": results
    }


async def generate_echo_reply(channel: str, bot_token: str, user_id: str, text: str) -> str:
    """Enhanced AI reply with cart and inventory awareness."""
    # Serve contextual reply using our Gemini layer
    ai_response = await generate_chat_response(
        bot_token=bot_token,
        user_id=str(user_id),
        user_message=text
    )
    return ai_response

async def process_checkout(user_id: str, order_data: Dict[str, Any]) -> str:
    """Core logic hook for whenever an order completes. Logs it to Sales Brain."""
    try:
        user_store.add_order(user_id, order_data)
        logger.info(f"Order successfully tracked for user {user_id} in Analytics Store.")
        return "Order verified and tracked."
    except Exception as e:
        logger.error(f"Failed to track order: {e}")
        return "Order processed but analytics tracking failed."
