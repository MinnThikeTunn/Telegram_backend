"""
Conversation State Machine for the AI Sales Bot.

Defines formal states mapped from flowchart.mmd and pure-function
transition logic. States are stored per-user in UserProfile.current_step.
"""

from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ConversationState(str, Enum):
    """All possible conversation states, mapped from the flowchart."""

    INTRODUCTION = "introduction"
    """Shop intro, welcome message with rich UI."""

    INTENT_CLASSIFICATION = "intent_classification"
    """AI judges: is user exploring (no specific product) or has a specific request?"""

    ADVERTISE = "advertise"
    """User is exploring → show bestsellers, new arrivals, marketing push."""

    SHOW_PRODUCT = "show_product"
    """Show a specific product with image + follow-up sales questions."""

    WILL_IT_BUY = "will_it_buy"
    """AI detects: wants to buy, not buying, or stopped asking."""

    STOCK_CHECK = "stock_check"
    """Check if selected product is in stock."""

    TRANSACTION = "transaction"
    """Hand off to existing payment flow (COD/Prepay → Township → Order)."""

    TERMINATE_WARM = "terminate_warm"
    """Warm goodbye + follow-up question about interests."""

    TERMINATE_NOTIFY = "terminate_notify"
    """Out-of-stock → remember arrival date, promise to notify."""

    BROWSING = "browsing"
    """Legacy/default state — user is casually browsing (pre-flow)."""


# ──────────────────────────────────────────────────────────────────────
# Signals emitted by AI classification or button callbacks
# ──────────────────────────────────────────────────────────────────────

class Signal(str, Enum):
    """Transition signals that drive state changes."""

    # From INTENT_CLASSIFICATION
    EXPLORING = "exploring"
    SPECIFIC_REQUEST = "specific_request"

    # From SHOW_PRODUCT / WILL_IT_BUY
    WANTS_TO_BUY = "wants_to_buy"
    NOT_BUYING = "not_buying"
    STOPPED_ASKING = "stopped_asking"
    BROWSE_MORE = "browse_more"

    # From STOCK_CHECK
    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"

    # From ADVERTISE
    VIEW_PRODUCT = "view_product"

    # From TERMINATE_NOTIFY (future: product arrived)
    PRODUCT_ARRIVED = "product_arrived"

    # Generic
    OFF_TOPIC = "off_topic"
    RESTART = "restart"


# ──────────────────────────────────────────────────────────────────────
# Transition Table
# ──────────────────────────────────────────────────────────────────────

_TRANSITIONS = {
    ConversationState.INTRODUCTION: {
        Signal.EXPLORING: ConversationState.ADVERTISE,
        Signal.SPECIFIC_REQUEST: ConversationState.SHOW_PRODUCT,
        # After intro, user responds → classify intent
        None: ConversationState.INTENT_CLASSIFICATION,
    },
    ConversationState.INTENT_CLASSIFICATION: {
        Signal.EXPLORING: ConversationState.ADVERTISE,
        Signal.SPECIFIC_REQUEST: ConversationState.SHOW_PRODUCT,
    },
    ConversationState.ADVERTISE: {
        Signal.VIEW_PRODUCT: ConversationState.SHOW_PRODUCT,
        Signal.SPECIFIC_REQUEST: ConversationState.SHOW_PRODUCT,
        Signal.STOPPED_ASKING: ConversationState.TERMINATE_WARM,
    },
    ConversationState.SHOW_PRODUCT: {
        Signal.WANTS_TO_BUY: ConversationState.STOCK_CHECK,
        Signal.NOT_BUYING: ConversationState.TERMINATE_WARM,
        Signal.STOPPED_ASKING: ConversationState.TERMINATE_WARM,
        Signal.BROWSE_MORE: ConversationState.ADVERTISE,
        Signal.SPECIFIC_REQUEST: ConversationState.SHOW_PRODUCT,  # Re-request loop
    },
    ConversationState.WILL_IT_BUY: {
        Signal.WANTS_TO_BUY: ConversationState.STOCK_CHECK,
        Signal.NOT_BUYING: ConversationState.TERMINATE_WARM,
        Signal.STOPPED_ASKING: ConversationState.TERMINATE_WARM,
    },
    ConversationState.STOCK_CHECK: {
        Signal.IN_STOCK: ConversationState.TRANSACTION,
        Signal.OUT_OF_STOCK: ConversationState.TERMINATE_NOTIFY,
    },
    ConversationState.TRANSACTION: {
        # Transaction end → back to browsing
        Signal.RESTART: ConversationState.INTRODUCTION,
    },
    ConversationState.TERMINATE_WARM: {
        Signal.RESTART: ConversationState.INTRODUCTION,
        Signal.SPECIFIC_REQUEST: ConversationState.SHOW_PRODUCT,
        Signal.EXPLORING: ConversationState.ADVERTISE,
    },
    ConversationState.TERMINATE_NOTIFY: {
        Signal.PRODUCT_ARRIVED: ConversationState.TRANSACTION,
        Signal.RESTART: ConversationState.INTRODUCTION,
        Signal.SPECIFIC_REQUEST: ConversationState.SHOW_PRODUCT,
    },
    ConversationState.BROWSING: {
        # Legacy state → treat as needing classification
        None: ConversationState.INTENT_CLASSIFICATION,
        Signal.EXPLORING: ConversationState.ADVERTISE,
        Signal.SPECIFIC_REQUEST: ConversationState.SHOW_PRODUCT,
    },
}


def get_next_state(
    current: ConversationState,
    signal: Optional[Signal],
) -> ConversationState:
    """
    Pure function: given a current state and a signal, return the next state.

    Falls back to the current state if the transition is not defined (the bot
    stays in its current state and the AI handles the message contextually).
    """
    state_transitions = _TRANSITIONS.get(current, {})
    next_state = state_transitions.get(signal)

    if next_state is None and signal is not None:
        # Try the None (default) transition for the current state
        next_state = state_transitions.get(None)

    if next_state is None:
        logger.debug(
            "No transition defined for state=%s signal=%s. Staying in current state.",
            current.value, signal.value if signal else "None",
        )
        return current

    logger.info(
        "State transition: %s --(signal: %s)--> %s",
        current.value, signal.value if signal else "default", next_state.value,
    )
    return next_state


def is_terminal(state: ConversationState) -> bool:
    """Check if the state is a terminal/end state."""
    return state in {
        ConversationState.TERMINATE_WARM,
        ConversationState.TERMINATE_NOTIFY,
    }


def parse_state(value: str) -> ConversationState:
    """Safely parse a string into a ConversationState, defaulting to BROWSING."""
    try:
        return ConversationState(value)
    except ValueError:
        logger.warning("Unknown state '%s', defaulting to BROWSING.", value)
        return ConversationState.BROWSING
