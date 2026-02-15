"""
Tests for company-level news caching:
- Cache store and retrieve via SupabaseClient
- Cache freshness/expiry logic
- Cache hit avoids GNews API call in orchestrator
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.services.supabase_client import SupabaseClient
from app.services.rad_orchestrator import RADOrchestrator


@pytest.fixture
def mock_supabase():
    """Fresh SupabaseClient in mock mode."""
    client = SupabaseClient()
    client._mock_raw_data = []
    client._mock_staging = []
    client._mock_finalize = []
    client._mock_jobs = []
    client._mock_outputs = []
    client._mock_pdfs = []
    return client


class TestNewsCacheStorage:
    """Test store_news_cache and get_cached_news on SupabaseClient."""

    def test_store_and_retrieve_news_cache(self, mock_supabase):
        """Stored news cache should be retrievable by domain."""
        payload = {
            "results": [{"title": "Test article", "url": "https://example.com"}],
            "result_count": 1,
            "themes": ["AI adoption"],
            "company_name": "Datadog",
        }
        mock_supabase.store_news_cache("datadoghq.com", payload)
        cached = mock_supabase.get_cached_news("datadoghq.com")

        assert cached is not None
        assert cached["payload"]["result_count"] == 1
        assert cached["payload"]["results"][0]["title"] == "Test article"

    def test_fresh_cache_is_returned(self, mock_supabase):
        """Cache within max_age_hours should be returned."""
        payload = {"results": [], "result_count": 0}
        mock_supabase.store_news_cache("example.com", payload)
        cached = mock_supabase.get_cached_news("example.com", max_age_hours=24)
        assert cached is not None

    def test_expired_cache_returns_none(self, mock_supabase):
        """Cache older than max_age_hours should return None."""
        payload = {"results": [], "result_count": 0}
        mock_supabase.store_news_cache("example.com", payload)

        # Manually set fetched_at to 25 hours ago
        for record in mock_supabase._mock_raw_data:
            if record.get("source") == "gnews_cache":
                old_time = (datetime.utcnow() - timedelta(hours=25)).isoformat()
                record["fetched_at"] = old_time

        cached = mock_supabase.get_cached_news("example.com", max_age_hours=24)
        assert cached is None

    def test_upsert_overwrites_existing_cache(self, mock_supabase):
        """Storing cache for same domain should overwrite old data."""
        mock_supabase.store_news_cache("example.com", {"result_count": 1})
        mock_supabase.store_news_cache("example.com", {"result_count": 5})

        cached = mock_supabase.get_cached_news("example.com")
        assert cached is not None
        assert cached["payload"]["result_count"] == 5

    def test_different_domains_cached_separately(self, mock_supabase):
        """Cache for different domains should be independent."""
        mock_supabase.store_news_cache("google.com", {"company": "Google"})
        mock_supabase.store_news_cache("microsoft.com", {"company": "Microsoft"})

        google = mock_supabase.get_cached_news("google.com")
        msft = mock_supabase.get_cached_news("microsoft.com")

        assert google["payload"]["company"] == "Google"
        assert msft["payload"]["company"] == "Microsoft"

    def test_no_cache_returns_none(self, mock_supabase):
        """Querying uncached domain returns None."""
        cached = mock_supabase.get_cached_news("never-cached.com")
        assert cached is None


class TestOrchestratorCacheIntegration:
    """Test that RADOrchestrator uses cache to avoid redundant GNews calls."""

    @pytest.mark.asyncio
    async def test_cache_hit_skips_gnews_api(self, mock_supabase):
        """When fresh cache exists, GNews API should NOT be called."""
        # Pre-populate cache
        cached_payload = {
            "domain": "datadoghq.com",
            "company_name": "Datadog",
            "answer": "Cached news summary",
            "results": [{"title": "Cached article"}],
            "result_count": 1,
            "themes": ["AI adoption"],
            "sentiment_indicators": {"positive": 1, "negative": 0, "neutral": 0},
            "fetched_at": datetime.utcnow().isoformat(),
        }
        mock_supabase.store_news_cache("datadoghq.com", cached_payload)

        orchestrator = RADOrchestrator(mock_supabase)

        # Mock the GNews API to track if it's called
        mock_gnews = AsyncMock()
        mock_gnews.enrich_with_name = AsyncMock(return_value={"should_not": "be_called"})
        orchestrator.apis["gnews"] = mock_gnews

        result = await orchestrator._fetch_gnews_with_name(
            "test@datadoghq.com", "datadoghq.com", "Datadog"
        )

        # GNews API should NOT have been called
        mock_gnews.enrich_with_name.assert_not_called()
        # Should return cached data
        assert result["answer"] == "Cached news summary"

    @pytest.mark.asyncio
    async def test_cache_miss_calls_gnews_and_stores(self, mock_supabase):
        """When no cache exists, GNews API should be called and result cached."""
        orchestrator = RADOrchestrator(mock_supabase)

        api_response = {
            "domain": "newco.com",
            "company_name": "NewCo",
            "answer": "Fresh from API",
            "results": [{"title": "New article"}],
            "result_count": 1,
            "themes": [],
            "sentiment_indicators": {"positive": 0, "negative": 0, "neutral": 0},
            "fetched_at": datetime.utcnow().isoformat(),
            "_query_stats": {"total": 2, "succeeded": 2, "failed": 0},
            "_quota_exhausted": False,
        }

        mock_gnews = AsyncMock()
        mock_gnews.enrich_with_name = AsyncMock(return_value=api_response)
        orchestrator.apis["gnews"] = mock_gnews

        result = await orchestrator._fetch_gnews_with_name(
            "test@newco.com", "newco.com", "NewCo"
        )

        # API should have been called
        mock_gnews.enrich_with_name.assert_called_once()
        assert result["answer"] == "Fresh from API"

        # Should now be cached
        cached = mock_supabase.get_cached_news("newco.com")
        assert cached is not None
