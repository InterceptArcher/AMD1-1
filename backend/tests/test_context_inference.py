"""
Tests for context inference service.
Validates that enrichment data is correctly analyzed to infer:
- IT environment (traditional/modernizing/modern)
- Business priority (reducing_cost/improving_performance/preparing_ai)
- Primary challenge (legacy_systems/integration_friction/resource_constraints/skills_gap/data_governance)
- Urgency level (low/medium/high)
- Journey stage (when not user-provided)
"""

import pytest
from app.services.context_inference_service import (
    infer_context,
    infer_it_environment,
    infer_business_priority,
    infer_challenge,
    infer_journey_stage,
    infer_urgency_level,
)


# === IT Environment Inference ===


class TestInferITEnvironment:
    """Test IT environment detection from enrichment signals."""

    def test_modern_from_company_tags(self):
        """Companies tagged with AI/cloud/SaaS should infer as modern."""
        profile = {
            "company_tags": ["saas", "artificial intelligence", "cloud computing"],
            "industry": "technology",
        }
        result = infer_it_environment(profile)
        assert result == "modern"

    def test_modern_from_young_tech_company(self):
        """Tech companies founded after 2015 should infer as modern."""
        profile = {
            "founded_year": 2018,
            "industry": "technology",
            "company_tags": [],
        }
        result = infer_it_environment(profile)
        assert result == "modern"

    def test_traditional_from_old_non_tech(self):
        """Companies founded before 2000 in non-tech industries should infer as traditional."""
        profile = {
            "founded_year": 1985,
            "industry": "manufacturing",
            "company_tags": [],
        }
        result = infer_it_environment(profile)
        assert result == "traditional"

    def test_modernizing_from_news_themes(self):
        """News themes about digital transformation should infer as modernizing."""
        profile = {
            "news_themes": ["digital transformation", "cloud migration"],
            "industry": "financial_services",
        }
        result = infer_it_environment(profile)
        assert result == "modernizing"

    def test_default_is_modernizing(self):
        """When no clear signals exist, default to modernizing."""
        profile = {}
        result = infer_it_environment(profile)
        assert result == "modernizing"


# === Business Priority Inference ===


class TestInferBusinessPriority:
    """Test business priority detection from enrichment signals."""

    def test_reducing_cost_from_news(self):
        """News about cost reduction should infer reducing_cost priority."""
        profile = {
            "news_themes": ["cost optimization"],
            "recent_news": [{"title": "Company announces cost reduction initiative"}],
        }
        result = infer_business_priority(profile)
        assert result == "reducing_cost"

    def test_preparing_ai_from_data_role(self):
        """Data/AI roles should infer preparing_ai priority."""
        profile = {
            "title": "VP of Data Science",
            "seniority": "vp",
        }
        result = infer_business_priority(profile)
        assert result == "preparing_ai"

    def test_preparing_ai_from_news_themes(self):
        """AI-related news themes should infer preparing_ai."""
        profile = {
            "news_themes": ["artificial intelligence", "machine learning adoption"],
        }
        result = infer_business_priority(profile)
        assert result == "preparing_ai"

    def test_improving_performance_from_high_growth(self):
        """High growth rate (>30%) should infer improving_performance."""
        profile = {
            "employee_growth_rate": 0.45,
        }
        result = infer_business_priority(profile)
        assert result == "improving_performance"

    def test_default_is_preparing_ai(self):
        """Default priority should be preparing_ai (AMD's primary message)."""
        profile = {}
        result = infer_business_priority(profile)
        assert result == "preparing_ai"


# === Challenge Inference ===


class TestInferChallenge:
    """Test challenge detection from enrichment signals."""

    def test_legacy_systems_from_old_company(self):
        """Old companies in non-tech industries likely face legacy system challenges."""
        profile = {
            "founded_year": 1990,
            "industry": "manufacturing",
        }
        result = infer_challenge(profile)
        assert result == "legacy_systems"

    def test_skills_gap_from_news(self):
        """News about talent/hiring/skills should infer skills_gap."""
        profile = {
            "recent_news": [{"title": "Company struggles with AI talent shortage"}],
            "news_themes": ["workforce development"],
        }
        result = infer_challenge(profile)
        assert result == "skills_gap"

    def test_resource_constraints_from_small_company(self):
        """Small companies (<200 employees) likely face resource constraints."""
        profile = {
            "employee_count": 85,
        }
        result = infer_challenge(profile)
        assert result == "resource_constraints"

    def test_data_governance_from_regulated_industry(self):
        """Healthcare and financial services face data governance challenges."""
        profile = {
            "industry": "healthcare",
        }
        result = infer_challenge(profile)
        assert result == "data_governance"

    def test_default_is_legacy_systems(self):
        """Default challenge should be legacy_systems."""
        profile = {}
        result = infer_challenge(profile)
        assert result == "legacy_systems"


