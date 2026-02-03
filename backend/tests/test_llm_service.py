"""
Tests for LLM service personalization generation.
Uses mock mode (no real API calls) for predictable testing.
"""

import pytest
from datetime import datetime
from unittest.mock import patch

from app.services.llm_service import LLMService, MAX_INTRO_LENGTH, MAX_CTA_LENGTH


class TestLLMService:
    """Tests for LLMService personalization generation."""

    @pytest.fixture
    def llm_service(self):
        """Fixture: LLM service in mock mode (no API key)."""
        # LLMService no longer accepts api_key parameter
        # Without API keys in settings, it falls back to mock mode
        return LLMService()

    @pytest.mark.asyncio
    async def test_generate_personalization_returns_dict(self, llm_service):
        """
        generate_personalization: Should return dict with intro_hook and cta.
        """
        profile = {
            "email": "john@acme.com",
            "first_name": "John",
            "company_name": "Acme",
            "title": "VP Sales"
        }

        result = await llm_service.generate_personalization(profile)

        assert isinstance(result, dict)
        assert "intro_hook" in result
        assert "cta" in result
        assert len(result["intro_hook"]) > 0
        assert len(result["cta"]) > 0

    @pytest.mark.asyncio
    async def test_generate_intro_hook(self, llm_service):
        """
        generate_intro_hook: Should return just the intro hook string.
        """
        profile = {
            "email": "john@acme.com",
            "first_name": "John",
            "company_name": "Acme"
        }

        result = await llm_service.generate_intro_hook(profile)

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_generate_cta(self, llm_service):
        """
        generate_cta: Should return just the CTA string.
        """
        profile = {
            "email": "john@acme.com",
            "title": "VP Sales"
        }

        result = await llm_service.generate_cta(profile)

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_personalization_uses_profile_data(self, llm_service):
        """
        generate_personalization: Should use profile fields in output.
        Mock response should reference company/name.
        """
        profile = {
            "email": "alice@techcorp.io",
            "first_name": "Alice",
            "company_name": "TechCorp",
            "title": "CTO"
        }

        result = await llm_service.generate_personalization(profile)

        # Mock implementation references company in intro
        output_text = result["intro_hook"] + result["cta"]
        assert "TechCorp" in output_text or "Alice" in output_text

    @patch('app.services.llm_service.settings')
    def test_llm_service_init_with_providers(self, mock_settings):
        """
        LLMService init: Should initialize with available providers.
        """
        # Mock settings to have an API key
        mock_settings.ANTHROPIC_API_KEY = "mock-key-123"
        mock_settings.OPENAI_API_KEY = None
        mock_settings.GEMINI_API_KEY = None

        service = LLMService()

        # Should have providers list
        assert hasattr(service, 'providers')
        assert isinstance(service.providers, list)

    @patch('app.services.llm_service.settings')
    def test_llm_service_init_without_api_key(self, mock_settings):
        """
        LLMService init: Should work without API key (mock mode).
        """
        # Mock settings to have no API keys
        mock_settings.ANTHROPIC_API_KEY = None
        mock_settings.OPENAI_API_KEY = None
        mock_settings.GEMINI_API_KEY = None

        service = LLMService()

        # Should not raise; providers will be empty
        assert service is not None
        assert len(service.providers) == 0

    @pytest.mark.asyncio
    @patch('app.services.llm_service.settings')
    async def test_mock_response_includes_metadata(self, mock_settings):
        """
        Mock response: Should include model_used and latency metadata.
        """
        # Force mock mode by patching ALL API keys to None
        mock_settings.ANTHROPIC_API_KEY = None
        mock_settings.OPENAI_API_KEY = None
        mock_settings.GEMINI_API_KEY = None

        llm_service = LLMService()
        profile = {"email": "john@acme.com", "first_name": "John"}

        result = await llm_service.generate_personalization(profile)

        assert result["model_used"] == "mock"
        assert result["tokens_used"] == 0
        assert result["latency_ms"] == 0

    @pytest.mark.asyncio
    @patch('app.services.llm_service.settings')
    async def test_mock_response_raw_response_flagged(self, mock_settings):
        """
        Mock response: raw_response should have _mock flag.
        """
        # Force mock mode by patching ALL API keys to None
        mock_settings.ANTHROPIC_API_KEY = None
        mock_settings.OPENAI_API_KEY = None
        mock_settings.GEMINI_API_KEY = None

        llm_service = LLMService()
        profile = {"email": "john@acme.com"}

        result = await llm_service.generate_personalization(profile)

        assert result["raw_response"].get("_mock") is True


