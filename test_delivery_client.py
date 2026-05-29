"""
Unit tests for the delivery_client module.

Tests the caching, fallback, and pagination behavior of the fetch_all_zones function.
"""

import pytest
import time
from unittest.mock import patch, AsyncMock, MagicMock
from api import delivery_client


class TestDeliveryClient:
    """Test suite for the delivery_client module."""

    @pytest.fixture(autouse=True)
    def reset_cache(self):
        """Reset the in-memory cache before each test."""
        delivery_client._cache = []
        delivery_client._cache_timestamp = 0.0
        yield
        # Clean up after test
        delivery_client._cache = []
        delivery_client._cache_timestamp = 0.0

    @pytest.mark.asyncio
    async def test_fetch_all_zones_returns_cached_data_within_ttl(self):
        """Test that cached data is returned when within TTL."""
        # Pre-populate cache
        test_zones = [
            {"township_name": "Yangon", "rate": 1000, "estimated_transit_timeline": "1 day"},
            {"township_name": "Mandalay", "rate": 2000, "estimated_transit_timeline": "2 days"},
        ]
        delivery_client._cache = test_zones
        delivery_client._cache_timestamp = time.time()

        result = await delivery_client.fetch_all_zones()

        assert result == test_zones
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_fetch_all_zones_refetches_on_cache_miss(self):
        """Test that data is refetched when cache is empty."""
        fallback_zones = [
            {"township_name": "TestTownship", "rate": 500, "estimated_transit_timeline": "1-2 days"}
        ]

        # Mock httpx to return API data
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"township_name": "API Zone 1", "rate": 1000, "estimated_transit_timeline": "1 day"},
                {"township_name": "API Zone 2", "rate": 1500, "estimated_transit_timeline": "2 days"},
            ],
            "pagination": {"has_next": False, "current_page": 1}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("api.delivery_client.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client

            result = await delivery_client.fetch_all_zones(fallback_zones=fallback_zones)

            # Should return API data, not fallback
            assert len(result) == 2
            assert result[0]["township_name"] == "API Zone 1"

    @pytest.mark.asyncio
    async def test_fetch_all_zones_fallback_on_api_failure(self):
        """Test that fallback zones are returned when API call fails."""
        fallback_zones = [
            {"township_name": "Fallback Township", "rate": 1000, "estimated_transit_timeline": "1 day"}
        ]

        with patch("api.delivery_client.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("Connection failed"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client

            result = await delivery_client.fetch_all_zones(fallback_zones=fallback_zones)

            # Should return fallback
            assert result == fallback_zones
            assert len(result) == 1
            assert result[0]["township_name"] == "Fallback Township"

    @pytest.mark.asyncio
    async def test_fetch_all_zones_uses_stale_cache_on_failure(self):
        """Test that stale cache is used when both API and fallback fail."""
        # Pre-populate cache with stale data
        stale_zones = [
            {"township_name": "Stale Zone", "rate": 500, "estimated_transit_timeline": "old timeline"}
        ]
        delivery_client._cache = stale_zones
        delivery_client._cache_timestamp = time.time() - 1000  # Old timestamp

        with patch("api.delivery_client.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("Connection failed"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client

            # No fallback provided
            result = await delivery_client.fetch_all_zones()

            # Should return stale cache as last resort
            assert result == stale_zones

    @pytest.mark.asyncio
    async def test_fetch_all_zones_paginates_correctly(self):
        """Test that multi-page pagination works correctly."""
        # Simulate 2 pages of results
        page_1_response = MagicMock()
        page_1_response.json.return_value = {
            "data": [
                {"township_name": "Zone 1", "rate": 1000, "estimated_transit_timeline": "1 day"},
            ],
            "pagination": {"has_next": True, "current_page": 1}
        }
        page_1_response.raise_for_status = MagicMock()

        page_2_response = MagicMock()
        page_2_response.json.return_value = {
            "data": [
                {"township_name": "Zone 2", "rate": 2000, "estimated_transit_timeline": "2 days"},
            ],
            "pagination": {"has_next": False, "current_page": 2}
        }
        page_2_response.raise_for_status = MagicMock()

        with patch("api.delivery_client.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=[page_1_response, page_2_response])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client

            result = await delivery_client.fetch_all_zones()

            # Should aggregate both pages
            assert len(result) == 2
            assert result[0]["township_name"] == "Zone 1"
            assert result[1]["township_name"] == "Zone 2"

    def test_invalidate_cache(self):
        """Test that cache invalidation clears the cache."""
        delivery_client._cache = [{"township_name": "Test", "rate": 100}]
        delivery_client._cache_timestamp = time.time()

        delivery_client.invalidate_cache()

        assert delivery_client._cache == []
        assert delivery_client._cache_timestamp == 0.0

    @pytest.mark.asyncio
    async def test_fetch_single_zone_hits_cache_if_fresh(self):
        """Test that fetch_single_zone returns cached zone when cache is fresh."""
        test_zones = [
            {"township_name": "Kamayut", "rate": 1500, "estimated_transit_timeline": "1 day"}
        ]
        delivery_client._cache = test_zones
        delivery_client._cache_timestamp = time.time()

        result = await delivery_client.fetch_single_zone("Kamayut")
        assert result == test_zones[0]

    @pytest.mark.asyncio
    async def test_fetch_single_zone_calls_api_on_cache_miss(self):
        """Test that fetch_single_zone queries API with search query on cache miss."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"township_name": "Kamayut", "rate": 3000, "estimated_transit_timeline": "1-2 Days"}
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("api.delivery_client.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client

            result = await delivery_client.fetch_single_zone("Kamayut")

            assert result is not None
            assert result["township_name"] == "Kamayut"
            assert result["rate"] == 3000
            mock_client.get.assert_called_once_with(
                "http://localhost:8000/api/v1/delivery-matrix",
                params={"search": "Kamayut", "limit": 1}
            )

    @pytest.mark.asyncio
    async def test_fetch_single_zone_uses_fallback_on_failure(self):
        """Test that fetch_single_zone searches fallback_zones when API fails."""
        fallback_zones = [
            {"township_name": "Latha", "rate": 2000, "estimated_transit_timeline": "2 Days"}
        ]

        with patch("api.delivery_client.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("API offline"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client

            result = await delivery_client.fetch_single_zone("Latha", fallback_zones=fallback_zones)

            assert result == fallback_zones[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])