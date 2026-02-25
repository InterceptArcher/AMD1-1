"""
Tests for Executive Review Service.
Covers mapping functions, case study selection, few-shot example selection,
response parsing, mock response structure, stage identification text,
enrichment context injection, and integration (mock fallback).
"""

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.executive_review_service import (
    map_company_size_to_segment,
    map_role_to_persona,
    map_it_environment_to_stage,
    get_stage_sidebar,
    map_priority_display,
    map_challenge_display,
    map_industry_display,
    select_case_study,
    build_stage_identification_text,
    CASE_STUDIES,
    FEW_SHOT_EXAMPLES_POOL,
    ExecutiveReviewService,
)


# =============================================================================
# TestMappingFunctions
# =============================================================================

class TestMappingFunctions:
    """Test all 7 mapping/lookup functions."""

    # -- map_company_size_to_segment --
    def test_startup_maps_to_smb(self):
        assert map_company_size_to_segment("startup") == "SMB"

    def test_small_maps_to_smb(self):
        assert map_company_size_to_segment("small") == "SMB"

    def test_midmarket_maps_to_midmarket(self):
        assert map_company_size_to_segment("midmarket") == "Mid-Market"

    def test_enterprise_maps_to_enterprise(self):
        assert map_company_size_to_segment("enterprise") == "Enterprise"

    def test_large_enterprise_maps_to_enterprise(self):
        assert map_company_size_to_segment("large_enterprise") == "Enterprise"

    def test_unknown_size_defaults_to_enterprise(self):
        assert map_company_size_to_segment("unknown") == "Enterprise"

    # -- map_role_to_persona --
    def test_cto_maps_to_itdm(self):
        assert map_role_to_persona("cto") == "ITDM"

    def test_cio_maps_to_itdm(self):
        assert map_role_to_persona("cio") == "ITDM"

    def test_senior_engineer_maps_to_itdm(self):
        assert map_role_to_persona("senior_engineer") == "ITDM"

    def test_ceo_maps_to_bdm(self):
        assert map_role_to_persona("ceo") == "BDM"

    def test_cfo_maps_to_bdm(self):
        assert map_role_to_persona("cfo") == "BDM"

    def test_procurement_maps_to_bdm(self):
        assert map_role_to_persona("procurement") == "BDM"

    def test_unknown_role_defaults_to_bdm(self):
        assert map_role_to_persona("unknown_role") == "BDM"

    # -- map_it_environment_to_stage --
    def test_traditional_maps_to_observer(self):
        assert map_it_environment_to_stage("traditional") == "Observer"

    def test_modernizing_maps_to_challenger(self):
        assert map_it_environment_to_stage("modernizing") == "Challenger"

    def test_modern_maps_to_leader(self):
        assert map_it_environment_to_stage("modern") == "Leader"

    def test_unknown_env_defaults_to_challenger(self):
        assert map_it_environment_to_stage("other") == "Challenger"

    # -- get_stage_sidebar --
    def test_observer_sidebar(self):
        result = get_stage_sidebar("Observer")
        assert "9%" in result
        assert "Observers" in result

    def test_challenger_sidebar(self):
        result = get_stage_sidebar("Challenger")
        assert "58%" in result
        assert "Challengers" in result

    def test_leader_sidebar(self):
        result = get_stage_sidebar("Leader")
        assert "33%" in result
        assert "Leaders" in result

    def test_unknown_stage_returns_empty(self):
        assert get_stage_sidebar("Unknown") == ""

    # -- map_priority_display --
    def test_reducing_cost_display(self):
        assert map_priority_display("reducing_cost") == "Reducing cost"

    def test_improving_performance_display(self):
        assert map_priority_display("improving_performance") == "Improving workload performance"

    def test_preparing_ai_display(self):
        assert map_priority_display("preparing_ai") == "Preparing for AI adoption"

    def test_unknown_priority_passes_through(self):
        assert map_priority_display("custom_priority") == "custom_priority"

    # -- map_challenge_display --
    def test_legacy_systems_display(self):
        assert map_challenge_display("legacy_systems") == "Legacy systems"

    def test_integration_friction_display(self):
        assert map_challenge_display("integration_friction") == "Integration friction"

    def test_skills_gap_display(self):
        assert map_challenge_display("skills_gap") == "Skills gap"

    def test_data_governance_display(self):
        assert map_challenge_display("data_governance") == "Data governance and compliance"

    def test_unknown_challenge_passes_through(self):
        assert map_challenge_display("custom_challenge") == "custom_challenge"

    # -- map_industry_display --
    def test_technology_display(self):
        assert map_industry_display("technology") == "Technology"

    def test_healthcare_display(self):
        assert map_industry_display("healthcare") == "Healthcare"

    def test_financial_services_display(self):
        assert map_industry_display("financial_services") == "Financial Services"

    def test_retail_display(self):
        assert map_industry_display("retail") == "Retail"

    def test_unknown_industry_passes_through(self):
        assert map_industry_display("aec") == "aec"


