import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List

import google.generativeai as genai
from google.generativeai import ChatSession

logger = logging.getLogger(__name__)

# =============================================================================
# Security Fix #1: Secret Handling - Validate and safely handle API key
# =============================================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
_is_configured = False

def _validate_api_key(key: str) -> bool:
    """Validate Gemini API key format (must start with AIza)."""
    if not key:
        return False
    # Gemini API keys typically start with "AIza" followed by alphanumeric chars
    return bool(re.match(r'^AIza[0-9A-Za-z_-]{35,}$', key))

if GEMINI_API_KEY:
    if _validate_api_key(GEMINI_API_KEY):
        genai.configure(api_key=GEMINI_API_KEY)
        _is_configured = True
        logger.info("Gemini API configured successfully")
    else:
        logger.warning("GEMINI_API_KEY format is invalid. AI responses will fail.")
else:
    logger.warning("GEMINI_API_KEY is not set. AI responses will fail.")


@dataclass(frozen=True)
class SmeConfig:
    """Immutable domain model for an SME's AI persona configuration."""
    bot_token: str
    persona_name: str
    system_prompt: str
    inventory: Dict[str, Any] = field(default_factory=dict)
    few_shot_examples: List[Dict[str, Any]] = field(default_factory=list)

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
        inventory={"Smart Jacket": "Available in Black and Navy", "Shoes": "Out of Stock"},
        few_shot_examples=[
            {
                "role": "user",
                "parts": ["အကျီ င်္ က အရောင် ဘာရှိလဲ"]
            },
            {
                "role": "model",
                "parts": ["ဟုတ်ကဲ့ပါရှင့်၊ အခုပြထားတဲ့ အကျီ င်္လေးက အနီရောင်နဲ့ အပြာရောင် နှစ်မျိုးလုံး အဆင်သင့်ရှိပါတယ်ရှင့်။ အစ်ကို/အစ်မ အတွက် ဘယ်ဆိုဒ်လေး ကြည့်ပေးရမလဲ ရှင့်?"]
            }
        ]
    )


# =============================================================================
# Security Fix #2: Input Sanitization - Prevent prompt injection
# =============================================================================
def _sanitize_user_input(user_message: str) -> str:
    """Sanitize user input to prevent prompt injection attacks."""
    if not user_message:
        return ""
    
    # Strip leading/trailing whitespace
    sanitized = user_message.strip()
    
    # Common prompt injection patterns to block
    injection_patterns = [
        r'^ignore\s+previous\s+instructions',
        r'^ignore\s+all\s+previous\s+instructions',
        r'^disregard\s+.*instructions',
        r'^forget\s+.*instructions',
        r'^you\s+are\s+now\s+',
        r'^system:\s*',
        r'^assistant:\s*',
        r'^respond\s+as\s+if\s+you\s+are',
        r'^pretend\s+to\s+be',
        r'^new\s+instruction',
        r'^override\s+',
    ]
    
    # Check for injection attempts and reject with safe fallback
    for pattern in injection_patterns:
        if re.search(pattern, sanitized, re.IGNORECASE):
            logger.warning("Blocked potential prompt injection from user")
            return "[Message blocked for safety - please rephrase your request]"
    
    # Limit message length to prevent resource abuse
    max_length = 2000
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    
    return sanitized


async def generate_chat_response(bot_token: str, user_id: str, user_message: str) -> str:
    """Process a user message and return the AI's response properly scoped to the bot context."""
    # Security Check: Validate API is configured
    if not _is_configured:
        logger.error("Gemini API key not configured")
        return "စနစ်ချိုယွင်းမှုဖြစ်ပေါ်နေပါသည်ရှင့်။ ခဏနေမှ ထပ်မံကြိုးစားပေးပါရှင့်။ (System error, please try again later.)"
    
    config = _get_sme_config(bot_token)
    session_key = (bot_token, str(user_id))
    
    # Security Fix #2: Sanitize user input before sending to AI
    sanitized_message = _sanitize_user_input(user_message)
    if not sanitized_message or sanitized_message.startswith("[Message blocked"):
        return "သတင်းစာကို လက်ခံမပါသည်ရှင့်။ နောက်တစ်ကြိမ်ထပ်မံကြိုးစားပေးပါရှင့်။ (Message not accepted, please try again.)"
    
    try:
        # Initialize an isolated chat session for this specific bot and user
        if session_key not in _chat_sessions:
            logger.debug("Creating new chat session for user_id=%s, bot_token=...%s", user_id, bot_token[-6:])
            
            # Combine core identity with dynamic knowledge grounding
            full_instruction = f"{config.system_prompt}\n\n[Current Inventory Status]\n{config.inventory}"
            
            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                system_instruction=full_instruction
            )
            # The start_chat method intrinsically holds conversational memory
            # history parameter allows pre-loading few-shot examples or session state
            _chat_sessions[session_key] = model.start_chat(history=config.few_shot_examples)
            
        chat = _chat_sessions[session_key]
        
        # Log with masking - never log actual user message content in production
        logger.info("AI Chat Input - user_id=%s, message_len=%d", user_id, len(sanitized_message))
        
        # Non-blocking I/O call
        response = await chat.send_message_async(sanitized_message)
        
        # Log with masking - never log AI response content in production  
        logger.info("AI Chat Output - user_id=%s, response_len=%d", user_id, len(response.text))
        return response.text
        
    except Exception as err:
        # Never expose API key or internal details in error messages
        logger.error("Failed to generate AI response: %s", type(err).__name__, exc_info=True)
        return "စနစ်ချိုယွင်းမှုဖြစ်ပေါ်နေပါသည်ရှင့်။ ခဏနေမှ ထပ်မံကြိုးစားပေးပါရှင့်။ (System error, please try again later.)"