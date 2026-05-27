from ai.ai_service import generate_chat_response
from ai.user_store import user_store
from bot_store import store
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Dict, Any, List
import logging
import datetime

logger = logging.getLogger(__name__)

async def handle_start(bot_token: str, user_id: str, user_name: str, bot_name: str) -> Dict[str, Any]:
    """Handle the /start command with interactive menu."""
    bot_state = store.get_state(bot_token)
    profile = user_store.get_profile(user_id)

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

        keyboard = []
        for zone in bot_state.delivery_zones:
            keyboard.append([InlineKeyboardButton(text=f"🛵 {zone['township']}", callback_data=f"township_{zone['township']}")])

        return {
            "text": township_text,
            "reply_markup": InlineKeyboardMarkup(inline_keyboard=keyboard)
        }

    # 3. Township Selection
    elif callback_data.startswith("township_"):
        township_name = callback_data.replace("township_", "")
        zone = next((z for z in bot_state.delivery_zones if z["township"] == township_name), None)

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
                        f"🚀 Delivery: {zone['deliveryTime']}\n\n"
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