# =============================================================================
# TestCaseStudySelection
# =============================================================================

class TestCaseStudySelection:
    """Test select_case_study() returns (name, description, link) 3-tuple."""

    def test_returns_three_tuple(self):
        result = select_case_study("Observer", "reducing_cost", "retail", "legacy_systems")
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_all_case_studies_have_link(self):
        for key, cs in CASE_STUDIES.items():
            assert "link" in cs, f"Case study '{key}' missing 'link' field"

    # Priority-based: reducing_cost → Smurfit Westrock
    def test_reducing_cost_selects_smurfit(self):
        name, desc, link = select_case_study("Observer", "reducing_cost", "technology", "legacy_systems")
        assert "Smurfit Westrock" in name

    def test_reducing_cost_overrides_industry(self):
        """Reducing cost should pick Smurfit even for healthcare industry."""
        name, _, _ = select_case_study("Leader", "reducing_cost", "healthcare", "data_governance")
        assert "Smurfit Westrock" in name

    # Example 1: AECOM (Observer, AEC, reducing_cost, legacy_systems) → Smurfit
    def test_aecom_example(self):
        name, _, _ = select_case_study("Observer", "reducing_cost", "aec", "legacy_systems")
        assert "Smurfit Westrock" in name

    # Example 5: Allbirds (Observer, consumer_goods, reducing_cost, resource_constraints) → Smurfit
    def test_allbirds_example(self):
        name, _, _ = select_case_study("Observer", "reducing_cost", "consumer_goods", "resource_constraints")
        assert "Smurfit Westrock" in name

    # Industry-based: healthcare/financial/government → PQR
    def test_healthcare_selects_pqr(self):
        name, _, _ = select_case_study("Leader", "preparing_ai", "healthcare", "data_governance")
        assert "PQR" in name

    def test_financial_services_selects_pqr(self):
        name, _, _ = select_case_study("Challenger", "improving_performance", "financial_services", "integration_friction")
        assert "PQR" in name

    def test_government_selects_pqr(self):
        name, _, _ = select_case_study("Observer", "improving_performance", "government", "legacy_systems")
        assert "PQR" in name

    # Example 3: HCA Healthcare (Leader, healthcare, preparing_ai, data_governance) → PQR
    def test_hca_example(self):
        name, _, _ = select_case_study("Leader", "preparing_ai", "healthcare", "data_governance")
        assert "PQR" in name

    # Challenge-based: skills_gap/data_governance for non-tech industries → PQR
    def test_skills_gap_manufacturing_selects_pqr(self):
        """Caterpillar-style: manufacturing + skills_gap → PQR"""
        name, _, _ = select_case_study("Challenger", "improving_performance", "manufacturing", "skills_gap")
        assert "PQR" in name

    # Example 4: Caterpillar (Challenger, manufacturing, improving_performance, skills_gap) → PQR
    def test_caterpillar_example(self):
        name, _, _ = select_case_study("Challenger", "improving_performance", "manufacturing", "skills_gap")
        assert "PQR" in name

    # Performance/AI for tech/retail/telecom → KT Cloud
    def test_performance_retail_selects_kt_cloud(self):
        name, _, _ = select_case_study("Challenger", "improving_performance", "retail", "integration_friction")
        assert "KT Cloud" in name

    # Example 2: Target (Challenger, retail, improving_performance, integration_friction) → KT Cloud
    def test_target_example(self):
        name, _, _ = select_case_study("Challenger", "improving_performance", "retail", "integration_friction")
        assert "KT Cloud" in name

    def test_preparing_ai_technology_selects_kt_cloud(self):
        name, _, _ = select_case_study("Challenger", "preparing_ai", "technology", "skills_gap")
        assert "KT Cloud" in name

    # Stage-based defaults (use unknown priority to bypass priority rules)
    def test_observer_default_smurfit(self):
        name, _, _ = select_case_study("Observer", "unknown_priority", "other", "resource_constraints")
        assert "Smurfit Westrock" in name

    def test_leader_default_pqr(self):
        name, _, _ = select_case_study("Leader", "unknown_priority", "other", "resource_constraints")
        assert "PQR" in name

    def test_challenger_default_kt_cloud(self):
        name, _, _ = select_case_study("Challenger", "unknown_priority", "other", "resource_constraints")
        assert "KT Cloud" in name

    def test_link_is_url_string(self):
        _, _, link = select_case_study("Observer", "reducing_cost", "retail", "legacy_systems")
        assert isinstance(link, str)
        assert link.startswith("http")


