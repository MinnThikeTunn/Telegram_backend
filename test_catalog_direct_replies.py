from core_logic import _answer_catalog_question
import core_logic
from ai.user_store import user_store


def test_cheapest_question_returns_cheapest_product(monkeypatch):
    monkeypatch.setattr(user_store, "save", lambda: None)
    user_id = "catalog-test-cheapest"
    user_store.profiles.pop(user_id, None)

    response = _answer_catalog_question(user_id, "ဈေးအပေါဆုံးက ဘာလေးဖြစ်မလဲဗျ")

    assert response is not None
    assert "Embroidered Scarf" in response["text"]
    assert "12,000 MMK" in response["text"]


def test_named_product_interest_returns_that_product(monkeypatch):
    monkeypatch.setattr(user_store, "save", lambda: None)
    user_id = "catalog-test-jacket"
    user_store.profiles.pop(user_id, None)

    response = _answer_catalog_question(user_id, "Casual street Jacket လေးသဘောကျ")

    assert response is not None
    assert "Casual Street Jacket" in response["text"]
    assert "42,000 MMK" in response["text"]
    assert user_store.get_profile(user_id).browsing_product_id == "mock-3"


def test_price_question_uses_current_product(monkeypatch):
    monkeypatch.setattr(user_store, "save", lambda: None)
    user_id = "catalog-test-price"
    user_store.profiles.pop(user_id, None)
    profile = user_store.get_profile(user_id)
    profile.browsing_product_id = "mock-1"

    response = _answer_catalog_question(user_id, "ဈေးနှုန်းကရော")

    assert response is not None
    assert "Silk Longyi (Traditional)" in response["text"]
    assert "35,000 MMK" in response["text"]


def test_view_callback_builds_product_detail_without_ai(monkeypatch):
    async def fail_if_called(*args, **kwargs):
        raise AssertionError("view callbacks should not call Gemini")

    monkeypatch.setattr(core_logic, "generate_stateful_response", fail_if_called)
    response = core_logic._build_product_detail_response("mock-2")

    assert "Modern Fitted Blouse" in response["text"]
    assert response["reply_markup"] is not None
