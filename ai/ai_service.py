import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List

import google.generativeai as genai
from google.generativeai import ChatSession

from bot_store import store, GENERAL_BASE_RULES
from ai.user_store import user_store

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


# In-memory session store (MVP guardrail: No Redis needed)
# Key: (bot_token, user_id) -> Value: ChatSession
_chat_sessions: Dict[tuple[str, str], ChatSession] = {}


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
    
    bot_state = store.get_state(bot_token)
    session_key = (bot_token, str(user_id))
    
    # Security Fix #2: Sanitize user input before sending to AI
    sanitized_message = _sanitize_user_input(user_message)
    if not sanitized_message or sanitized_message.startswith("[Message blocked"):
        return "သတင်းစာကို လက်ခံမပါသည်ရှင့်။ နောက်တစ်ကြိမ်ထပ်မံကြိုးစားပေးပါရှင့်။ (Message not accepted, please try again.)"
    
    try:
        # Initialize an isolated chat session for this specific bot and user
        if session_key not in _chat_sessions:
            logger.debug("Creating new chat session for user_id=%s, bot_token=...%s", user_id, bot_token[-6:])
            
            # Combine Global Rules with core identity, specific rules and dynamic knowledge grounding
            full_instruction = f"{GENERAL_BASE_RULES}\n\n[Bot Specific Rules]\n{bot_state.specific_rules}\n\n[Current Dynamic State/Inventory]\n{bot_state.dynamic_state}"
            
            tool_schema = {
                "function_declarations": [
                    {
                        "name": "update_user_preferences",
                        "description": "Log what new things the customer explicitly likes or dislikes based on the conversation.",
                        "parameters": {
                            "type_": "OBJECT",
                            "properties": {
                                "new_likes": {
                                    "type_": "ARRAY",
                                    "items": {"type_": "STRING"},
                                    "description": "List of new items, product categories or colors the user likes."
                                },
                                "new_dislikes": {
                                    "type_": "ARRAY",
                                    "items": {"type_": "STRING"},
                                    "description": "List of new items, product categories or colors the user dislikes."
                                }
                            }
                        }
                    }
                ]
            }

            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                system_instruction=full_instruction,
                tools=[tool_schema]
            )
            # The start_chat method intrinsically holds conversational memory
            # history parameter allows pre-loading few-shot examples or session state
            _chat_sessions[session_key] = model.start_chat(history=bot_state.specific_few_shots)
            
        chat = _chat_sessions[session_key]
        
        # Inject user profile context into the current message invisibly
        user_profile = user_store.get_profile(user_id)
        internal_context = (
            f"[Internal System Note - Customer Analytics Profile]\n"
            f"- Known Likes: {', '.join(user_profile.likes) if user_profile.likes else 'None yet'}\n"
            f"- Known Dislikes: {', '.join(user_profile.dislikes) if user_profile.dislikes else 'None yet'}\n"
            f"- Successful Past Orders count: {len(user_profile.order_history)}\n"
            f"Please subtly personalize your tone and recommendation based on this context.\n\n"
        )
        enriched_message = f"{internal_context}User says: {sanitized_message}"
        
        # Log with masking - never log actual user message content in production
        logger.info("AI Chat Input - user_id=%s, message_len=%d", user_id, len(sanitized_message))
        
        # Non-blocking I/O call
        response = await chat.send_message_async(enriched_message)
        
        # Handle function calls if the logic emitted updates
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if getattr(part, "function_call", None) and part.function_call.name == "update_user_preferences":
                    args = part.function_call.args
                    # The args usually come as protobuf MapComposite, wrapping to standard dict via type casting if needed
                    likes = list(args.get("new_likes", [])) if "new_likes" in args else []
                    dislikes = list(args.get("new_dislikes", [])) if "new_dislikes" in args else []
                    
                    # Update local json
                    user_store.update_preferences(user_id, likes, dislikes)
                    logger.info("Executed update_user_preferences tool for user %s", user_id)
                    
                    # Send tool execution result back to the model so it can formulate the final text reply
                    response = await chat.send_message_async(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name="update_user_preferences",
                                response={"status": "Updated user database successfully."}
                            )
                        )
                    )
                    break
        
        # Log with masking - never log AI response content in production  
        logger.info("AI Chat Output - user_id=%s, response_len=%d", user_id, len(response.text))
        return response.text
        
    except Exception as err:
        # Never expose API key or internal details in error messages
        logger.error("Failed to generate AI response: %s", type(err).__name__, exc_info=True)
        return "စနစ်ချိုယွင်းမှုဖြစ်ပေါ်နေပါသည်ရှင့်။ ခဏနေမှ ထပ်မံကြိုးစားပေးပါရှင့်။ (System error, please try again later.)"