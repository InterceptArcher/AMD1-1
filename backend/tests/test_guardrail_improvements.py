"""
Tests for guardrail improvements:
1. Blocking personalization checks (priority→advantage, challenge→risk)
2. Case study relevance must mention industry or challenge
3. Company name in non-first items triggers failure
4. LLM-as-judge specificity scoring
5. End-to-end integration test

TDD: These tests are written FIRST and must FAIL before implementation.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.executive_review_service import (
    validate_executive_review_content,
    ExecutiveReviewService,
)


# =============================================================================
# HELPER: Build a valid content dict for testing
# =============================================================================

def _make_valid_content(
    company_name="Acme Corp",
    priority_keyword="cost",
    challenge_keyword="legacy",
    industry_keyword="healthcare",
    case_study_relevance=None,
):
    """Create content that passes baseline validation, with controllable personalization."""
    return {
        "company_name": company_name,
        "executive_summary": f"{company_name} operates in the {industry_keyword} sector where {priority_keyword} management and {challenge_keyword} system modernization are critical priorities. This assessment identifies targeted opportunities to improve infrastructure efficiency and operational performance across core {industry_keyword} workloads.",
        "advantages": [
            {
                "headline": f"Reducing {priority_keyword} through infrastructure upgrades",
                "description": f"By modernizing their core {industry_keyword} systems, {company_name} can significantly reduce operational overhead while improving system reliability and throughput across distributed operations. Targeting the highest-{priority_keyword} workloads first delivers measurable savings within the first quarter while building momentum for broader modernization initiatives.",
            },
            {
                "headline": "Scalable cloud architecture enables sustainable growth",
                "description": f"Moving to a distributed architecture allows the organization to handle increased demand without proportional increases in infrastructure spending or complexity. This scalable foundation supports future {industry_keyword} workload requirements while reducing the total cost of ownership compared to maintaining aging on-premises infrastructure.",
            },
        ],
        "risks": [
            {
                "headline": f"Persistent slowdowns from {challenge_keyword} system debt",
                "description": f"Without addressing aging {industry_keyword} infrastructure, the organization faces growing maintenance costs and declining system performance that impacts operations daily. These {challenge_keyword} system constraints compound over time, consuming an increasing share of IT budget while delivering diminishing returns on reliability and performance.",
            },
            {
                "headline": "Falling behind competitors in technology adoption",
                "description": "Organizations that delay modernization risk losing market position as competitors leverage newer technologies to deliver faster and more reliable services. Each quarter of delayed infrastructure investment widens the gap in operational efficiency and makes the eventual modernization effort more complex and expensive.",
            },
        ],
        "recommendations": [
            {
                "title": f"Prioritize {priority_keyword} reduction in core systems",
                "description": f"Begin with a focused assessment of highest-{priority_keyword} workloads at {company_name} to identify quick wins that demonstrate measurable value within the first quarter. Target systems with the most expensive maintenance contracts or upcoming renewal deadlines, as these represent the clearest opportunities to reduce spend.",
            },
            {
                "title": "Establish a phased migration roadmap for modernization",
                "description": "Create a structured plan that moves workloads to modern infrastructure in stages, starting with low-risk applications to build confidence and momentum. This phased approach reduces operational risk while allowing teams to develop the skills and processes needed for more complex migrations.",
            },
            {
                "title": "Build internal expertise through targeted training programs",
                "description": "Invest in upskilling the existing team on modern infrastructure technologies and operational practices to reduce dependency on external consultants and accelerate delivery. Role-specific certification paths ensure that training investments translate directly into improved capability for maintaining modernized systems.",
            },
        ],
        "case_study_relevance": case_study_relevance or f"This case study demonstrates how {industry_keyword} organizations have successfully addressed {challenge_keyword} system challenges through AMD-powered data center modernization. Their phased approach to consolidation and infrastructure upgrades mirrors the path forward for organizations facing similar constraints in the {industry_keyword} sector.",
    }


# =============================================================================
# Test 1: Personalization checks are BLOCKING
# =============================================================================

class TestBlockingPersonalizationChecks:
    """Advantage 1 must reference priority, Risk 1 must reference challenge."""

    def test_advantage_without_priority_keyword_fails(self):
        """If advantage[0] doesn't reference the priority, validation should fail."""
        content = _make_valid_content(priority_keyword="cost")
        # Overwrite advantage 0 with generic content that doesn't mention priority
        content["advantages"][0]["headline"] = "Modernizing enterprise server infrastructure"
        content["advantages"][0]["description"] = (
            "Upgrading from older generation hardware to newer platforms enables the organization "
            "to handle increased workloads with greater efficiency and lower maintenance burden."
        )

        result = validate_executive_review_content(
            content, priority="Reducing cost", challenge="Legacy systems", industry="Healthcare"
        )
        assert not result["passed"], "Should fail when advantage[0] doesn't reference priority"
        personalization_failures = [f for f in result["failures"] if "priority" in f["reason"].lower()]
        assert len(personalization_failures) > 0

    def test_risk_without_challenge_keyword_fails(self):
        """If risk[0] doesn't reference the challenge, validation should fail."""
        content = _make_valid_content(challenge_keyword="legacy")
        # Overwrite risk 0 with generic content that doesn't mention challenge
        content["risks"][0]["headline"] = "Performance degradation across computing workloads"
        content["risks"][0]["description"] = (
            "Without a proactive modernization plan, the organization may experience diminishing "
            "returns on existing infrastructure investments as workload demands continue growing."
        )

        result = validate_executive_review_content(
            content, priority="Reducing cost", challenge="Legacy systems", industry="Healthcare"
        )
        assert not result["passed"], "Should fail when risk[0] doesn't reference challenge"
        challenge_failures = [f for f in result["failures"] if "challenge" in f["reason"].lower()]
        assert len(challenge_failures) > 0

    def test_valid_personalization_passes(self):
        """Content that references both priority and challenge should pass."""
        content = _make_valid_content(
            priority_keyword="cost",
            challenge_keyword="legacy",
            industry_keyword="healthcare",
        )
        result = validate_executive_review_content(
            content, priority="Reducing cost", challenge="Legacy systems", industry="Healthcare"
        )
        personalization_failures = [
            f for f in result["failures"]
            if "priority" in f["reason"].lower() or "challenge" in f["reason"].lower()
        ]
        assert len(personalization_failures) == 0, f"Unexpected personalization failures: {personalization_failures}"


