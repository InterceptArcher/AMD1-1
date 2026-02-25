"""
Tests that the executive review endpoint uses user wizard selections
(itEnvironment, businessPriority, challenge) instead of ignoring them
and relying solely on inferred values from API data.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.routes.enrichment import generate_executive_review
from app.models.schemas import EnrichmentRequest


def _make_request(**overrides) -> EnrichmentRequest:
    """Build a minimal EnrichmentRequest with optional overrides."""
    defaults = {
        "email": "test@acme.com",
        "company": "Acme Corp",
        "companySize": "enterprise",
        "industry": "technology",
        "persona": "cto",
    }
    defaults.update(overrides)
    return EnrichmentRequest(**defaults)


def _mock_enrichment_result():
    """Minimal enrichment result from the orchestrator."""
    return {
        "company_name": "Acme Corp",
        "industry": "technology",
        "employee_count": 5000,
        "title": "CTO",
        "departments": ["engineering"],
        "founded_year": 2010,
        "employee_growth_rate": None,
        "latest_funding_stage": None,
        "total_funding_raised": None,
        "company_summary": "A tech company",
        "recent_news": [],
        "news_themes": [],
        "data_quality_score": 0.7,
        "first_name": "Test",
        "last_name": "User",
    }


def _mock_inferred_context():
    """Inferred context — represents what the backend would guess from API data."""
    return {
        "it_environment": "traditional",  # backend guess
        "business_priority": "reducing_cost",  # backend guess
        "primary_challenge": "legacy_systems",  # backend guess
        "urgency_level": "medium",
        "tech_signals": [],
        "confidence_score": 0.5,
    }


def _mock_review_result():
    """Minimal executive review service result."""
    return {
        "executive_summary": "Test summary",
        "advantages": [
            {"title": "Adv 1", "description": "Desc 1"},
            {"title": "Adv 2", "description": "Desc 2"},
        ],
        "risks": [
            {"title": "Risk 1", "description": "Desc 1"},
            {"title": "Risk 2", "description": "Desc 2"},
        ],
        "recommendations": [
            {"title": "Rec 1", "description": "Desc 1", "timeline": "Q1 2026"},
            {"title": "Rec 2", "description": "Desc 2", "timeline": "Q2 2026"},
            {"title": "Rec 3", "description": "Desc 3", "timeline": "Q3 2026"},
        ],
        "case_study_relevance": "Test relevance",
        "_source": "mock_fallback",
    }


@pytest.mark.asyncio
class TestUserInputOverridesInferred:
    """User wizard selections must override backend-inferred values."""

    @patch("app.routes.enrichment.RADOrchestrator")
    @patch("app.routes.enrichment.infer_context")
    @patch("app.routes.enrichment.analyze_news")
    @patch("app.routes.enrichment.ExecutiveReviewService")
    async def test_user_modern_overrides_inferred_traditional(
        self, MockService, mock_news, mock_infer, MockOrch
    ):
        """User selects 'modern' → stage should be 'Leader', not 'Observer'."""
        # Setup mocks
        orch_instance = AsyncMock()
        orch_instance.enrich = AsyncMock(return_value=_mock_enrichment_result())
        orch_instance.data_sources = ["pdl"]
        MockOrch.return_value = orch_instance

        mock_infer.return_value = _mock_inferred_context()  # returns "traditional"
        mock_news.return_value = {
            "sentiment": {"overall": "neutral"},
            "ai_readiness": {"stage": "exploring"},
            "crisis": {"is_crisis": False},
        }

        svc_instance = AsyncMock()
        svc_instance.generate_executive_review = AsyncMock(return_value=_mock_review_result())
        MockService.return_value = svc_instance

        request = _make_request(itEnvironment="modern")
        result = await generate_executive_review(request, supabase=MagicMock())

        assert result["inputs"]["stage"] == "Leader"

    @patch("app.routes.enrichment.RADOrchestrator")
    @patch("app.routes.enrichment.infer_context")
    @patch("app.routes.enrichment.analyze_news")
    @patch("app.routes.enrichment.ExecutiveReviewService")
    async def test_user_priority_overrides_inferred(
        self, MockService, mock_news, mock_infer, MockOrch
    ):
        """User selects 'preparing_ai' → priority should be 'Preparing for AI adoption'."""
        orch_instance = AsyncMock()
        orch_instance.enrich = AsyncMock(return_value=_mock_enrichment_result())
        orch_instance.data_sources = ["pdl"]
        MockOrch.return_value = orch_instance

        mock_infer.return_value = _mock_inferred_context()  # returns "reducing_cost"
        mock_news.return_value = {
            "sentiment": {"overall": "neutral"},
            "ai_readiness": {"stage": "exploring"},
            "crisis": {"is_crisis": False},
        }

        svc_instance = AsyncMock()
        svc_instance.generate_executive_review = AsyncMock(return_value=_mock_review_result())
        MockService.return_value = svc_instance

        request = _make_request(businessPriority="preparing_ai")
        result = await generate_executive_review(request, supabase=MagicMock())

        assert result["inputs"]["priority"] == "Preparing for AI adoption"

    @patch("app.routes.enrichment.RADOrchestrator")
    @patch("app.routes.enrichment.infer_context")
    @patch("app.routes.enrichment.analyze_news")
    @patch("app.routes.enrichment.ExecutiveReviewService")
    async def test_user_challenge_overrides_inferred(
        self, MockService, mock_news, mock_infer, MockOrch
    ):
        """User selects 'skills_gap' → challenge should be 'Skills gap'."""
        orch_instance = AsyncMock()
        orch_instance.enrich = AsyncMock(return_value=_mock_enrichment_result())
        orch_instance.data_sources = ["pdl"]
        MockOrch.return_value = orch_instance

        mock_infer.return_value = _mock_inferred_context()  # returns "legacy_systems"
        mock_news.return_value = {
            "sentiment": {"overall": "neutral"},
            "ai_readiness": {"stage": "exploring"},
            "crisis": {"is_crisis": False},
        }

        svc_instance = AsyncMock()
        svc_instance.generate_executive_review = AsyncMock(return_value=_mock_review_result())
        MockService.return_value = svc_instance

        request = _make_request(challenge="skills_gap")
        result = await generate_executive_review(request, supabase=MagicMock())

        assert result["inputs"]["challenge"] == "Skills gap"

    @patch("app.routes.enrichment.RADOrchestrator")
    @patch("app.routes.enrichment.infer_context")
    @patch("app.routes.enrichment.analyze_news")
    @patch("app.routes.enrichment.ExecutiveReviewService")
    async def test_missing_user_input_falls_back_to_inferred(
        self, MockService, mock_news, mock_infer, MockOrch
    ):
        """When user doesn't provide itEnvironment/priority/challenge, use inferred."""
        orch_instance = AsyncMock()
        orch_instance.enrich = AsyncMock(return_value=_mock_enrichment_result())
        orch_instance.data_sources = ["pdl"]
        MockOrch.return_value = orch_instance

        mock_infer.return_value = _mock_inferred_context()
        mock_news.return_value = {
            "sentiment": {"overall": "neutral"},
            "ai_readiness": {"stage": "exploring"},
            "crisis": {"is_crisis": False},
        }

        svc_instance = AsyncMock()
        svc_instance.generate_executive_review = AsyncMock(return_value=_mock_review_result())
        MockService.return_value = svc_instance

        # No itEnvironment, businessPriority, or challenge provided
        request = _make_request()
        result = await generate_executive_review(request, supabase=MagicMock())

        # Should fall back to inferred values
        assert result["inputs"]["stage"] == "Observer"  # from "traditional"
        assert result["inputs"]["priority"] == "Reducing cost"  # from "reducing_cost"
        assert result["inputs"]["challenge"] == "Legacy systems"  # from "legacy_systems"