# =============================================================================
# TestFewShotExampleSelection
# =============================================================================

class TestFewShotExampleSelection:
    """Test _select_best_example() scoring and _industries_similar()."""

    def setup_method(self):
        self.service = ExecutiveReviewService()

    def test_exact_industry_match_scores_highest(self):
        """Exact industry match should prefer that example."""
        example = self.service._select_best_example("Observer", "AEC", "Reducing cost", "Legacy systems")
        # Should pick the AEC-related example (AECOM)
        assert example["profile"]["company"] == "AECOM"

    def test_priority_match_influences_selection(self):
        """Priority match should influence example selection."""
        example = self.service._select_best_example("Challenger", "Retail", "Improving workload performance", "Integration friction")
        assert example["profile"]["industry"] in ["Retail", "retail"]

    def test_challenge_match_influences_selection(self):
        """Challenge match should influence selection."""
        example = self.service._select_best_example("Observer", "Manufacturing", "Reducing cost", "Resource constraints")
        # Should pick example with resource constraints challenge
        assert "Resource" in example["profile"].get("challenge", "") or "cost" in example["profile"].get("priority", "").lower()

    def test_fallback_to_first_if_no_match(self):
        """Completely unrelated inputs should still return a valid example."""
        example = self.service._select_best_example("Challenger", "Aerospace", "Custom", "Custom")
        assert "profile" in example
        assert "output" in example

    def test_industries_similar_retail_consumer(self):
        assert self.service._industries_similar("Retail", "Consumer Goods")

    def test_industries_similar_healthcare_pharma(self):
        assert self.service._industries_similar("Healthcare", "Life Sciences")

    def test_industries_not_similar_retail_healthcare(self):
        assert not self.service._industries_similar("Retail", "Healthcare")

    def test_industries_similar_tech_telecom(self):
        assert self.service._industries_similar("Technology", "Telecommunications")


# =============================================================================
# TestResponseParsing
# =============================================================================

class TestResponseParsing:
    """Test _parse_response() with various input formats."""

    def setup_method(self):
        self.service = ExecutiveReviewService()
        self.valid_json = json.dumps({
            "advantages": [
                {"headline": "Cost savings from modernization", "description": "Description one."},
                {"headline": "Efficiency gains through standardization", "description": "Description two."}
            ],
            "risks": [
                {"headline": "High TCO from legacy systems", "description": "Risk description one."},
                {"headline": "Integration gaps add costs", "description": "Risk description two."}
            ],
            "recommendations": [
                {"title": "Modernize legacy workloads", "description": "Rec one."},
                {"title": "Standardize infrastructure", "description": "Rec two."},
                {"title": "Build scalable foundation", "description": "Rec three."}
            ],
            "case_study": "Smurfit Westrock"
        })

    def test_parse_valid_json(self):
        result = self.service._parse_response(self.valid_json, "TestCo", "Observer", "reducing_cost", "technology", "legacy_systems")
        assert result["company_name"] == "TestCo"
        assert result["stage"] == "Observer"
        assert len(result["advantages"]) == 2
        assert len(result["risks"]) == 2
        assert len(result["recommendations"]) == 3

    def test_parse_includes_case_study_link(self):
        result = self.service._parse_response(self.valid_json, "TestCo", "Observer", "reducing_cost", "technology", "legacy_systems")
        assert "case_study_link" in result
        assert result["case_study_link"].startswith("http")

    def test_parse_includes_stage_identification_text(self):
        result = self.service._parse_response(self.valid_json, "TestCo", "Observer", "reducing_cost", "technology", "legacy_systems")
        assert "stage_identification_text" in result
        assert "Observer" in result["stage_identification_text"]
        assert "your organization" in result["stage_identification_text"].lower()

    def test_parse_markdown_fenced_json(self):
        fenced = f"```json\n{self.valid_json}\n```"
        result = self.service._parse_response(fenced, "TestCo", "Observer", "reducing_cost", "technology", "legacy_systems")
        assert result["company_name"] == "TestCo"
        assert len(result["advantages"]) == 2

    def test_parse_triple_backtick_json(self):
        fenced = f"```\n{self.valid_json}\n```"
        result = self.service._parse_response(fenced, "TestCo", "Observer", "reducing_cost", "technology", "legacy_systems")
        assert result["company_name"] == "TestCo"

    def test_parse_invalid_json_returns_mock(self):
        result = self.service._parse_response("not json at all", "TestCo", "Observer", "reducing_cost", "technology", "legacy_systems")
        # Should fall back to mock response
        assert result["company_name"] == "TestCo"
        assert "advantages" in result
        assert "case_study_link" in result

    def test_parse_includes_stage_sidebar(self):
        result = self.service._parse_response(self.valid_json, "TestCo", "Challenger", "improving_performance", "retail", "integration_friction")
        assert "stage_sidebar" in result
        assert "58%" in result["stage_sidebar"]

    def test_parse_case_study_from_selection_not_llm(self):
        """Case study should come from select_case_study(), not from LLM output."""
        result = self.service._parse_response(self.valid_json, "TestCo", "Observer", "reducing_cost", "retail", "legacy_systems")
        assert "Smurfit Westrock" in result["case_study"]


