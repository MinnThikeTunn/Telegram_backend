"""
Mock shop and product data for the AI Sales Bot demo.

This module provides a rich set of mock data including shop metadata,
product catalog with stock levels, and image paths. Used by core_logic.py
for the stateful sales flow.
"""

import os
from typing import Dict, Any, List, Optional

# Base path for resolving image paths relative to the project root
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ──────────────────────────────────────────────────────────────────────
# Shop Information
# ──────────────────────────────────────────────────────────────────────

SHOP_INFO: Dict[str, Any] = {
    "name": "Shwe Thitsar Fashion House",
    "tagline": "✨ Where Style Meets Quality ✨",
    "description": (
        "Yangon's favorite online fashion boutique — handpicked styles "
        "for the modern Myanmar woman and man. From traditional elegance "
        "to street-ready trends, we dress your confidence."
    ),
    "attributes": [
        "🏅 Premium Quality Fabrics",
        "🚀 Fast Delivery (Same-day in Yangon)",
        "🔄 Easy Returns within 7 days",
        "🇲🇲 Authentic Myanmar Designs",
        "💎 Handpicked by Professional Stylists",
        "📦 Secure Packaging",
    ],
    "established": "2023",
    "location": "Latha Township, Yangon",
}


# ──────────────────────────────────────────────────────────────────────
# Product Catalog
# ──────────────────────────────────────────────────────────────────────

# Default placeholder image for all products
_DEFAULT_IMAGE = os.path.join(_PROJECT_ROOT, "test_image", "transaction-processing-system-2-1.jpg")

PRODUCTS: List[Dict[str, Any]] = [
    {
        "id": "mock-1",
        "name": "Silk Longyi (Traditional)",
        "price": 35000,
        "category": "Traditional Wear",
        "description": (
            "Handwoven pure silk longyi with intricate Amarapura patterns. "
            "Perfect for ceremonies, pagoda visits, and special occasions."
        ),
        "stock": 12,
        "is_bestseller": True,
        "is_new": False,
        "image_path": _DEFAULT_IMAGE,
        "sizes": ["Free Size"],
        "colors": ["Royal Purple", "Emerald Green", "Ruby Red"],
    },
    {
        "id": "mock-2",
        "name": "Modern Fitted Blouse",
        "price": 18000,
        "category": "Tops",
        "description": (
            "Stylish cotton-blend fitted blouse with delicate lace detailing. "
            "Pairs beautifully with longyis or jeans."
        ),
        "stock": 25,
        "is_bestseller": True,
        "is_new": False,
        "image_path": _DEFAULT_IMAGE,
        "sizes": ["S", "M", "L", "XL"],
        "colors": ["Cream White", "Blush Pink", "Sky Blue"],
    },
    {
        "id": "mock-3",
        "name": "Casual Street Jacket",
        "price": 42000,
        "category": "Outerwear",
        "description": (
            "Lightweight bomber-style jacket with Myanmar-inspired embroidery. "
            "Water-resistant, perfect for Yangon's rainy season."
        ),
        "stock": 8,
        "is_bestseller": False,
        "is_new": True,
        "image_path": _DEFAULT_IMAGE,
        "sizes": ["M", "L", "XL"],
        "colors": ["Midnight Black", "Olive Green"],
    },
    {
        "id": "mock-4",
        "name": "Cotton Palazzo Pants",
        "price": 22000,
        "category": "Bottoms",
        "description": (
            "Flowy wide-leg palazzo pants in breathable cotton. "
            "Elastic waist for all-day comfort and effortless elegance."
        ),
        "stock": 15,
        "is_bestseller": False,
        "is_new": False,
        "image_path": _DEFAULT_IMAGE,
        "sizes": ["S", "M", "L"],
        "colors": ["Sand Beige", "Charcoal", "Navy"],
    },
    {
        "id": "mock-5",
        "name": "Designer Handbag (Limited Edition)",
        "price": 65000,
        "category": "Accessories",
        "description": (
            "Exclusive hand-stitched leather crossbody bag with gold-tone hardware. "
            "Only 50 pieces made — a true collector's item."
        ),
        "stock": 0,  # OUT OF STOCK
        "is_bestseller": False,
        "is_new": True,
        "image_path": _DEFAULT_IMAGE,
        "sizes": ["One Size"],
        "colors": ["Cognac Brown", "Classic Black"],
        "arrival_date": "June 10, 2026",
    },
    {
        "id": "mock-6",
        "name": "Embroidered Scarf",
        "price": 12000,
        "category": "Accessories",
        "description": (
            "Lightweight chiffon scarf with hand-embroidered floral motifs. "
            "Perfect gift or everyday accessory."
        ),
        "stock": 30,
        "is_bestseller": True,
        "is_new": False,
        "image_path": _DEFAULT_IMAGE,
        "sizes": ["Free Size"],
        "colors": ["Rose Gold", "Ocean Blue", "Ivory"],
    },
    {
        "id": "mock-7",
        "name": "Men's Linen Shirt",
        "price": 28000,
        "category": "Men's Wear",
        "description": (
            "Premium linen button-down shirt. Relaxed fit, ideal for "
            "Yangon's warm weather. Looks sharp tucked or untucked."
        ),
        "stock": 0,  # OUT OF STOCK
        "is_bestseller": False,
        "is_new": False,
        "image_path": _DEFAULT_IMAGE,
        "sizes": ["M", "L", "XL", "XXL"],
        "colors": ["White", "Light Blue"],
        "arrival_date": "June 3, 2026",
    },
    {
        "id": "mock-8",
        "name": "Anklet Sandals (Handmade)",
        "price": 19000,
        "category": "Footwear",
        "description": (
            "Artisan-crafted leather sandals with delicate ankle strap. "
            "Comfortable enough for all-day wear, chic enough for dinner."
        ),
        "stock": 10,
        "is_bestseller": False,
        "is_new": True,
        "image_path": _DEFAULT_IMAGE,
        "sizes": ["36", "37", "38", "39", "40"],
        "colors": ["Tan", "Black"],
    },
]


