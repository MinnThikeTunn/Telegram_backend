import logging
import os
from dataclasses import dataclass, field
from typing import Dict, Any

import google.generativeai as genai
from google.generativeai import ChatSession

logger = logging.getLogger(__name__)

# Configure API Key safely
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY is not set. AI responses will fail.")

@dataclass(frozen=True)
class SmeConfig:
    """Immutable domain model for an SME's AI persona configuration."""
    bot_token: str
    persona_name: str
    system_prompt: str
    inventory: Dict[str, Any] = field(default_factory=dict)

# In-memory session store (MVP guardrail: No Redis needed)
# Key: (bot_token, user_id) -> Value: ChatSession
_chat_sessions: Dict[tuple[str, str], ChatSession] = {}

# In-memory SME configurations mapping
_sme_configs: Dict[str, SmeConfig] = {}

def register_sme_config(config: SmeConfig) -> None:
    """Register a bot's specific SME configuration."""
    _sme_configs[config.bot_token] = config

def _get_sme_config(bot_token: str) -> SmeConfig:
    """Retrieve SME config or default to a generic polite assistant."""
    if bot_token in _sme_configs:
        return _sme_configs[bot_token]
    
    # Fallback default configuration
    return SmeConfig(
        bot_token=bot_token,
        persona_name="Ma Thida",
        system_prompt=(
            "You are 'Ma Thida', a highly professional, warm, and exceptionally polite digital sales assistant. "
            "CRITICAL: Always end sentences with respectful particles like 'ပါရှင့်' (par shint) or 'ပါခင်ဗျာ' (par khin byar) appropriately. "
            "Be brief, friendly, and helpful. Guide users politely."
        ),
        inventory={"Smart Jacket": "Available in Black and Navy", "Shoes": "Out of Stock"}
    )

async def generate_chat_response(bot_token: str, user_id: str, user_message: str) -> str:
    """Process a user message and return the AI's response properly scoped to the bot context."""
    config = _get_sme_config(bot_token)
    session_key = (bot_token, str(user_id))
    
    try:
        # Initialize an isolated chat session for this specific bot and user
        if session_key not in _chat_sessions:
            logger.debug("creating new chat session for user_id=%s, bot_token=...%s", user_id, bot_token[-6:])
            
            # Combine core identity with dynamic knowledge grounding
            full_instruction = f"{config.system_prompt}\n\n[Current Inventory Status]\n{config.inventory}"
            
            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                system_instruction=full_instruction
            )
            # The start_chat method intrinsically holds conversational memory
            _chat_sessions[session_key] = model.start_chat()
            
        chat = _chat_sessions[session_key]
        
        logger.info("AI Chat Input - user_id=%s, message='%s'", user_id, user_message)
        # Non-blocking I/O call
        response = await chat.send_message_async(user_message)
        logger.info("AI Chat Output - user_id=%s, response='%s'", user_id, response.text)
        return response.text
        
    except Exception as err:
        # Chain exceptions logically or fallback gracefully
        logger.error("Failed to generate AI response: %s", err, exc_info=True)
        return "စနစ်ချိုယွင်းမှုဖြစ်ပေါ်နေပါသည်ရှင့်။ ခဏနေမှ ထပ်မံကြိုးစားပေးပါရှင့်။ (System error, please try again later.)"
