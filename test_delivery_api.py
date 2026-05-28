import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

# Configure isolated test cache file to avoid mutating production delivery cache
import api.delivery_service
api.delivery_service.CACHE_FILE = os.path.join(os.path.dirname(__file__), "test_delivery_matrix_cache.json")
if os.path.exists(api.delivery_service.CACHE_FILE):
    try:
        os.remove(api.delivery_service.CACHE_FILE)
    except Exception:
        pass

# Clear cache loaded into memory
api.delivery_service.delivery_service.cache = {}
api.delivery_service.delivery_service.file_path = api.delivery_service.CACHE_FILE

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_delivery_matrix_pagination_and_defaults():
    """Test default pagination behavior (page=1, limit=10)."""
    response = client.get("/api/v1/delivery-matrix")
    assert response.status_code == 200
    
    json_data = response.json()
    assert "data" in json_data
    assert "pagination" in json_data
    
    # Defaults check
    pagination = json_data["pagination"]
    assert pagination["current_page"] == 1
    assert pagination["limit"] == 10
    
    # We should have exactly 10 items in the response
    assert len(json_data["data"]) == 10
    
    # Total records should be > 10 (12 mock + 400+ CSV records)
    assert pagination["total_records"] > 10
    assert pagination["total_pages"] > 1
    assert pagination["has_next"] is True
    assert pagination["has_prev"] is False

def test_delivery_matrix_custom_limit_and_page():
    """Test custom limit and page parameters."""
    # Fetch page 2 with limit 5
    response = client.get("/api/v1/delivery-matrix?page=2&limit=5")
    assert response.status_code == 200
    
    json_data = response.json()
    pagination = json_data["pagination"]
    assert pagination["current_page"] == 2
    assert pagination["limit"] == 5
    assert len(json_data["data"]) == 5

def test_delivery_matrix_search():
    """Test case-insensitive substring searching."""
    # Search for "Kamayut"
    response = client.get("/api/v1/delivery-matrix?search=Kamayut")
    assert response.status_code == 200
    
    json_data = response.json()
    assert len(json_data["data"]) >= 1
    assert json_data["data"][0]["township_name"] == "Kamayut"
    
    # Search for "sanchaung" lowercase
    response = client.get("/api/v1/delivery-matrix?search=sanchaung")
    assert response.status_code == 200
    json_data = response.json()
    assert len(json_data["data"]) >= 1
    assert json_data["data"][0]["township_name"] == "Sanchaung"

def test_delivery_matrix_rate_calculation_fallback():
    """Test the correctness of rates and timelines (using python fallback validation)."""
    # Latha (Downtown) -> 2000, 1 Day
    response = client.get("/api/v1/delivery-matrix?search=Latha (Downtown)")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) >= 1
    assert data[0]["rate"] == 2000
    assert data[0]["estimated_transit_timeline"] == "1 Day"

    # Bahan -> 2500, 1-2 Days
    response = client.get("/api/v1/delivery-matrix?search=Bahan")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) >= 1
    assert data[0]["rate"] == 2500
    assert data[0]["estimated_transit_timeline"] == "1-2 Days"

    # Hlaing -> 3000, 1-2 Days
    response = client.get("/api/v1/delivery-matrix?search=Hlaing")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) >= 1
    assert data[0]["rate"] == 3000
    assert data[0]["estimated_transit_timeline"] == "1-2 Days"

    # Mayangone -> 3500, 2 Days
    response = client.get("/api/v1/delivery-matrix?search=Mayangone")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) >= 1
    assert data[0]["rate"] == 3500
    assert data[0]["estimated_transit_timeline"] == "2 Days"

    # Non-specific fallback -> 4500, 2-3 Days
    response = client.get("/api/v1/delivery-matrix?search=Gangaw")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) >= 1
    # Check fallback value
    assert data[0]["rate"] == 4500
    assert data[0]["estimated_transit_timeline"] == "2-3 Days"

@pytest.mark.asyncio
async def test_ai_calculation_service():
    """Verify delivery service calculation and mock AI response."""
    from api.delivery_service import delivery_service
    
    # We mock Gemini Model generate_content_async to simulate a successful AI call
    with patch("api.delivery_service.genai.GenerativeModel") as MockModel, \
         patch("api.delivery_service.os.getenv") as mock_env:
        
        # Simulate API Key and configured state
        mock_env.side_effect = lambda key, default="": "AIzaMockKey" if key == "GEMINI_API_KEY" else default
        
        mock_model_instance = MockModel.return_value
        mock_response = MagicMock()
        mock_response.text = '{"rate": 8000, "estimated_transit_timeline": "3-4 Days"}'
        mock_model_instance.generate_content_async = AsyncMock(return_value=mock_response)
        
        # Force cache clear for testing AI call
        test_key = "gangaw|magway region|gangaw"
        if test_key in delivery_service.cache:
            del delivery_service.cache[test_key]
            
        result = await delivery_service.calculate_rate_and_timeline("Gangaw", "Magway Region", "Gangaw")
        
        # Verify custom calculated AI rates were fetched and parsed
        assert result["rate"] == 8000
        assert result["estimated_transit_timeline"] == "3-4 Days"
        
        # Clean up cache
        if test_key in delivery_service.cache:
            del delivery_service.cache[test_key]
            delivery_service.save_cache()