class TestPersonalizationQuality:
    """Tests for personalization content quality (mock mode)."""

    @pytest.mark.asyncio
    @patch('app.services.llm_service.settings')
    async def test_intro_hook_length(self, mock_settings):
        """
        Intro hook: Should respect max length constraint.
        """
        mock_settings.ANTHROPIC_API_KEY = None
        mock_settings.OPENAI_API_KEY = None
        mock_settings.GEMINI_API_KEY = None
        llm_service = LLMService()

        profile = {"email": "john@acme.com", "company_name": "Acme"}

        result = await llm_service.generate_intro_hook(profile)

        # Should be non-empty and within limits
        assert len(result) > 20
        assert len(result) <= MAX_INTRO_LENGTH

    @pytest.mark.asyncio
    @patch('app.services.llm_service.settings')
    async def test_cta_length(self, mock_settings):
        """
        CTA: Should respect max length constraint.
        """
        mock_settings.ANTHROPIC_API_KEY = None
        mock_settings.OPENAI_API_KEY = None
        mock_settings.GEMINI_API_KEY = None
        llm_service = LLMService()

        profile = {"email": "john@acme.com", "title": "VP Sales"}

        result = await llm_service.generate_cta(profile)

        # Should be non-empty and within limits
        assert len(result) > 10
        assert len(result) <= MAX_CTA_LENGTH

    @pytest.mark.asyncio
    @patch('app.services.llm_service.settings')
    async def test_personalization_not_generic(self, mock_settings):
        """
        Personalization: Should vary based on profile and user context.
        """
        mock_settings.ANTHROPIC_API_KEY = None
        mock_settings.OPENAI_API_KEY = None
        mock_settings.GEMINI_API_KEY = None
        llm_service = LLMService()

        profile1 = {
            "email": "john@acme.com",
            "first_name": "John",
            "company_name": "Acme",
            "title": "VP Sales"
        }
        profile2 = {
            "email": "alice@techcorp.io",
            "first_name": "Alice",
            "company_name": "TechCorp",
            "title": "CTO"
        }

        # Different user contexts
        user_context1 = {"goal": "exploring", "persona": "executive", "industry_input": "healthcare"}
        user_context2 = {"goal": "evaluating", "persona": "security", "industry_input": "financial_services"}

        result1 = await llm_service.generate_personalization(profile1, user_context=user_context1)
        result2 = await llm_service.generate_personalization(profile2, user_context=user_context2)

        # Each should produce different content based on user context
        assert result1["intro_hook"] != result2["intro_hook"]
        # Verify industry-specific content
        assert "healthcare" in result1["intro_hook"].lower() or "patient" in result1["intro_hook"].lower()
        assert "financial" in result2["intro_hook"].lower() or "risk" in result2["intro_hook"].lower()


class TestIndustryHooks:
    """Tests for industry-specific personalization (mock mode)."""

    @pytest.fixture
    @patch('app.services.llm_service.settings')
    def llm_service(self, mock_settings):
        mock_settings.ANTHROPIC_API_KEY = None
        mock_settings.OPENAI_API_KEY = None
        mock_settings.GEMINI_API_KEY = None
        return LLMService()

    @pytest.mark.asyncio
    @patch('app.services.llm_service.settings')
    async def test_technology_industry_hook(self, mock_settings):
        """Technology industry should get tech-specific hook."""
        mock_settings.ANTHROPIC_API_KEY = None
        mock_settings.OPENAI_API_KEY = None
        mock_settings.GEMINI_API_KEY = None
        llm_service = LLMService()

        profile = {
            "first_name": "John",
            "company_name": "TechCo",
        }
        user_context = {"industry_input": "technology"}

        result = await llm_service.generate_personalization(profile, user_context=user_context)

        # Mock response should contain technology-related language
        intro_lower = result["intro_hook"].lower()
        assert "tech" in intro_lower or "innovation" in intro_lower or "infrastructure" in intro_lower

    @pytest.mark.asyncio
    @patch('app.services.llm_service.settings')
    async def test_finance_industry_hook(self, mock_settings):
        """Financial services industry should get finance-specific hook."""
        mock_settings.ANTHROPIC_API_KEY = None
        mock_settings.OPENAI_API_KEY = None
        mock_settings.GEMINI_API_KEY = None
        llm_service = LLMService()

        profile = {
            "first_name": "Jane",
            "company_name": "FinCorp",
        }
        user_context = {"industry_input": "financial_services"}

        result = await llm_service.generate_personalization(profile, user_context=user_context)

        # Mock response should contain finance-related language
        intro_lower = result["intro_hook"].lower()
        assert "financial" in intro_lower or "regulatory" in intro_lower or "risk" in intro_lower


class TestShouldUseOpus:
    """Tests for Opus model selection logic."""

    def test_high_quality_uses_opus(self):
        """Should use Opus for high quality profiles."""
        service = LLMService()
        profile = {"data_quality_score": 0.9}

        assert service.should_use_opus(profile) is True

    def test_low_quality_uses_haiku(self):
        """Should use Haiku for low quality profiles."""
        service = LLMService()
        profile = {"data_quality_score": 0.3}

        assert service.should_use_opus(profile) is False

    def test_vip_domain_uses_opus(self):
        """Should use Opus for VIP domains."""
        service = LLMService()
        profile = {"domain": "google.com", "data_quality_score": 0.5}

        assert service.should_use_opus(profile) is True

    def test_non_vip_domain_quality_threshold(self):
        """Non-VIP domain should depend on quality score."""
        service = LLMService()
        profile = {"domain": "smallco.com", "data_quality_score": 0.5}

        assert service.should_use_opus(profile) is False


class TestPromptBuilding:
    """Tests for prompt construction."""

    def test_build_prompt_includes_name(self):
        """Prompt should include first name."""
        service = LLMService()
        profile = {"first_name": "John", "company_name": "Acme"}

        prompt = service._build_prompt(profile)

        assert "John" in prompt

    def test_build_prompt_includes_company(self):
        """Prompt should include company name."""
        service = LLMService()
        profile = {"first_name": "John", "company_name": "Acme Corp"}

        prompt = service._build_prompt(profile)

        assert "Acme Corp" in prompt

    def test_build_prompt_includes_title(self):
        """Prompt should include job title."""
        service = LLMService()
        profile = {"title": "VP Sales"}

        prompt = service._build_prompt(profile)

        assert "VP Sales" in prompt

    def test_build_prompt_includes_industry(self):
        """Prompt should include industry."""
        service = LLMService()
        profile = {"industry": "Technology"}

        prompt = service._build_prompt(profile)

        assert "Technology" in prompt

    def test_system_prompt_format(self):
        """System prompt should instruct JSON output."""
        service = LLMService()

        system_prompt = service._get_system_prompt()

        assert "JSON" in system_prompt
        assert "intro_hook" in system_prompt
        assert "cta" in system_prompt