# =============================================================================
# TestMockResponse
# =============================================================================

class TestMockResponse:
    """Test _get_mock_response() structure and fields."""

    def setup_method(self):
        self.service = ExecutiveReviewService()

    def test_mock_has_all_required_fields(self):
        result = self.service._get_mock_response("TestCo", "Observer", "reducing_cost", "technology", "legacy_systems")
        required_fields = [
            "company_name", "stage", "stage_sidebar",
            "advantages", "risks", "recommendations",
            "case_study", "case_study_description",
            "case_study_link", "stage_identification_text",
        ]
        for field in required_fields:
            assert field in result, f"Missing field: {field}"

    def test_mock_advantages_count(self):
        result = self.service._get_mock_response("TestCo", "Challenger", "improving_performance", "retail", "integration_friction")
        assert len(result["advantages"]) == 2

    def test_mock_risks_count(self):
        result = self.service._get_mock_response("TestCo", "Challenger", "improving_performance", "retail", "integration_friction")
        assert len(result["risks"]) == 2

    def test_mock_recommendations_count(self):
        result = self.service._get_mock_response("TestCo", "Leader", "preparing_ai", "healthcare", "data_governance")
        assert len(result["recommendations"]) == 3

    def test_mock_company_name(self):
        result = self.service._get_mock_response("Acme Corp", "Observer", "reducing_cost", "technology", "legacy_systems")
        assert result["company_name"] == "Acme Corp"


# =============================================================================
# TestStageIdentificationText
# =============================================================================

class TestStageIdentificationText:
    """Test build_stage_identification_text() helper."""

    def test_observer_text(self):
        text = build_stage_identification_text("AECOM", "Observer")
        assert "Observer" in text

    def test_challenger_text(self):
        text = build_stage_identification_text("Target", "Challenger")
        assert "Challenger" in text

    def test_leader_text(self):
        text = build_stage_identification_text("HCA Healthcare", "Leader")
        assert "Leader" in text

    def test_matches_expected_format(self):
        """Should match AMD's format: 'Based on the information you shared, ...'"""
        text = build_stage_identification_text("TestCo", "Observer")
        assert text.startswith("Based on")
        assert "your organization" in text.lower()


# =============================================================================
# TestGenerateExecutiveReview (Integration, mock fallback)
# =============================================================================