# === Urgency Level ===


class TestInferUrgencyLevel:
    """Test urgency level detection."""

    def test_high_urgency_from_rapid_growth(self):
        """Rapid growth (>40%) signals high urgency."""
        profile = {
            "employee_growth_rate": 0.55,
        }
        result = infer_urgency_level(profile)
        assert result == "high"

    def test_high_urgency_from_recent_funding(self):
        """Recent funding signals high urgency for infrastructure decisions."""
        profile = {
            "latest_funding_stage": "series_c",
            "total_funding": 50000000,
        }
        result = infer_urgency_level(profile)
        assert result == "high"

    def test_medium_urgency_default(self):
        """Most profiles should have medium urgency."""
        profile = {
            "employee_count": 500,
            "industry": "technology",
        }
        result = infer_urgency_level(profile)
        assert result == "medium"

    def test_low_urgency_from_stable_company(self):
        """Small, stable companies with no growth signals have low urgency."""
        profile = {
            "employee_count": 50,
            "employee_growth_rate": -0.05,
        }
        result = infer_urgency_level(profile)
        assert result == "low"


# === Journey Stage Inference ===


class TestInferJourneyStage:
    """Test journey stage inference when not user-provided."""

    def test_decision_from_c_level_with_investment_news(self):
        """C-level role + investment news signals decision stage."""
        profile = {
            "seniority": "c_suite",
            "title": "CTO",
            "recent_news": [{"title": "Company secures $50M for AI infrastructure"}],
        }
        result = infer_journey_stage(profile)
        assert result == "decision"

    def test_implementation_from_pilot_news(self):
        """News about pilots/testing signals implementation stage."""
        profile = {
            "recent_news": [{"title": "Company begins pilot program for new AI platform"}],
        }
        result = infer_journey_stage(profile)
        assert result == "implementation"

    def test_consideration_from_recent_funding(self):
        """Recent funding signals consideration stage."""
        profile = {
            "latest_funding_stage": "series_b",
        }
        result = infer_journey_stage(profile)
        assert result == "consideration"

    def test_default_is_consideration(self):
        """Default journey stage should be consideration."""
        profile = {}
        result = infer_journey_stage(profile)
        assert result == "consideration"


# === Full Context Inference ===


class TestInferContext:
    """Test the full context inference pipeline."""

    def test_full_inference_returns_all_fields(self):
        """infer_context should return all expected fields."""
        profile = {
            "company_name": "Acme Corp",
            "industry": "technology",
            "founded_year": 2015,
            "employee_count": 500,
            "title": "CTO",
        }
        result = infer_context(profile)

        assert "it_environment" in result
        assert "business_priority" in result
        assert "primary_challenge" in result
        assert "urgency_level" in result
        assert "journey_stage" in result
        assert "confidence_score" in result

    def test_confidence_score_higher_with_more_data(self):
        """More enrichment data should yield higher confidence scores."""
        sparse_profile = {"industry": "technology"}
        rich_profile = {
            "company_name": "TechCo",
            "industry": "technology",
            "founded_year": 2018,
            "employee_count": 1200,
            "employee_growth_rate": 0.35,
            "title": "VP Engineering",
            "seniority": "vp",
            "company_tags": ["ai", "cloud", "saas"],
            "news_themes": ["ai adoption", "growth"],
            "recent_news": [{"title": "TechCo launches AI platform"}],
            "latest_funding_stage": "series_c",
        }

        sparse_result = infer_context(sparse_profile)
        rich_result = infer_context(rich_profile)

        assert rich_result["confidence_score"] > sparse_result["confidence_score"]

    def test_user_provided_goal_preserved(self):
        """When user provides a goal, it should be used instead of inferred stage."""
        profile = {"industry": "technology"}
        result = infer_context(profile, user_goal="implementation")

        assert result["journey_stage"] == "implementation"

    def test_inference_with_minimal_data(self):
        """Inference should work with almost no data (just email domain context)."""
        profile = {"domain": "hospital.org"}
        result = infer_context(profile)

        assert result["it_environment"] is not None
        assert result["business_priority"] is not None
        assert result["primary_challenge"] is not None
        assert result["urgency_level"] is not None
        assert result["journey_stage"] is not None
