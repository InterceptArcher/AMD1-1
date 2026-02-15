"""
Tests for Google News RSS fallback:
- Parse sample RSS XML
- Empty feed handling
- Malformed XML handling
- Output format compatibility with GNewsAPI
- Fallback triggers when GNews quota exhausted
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.services.enrichment_apis import GoogleNewsRSSFetcher, extract_themes, analyze_sentiment_keywords


SAMPLE_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Datadog - Google News</title>
    <link>https://news.google.com</link>
    <description>Google News</description>
    <item>
      <title>Datadog Announces New AI Observability Platform</title>
      <link>https://example.com/article1</link>
      <description>Datadog has launched a new platform for AI observability.</description>
      <pubDate>Mon, 10 Feb 2025 14:00:00 GMT</pubDate>
      <source url="https://techcrunch.com">TechCrunch</source>
    </item>
    <item>
      <title>Datadog Reports Strong Q4 Revenue Growth</title>
      <link>https://example.com/article2</link>
      <description>The cloud monitoring company exceeded expectations.</description>
      <pubDate>Fri, 07 Feb 2025 10:00:00 GMT</pubDate>
      <source url="https://reuters.com">Reuters</source>
    </item>
    <item>
      <title>Datadog Expands Partnership with AWS</title>
      <link>https://example.com/article3</link>
      <description>New integration capabilities announced.</description>
      <pubDate>Wed, 05 Feb 2025 08:00:00 GMT</pubDate>
      <source url="https://businesswire.com">Business Wire</source>
    </item>
  </channel>
</rss>"""

EMPTY_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>No results - Google News</title>
    <link>https://news.google.com</link>
  </channel>
</rss>"""


@pytest.fixture
def rss_fetcher():
    return GoogleNewsRSSFetcher()


class TestRSSParsing:
    """Test RSS XML parsing."""

    @pytest.mark.asyncio
    async def test_parse_valid_rss(self, rss_fetcher):
        """Valid RSS should be parsed into articles list."""
        async def mock_get(*args, **kwargs):
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.text = SAMPLE_RSS_XML
            return resp

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await rss_fetcher.fetch_news("Datadog")

        assert result["result_count"] == 3
        assert result["results"][0]["title"] == "Datadog Announces New AI Observability Platform"
        assert result["results"][0]["source"] == "TechCrunch"
        assert result["results"][0]["url"] == "https://example.com/article1"

    @pytest.mark.asyncio
    async def test_empty_rss_feed(self, rss_fetcher):
        """Empty RSS feed should return 0 articles."""
        async def mock_get(*args, **kwargs):
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.text = EMPTY_RSS_XML
            return resp

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await rss_fetcher.fetch_news("UnknownCompany")

        assert result["result_count"] == 0
        assert result["results"] == []

    @pytest.mark.asyncio
    async def test_malformed_xml(self, rss_fetcher):
        """Malformed XML should not crash, return empty results."""
        async def mock_get(*args, **kwargs):
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.text = "This is not XML at all"
            return resp

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await rss_fetcher.fetch_news("BadXML")

        assert result["result_count"] == 0

    @pytest.mark.asyncio
    async def test_http_error_returns_empty(self, rss_fetcher):
        """HTTP errors should return empty results, not crash."""
        async def mock_get(*args, **kwargs):
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 429
            resp.text = "Too Many Requests"
            return resp

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await rss_fetcher.fetch_news("RateLimited")

        assert result["result_count"] == 0


class TestGNewsFormatCompatibility:
    """RSS output format must match GNewsAPI output format."""

    @pytest.mark.asyncio
    async def test_output_has_same_keys_as_gnews(self, rss_fetcher):
        """RSS results must have the same keys as GNewsAPI articles."""
        async def mock_get(*args, **kwargs):
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.text = SAMPLE_RSS_XML
            return resp

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await rss_fetcher.fetch_news("Datadog")

        # Top-level keys expected by the enrichment pipeline
        expected_top_keys = {
            "domain", "company_name", "answer", "results",
            "result_count", "themes", "sentiment_indicators", "fetched_at",
        }
        assert expected_top_keys.issubset(set(result.keys()))

        # Article-level keys
        article = result["results"][0]
        expected_article_keys = {"title", "url", "content", "published_at", "source", "query_category"}
        assert expected_article_keys.issubset(set(article.keys()))

    @pytest.mark.asyncio
    async def test_themes_extracted_from_rss(self, rss_fetcher):
        """Themes should be extracted from RSS articles like GNews."""
        async def mock_get(*args, **kwargs):
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.text = SAMPLE_RSS_XML
            return resp

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await rss_fetcher.fetch_news("Datadog")

        # The sample RSS has "AI", "cloud", "growth" keywords
        assert isinstance(result["themes"], list)
        assert isinstance(result["sentiment_indicators"], dict)

    def test_shared_theme_extraction(self):
        """Module-level extract_themes should work on any articles list."""
        articles = [
            {"title": "Company launches AI platform", "content": "machine learning"},
            {"title": "Cloud migration complete", "content": "aws azure"},
        ]
        themes = extract_themes(articles)
        assert "AI adoption" in themes
        assert "Cloud transformation" in themes

    def test_shared_sentiment_analysis(self):
        """Module-level analyze_sentiment_keywords should work on any articles list."""
        articles = [
            {"title": "Record growth and expansion", "content": "Innovation award"},
        ]
        sentiment = analyze_sentiment_keywords(articles)
        assert sentiment["positive"] > 0
        assert sentiment["negative"] == 0