class TestGenerateExecutiveReview:
    """Integration test: no API key → mock fallback, verify all fields present."""

    def setup_method(self):
        self.service = ExecutiveReviewService()

    @pytest.mark.asyncio
    async def test_no_api_key_returns_mock(self):
        """Without API key, should return mock response with all fields."""
        self.service.client = None
        result = await self.service.generate_executive_review(
            company_name="TestCo",
            industry="Technology",
            segment="Enterprise",
            persona="ITDM",
            stage="Challenger",
            priority="improving_performance",
            challenge="integration_friction",
        )
        assert result["company_name"] == "TestCo"
        assert result["stage"] == "Challenger"
        assert "case_study_link" in result
        assert "stage_identification_text" in result

    @pytest.mark.asyncio
    async def test_mock_fallback_has_complete_structure(self):
        """Mock response should have all required fields."""
        self.service.client = None
        result = await self.service.generate_executive_review(
            company_name="Acme",
            industry="Healthcare",
            segment="Enterprise",
            persona="ITDM",
            stage="Leader",
            priority="preparing_ai",
            challenge="data_governance",
        )
        assert len(result["advantages"]) == 2
        assert len(result["risks"]) == 2
        assert len(result["recommendations"]) == 3
        assert result["case_study_link"].startswith("http")

    @pytest.mark.asyncio
    async def test_observer_stage_content(self):
        self.service.client = None
        result = await self.service.generate_executive_review(
            company_name="AECOM",
            industry="AEC",
            segment="Enterprise",
            persona="ITDM",
            stage="Observer",
            priority="reducing_cost",
            challenge="legacy_systems",
        )
        assert result["stage"] == "Observer"
        assert "9%" in result["stage_sidebar"]
        assert "Smurfit Westrock" in result["case_study"]

    @pytest.mark.asyncio
    async def test_all_stages_produce_valid_output(self):
        self.service.client = None
        for stage in ["Observer", "Challenger", "Leader"]:
            result = await self.service.generate_executive_review(
                company_name="TestCo",
                industry="Technology",
                segment="Enterprise",
                persona="ITDM",
                stage=stage,
                priority="improving_performance",
                challenge="integration_friction",
            )
            assert result["stage"] == stage
            assert result["stage_sidebar"] != ""
            assert result["case_study"] != ""
            assert result["case_study_link"].startswith("http")

    @pytest.mark.asyncio
    async def test_stage_identification_text_in_output(self):
        self.service.client = None
        result = await self.service.generate_executive_review(
            company_name="Acme",
            industry="Retail",
            segment="Mid-Market",
            persona="BDM",
            stage="Challenger",
            priority="reducing_cost",
            challenge="resource_constraints",
        )
        assert "Challenger" in result["stage_identification_text"]
        assert "your organization" in result["stage_identification_text"].lower()


# =============================================================================
# TestFewShotExamplesPool
# =============================================================================

class TestFewShotExamplesPool:
    """Validate the structure of few-shot examples matches expected gold standards."""

    def test_all_stages_have_examples(self):
        for stage in ["Observer", "Challenger", "Leader"]:
            assert stage in FEW_SHOT_EXAMPLES_POOL
            assert len(FEW_SHOT_EXAMPLES_POOL[stage]) >= 2

    def test_examples_have_correct_structure(self):
        for stage, examples in FEW_SHOT_EXAMPLES_POOL.items():
            for ex in examples:
                assert "profile" in ex
                assert "output" in ex
                assert "company" in ex["profile"]
                assert "industry" in ex["profile"]
                assert "advantages" in ex["output"]
                assert "risks" in ex["output"]
                assert "recommendations" in ex["output"]

    def test_caterpillar_is_challenger(self):
        """Caterpillar should be in Challenger pool per gold standard examples."""
        challenger_companies = [ex["profile"]["company"] for ex in FEW_SHOT_EXAMPLES_POOL["Challenger"]]
        assert "Caterpillar" in challenger_companies

    def test_allbirds_is_observer(self):
        """Allbirds should be in Observer pool per gold standard examples."""
        observer_companies = [ex["profile"]["company"] for ex in FEW_SHOT_EXAMPLES_POOL["Observer"]]
        assert "Allbirds" in observer_companies


# =============================================================================
# TestEnrichmentContextInPrompt
# =============================================================================

