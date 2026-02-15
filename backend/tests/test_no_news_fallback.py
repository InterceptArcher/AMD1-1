"""
Tests for better LLM fallback when all news sources fail:
- Prompt contains DERIVED INTELLIGENCE section when no news
- Prompt does NOT contain derived intelligence when news exists
- Company intelligence signals (employee count, growth, summary) appear in prompt
- Executive review enrichment section uses company data as news substitute
"""

import pytest

from app.services.llm_service import LLMService
from app.services.executive_review_service import ExecutiveReviewService


@pytest.fixture
def llm_service():
    return LLMService()


@pytest.fixture
def exec_service():
    return ExecutiveReviewService()


class TestEbookPromptNoNewsFallback:
    """Test _build_ebook_prompt uses company intelligence when no news."""

    def test_derived_intelligence_when_no_news(self, llm_service):
        """When recent_news is empty, prompt should contain DERIVED INTELLIGENCE section."""
        profile = {
            "first_name": "John",
            "last_name": "Doe",
            "title": "CTO",
            "company_name": "Datadog",
            "industry": "technology",
            "employee_count": 5000,
            "employee_growth_rate": 0.25,
            "company_summary": "Datadog is a monitoring and analytics platform for cloud-scale applications.",
            "total_funding": 147800000,
            "latest_funding_stage": "ipo",
            "company_tags": ["cloud", "monitoring", "saas", "analytics"],
            "recent_news": [],  # No news
            "news_themes": [],
        }
        user_context = {"goal": "consideration", "persona": "cto"}

        prompt = llm_service._build_ebook_prompt(profile, user_context, None)

        # Should contain derived intelligence section
        assert "DERIVED INTELLIGENCE" in prompt or "COMPANY INTELLIGENCE SIGNALS" in prompt
        # Should reference specific company data
        assert "5,000" in prompt or "5000" in prompt
        assert "Datadog" in prompt
        assert "monitoring" in prompt.lower() or "analytics" in prompt.lower()

    def test_no_derived_intelligence_when_news_exists(self, llm_service):
        """When recent_news has articles, should NOT add derived intelligence section."""
        profile = {
            "first_name": "Jane",
            "last_name": "Smith",
            "title": "VP Engineering",
            "company_name": "Stripe",
            "industry": "financial_services",
            "employee_count": 8000,
            "company_summary": "Stripe builds payment infrastructure.",
            "recent_news": [
                {"title": "Stripe launches new AI fraud detection", "source": "TechCrunch", "content": "Details..."}
            ],
            "news_themes": ["AI adoption", "Innovation"],
        }
        user_context = {"goal": "awareness", "persona": "vp_engineering"}

        prompt = llm_service._build_ebook_prompt(profile, user_context, "Stripe launches AI")

        # Should NOT have the derived intelligence fallback section
        assert "DERIVED INTELLIGENCE" not in prompt
        # But should still have the normal news section
        assert "Stripe launches new AI fraud detection" in prompt

    def test_growth_signals_in_fallback(self, llm_service):
        """Fallback should include growth rate as a substitute for news."""
        profile = {
            "first_name": "Alice",
            "company_name": "ScaleAI",
            "title": "Director of Engineering",
            "industry": "technology",
            "employee_count": 600,
            "employee_growth_rate": 0.45,
            "company_summary": "Scale AI provides data labeling for AI.",
            "recent_news": [],
            "news_themes": [],
        }
        user_context = {}

        prompt = llm_service._build_ebook_prompt(profile, user_context, None)

        assert "45%" in prompt or "0.45" in prompt or "rapidly growing" in prompt.lower()

    def test_funding_signals_in_fallback(self, llm_service):
        """Fallback should include funding stage when no news."""
        profile = {
            "first_name": "Bob",
            "company_name": "Anthropic",
            "title": "ML Engineer",
            "industry": "technology",
            "latest_funding_stage": "series_d",
            "total_funding": 7100000000,
            "recent_news": [],
            "news_themes": [],
        }
        user_context = {}

        prompt = llm_service._build_ebook_prompt(profile, user_context, None)

        assert "series_d" in prompt.lower() or "series d" in prompt.lower()

    def test_company_tags_in_fallback(self, llm_service):
        """Company tags should be used as intelligence signals when no news."""
        profile = {
            "first_name": "Carol",
            "company_name": "Snowflake",
            "title": "Data Architect",
            "industry": "technology",
            "company_tags": ["cloud", "data warehouse", "analytics", "ai", "enterprise"],
            "recent_news": [],
            "news_themes": [],
        }
        user_context = {}

        prompt = llm_service._build_ebook_prompt(profile, user_context, None)

        assert "cloud" in prompt.lower()
        assert "data warehouse" in prompt.lower() or "analytics" in prompt.lower()

    def test_no_generic_fallback_message(self, llm_service):
        """When company data exists, prompt should NOT say just 'use industry trends instead'."""
        profile = {
            "first_name": "Dave",
            "company_name": "CrowdStrike",
            "title": "CISO",
            "industry": "technology",
            "employee_count": 7000,
            "company_summary": "CrowdStrike provides cloud-native endpoint protection.",
            "company_tags": ["cybersecurity", "cloud", "endpoint"],
            "recent_news": [],
            "news_themes": [],
        }
        user_context = {}

        prompt = llm_service._build_ebook_prompt(profile, user_context, None)

        # The old generic fallback should be replaced
        # It should have company-specific data instead
        assert "CrowdStrike" in prompt
        assert "7,000" in prompt or "7000" in prompt


class TestExecReviewEnrichmentSection:
    """Test _build_enrichment_section in ExecutiveReviewService."""

    def test_company_intelligence_when_no_news(self, exec_service):
        """When recent_news is empty but company data exists, should include intelligence."""
        ctx = {
            "employee_count": 15000,
            "employee_growth_rate": 0.12,
            "company_summary": "Dell Technologies is a global leader in digital transformation.",
            "total_funding": 0,
            "founded_year": 1984,
            "recent_news": [],
            "news_themes": [],
            "title": "VP of IT",
        }

        section = exec_service._build_enrichment_section(ctx)

        assert "15,000" in section
        assert "1984" in section
        assert "Dell Technologies" in section.lower() or "digital transformation" in section.lower()

    def test_news_present_uses_normal_section(self, exec_service):
        """When news exists, should use normal news formatting."""
        ctx = {
            "employee_count": 5000,
            "recent_news": [
                {"title": "Company wins big contract"},
                {"title": "Company expands to Asia"},
            ],
            "news_themes": ["Growth & expansion"],
            "title": "CTO",
        }

        section = exec_service._build_enrichment_section(ctx)

        assert "Company wins big contract" in section
        assert "Growth & expansion" in section

    def test_empty_context_returns_empty(self, exec_service):
        """Empty context should return empty string."""
        section = exec_service._build_enrichment_section({})
        assert section == ""

    def test_no_news_directive_added(self, exec_service):
        """When no news, should add directive to use company data."""
        ctx = {
            "employee_count": 3000,
            "company_summary": "A logistics company.",
            "recent_news": [],
            "news_themes": [],
        }

        section = exec_service._build_enrichment_section(ctx)

        # Should instruct LLM to use company data
        assert "3,000" in section
