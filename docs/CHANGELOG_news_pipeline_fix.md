# News Enrichment Pipeline Fix — 2026-02-15

## Problem

GNews API (the only news source) returned **zero articles for ALL companies** — Datadog, Pfizer, Dell, Microsoft. The free tier (100 req/day) was exhausted because each enrichment fired 5 parallel queries, allowing only 20 enrichments/day. The code silently swallowed 403 errors at `enrichment_apis.py:533` with no logging.

Without news data, the LLM prompt received empty context and generated generic industry content instead of company-specific personalization — defeating the core value proposition.

---

## Fix 1: GNews Error Logging + Reduce Queries

**File**: `backend/app/services/enrichment_apis.py`

**What changed**:
- Reduced search queries from 5 to 2 per enrichment (exact match + AI-focused query)
- Added `else` branch to log HTTP status + response body for non-200 responses
- Added `_quota_exhausted: True` flag when 403 is received
- Added `_query_stats` metadata dict (`total`, `succeeded`, `failed`) to every response
- Updated `_get_query_category()` to match the 2-query setup
- Refactored `_extract_themes()` and `_analyze_sentiment_keywords()` from instance methods to module-level functions (`extract_themes()`, `analyze_sentiment_keywords()`) so they can be shared with the RSS fetcher

**Impact**: 60% quota savings — 50 enrichments/day instead of 20 on GNews free tier (100 req/day).

**Test file**: `backend/tests/test_gnews_error_handling.py` (7 tests)
- `test_fetch_multi_query_sends_two_queries` — verifies exactly 2 HTTP requests
- `test_query_categories_match_two_queries` — categories for index 0 and 1
- `test_403_sets_quota_exhausted` — 403 response sets flag
- `test_enrich_with_name_returns_quota_exhausted_flag` — flag propagated to caller
- `test_partial_success_returns_articles` — one query succeeds, one fails
- `test_500_error_handled_gracefully` — server errors don't crash
- `test_query_stats_included_in_response` — metadata always present

---

## Fix 2: Company-Level News Caching

**Files**: `backend/app/services/supabase_client.py`, `backend/app/services/rad_orchestrator.py`

**What changed**:
- Added `store_news_cache(domain, payload)` to SupabaseClient — upserts into `raw_data` table with `source='gnews_cache'` and `email=domain`
- Added `get_cached_news(domain, max_age_hours=24)` — queries `raw_data` for cached news, checks freshness against `fetched_at` timestamp
- Updated `_fetch_gnews_with_name()` in RADOrchestrator to check cache FIRST before calling any news API, and store results after fetching
- No new database tables — reuses existing `raw_data` table

**Impact**: 10 employees from the same company domain = 1 GNews API call instead of 10. Cache expires after 24 hours.

**Test file**: `backend/tests/test_news_caching.py` (8 tests)
- `test_store_and_retrieve_news_cache` — basic store/retrieve
- `test_fresh_cache_is_returned` — cache within TTL returned
- `test_expired_cache_returns_none` — stale cache ignored
- `test_upsert_overwrites_existing_cache` — second store replaces first
- `test_different_domains_cached_separately` — domain isolation
- `test_no_cache_returns_none` — uncached domain returns None
- `test_cache_hit_skips_gnews_api` — GNews API not called when cache exists
- `test_cache_miss_calls_gnews_and_stores` — API called + result cached on miss

---

## Fix 3: Google News RSS Fallback

**Files**: `backend/app/services/enrichment_apis.py`, `backend/app/services/rad_orchestrator.py`

**What changed**:
- New `GoogleNewsRSSFetcher` class in `enrichment_apis.py`:
  - Fetches `https://news.google.com/rss/search?q={company_name}&hl=en-US&gl=US&ceid=US:en`
  - Parses XML with stdlib `xml.etree.ElementTree` (no new dependencies)
  - Output format matches GNewsAPI exactly (same keys: `title`, `url`, `content`, `published_at`, `source`, `query_category`, same top-level structure)
  - Handles malformed XML, HTTP errors, and empty feeds gracefully
- Updated `_fetch_gnews_with_name()` in RADOrchestrator with 3-layer strategy:
  1. Check domain-level cache
  2. Try GNews API
  3. If GNews returns 0 articles or `_quota_exhausted`, try Google News RSS
  - RSS results are also cached for future lookups