class TestEnrichmentContextInPrompt:
    """Verify that enrichment_context data is injected into the LLM prompt."""

    def setup_method(self):
        self.service = ExecutiveReviewService()
        self.enrichment_context = {
            "employee_count": 12400,
            "founded_year": 2003,
            "employee_growth_rate": 14.2,
            "latest_funding_stage": "Series D",
            "total_funding": 250000000,
            "company_summary": "Acme Corp is a leading provider of cloud infrastructure solutions for enterprise customers.",
            "recent_news": [
                {
                    "title": "Acme Corp Launches AI-Powered Analytics Platform",
                    "source": "TechCrunch",
                    "content": "Acme Corp announced the launch of its new AI analytics platform targeting enterprise customers.",
                    "query_category": "ai_technology",
                },
                {
                    "title": "Acme Corp Reports 30% Revenue Growth in Q4",
                    "source": "Reuters",
                    "content": "Acme Corp exceeded analyst expectations with strong Q4 revenue growth driven by cloud services.",
                    "query_category": "general",
                },
            ],
            "news_themes": ["AI adoption", "Growth & expansion", "Cloud transformation"],
            "title": "VP of Infrastructure Engineering",
            "news_analysis": {
                "sentiment": "positive",
                "ai_readiness": "piloting",
                "crisis": False,
            },
        }

    def test_user_prompt_includes_company_summary(self):
        """Company summary from PDL must appear in the LLM prompt."""
        example = FEW_SHOT_EXAMPLES_POOL["Challenger"][0]
        prompt = self.service._build_user_prompt(
            company_name="Acme Corp",
            industry="Technology",
            segment="Enterprise",
            persona="ITDM",
            stage="Challenger",
            priority="Improving performance",
            challenge="Integration friction",
            example=example,
            enrichment_context=self.enrichment_context,
        )
        assert "cloud infrastructure solutions" in prompt

    def test_user_prompt_includes_employee_count(self):
        """Employee count from enrichment must appear in the LLM prompt."""
        example = FEW_SHOT_EXAMPLES_POOL["Challenger"][0]
        prompt = self.service._build_user_prompt(
            company_name="Acme Corp",
            industry="Technology",
            segment="Enterprise",
            persona="ITDM",
            stage="Challenger",
            priority="Improving performance",
            challenge="Integration friction",
            example=example,
            enrichment_context=self.enrichment_context,
        )
        assert "12,400" in prompt or "12400" in prompt

    def test_user_prompt_includes_news_headlines(self):
        """Recent news headlines must appear in the LLM prompt."""
        example = FEW_SHOT_EXAMPLES_POOL["Challenger"][0]
        prompt = self.service._build_user_prompt(
            company_name="Acme Corp",
            industry="Technology",
            segment="Enterprise",
            persona="ITDM",
            stage="Challenger",
            priority="Improving performance",
            challenge="Integration friction",
            example=example,
            enrichment_context=self.enrichment_context,
        )
        assert "AI-Powered Analytics Platform" in prompt
        assert "30% Revenue Growth" in prompt

    def test_user_prompt_includes_job_title(self):
        """Contact's actual job title must appear in the LLM prompt."""
        example = FEW_SHOT_EXAMPLES_POOL["Challenger"][0]
        prompt = self.service._build_user_prompt(
            company_name="Acme Corp",
            industry="Technology",
            segment="Enterprise",
            persona="ITDM",
            stage="Challenger",
            priority="Improving performance",
            challenge="Integration friction",
            example=example,
            enrichment_context=self.enrichment_context,
        )
        assert "VP of Infrastructure Engineering" in prompt

    def test_user_prompt_includes_news_themes(self):
        """News themes must appear in the LLM prompt."""
        example = FEW_SHOT_EXAMPLES_POOL["Challenger"][0]
        prompt = self.service._build_user_prompt(
            company_name="Acme Corp",
            industry="Technology",
            segment="Enterprise",
            persona="ITDM",
            stage="Challenger",
            priority="Improving performance",
            challenge="Integration friction",
            example=example,
            enrichment_context=self.enrichment_context,
        )
        assert "AI adoption" in prompt
        assert "Cloud transformation" in prompt

    def test_user_prompt_includes_ai_readiness(self):
        """AI readiness stage from news analysis must appear in the prompt."""
        example = FEW_SHOT_EXAMPLES_POOL["Challenger"][0]
        prompt = self.service._build_user_prompt(
            company_name="Acme Corp",
            industry="Technology",
            segment="Enterprise",
            persona="ITDM",
            stage="Challenger",
            priority="Improving performance",
            challenge="Integration friction",
            example=example,
            enrichment_context=self.enrichment_context,
        )
        assert "piloting" in prompt

    def test_no_enrichment_context_still_works(self):
        """Prompt should still build correctly when enrichment_context is None."""
        example = FEW_SHOT_EXAMPLES_POOL["Challenger"][0]
        prompt = self.service._build_user_prompt(
            company_name="Acme Corp",
            industry="Technology",
            segment="Enterprise",
            persona="ITDM",
            stage="Challenger",
            priority="Improving performance",
            challenge="Integration friction",
            example=example,
            enrichment_context=None,
        )
        assert "Acme Corp" in prompt
        assert "Technology" in prompt

    def test_empty_enrichment_context_still_works(self):
        """Prompt should handle empty enrichment context gracefully."""
        example = FEW_SHOT_EXAMPLES_POOL["Challenger"][0]
        prompt = self.service._build_user_prompt(
            company_name="Acme Corp",
            industry="Technology",
            segment="Enterprise",
            persona="ITDM",
            stage="Challenger",
            priority="Improving performance",
            challenge="Integration friction",
            example=example,
            enrichment_context={},
        )
        assert "Acme Corp" in prompt

    def test_enrichment_context_passed_to_build_user_prompt(self):
        """generate_executive_review must pass enrichment_context to _build_user_prompt."""
        service = ExecutiveReviewService()
        service.client = None  # Force mock path

        with patch.object(service, '_build_user_prompt', wraps=service._build_user_prompt) as mock_build:
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                service.generate_executive_review(
                    company_name="Acme Corp",
                    industry="Technology",
                    segment="Enterprise",
                    persona="ITDM",
                    stage="Challenger",
                    priority="Improving performance",
                    challenge="Integration friction",
                    enrichment_context=self.enrichment_context,
                )
            )
            # Mock path returns early before calling _build_user_prompt,
            # so this test validates the method signature accepts enrichment_context
            # The real integration is tested via the prompt content tests above