# ──────────────────────────────────────────────────────────────────────
# Helper functions
# ──────────────────────────────────────────────────────────────────────

def get_product_by_id(product_id: str) -> Optional[Dict[str, Any]]:
    """Look up a product by its ID."""
    return next((p for p in PRODUCTS if p["id"] == product_id), None)


def get_bestsellers() -> List[Dict[str, Any]]:
    """Return all products marked as bestsellers."""
    return [p for p in PRODUCTS if p.get("is_bestseller")]


def get_new_arrivals() -> List[Dict[str, Any]]:
    """Return all products marked as new arrivals."""
    return [p for p in PRODUCTS if p.get("is_new")]


def get_in_stock_products() -> List[Dict[str, Any]]:
    """Return all products currently in stock."""
    return [p for p in PRODUCTS if p.get("stock", 0) > 0]


def search_products(query: str) -> List[Dict[str, Any]]:
    """Simple keyword search across product names, categories, and descriptions."""
    query_lower = query.lower()
    results = []
    for p in PRODUCTS:
        searchable = f"{p['name']} {p['category']} {p['description']}".lower()
        if query_lower in searchable:
            results.append(p)
    return results


def format_product_card(product: Dict[str, Any], compact: bool = False) -> str:
    """Format a product into a rich text card for Telegram."""
    stock_badge = "✅ In Stock" if product["stock"] > 0 else "❌ Out of Stock"
    tags = []
    if product.get("is_bestseller"):
        tags.append("🔥 Bestseller")
    if product.get("is_new"):
        tags.append("🆕 New Arrival")

    if compact:
        tag_str = " ".join(tags)
        return (
            f"{'  '.join(tags)}\n" if tags else ""
        ) + (
            f"**{product['name']}**\n"
            f"💰 {product['price']:,} MMK | {stock_badge}\n"
            f"_{product['description'][:80]}..._"
        )

    colors = ", ".join(product.get("colors", []))
    sizes = ", ".join(product.get("sizes", []))

    card = (
        f"{'  '.join(tags)}\n" if tags else ""
    ) + (
        f"✦ **{product['name']}** ✦\n\n"
        f"📝 _{product['description']}_\n\n"
        f"💰 **Price: {product['price']:,} MMK**\n"
        f"📦 {stock_badge}"
    )

    if product["stock"] == 0 and product.get("arrival_date"):
        card += f" — Expected: {product['arrival_date']}"
    card += "\n"

    if colors:
        card += f"🎨 Colors: {colors}\n"
    if sizes:
        card += f"📏 Sizes: {sizes}\n"

    return card


def format_shop_intro() -> str:
    """Format the shop introduction message."""
    attrs = "\n".join(f"  {a}" for a in SHOP_INFO["attributes"])
    in_stock_count = len(get_in_stock_products())
    total_count = len(PRODUCTS)

    return (
        f"🏬 **{SHOP_INFO['name']}**\n"
        f"{SHOP_INFO['tagline']}\n\n"
        f"_{SHOP_INFO['description']}_\n\n"
        f"**Why shop with us?**\n{attrs}\n\n"
        f"📍 {SHOP_INFO['location']} | Est. {SHOP_INFO['established']}\n"
        f"🛍 {in_stock_count} products available ({total_count} total in catalog)\n\n"
        f"How can I help you today? 💕"
    )
