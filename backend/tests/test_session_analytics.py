"""Tests for anonymized session analytics storage."""
import pytest
from app.services.supabase_client import SupabaseClient


class TestSessionAnalytics:
    """Verify session_analytics stores only anonymized data."""

    def test_store_session_analytics_returns_record(self, mock_supabase):
        result = mock_supabase.store_session_analytics(
            industry="healthcare",
            company_size="enterprise",
            stage="challenger",
            persona="ITDM",
            challenge="legacy_integration",
            enrichment_sources=["apollo", "pdl"],
            llm_source="llm",
            llm_latency_ms=3200,
            enrichment_latency_ms=4500,
            total_latency_ms=7700,
        )
        assert result is not None
        assert "id" in result
        assert result["industry"] == "healthcare"
        assert result["llm_source"] == "llm"

    def test_store_session_analytics_has_no_pii(self, mock_supabase):
        result = mock_supabase.store_session_analytics(
            industry="technology",
            company_size="mid_market",
            stage="observer",
            persona="BDM",
        )
        assert "email" not in result
        assert "name" not in result
        assert "first_name" not in result
        assert "last_name" not in result
        assert "company_name" not in result
        assert "company" not in result
        assert "domain" not in result
        assert "linkedin_url" not in result

    def test_store_session_analytics_minimal_fields(self, mock_supabase):
        result = mock_supabase.store_session_analytics(
            industry="financial_services",
            company_size="smb",
        )
        assert result is not None
        assert result["industry"] == "financial_services"
        assert result["stage"] is None
        assert result["persona"] is None

    def test_store_session_analytics_accumulates(self, mock_supabase):
        mock_supabase.store_session_analytics(industry="healthcare", company_size="enterprise")
        mock_supabase.store_session_analytics(industry="technology", company_size="smb")
        assert len(mock_supabase._mock_analytics) == 2
