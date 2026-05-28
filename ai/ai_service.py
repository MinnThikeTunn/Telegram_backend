import logging
import os
import re
import time
import asyncio
from types import SimpleNamespace
from dataclasses import dataclass, field
from typing import Dict, Any, List
from collections import deque

try:
    from dotenv import load_dotenv
    load_dotenv(".env.local")
    load_dotenv()
except ImportError:
    pass

try:
    import google.generativeai as genai
    from google.generativeai import ChatSession
except Exception:  # pragma: no cover - fallback for test environments without the Google SDK
    class _FallbackPart:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    class _FallbackFunctionResponse:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    genai = SimpleNamespace(
        configure=lambda **kwargs: None,
        GenerativeModel=None,
        protos=SimpleNamespace(Part=_FallbackPart, FunctionResponse=_FallbackFunctionResponse),
    )
    ChatSession = object

try:
    from google.api_core.exceptions import ResourceExhausted
except Exception:  # pragma: no cover - fallback for environments without google.api_core
    class ResourceExhausted(Exception):
        pass

from bot_store import store, GENERAL_BASE_RULES
from ai.user_store import user_store

logger = logging.getLogger(__name__)

# =============================================================================
# Security Fix #1: Secret Handling - Validate and safely handle API key
# =============================================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash").strip().lower().replace(" ", "-")
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
_quota_cooldown_until = 0.0

# =============================================================================
# Global Rate Limiter - Protect shared Gemini API quota
# =============================================================================
# Free tier: 5 requests/minute. We rate-limit to 4/min to have buffer
GLOBAL_RATE_LIMIT = 4  # Max requests per minute
_request_timestamps: deque = deque(maxlen=100)  # Store recent request times
_request_lock = asyncio.Lock()