**Impact**: Free, unlimited news fallback. When GNews quota is exhausted, the system automatically gets news from Google News RSS instead of returning nothing.

**Test file**: `backend/tests/test_google_news_rss.py` (8 tests)
- `test_parse_valid_rss` — 3 articles parsed from sample XML
- `test_empty_rss_feed` — empty feed returns 0 articles
- `test_malformed_xml` — invalid XML doesn't crash
- `test_http_error_returns_empty` — HTTP 429 returns empty result
- `test_output_has_same_keys_as_gnews` — format compatibility verified
- `test_themes_extracted_from_rss` — themes extracted from RSS articles
- `test_shared_theme_extraction` — module-level function works standalone
- `test_shared_sentiment_analysis` — module-level function works standalone

---

## Fix 4: Better LLM Fallback When All News Fails

**Files**: `backend/app/services/llm_service.py`, `backend/app/services/executive_review_service.py`

**What changed**:
- In `_build_ebook_prompt()` (llm_service.py): When `recent_news` is empty AND no `company_news`, replaced the old "No recent news found - use industry trends instead" with a structured **DERIVED INTELLIGENCE** section containing:
  - `COMPANY OVERVIEW` — from PDL company summary
  - `SCALE SIGNAL` — employee count with infrastructure complexity context
  - `GROWTH SIGNAL` — employee growth rate with scaling challenge framing
  - `FUNDING SIGNAL` — total funding with investment capacity context
  - `MATURITY SIGNAL` — funding stage with maturity-appropriate recommendations
  - `TECH SIGNALS` — company tags with AI readiness indicators
  - `MATURITY` — founded year with legacy considerations
  - Mandatory directive: "Reference {company_name} by name, use their employee count, growth rate, or company summary. DO NOT use generic phrases."
- In `_build_enrichment_section()` (executive_review_service.py): When `recent_news` is empty but company data exists, adds company profile, scale, and growth trajectory as substitute signals with "(Use these company signals in place of news for personalization)" directive.

**Impact**: Even when ALL news sources fail (GNews quota + RSS blocked), the LLM receives company-specific data and is explicitly told not to generate generic content.

**Test file**: `backend/tests/test_no_news_fallback.py` (10 tests)
- `test_derived_intelligence_when_no_news` — DERIVED INTELLIGENCE section present
- `test_no_derived_intelligence_when_news_exists` — section NOT present when news exists
- `test_growth_signals_in_fallback` — growth rate appears in prompt
- `test_funding_signals_in_fallback` — funding stage appears in prompt
- `test_company_tags_in_fallback` — tech tags appear in prompt
- `test_no_generic_fallback_message` — company-specific data replaces generic message
- `test_company_intelligence_when_no_news` — exec review section has company data
- `test_news_present_uses_normal_section` — normal formatting when news exists
- `test_empty_context_returns_empty` — empty input returns empty string
- `test_no_news_directive_added` — directive to use company data present

---

## Test Results

```
33 new tests: ALL PASSING
195 total tests: ALL PASSING (0 regressions, 11 skipped)
```

## Files Modified

| File | Changes |
|------|---------|
| `backend/app/services/enrichment_apis.py` | Reduced queries 5→2, error logging, `_quota_exhausted` flag, `_query_stats`, module-level theme/sentiment functions, `GoogleNewsRSSFetcher` class |
| `backend/app/services/supabase_client.py` | Added `store_news_cache()`, `get_cached_news()` |
| `backend/app/services/rad_orchestrator.py` | 3-layer news fetch (cache → GNews → RSS), imported `GoogleNewsRSSFetcher` |
| `backend/app/services/llm_service.py` | DERIVED INTELLIGENCE section in `_build_ebook_prompt()` |
| `backend/app/services/executive_review_service.py` | Company intelligence fallback in `_build_enrichment_section()` |

## Files Created

| File | Purpose |
|------|---------|
| `backend/tests/test_gnews_error_handling.py` | 7 tests for Fix 1 |
| `backend/tests/test_news_caching.py` | 8 tests for Fix 2 |
| `backend/tests/test_google_news_rss.py` | 8 tests for Fix 3 |
| `backend/tests/test_no_news_fallback.py` | 10 tests for Fix 4 |

## No New Dependencies

All changes use existing packages (`httpx`, stdlib `xml.etree.ElementTree`, `urllib.parse`). Zero new pip installs required.