# =============================================================================
# Test 2: Case study relevance must mention industry or challenge
# =============================================================================

class TestCaseStudyRelevanceValidation:
    """case_study_relevance must specifically mention the user's industry or challenge."""

    def test_generic_relevance_fails(self):
        """A relevance string that doesn't mention industry or challenge should fail."""
        content = _make_valid_content(
            case_study_relevance="This case study demonstrates how organizations can modernize their infrastructure and achieve better results through strategic technology investments."
        )
        result = validate_executive_review_content(
            content, priority="Reducing cost", challenge="Legacy systems", industry="Healthcare"
        )
        relevance_failures = [f for f in result["failures"] if "case_study_relevance" in f["field"]]
        assert len(relevance_failures) > 0, "Generic case_study_relevance should fail"

    def test_relevance_with_industry_passes(self):
        """Relevance that mentions the industry should pass this check."""
        content = _make_valid_content(
            case_study_relevance="This case study demonstrates how healthcare organizations can modernize their infrastructure through AMD-powered data center upgrades for better outcomes."
        )
        result = validate_executive_review_content(
            content, priority="Reducing cost", challenge="Legacy systems", industry="Healthcare"
        )
        relevance_failures = [f for f in result["failures"] if "case_study_relevance" in f["field"] and "industry" in f["reason"].lower()]
        assert len(relevance_failures) == 0

    def test_relevance_with_challenge_passes(self):
        """Relevance that mentions the challenge should pass this check."""
        content = _make_valid_content(
            case_study_relevance="This case study shows how addressing legacy system constraints through AMD infrastructure enables organizations to regain competitive advantage and operational speed."
        )
        result = validate_executive_review_content(
            content, priority="Reducing cost", challenge="Legacy systems", industry="Healthcare"
        )
        relevance_failures = [f for f in result["failures"] if "case_study_relevance" in f["field"] and "industry" in f["reason"].lower()]
        assert len(relevance_failures) == 0


# =============================================================================
# Test 3: Company name in non-first items triggers failure
# =============================================================================

class TestCompanyNameRepetition:
    """Company name should only appear in first item of each section."""

    def test_company_name_in_second_advantage_fails(self):
        """Company name in advantage[1] should trigger a failure."""
        content = _make_valid_content(company_name="Acme Corp")
        content["advantages"][1]["description"] = (
            "Acme Corp can leverage distributed architecture to handle increased demand "
            "without proportional increases in infrastructure spending or operational complexity."
        )
        result = validate_executive_review_content(content)
        name_failures = [f for f in result["failures"] if "company name" in f["reason"].lower()]
        assert len(name_failures) > 0, "Company name in second item should fail"

    def test_company_name_only_in_first_item_passes(self):
        """Company name only in first item of each section should pass."""
        content = _make_valid_content(company_name="Acme Corp")
        result = validate_executive_review_content(content)
        name_failures = [f for f in result["failures"] if "company name" in f["reason"].lower()]
        assert len(name_failures) == 0, f"Unexpected company name failures: {name_failures}"


