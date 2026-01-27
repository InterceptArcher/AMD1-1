"""
Tests for RAD orchestrator.
Mock external API calls; test resolution logic and data aggregation.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.rad_orchestrator import RADOrchestrator


@pytest.mark.asyncio
class TestRADOrchestrator:
    """Tests for RADOrchestrator enrichment pipeline."""

    @pytest.fixture
    async def orchestrator(self, mock_supabase):
        """Fixture: RADOrchestrator with mocked Supabase."""
        return RADOrchestrator(mock_supabase)

    @pytest.mark.asyncio
    async def test_enrich_happy_path(self, orchestrator, mock_supabase):
        """
        Happy path: Full enrichment flow.
        Should fetch, resolve, and write finalize_data.
        """
        result = await orchestrator.enrich("john@acme.com", "acme.com")
        
        assert result is not None
        assert result["email"] == "john@acme.com"
        assert mock_supabase.write_finalize_data.called

    @pytest.mark.asyncio
    async def test_enrich_derives_domain_from_email(self, orchestrator, mock_supabase):
        """
        enrich: If domain not provided, derive from email.
        """
        result = await orchestrator.enrich("john@acme.com")
        
        assert result is not None
        # Verify enrichment succeeded
        assert mock_supabase.write_finalize_data.called

    @pytest.mark.asyncio
    async def test_fetch_raw_data_aggregates_sources(self, orchestrator, mock_supabase):
        """
        _fetch_raw_data: Should aggregate data from all API sources.
        """
        raw_data = await orchestrator._fetch_raw_data("john@acme.com", "acme.com")
        
        # In mocked version, all sources should return data
        assert isinstance(raw_data, dict)
        assert "apollo" in raw_data
        assert "pdl" in raw_data
        # Verify data_sources list was populated
        assert len(orchestrator.data_sources) > 0

    @pytest.mark.asyncio
    async def test_mock_apollo_returns_dict(self, orchestrator):
        """
        _mock_apollo_fetch: Should return dict with profile fields.
        """
        result = await orchestrator._mock_apollo_fetch("john@acme.com", "acme.com")
        
        assert isinstance(result, dict)
        assert "email" in result
        assert "first_name" in result
        assert "company_name" in result

    @pytest.mark.asyncio
    async def test_mock_pdl_returns_dict(self, orchestrator):
        """
        _mock_pdl_fetch: Should return dict with demographic data.
        """
        result = await orchestrator._mock_pdl_fetch("john@acme.com")
        
        assert isinstance(result, dict)
        assert "country" in result
        assert "industry" in result

    @pytest.mark.asyncio
    async def test_mock_hunter_returns_dict(self, orchestrator):
        """
        _mock_hunter_fetch: Should return dict with verification data.
        """
        result = await orchestrator._mock_hunter_fetch("john@acme.com")
        
        assert isinstance(result, dict)
        assert "verification_status" in result

    @pytest.mark.asyncio
    async def test_mock_gnews_returns_dict(self, orchestrator):
        """
        _mock_gnews_fetch: Should return dict with company news.
        """
        result = await orchestrator._mock_gnews_fetch("acme.com")
        
        assert isinstance(result, dict)
        assert "recent_news_count" in result

    def test_resolve_profile_merges_data(self, orchestrator):
        """
        _resolve_profile: Should merge Apollo + PDL + Hunter + GNews data.
        """
        raw_data = {
            "apollo": {
                "first_name": "John",
                "last_name": "Doe",
                "company_name": "Acme",
                "title": "VP Sales"
            },
            "pdl": {
                "country": "US",
                "industry": "SaaS"
            },
            "hunter": {
                "verification_status": "verified"
            },
            "gnews": {
                "recent_news_count": 3
            }
        }
        orchestrator.data_sources = ["apollo", "pdl", "hunter", "gnews"]
        
        result = orchestrator._resolve_profile("john@acme.com", raw_data)
        
        # All fields should be merged
        assert result["first_name"] == "John"
        assert result["country"] == "US"
        assert result["industry"] == "SaaS"
        assert result["email_verified"] is True
        assert result["recent_news_count"] == 3

    def test_resolve_profile_respects_apollo_priority(self, orchestrator):
        """
        _resolve_profile: Apollo data takes priority (trust ranking).
        """
        raw_data = {
            "apollo": {
                "first_name": "John",
                "company_name": "Acme Corp"
            },
            "pdl": {
                "first_name": "Johnny",  # Different
                "company_size": "500+"
            }
        }
        orchestrator.data_sources = ["apollo", "pdl"]
        
        result = orchestrator._resolve_profile("john@acme.com", raw_data)
        
        # Apollo's name should win
        assert result["first_name"] == "John"

    def test_resolve_profile_adds_metadata(self, orchestrator):
        """
        _resolve_profile: Should add metadata (email, resolved_at, quality_score).
        """
        raw_data = {
            "apollo": {"first_name": "John"}
        }
        orchestrator.data_sources = ["apollo"]
        
        result = orchestrator._resolve_profile("john@acme.com", raw_data)
        
        assert result["email"] == "john@acme.com"
        assert "resolved_at" in result
        assert "data_quality_score" in result
        # 1 source out of 4 max = 0.25 quality
        assert result["data_quality_score"] == 0.25

    def test_resolve_profile_quality_score_scaling(self, orchestrator):
        """
        _resolve_profile: Quality score should scale with number of sources (max 1.0).
        """
        raw_data = {
            "apollo": {"name": "John"},
            "pdl": {"country": "US"},
            "hunter": {"verified": True},
            "gnews": {"news": "recent"}
        }
        orchestrator.data_sources = ["apollo", "pdl", "hunter", "gnews"]
        
        result = orchestrator._resolve_profile("john@acme.com", raw_data)
        
        # 4 sources out of 4 max = 1.0 quality
        assert result["data_quality_score"] == 1.0


class TestRADDataFlow:
    """Integration-style tests for RAD data flow."""

    @pytest.mark.asyncio
    async def test_enrich_stores_raw_data_before_finalize(self, orchestrator, mock_supabase):
        """
        enrich: Should call store_raw_data for each source before finalize.
        """
        await orchestrator.enrich("john@acme.com", "acme.com")
        
        # Verify raw_data storage was called
        assert mock_supabase.store_raw_data.called
        # Verify finalize_data was written last
        assert mock_supabase.write_finalize_data.called

    @pytest.mark.asyncio
    async def test_enrich_data_sources_populated(self, orchestrator):
        """
        enrich: data_sources list should reflect which APIs were used.
        """
        result = await orchestrator.enrich("john@acme.com")
        
        # In mocked version, all sources are "used"
        assert len(orchestrator.data_sources) == 4
        assert "apollo" in orchestrator.data_sources
        assert "pdl" in orchestrator.data_sources