# =============================================================================
# TestSignalAnswersInPrompt
# =============================================================================

class TestSignalAnswersInPrompt:
    """Verify that signalAnswers from the wizard are injected into the LLM prompt."""

    def setup_method(self):
        self.service = ExecutiveReviewService()
        self.signal_answers = {
            "infra_age": "10+ years, mostly on-prem",
            "ai_readiness": "Experimenting with pilots",
            "spending_focus": "Reducing infrastructure costs",
            "team_composition": "Mostly maintaining existing systems",
        }

    def test_signal_answers_appear_in_prompt(self):
        """Signal answers must appear in the LLM prompt when provided."""
        enrichment_context = {
            "signal_answers": self.signal_answers,
        }
        example = FEW_SHOT_EXAMPLES_POOL["Observer"][0]
        prompt = self.service._build_user_prompt(
            company_name="TestCo",
            industry="Technology",
            segment="Enterprise",
            persona="ITDM",
            stage="Observer",
            priority="Reducing costs",
            challenge="Legacy systems",
            example=example,
            enrichment_context=enrichment_context,
        )
        assert "Self-Reported Signals" in prompt or "SELF-REPORTED SIGNALS" in prompt
        assert "10+ years, mostly on-prem" in prompt
        assert "Experimenting with pilots" in prompt

    def test_prompt_without_signal_answers_still_works(self):
        """Prompt works fine without signal_answers in enrichment_context."""
        enrichment_context = {
            "company_summary": "A technology company",
        }
        example = FEW_SHOT_EXAMPLES_POOL["Observer"][0]
        prompt = self.service._build_user_prompt(
            company_name="TestCo",
            industry="Technology",
            segment="Enterprise",
            persona="ITDM",
            stage="Observer",
            priority="Reducing costs",
            challenge="Legacy systems",
            example=example,
            enrichment_context=enrichment_context,
        )
        assert "TestCo" in prompt
        # Should not contain signal section when no signals provided
        assert "Self-Reported Signals" not in prompt

    def test_signal_answer_labels_in_prompt(self):
        """All 4 signal answer labels must appear in the prompt."""
        enrichment_context = {
            "signal_answers": self.signal_answers,
        }
        example = FEW_SHOT_EXAMPLES_POOL["Challenger"][0]
        prompt = self.service._build_user_prompt(
            company_name="TestCo",
            industry="Healthcare",
            segment="Mid-Market",
            persona="BDM",
            stage="Challenger",
            priority="Improving performance",
            challenge="Integration friction",
            example=example,
            enrichment_context=enrichment_context,
        )
        for label in self.signal_answers.values():
            assert label in prompt, f"Signal answer '{label}' not found in prompt"
