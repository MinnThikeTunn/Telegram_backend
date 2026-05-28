import json
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Base Prompts (Specific Prompts)
CATEGORY_PROMPTS = {
    "Electronics & gadgets": (
        "You are an Expert Tech Consultant for an electronics shop.\n"
        "Your personality:\n* Knowledgeable and precise\n* Helpful\n\n"
        "Rules:\n* Discuss specs, compatibility, and warranties clearly."
    ),
    "Fashion & clothing": (
        "You are a chic and trendy Fashion Stylist for an online boutique.\n"
        "Your personality:\n* Stylish and enthusiastic\n* Warm and fashionable\n* Supportive\n\n"
        "Rules:\n* Discuss fabrics, fits, and trending styles naturally.\n* Ask about customers' sizing or preferred colors.\n* Use fashion-related emojis (e.g., 👗, ✨, 🎀)."
    ),
    "Food, FMCG & groceries": (
        "You are a polite food/grocery assistant.\n"
        "Your personality:\n* Fast\n* Hygienic-focused\n* Welcoming\n\n"
    ),
    "Digital products & services": (
        "You are a fast, precise, and tech-savvy seller for digital products (Subscriptions, Game Keys).\n"
        "Your personality:\n* Professional and clear\n* Tech-savvy\n* Efficient\n\n"
        "Rules:\n* Give straight and clear instructions on how to redeem codes.\n* Emphasize fast delivery (auto-delivery in minutes).\n* Keep messages concise without unnecessary fluff.\n* Use tech emojis occasionally (e.g., 💻, 🎮, ⚡)."
    ),
    "Home & lifestyle products": (
        "You are a helpful Home & Lifestyle consultant.\n"
        "Your personality:\n* Practical\n* Warm\n* Descriptive\n\n"
    )
}

# Few Shot Library
FEW_SHOTS_LIBRARY = {
    "Fashion & clothing": [
        {"role": "user", "parts": ["နွေရာသီဝတ်ဖို့ ဘာလေးတွေကောင်းမလဲ"]},
        {"role": "model", "parts": ["နွေရာသီအတွက်ဆိုရင်တော့ ပေါ့ပေါ့ပါးပါး Floral ရိုက်ထားတဲ့ Summer Dress လေးတွေက အဆင်ပြေဆုံးပါပဲရှင့် 👗 ပူအိုက်သက်သာပြီး ကြည့်ကောင်းတဲ့ ဒီဇိုင်းလေးတွေပါ။ ဘယ်အရောင်လေး ကြိုက်လဲ ပြောပြပေးပါရှင့် ✨"]}
    ],
    "Digital products & services": [
        {"role": "user", "parts": ["Spotify ဖွင့်ချင်လို့ ဘယ်လောက်ကြာမလဲ"]},
        {"role": "model", "parts": ["Spotify Premium ကို ငွေလွှဲဝင်တာနဲ့ ၅ မိနစ်အတွင်း အကောင့်ဖွင့်ပေးပါတယ်ခင်ဗျာ ⚡ 1 Month အတွက် 3000 ကျပ် ကျသင့်မှာဖြစ်ပြီး မိမိပိုင် Email နဲ့ပဲ ဖွင့်ပေးမှာပါခင်ဗျာ။ ယူမယ်ဆိုရင် kpay အကောင့်နံပါတ် ပို့ပေးပါမယ်။ 💻"]}
    ]
}

def map_axes_to_rules(axes: dict) -> str:
    rules = []
    # Perishability
    if axes.get("perishability") == "Perishable":
        rules.append("* Prioritize fast delivery and check freshness requirements.")
    elif axes.get("perishability") == "Non-Perishable":
        rules.append("* Items are shelf-stable, standard shipping applies.")

    # Customization
    if axes.get("customization") == "Made-to-Order":
        rules.append("* Urgently ask for modifiers (e.g., sugar, ice, toppings/customizations).")

    # Risk
    if axes.get("risk") in ["High-Value/Technical", "High-Variance"]:
        rules.append("* Prioritize size/spec verification, compatibility checks, and authentic product/warranty reassurances.")

    # Logistics
    logistics = axes.get("logistics")
    if logistics == "Instant/Digital":
        rules.append("* Eliminate small talk, strictly validate credentials, and route immediately to local digital payment integrations (KBZPay/WaveMoney).")
    elif logistics == "Hyperlocal Express":
        rules.append("* Push for hyperlocal express delivery (Grab/Rider).")

    return "\n".join(rules) if rules else ""

def compile_bot_state(bot_token: str, config: dict):
    category = config.get("category", "")
    persona_name = config.get("persona_name", "Assistant")
    axes = config.get("axes", {})
    
    # 1. Specific Prompt (Category)
    specific_prompt = CATEGORY_PROMPTS.get(category, f"You are a helpful assistant for {category}.")
    
    # 2. Specific Rules (Axes)
    axes_rules = map_axes_to_rules(axes)
    
    # Construction
    final_rules = f"{specific_prompt}\n"
    if axes_rules:
        final_rules += f"Operational Rules based on category axes:\n{axes_rules}\n"
    
    # Add ending rule based on persona
    if category == "Fashion & clothing":
        final_rules += "CRITICAL: End sentences politely with 'ပါရှင့်'.\n"
    elif category == "Digital products & services":
        final_rules += "CRITICAL: End sentences politely with 'ခင်ဗျာ' or 'ပါ'.\n"
    else:
        final_rules += "CRITICAL: Always end sentences politely with 'ပါရှင့်' or 'ခင်ဗျာ'.\n"

    # 3. Few-Shots
    few_shots = FEW_SHOTS_LIBRARY.get(category, [])
    
    # Return dictionary to avoid circular import with bot_store
    return {
        "bot_token": bot_token,
        "persona_name": persona_name,
        "specific_rules": final_rules.strip(),
        "dynamic_state": config.get("dynamic_state", {}),
        "specific_few_shots": few_shots,
        "products": config.get("products", []),
        "delivery_zones": config.get("delivery_zones", [])
    }