# =============================================================================
# Test 4: LLM-as-judge specificity scoring
# =============================================================================

class TestLLMSpecificityJudge:
    """LLM-as-judge should reject generic content that lacks industry specificity."""

    @pytest.mark.asyncio
    async def test_judge_rejects_generic_content(self):
        """When the LLM judge returns a low score, content should be flagged as non-specific."""
        service = ExecutiveReviewService()

        generic_content = _make_valid_content(
            industry_keyword="business",
            priority_keyword="efficiency",
            challenge_keyword="system",
        )

        # Mock the Anthropic client to return a low score
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"score": 2, "reason": "Content is generic and could apply to any industry."}')]
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        service.client = mock_client

        result = await service.judge_content_specificity(
            generic_content, industry="Healthcare", persona="ITDM"
        )
        assert result["is_specific"] is False, "Generic content should be flagged as non-specific"
        assert result["score"] == 2

    @pytest.mark.asyncio
    async def test_judge_accepts_specific_content(self):
        """When the LLM judge returns a high score, content should pass."""
        service = ExecutiveReviewService()

        specific_content = _make_valid_content(
            industry_keyword="healthcare",
            priority_keyword="cost",
            challenge_keyword="legacy",
        )

        # Mock the Anthropic client to return a high score
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"score": 4, "reason": "Content uses healthcare-specific terminology and references relevant systems."}')]
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        service.client = mock_client

        result = await service.judge_content_specificity(
            specific_content, industry="Healthcare", persona="ITDM"
        )
        assert result["is_specific"] is True, "Industry-specific content should pass"
        assert result["score"] == 4

    @pytest.mark.asyncio
    async def test_judge_handles_markdown_fenced_json(self):
        """Judge should parse JSON wrapped in markdown code blocks."""
        service = ExecutiveReviewService()
        content = _make_valid_content()

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='```json\n{"score": 3, "reason": "Moderate specificity."}\n```')]
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        service.client = mock_client

        result = await service.judge_content_specificity(content, industry="Healthcare", persona="ITDM")
        assert result["is_specific"] is True
        assert result["score"] == 3

    @pytest.mark.asyncio
    async def test_judge_graceful_on_api_failure(self):
        """Judge should not block on API errors — assumes specific."""
        service = ExecutiveReviewService()
        content = _make_valid_content()

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=Exception("API timeout"))
        service.client = mock_client

        result = await service.judge_content_specificity(content, industry="Healthcare", persona="ITDM")
        assert result["is_specific"] is True, "Should not block on judge failure"
        assert "Judge error" in result["reason"]


# =============================================================================
# Test 5: End-to-end integration test (against live API)
# =============================================================================

class TestEndToEndIntegration:
    """Smoke test the full executive review pipeline."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not (
            __import__("os").environ.get("ANTHROPIC_API_KEY")
            and __import__("os").environ.get("RUN_INTEGRATION_TESTS") == "true"
        ),
        reason="Integration test - requires ANTHROPIC_API_KEY and RUN_INTEGRATION_TESTS=true",
    )
    async def test_full_generation_passes_all_guardrails(self):
        """Full LLM generation should produce content that passes every guardrail."""
        service = ExecutiveReviewService()

        result = await service.generate_executive_review(
            company_name="Stripe",
            industry="Financial Services",
            segment="Enterprise",
            persona="ITDM",
            stage="Challenger",
            priority="Improving workload performance",
            challenge="Integration friction",
        )

        # Verify structure
        assert "advantages" in result
        assert "risks" in result
        assert "recommendations" in result
        assert len(result["advantages"]) == 2
        assert len(result["risks"]) == 2
        assert len(result["recommendations"]) == 3

        # Run full validation
        validation = validate_executive_review_content(
            result,
            priority="Improving workload performance",
            challenge="Integration friction",
            industry="Financial Services",
        )
        assert validation["passed"], f"Validation failed: {validation['failures']}"

        # Verify case study populated
        assert result.get("case_study"), "Case study should be populated"
        assert result.get("case_study_description"), "Case study description should be populated"

        # Verify stage fields
        assert result["stage"] == "Challenger"
        assert result["stage_sidebar"]
        assert result["stage_identification_text"]
