"""
Tests for LLM service personalization generation.
Mocked Claude API calls; no real LLM inference.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.llm_service import LLMService


@pytest.mark.asyncio
class TestLLMService:
    """Tests for LLMService personalization generation."""

    @pytest.fixture
    def llm_service(self, mock_llm_service):
        """Fixture: LLM service for testing."""
        return mock_llm_service

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
            "company_name": "Acme"
        }
        
        result = await llm_service.generate_intro_hook(profile)
        
        assert isinstance(result, str)
        assert len(result) > 0
        # Alpha: Synthetic response should contain company name
        assert "Acme" in result or "John" in result

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
        Alpha: Synthetic response should reference company/name.
        """
        profile = {
            "email": "alice@techcorp.io",
            "first_name": "Alice",
            "company_name": "TechCorp",
            "title": "CTO"
        }
        
        result = await llm_service.generate_personalization(profile)
        
        # Alpha implementation references email/company
        output_text = result["intro_hook"] + result["cta"]
        assert "TechCorp" in output_text or "alice" in output_text

    def test_llm_service_init_with_api_key(self):
        """
        LLMService init: Should accept optional API key.
        """
        service = LLMService(api_key="mock-key-123")
        
        assert service.api_key == "mock-key-123"

    def test_llm_service_init_without_api_key(self):
        """
        LLMService init: Should work without API key (uses env).
        """
        service = LLMService()
        
        # Should not raise; api_key will be None
        assert service is not None


class TestPersonalizationQuality:
    """Tests for personalization content quality."""

    @pytest.mark.asyncio
    async def test_intro_hook_length(self, mock_llm_service):
        """
        Intro hook: Should be 1-2 sentences (roughly 20-100 words).
        """
        profile = {"email": "john@acme.com", "company_name": "Acme"}
        
        result = await mock_llm_service.generate_intro_hook(profile)
        
        # Alpha: Should be reasonable length
        assert len(result) > 20
        assert len(result) < 200

    @pytest.mark.asyncio
    async def test_cta_length(self, mock_llm_service):
        """
        CTA: Should be concise (roughly 10-50 words).
        """
        profile = {"email": "john@acme.com", "title": "VP Sales"}
        
        result = await mock_llm_service.generate_cta(profile)
        
        # Alpha: Should be reasonable length
        assert len(result) > 10
        assert len(result) < 150

    @pytest.mark.asyncio
    async def test_personalization_not_generic(self, mock_llm_service):
        """
        Personalization: Should vary based on profile (not completely generic).
        """
        profile1 = {
            "email": "john@acme.com",
            "company_name": "Acme",
            "title": "VP Sales"
        }
        profile2 = {
            "email": "alice@techcorp.io",
            "company_name": "TechCorp",
            "title": "CTO"
        }
        
        result1 = await mock_llm_service.generate_personalization(profile1)
        result2 = await mock_llm_service.generate_personalization(profile2)
        
        # Alpha: Both should have different company/title references
        assert "Acme" in result1["intro_hook"] or "john" in result1["intro_hook"]
        assert "TechCorp" in result2["intro_hook"] or "alice" in result2["intro_hook"]
