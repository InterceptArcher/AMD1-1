"""
Tests for GNews error handling improvements:
- Reduced queries (5 → 2)
- HTTP error logging (403 quota, 500 server errors)
- Error metadata propagation (_quota_exhausted, _query_stats)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.services.enrichment_apis import GNewsAPI


@pytest.fixture
def gnews_api():
    """GNewsAPI with a fake key so it doesn't use mock mode."""
    return GNewsAPI(api_key="test-key-for-testing")


class TestReducedQueries:
    """Verify that GNews now sends only 2 queries instead of 5."""

    @pytest.mark.asyncio
    async def test_fetch_multi_query_sends_two_queries(self, gnews_api):
        """_fetch_multi_query_news should issue exactly 2 HTTP requests."""
        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.json.return_value = {"articles": []}
            return resp

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            await gnews_api._fetch_multi_query_news("Datadog")

        assert call_count == 2, f"Expected 2 queries, got {call_count}"

    def test_query_categories_match_two_queries(self, gnews_api):
        """_get_query_category should return valid categories for indices 0 and 1."""
        assert gnews_api._get_query_category(0) == "general"
        assert gnews_api._get_query_category(1) == "ai_technology"
        # Index 2+ should return "other" (no longer used)
        assert gnews_api._get_query_category(2) == "other"


class TestErrorLogging:
    """Verify that non-200 responses are logged and metadata propagated."""

    @pytest.mark.asyncio
    async def test_403_sets_quota_exhausted(self, gnews_api):
        """A 403 response should set _quota_exhausted flag."""
        async def mock_get(*args, **kwargs):
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 403
            resp.text = "Forbidden - quota exceeded"
            resp.json.return_value = {"errors": ["quota exceeded"]}
            return resp

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            articles = await gnews_api._fetch_multi_query_news("Datadog")

        assert isinstance(articles, list)
        assert len(articles) == 0

    @pytest.mark.asyncio
    async def test_enrich_with_name_returns_quota_exhausted_flag(self, gnews_api):
        """enrich_with_name should propagate _quota_exhausted when all queries get 403."""
        async def mock_get(*args, **kwargs):
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 403
            resp.text = "Forbidden"
            resp.json.return_value = {"errors": ["quota exceeded"]}
            return resp

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await gnews_api.enrich_with_name(
                "test@datadog.com", "datadoghq.com", "Datadog"
            )

        assert result["_quota_exhausted"] is True
        assert result["result_count"] == 0

    @pytest.mark.asyncio
    async def test_partial_success_returns_articles(self, gnews_api):
        """When one query succeeds and one fails, articles from success are returned."""
        call_index = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_index
            resp = MagicMock(spec=httpx.Response)
            if call_index == 0:
                # First query succeeds
                resp.status_code = 200
                resp.json.return_value = {
                    "articles": [
                        {
                            "title": "Datadog launches new AI feature",
                            "url": "https://example.com/1",
                            "description": "Desc",
                            "content": "Content",
                            "publishedAt": "2025-01-01",
                            "source": {"name": "TechCrunch", "url": "https://tc.com"},
                            "image": None,
                        }
                    ]
                }
            else:
                # Second query gets 403
                resp.status_code = 403
                resp.text = "Forbidden"
                resp.json.return_value = {"errors": ["quota"]}
            call_index += 1
            return resp

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await gnews_api.enrich_with_name(
                "test@datadog.com", "datadoghq.com", "Datadog"
            )

        assert result["result_count"] == 1
        assert result["results"][0]["title"] == "Datadog launches new AI feature"
        # Partial failure means quota may still be exhausted
        assert "_quota_exhausted" in result

    @pytest.mark.asyncio
    async def test_500_error_handled_gracefully(self, gnews_api):
        """500 server errors should be logged but not crash."""
        async def mock_get(*args, **kwargs):
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 500
            resp.text = "Internal Server Error"
            resp.json.return_value = {}
            return resp

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await gnews_api.enrich_with_name(
                "test@example.com", "example.com", "ExampleCo"
            )

        assert result["result_count"] == 0
        assert "_query_stats" in result


class TestQueryStats:
    """Verify _query_stats metadata is present in responses."""

    @pytest.mark.asyncio
    async def test_query_stats_included_in_response(self, gnews_api):
        """Response should include _query_stats with success/fail counts."""
        async def mock_get(*args, **kwargs):
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.json.return_value = {"articles": []}
            return resp

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await gnews_api.enrich_with_name(
                "test@example.com", "example.com", "ExampleCo"
            )

        assert "_query_stats" in result
        stats = result["_query_stats"]
        assert "total" in stats
        assert "succeeded" in stats
        assert "failed" in stats
        assert stats["total"] == 2
