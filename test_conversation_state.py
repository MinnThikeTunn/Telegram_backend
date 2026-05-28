import pytest
from bot_state.conversation_state import ConversationState, Signal, get_next_state

@pytest.mark.parametrize(
    "current,signal,expected",
    [
        (ConversationState.INTRODUCTION, None, ConversationState.INTENT_CLASSIFICATION),
        (ConversationState.INTRODUCTION, Signal.EXPLORING, ConversationState.ADVERTISE),
        (ConversationState.INTRODUCTION, Signal.SPECIFIC_REQUEST, ConversationState.SHOW_PRODUCT),
        (ConversationState.INTENT_CLASSIFICATION, Signal.EXPLORING, ConversationState.ADVERTISE),
        (ConversationState.INTENT_CLASSIFICATION, Signal.SPECIFIC_REQUEST, ConversationState.SHOW_PRODUCT),
        (ConversationState.ADVERTISE, Signal.VIEW_PRODUCT, ConversationState.SHOW_PRODUCT),
        (ConversationState.SHOW_PRODUCT, Signal.WANTS_TO_BUY, ConversationState.STOCK_CHECK),
        (ConversationState.SHOW_PRODUCT, Signal.NOT_BUYING, ConversationState.TERMINATE_WARM),
        (ConversationState.STOCK_CHECK, Signal.IN_STOCK, ConversationState.TRANSACTION),
        (ConversationState.STOCK_CHECK, Signal.OUT_OF_STOCK, ConversationState.TERMINATE_NOTIFY),
        (ConversationState.TERMINATE_WARM, Signal.RESTART, ConversationState.INTRODUCTION),
        (ConversationState.TERMINATE_NOTIFY, Signal.RESTART, ConversationState.INTRODUCTION),
    ]
)
def test_state_transitions(current, signal, expected):
    assert get_next_state(current, signal) == expected