async def _wait_for_rate_limit() -> None:
    """Wait if we're exceeding the global rate limit."""
    global _request_timestamps
    async with _request_lock:
        now = time.time()
        # Remove timestamps older than 60 seconds
        while _request_timestamps and now - _request_timestamps[0] > 60:
            _request_timestamps.popleft()
        
        # If we're at the limit, wait until oldest request expires
        if len(_request_timestamps) >= GLOBAL_RATE_LIMIT:
            wait_time = 60 - (now - _request_timestamps[0]) + 0.5
            logger.warning("Global rate limit reached, waiting %.1fs", wait_time)
            await asyncio.sleep(wait_time)
            now = time.time()
            while _request_timestamps and now - _request_timestamps[0] > 60:
                _request_timestamps.popleft()
        
        # Add current timestamp
        _request_timestamps.append(now)


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
    global _quota_cooldown_until

    # Security Check: Validate API is configured
    if not _is_configured:
        logger.error("Gemini API key not configured")
        return "စနစ်ချိုယွင်းမှုဖြစ်ပေါ်နေပါသည်ရှင့်။ ခဏနေမှ ထပ်မံကြိုးစားပေးပါရှင့်။ (System error, please try again later.)"

    if time.time() < _quota_cooldown_until:
        logger.warning("Gemini quota cooldown active; returning fallback response without API call")
        return "လက်ရှိ AI စနစ်မှာ request အရေအတွက်ကန့်သတ်ချက် မပြည့်မီသေးပါရှင့်။ ခဏနေမှ ထပ်မံကြိုးစားပေးပါရှင့်။"
    
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
            
            # Format product inventory for the prompt
            products_context = "INVENTORY:\n"
            for p in bot_state.products:
                products_context += f"- [ID: {p['id']}] {p['name']} | Price: {p['price']} MMK | Info: {p['description']}\n"

            # Fetch live delivery zones from the Delivery Matrix API
            # Use static fallback immediately without API call for fast response
            _static_fallback = [
                {"township_name": z["township"], "rate": z["rate"],
                 "estimated_transit_timeline": z.get("deliveryTime", "N/A")}
                for z in bot_state.delivery_zones
            ]
            
            # Try to fetch live zones with short timeout - fall back to static if slow
            try:
                import asyncio
                from api.delivery_client import fetch_all_zones
                all_zones = await asyncio.wait_for(
                    fetch_all_zones(fallback_zones=_static_fallback),
                    timeout=3.0  # Max 3 seconds wait for API
                )
            except (asyncio.TimeoutError, Exception) as _fetch_err:
                logger.warning("Delivery zone fetch failed: %s. Using static fallback.", _fetch_err)
                all_zones = _static_fallback

            delivery_context = "DELIVERY TOWNSHIPS:\n"
            display_zones = all_zones[:20]
            for z in display_zones:
                township = z.get("township_name", "Unknown")
                rate = z.get("rate", 0)
                timeline = z.get("estimated_transit_timeline", "N/A")
                delivery_context += f"- {township}: {rate:,} MMK (Time: {timeline})\n"
            if len(all_zones) > 20:
                delivery_context += (
                    f"... and {len(all_zones) - 20} more townships available. "
                    f"Ask the customer for their township name to look up the exact rate.\n"
                )

            # Combine Global Rules with core identity, specific rules and dynamic knowledge grounding
            full_instruction = (
                f"{GENERAL_BASE_RULES}\n\n"
                f"[Bot Specific Rules]\n{bot_state.specific_rules}\n\n"
                f"[Product Context]\n{products_context}\n"
                f"[Delivery Context]\n{delivery_context}\n"
                f"[Current Dynamic State]\n{bot_state.dynamic_state}"
            )
            
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
                model_name=GEMINI_MODEL_NAME,
                system_instruction=full_instruction,
                tools=[tool_schema]
            )
            # The start_chat method intrinsically holds conversational memory
            # history parameter allows pre-loading few-shot examples or session state
            _chat_sessions[session_key] = model.start_chat(history=bot_state.specific_few_shots)
            
        chat = _chat_sessions[session_key]
        
        # Inject user profile context into the current message invisibly
        user_profile = user_store.get_profile(user_id)

        # Format current cart for AI context
        cart_summary = "Empty"
        if user_profile.cart:
            cart_summary = ", ".join([f"{item['name']} x{item['quantity']}" for item in user_profile.cart])

        internal_context = (
            f"[Internal System Note - Customer Analytics Profile]\n"
            f"- Current Cart: {cart_summary}\n"
            f"- Current Step: {user_profile.current_step}\n"
            f"- Known Likes: {', '.join(user_profile.likes) if user_profile.likes else 'None yet'}\n"
            f"- Known Dislikes: {', '.join(user_profile.dislikes) if user_profile.dislikes else 'None yet'}\n"
            f"- Successful Past Orders count: {len(user_profile.order_history)}\n"
            f"Please subtly personalize your tone and recommendation based on this context. "
            f"If the user wants to buy something, guide them to use the interactive 'Add to Cart' buttons or acknowledge their choice.\n\n"
        )
        enriched_message = f"{internal_context}User says: {sanitized_message}"
        
        # Log with masking - never log actual user message content in production
        logger.info("AI Chat Input - user_id=%s, message_len=%d", user_id, len(sanitized_message))
        
        # Apply global rate limit before making API call (protect shared quota)
        await _wait_for_rate_limit()
        
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
        
    except ResourceExhausted as err:
        retry_delay = 60
        match = re.search(r"Please retry in ([0-9.]+)s", str(err))
        if match:
            try:
                retry_delay = max(1, int(float(match.group(1))))
            except ValueError:
                retry_delay = 60
        _quota_cooldown_until = time.time() + retry_delay
        logger.warning("Gemini quota exhausted; cooling down for %ss", retry_delay, exc_info=True)
        return "လက်ရှိ AI request quota ကျပ်တည်းနေပါသည်ရှင့်။ ခဏအကြာမှ ထပ်မံကြိုးစားပေးပါရှင့်။"
    except Exception as err:
        # Never expose API key or internal details in error messages
        logger.error("Failed to generate AI response: %s", type(err).__name__, exc_info=True)
        return "စနစ်ချိုယွင်းမှုဖြစ်ပေါ်နေပါသည်ရှင့်။ ခဏနေမှ ထပ်မံကြိုးစားပေးပါရှင့်။ (System error, please try again later.)"
