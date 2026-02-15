"""
Tests for enrichment pipeline improvements.
Tests: company name resolution, industry normalization,
GNews with company name, completeness report, tech signals,
persona inference with departments.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.rad_orchestrator import RADOrchestrator
from app.services.context_inference_service import (
    extract_tech_signals_from_tags,
    infer_it_environment,
    infer_context,
)


class TestResolveCompanyName:
    """Tests for _resolve_company_name helper."""

    @pytest.fixture
    def orchestrator(self, mock_supabase):
        return RADOrchestrator(mock_supabase)

    def test_prefers_pdl_display_name(self, orchestrator):
        raw_data = {
            "pdl_company": {"display_name": "Google", "name": "Alphabet Inc."},
            "apollo": {"company_name": "Google Inc"},
            "pdl": {},
            "zoominfo": {},
        }
        assert orchestrator._resolve_company_name(raw_data, "google.com") == "Google"

    def test_falls_back_to_pdl_name(self, orchestrator):
        raw_data = {
            "pdl_company": {"name": "Alphabet Inc."},
            "apollo": {"_error": "failed"},
            "pdl": {},
            "zoominfo": {},
        }
        assert (
            orchestrator._resolve_company_name(raw_data, "google.com")
            == "Alphabet Inc."
        )

    def test_falls_back_to_apollo(self, orchestrator):
        raw_data = {
            "pdl_company": {"_error": "failed"},
            "apollo": {"company_name": "JPMorgan Chase"},
            "pdl": {},
            "zoominfo": {},
        }
        assert (
            orchestrator._resolve_company_name(raw_data, "jpmorgan.com")
            == "JPMorgan Chase"
        )

    def test_falls_back_to_zoominfo(self, orchestrator):
        raw_data = {
            "pdl_company": {"_error": "failed"},
            "apollo": {"_error": "failed"},
            "pdl": {"_error": "failed"},
            "zoominfo": {"company_name": "General Electric"},
        }
        assert (
            orchestrator._resolve_company_name(raw_data, "ge.com")
            == "General Electric"
        )

    def test_falls_back_to_pdl_person(self, orchestrator):
        raw_data = {
            "pdl_company": {"_error": "failed"},
            "apollo": {"_error": "failed"},
            "pdl": {"job_company_name": "Acme Corp"},
            "zoominfo": {"_error": "failed"},
        }
        assert (
            orchestrator._resolve_company_name(raw_data, "acme.com") == "Acme Corp"
        )

    def test_falls_back_to_domain(self, orchestrator):
        raw_data = {
            "pdl_company": {"_error": "failed"},
            "apollo": {"_error": "failed"},
            "pdl": {"_error": "failed"},
            "zoominfo": {"_error": "failed"},
        }
        assert (
            orchestrator._resolve_company_name(raw_data, "microsoft.com")
            == "Microsoft"
        )

    def test_skips_mock_data(self, orchestrator):
        raw_data = {
            "pdl_company": {"display_name": "Company at test.com", "_mock": True},
            "apollo": {"company_name": "Real Company"},
            "pdl": {},
            "zoominfo": {},
        }
        assert (
            orchestrator._resolve_company_name(raw_data, "test.com") == "Real Company"
        )


class TestNormalizeIndustry:
    """Tests for _normalize_industry."""

    @pytest.fixture
    def orchestrator(self, mock_supabase):
        return RADOrchestrator(mock_supabase)

    def test_normalize_it_services(self, orchestrator):
        assert (
            orchestrator._normalize_industry("information technology and services")
            == "technology"
        )

    def test_normalize_software(self, orchestrator):
        assert orchestrator._normalize_industry("software") == "technology"

    def test_normalize_internet(self, orchestrator):
        assert orchestrator._normalize_industry("Internet") == "technology"

    def test_normalize_banking(self, orchestrator):
        assert orchestrator._normalize_industry("banking") == "financial_services"

    def test_normalize_financial_services(self, orchestrator):
        assert (
            orchestrator._normalize_industry("Financial Services")
            == "financial_services"
        )

    def test_normalize_pharma(self, orchestrator):
        assert orchestrator._normalize_industry("pharmaceutical") == "healthcare"

    def test_normalize_healthcare(self, orchestrator):
        assert orchestrator._normalize_industry("healthcare") == "healthcare"

    def test_normalize_manufacturing(self, orchestrator):
        assert orchestrator._normalize_industry("manufacturing") == "manufacturing"

    def test_normalize_telecom(self, orchestrator):
        assert (
            orchestrator._normalize_industry("telecommunications")
            == "telecommunications"
        )

    def test_normalize_none(self, orchestrator):
        assert orchestrator._normalize_industry(None) is None

    def test_normalize_empty(self, orchestrator):
        assert orchestrator._normalize_industry("") is None

    def test_normalize_unknown_lowercased(self, orchestrator):
        result = orchestrator._normalize_industry("Underwater Basket Weaving")
        assert result == "underwater_basket_weaving"


class TestCompletenessReport:
    """Tests for _build_completeness_report."""

    @pytest.fixture
    def orchestrator(self, mock_supabase):
        return RADOrchestrator(mock_supabase)

    def test_full_data_high_score(self, orchestrator):
        profile = {
            "company_name": "Acme",
            "industry": "technology",
            "title": "CTO",
            "employee_count": 5000,
            "company_summary": "A tech company",
            "founded_year": 2010,
            "seniority": "c_suite",
            "recent_news": [{"title": "news"}],
            "skills": ["python"],
            "employee_growth_rate": 0.3,
            "total_funding": 50000000,
            "latest_funding_stage": "series_c",
            "company_tags": ["ai"],
            "news_themes": ["growth"],
        }
        report = orchestrator._build_completeness_report(profile)
        assert report["score"] > 0.8
        assert report["missing_critical"] == []

    def test_missing_critical_fields(self, orchestrator):
        profile = {"domain": "test.com"}
        report = orchestrator._build_completeness_report(profile)
        assert "company_name" in report["missing_critical"]
        assert "industry" in report["missing_critical"]
        assert "title" in report["missing_critical"]
        assert "employee_count" in report["missing_critical"]
        assert report["score"] < 0.3

    def test_partial_data(self, orchestrator):
        profile = {
            "company_name": "Acme",
            "industry": "technology",
            "title": "CTO",
        }
        report = orchestrator._build_completeness_report(profile)
        assert report["missing_critical"] == ["employee_count"]
        assert report["score"] > 0.2
        assert report["score"] < 0.8

    def test_field_coverage_string(self, orchestrator):
        profile = {"company_name": "Acme"}
        report = orchestrator._build_completeness_report(profile)
        assert "/" in report["field_coverage"]


class TestTechSignals:
    """Tests for extract_tech_signals_from_tags."""

    def test_cloud_and_ai_tags(self):
        tags = ["cloud computing", "artificial intelligence", "saas", "machine learning"]
        result = extract_tech_signals_from_tags(tags)
        assert result["maturity"] == "advanced"
        assert len(result["cloud"]) > 0
        assert len(result["ai_ml"]) > 0

    def test_cloud_only(self):
        tags = ["cloud computing", "aws", "saas"]
        result = extract_tech_signals_from_tags(tags)
        assert result["maturity"] == "modern"
        assert len(result["cloud"]) > 0
        assert len(result["ai_ml"]) == 0

    def test_traditional_tags(self):
        tags = ["mainframe", "legacy", "erp"]
        result = extract_tech_signals_from_tags(tags)
        assert result["maturity"] == "traditional"

    def test_empty_tags(self):
        result = extract_tech_signals_from_tags([])
        assert result["maturity"] == "unknown"

    def test_mixed_tags(self):
        tags = ["enterprise software", "consulting", "management"]
        result = extract_tech_signals_from_tags(tags)
        assert result["maturity"] == "mixed"

    def test_security_tags(self):
        tags = ["cybersecurity", "information security"]
        result = extract_tech_signals_from_tags(tags)
        assert len(result["security"]) > 0

    def test_data_tags(self):
        tags = ["big data", "analytics", "data warehouse"]
        result = extract_tech_signals_from_tags(tags)
        assert len(result["data"]) > 0


class TestTechSignalsInference:
    """Test that tech signals improve IT environment inference."""

    def test_advanced_tech_signals_infer_modern(self):
        profile = {
            "company_tags": ["cloud computing", "artificial intelligence", "saas"],
            "industry": "technology",
        }
        result = infer_it_environment(profile)
        assert result == "modern"

    def test_traditional_tech_signals_infer_traditional(self):
        profile = {
            "company_tags": ["mainframe", "legacy"],
            "industry": "manufacturing",
        }
        result = infer_it_environment(profile)
        assert result == "traditional"

    def test_tech_signals_included_in_context(self):
        profile = {
            "company_tags": ["cloud computing", "machine learning"],
            "industry": "technology",
        }
        result = infer_context(profile)
        assert "tech_signals" in result
        assert result["tech_signals"]["maturity"] in ("advanced", "modern")


class TestInferPersona:
    """Tests for _infer_persona_from_title with departments."""

    def test_clear_itdm_title(self):
        from app.routes.enrichment import _infer_persona_from_title

        assert _infer_persona_from_title("Chief Technology Officer") == "ITDM"

    def test_clear_bdm_title(self):
        from app.routes.enrichment import _infer_persona_from_title

        assert _infer_persona_from_title("VP of Sales") == "BDM"

    def test_ambiguous_title_with_itdm_departments(self):
        from app.routes.enrichment import _infer_persona_from_title

        result = _infer_persona_from_title("Director", departments=["engineering"])
        assert result == "ITDM"

    def test_ambiguous_title_with_bdm_departments(self):
        from app.routes.enrichment import _infer_persona_from_title

        result = _infer_persona_from_title("Director", departments=["sales"])
        assert result == "BDM"

    def test_no_title_with_departments(self):
        from app.routes.enrichment import _infer_persona_from_title

        result = _infer_persona_from_title("", departments=["information_technology"])
        assert result == "ITDM"

    def test_no_title_no_departments(self):
        from app.routes.enrichment import _infer_persona_from_title

        result = _infer_persona_from_title("")
        assert result == "BDM"


@pytest.mark.asyncio
class TestTwoPhaseEnrichment:
    """Tests for the two-phase enrichment flow."""

    @pytest.fixture
    def orchestrator(self, mock_supabase):
        return RADOrchestrator(mock_supabase)

    @pytest.mark.asyncio
    async def test_fetch_all_sources_still_returns_all_keys(self, orchestrator):
        """Two-phase enrichment should still return all source keys."""
        raw_data = await orchestrator._fetch_all_sources("john@acme.com", "acme.com")

        assert isinstance(raw_data, dict)
        assert "apollo" in raw_data
        assert "pdl" in raw_data
        assert "hunter" in raw_data
        assert "gnews" in raw_data
        assert "zoominfo" in raw_data
        assert "pdl_company" in raw_data

    @pytest.mark.asyncio
    async def test_enrich_includes_completeness_report(self, orchestrator):
        """Enrichment result should include completeness report."""
        result = await orchestrator.enrich("john@acme.com", "acme.com")

        assert "completeness_report" in result
        report = result["completeness_report"]
        assert "score" in report
        assert "missing_critical" in report
        assert "field_coverage" in report

    @pytest.mark.asyncio
    async def test_enrich_normalizes_industry(self, orchestrator):
        """Enrichment should normalize industry strings."""
        result = await orchestrator.enrich("john@acme.com", "acme.com")

        # Even with mock data, industry should be processed
        if result.get("industry"):
            # Should not contain "and services" or mixed case
            assert result["industry"] == result["industry"].lower().replace(" ", "_") or \
                   result["industry"] in (
                       "technology", "healthcare", "financial_services",
                       "manufacturing", "retail", "energy",
                       "telecommunications", "government", "education",
                   )
