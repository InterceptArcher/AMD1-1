"""
Tests for Content Guardrails System.
Covers: field-level character limits, word counts, banned phrases,
company name rules, AMD content loading, validation + retry + fallback.

TDD: These tests are written FIRST and must FAIL before implementation.
"""

import pytest
import os
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.executive_review_service import (
    ExecutiveReviewService,
    FEW_SHOT_EXAMPLES_POOL,
)


# =============================================================================
# FIELD SPEC CONSTANTS (these define the contract)
# =============================================================================

# Expected field specs - the implementation must match these
HEADLINE_MIN_CHARS = 20
HEADLINE_MAX_CHARS = 80
HEADLINE_MIN_WORDS = 4
HEADLINE_MAX_WORDS = 12

DESCRIPTION_MIN_CHARS = 150
DESCRIPTION_MAX_CHARS = 400
DESCRIPTION_MIN_WORDS = 25
DESCRIPTION_MAX_WORDS = 65

TITLE_MIN_CHARS = 20
TITLE_MAX_CHARS = 80
TITLE_MIN_WORDS = 4
TITLE_MAX_WORDS = 12

REC_DESC_MIN_CHARS = 150
REC_DESC_MAX_CHARS = 400
REC_DESC_MIN_WORDS = 25
REC_DESC_MAX_WORDS = 65


# =============================================================================
# TestFieldSpecExists
# =============================================================================

class TestFieldSpecExists:
    """Verify that FIELD_SPECS constant exists and has correct structure."""

    def test_field_specs_importable(self):
        from app.services.executive_review_service import FIELD_SPECS
        assert isinstance(FIELD_SPECS, dict)

    def test_field_specs_has_headline(self):
        from app.services.executive_review_service import FIELD_SPECS
        assert "headline" in FIELD_SPECS
        spec = FIELD_SPECS["headline"]
        assert "min_chars" in spec
        assert "max_chars" in spec
        assert "min_words" in spec
        assert "max_words" in spec

    def test_field_specs_has_description(self):
        from app.services.executive_review_service import FIELD_SPECS
        assert "description" in FIELD_SPECS

    def test_field_specs_has_rec_title(self):
        from app.services.executive_review_service import FIELD_SPECS
        assert "rec_title" in FIELD_SPECS

    def test_field_specs_has_rec_description(self):
        from app.services.executive_review_service import FIELD_SPECS
        assert "rec_description" in FIELD_SPECS

    def test_headline_limits(self):
        from app.services.executive_review_service import FIELD_SPECS
        spec = FIELD_SPECS["headline"]
        assert spec["min_chars"] == HEADLINE_MIN_CHARS
        assert spec["max_chars"] == HEADLINE_MAX_CHARS
        assert spec["min_words"] == HEADLINE_MIN_WORDS
        assert spec["max_words"] == HEADLINE_MAX_WORDS


# =============================================================================
# TestContentValidator
# =============================================================================

class TestContentValidator:
    """Test validate_executive_review_content() function."""

    def test_validator_importable(self):
        from app.services.executive_review_service import validate_executive_review_content
        assert callable(validate_executive_review_content)

    def test_valid_content_passes(self):
        """Content that meets all specs should pass validation."""
        from app.services.executive_review_service import validate_executive_review_content

        valid_content = {
            "advantages": [
                {
                    "headline": "Cost savings from reducing legacy system overhead",
                    "description": "Retiring aging on-prem systems lowers operating costs and reduces the maintenance burden across globally distributed project teams. By consolidating redundant infrastructure, IT can redirect budget toward modernization priorities while reducing the maintenance hours spent on end-of-life hardware and software licensing."
                },
                {
                    "headline": "Efficiency gains through standardizing project data environments",
                    "description": "Unifying fragmented data environments across regions creates quick workflow efficiencies without requiring major architectural change across departments. Standardized environments reduce onboarding time for distributed teams and eliminate the duplicated tooling costs from each site running its own infrastructure stack."
                }
            ],
            "risks": [
                {
                    "headline": "High total cost of ownership from legacy infrastructure",
                    "description": "Running large outdated systems at enterprise scale drives rising support licensing and hardware costs that conflict with cost reduction goals. Without a clear modernization path, these legacy systems will consume an increasing share of IT budget while delivering diminishing returns on reliability and performance."
                },
                {
                    "headline": "Integration gaps that add avoidable project costs",
                    "description": "Siloed tools and limited interoperability across field design and systems increase rework risk and make secure integration harder overall. Each manual data handoff between disconnected platforms introduces errors that compound across the global project portfolio, increasing operational overhead."
                }
            ],
            "recommendations": [
                {
                    "title": "Modernize the highest-cost legacy workloads first",
                    "description": "Target the most cost-intensive on-prem systems to reduce maintenance overhead and improve stability for distributed project teams across regions. Focus on the workloads where maintenance contracts are expiring or hardware refresh cycles are imminent, as these represent the clearest opportunities to reduce spend."
                },
                {
                    "title": "Standardize core infrastructure to reduce regional fragmentation",
                    "description": "Adopt consistent tooling and platform standards across regions to lower integration effort and eliminate duplicated spend across project sites. This creates a unified environment that simplifies support, reduces training overhead, and accelerates new project onboarding across the organization."
                },
                {
                    "title": "Build a scalable foundation for future AI-driven workloads",
                    "description": "Upgrade underlying compute and storage so the organization can support emerging AI-driven design and planning tools without incurring higher costs. Investing in scalable architecture now prevents the costly cycle of repeated rework when new capabilities are layered onto infrastructure that cannot handle additional demand."
                }
            ]
        }

        result = validate_executive_review_content(valid_content)
        assert result["passed"] is True
        assert len(result["failures"]) == 0

    def test_headline_too_short_fails(self):
        """Headline under min chars should fail."""
        from app.services.executive_review_service import validate_executive_review_content

        content = {
            "advantages": [
                {"headline": "Too short", "description": "A valid description that is long enough to meet the minimum character count for this field type. It includes additional context about infrastructure modernization and operational efficiency improvements that help demonstrate compliance with the expanded content requirements for executive review descriptions."},
                {"headline": "Efficiency gains through basic standardization", "description": "A valid description that meets the minimum character and word count requirements for the description field. This expanded content provides sufficient detail about modernization approaches and system improvements to pass the updated character and word count validation thresholds."}
            ],
            "risks": [
                {"headline": "High total cost from legacy infrastructure", "description": "Running large outdated systems at enterprise scale drives rising support licensing and hardware costs that conflict with cost reduction goals. Without a clear modernization path, these legacy systems will consume an increasing share of IT budget while delivering diminishing returns on reliability and performance across the organization."},
                {"headline": "Integration gaps that add avoidable costs", "description": "Siloed tools and limited interoperability increase rework risk and make secure integration harder for teams across the business. Each manual data handoff between disconnected platforms introduces errors that compound across the project portfolio, increasing operational overhead and slowing delivery timelines for critical modernization initiatives."}
            ],
            "recommendations": [
                {"title": "Modernize high-impact legacy workloads first", "description": "Target the most cost-intensive on-prem systems to reduce maintenance overhead and improve stability for distributed teams across regions. Focus on workloads where maintenance contracts are expiring or hardware refresh cycles are imminent, as these represent the clearest opportunities to reduce spend while improving system reliability."},
                {"title": "Standardize core infrastructure to reduce fragmentation", "description": "Adopt consistent tooling and platform standards across regions to lower integration effort and eliminate duplicated spend across project sites. This creates a unified environment that simplifies support, reduces training overhead, and accelerates new project onboarding across the organization."},
                {"title": "Build a scalable foundation for future workloads", "description": "Upgrade underlying compute and storage to support emerging design and planning tools without incurring higher costs from repeated work. Investing in scalable architecture now prevents the costly cycle of rework when new capabilities are layered onto infrastructure that cannot handle additional workload demands."}
            ]
        }

        result = validate_executive_review_content(content)
        assert result["passed"] is False
        assert any("headline" in f["field"] and "char" in f["reason"].lower() for f in result["failures"])

    def test_headline_too_long_fails(self):
        """Headline over max chars should fail."""
        from app.services.executive_review_service import validate_executive_review_content

        content = {
            "advantages": [
                {"headline": "This is a very long headline that exceeds the maximum character limit set for headlines in the spec", "description": "A valid description that meets the minimum character and word count requirements for the description field type. It includes sufficient detail about infrastructure systems and operational processes to satisfy the expanded content validation rules for executive review output sections."},
                {"headline": "Efficiency gains through basic standardization", "description": "A valid description that meets the minimum character and word count requirements for the description field. This expanded content provides sufficient detail about modernization approaches and system improvements to pass the updated character and word count validation thresholds."}
            ],
            "risks": [
                {"headline": "High total cost from legacy infrastructure", "description": "Running large outdated systems at enterprise scale drives rising support licensing and hardware costs that conflict with cost reduction goals. Without a clear modernization path, these legacy systems will consume an increasing share of IT budget while delivering diminishing returns on reliability and performance across the organization."},
                {"headline": "Integration gaps that add avoidable costs", "description": "Siloed tools and limited interoperability increase rework risk and make secure integration harder for teams across the business. Each manual data handoff between disconnected platforms introduces errors that compound across the project portfolio, increasing operational overhead and slowing delivery timelines for critical modernization initiatives."}
            ],
            "recommendations": [
                {"title": "Modernize high-impact legacy workloads first", "description": "Target the most cost-intensive on-prem systems to reduce maintenance overhead and improve stability for distributed teams across regions. Focus on workloads where maintenance contracts are expiring or hardware refresh cycles are imminent, as these represent the clearest opportunities to reduce spend while improving system reliability."},
                {"title": "Standardize core infrastructure to reduce fragmentation", "description": "Adopt consistent tooling and platform standards across regions to lower integration effort and eliminate duplicated spend across project sites. This creates a unified environment that simplifies support, reduces training overhead, and accelerates new project onboarding across the organization."},
                {"title": "Build a scalable foundation for future workloads", "description": "Upgrade underlying compute and storage to support emerging design and planning tools without incurring higher costs from repeated work. Investing in scalable architecture now prevents the costly cycle of rework when new capabilities are layered onto infrastructure that cannot handle additional workload demands."}
            ]
        }

        result = validate_executive_review_content(content)
        assert result["passed"] is False
        assert any("headline" in f["field"] and "char" in f["reason"].lower() for f in result["failures"])

    def test_description_too_short_fails(self):
        """Description under min chars should fail."""
        from app.services.executive_review_service import validate_executive_review_content

        content = {
            "advantages": [
                {"headline": "Cost savings from reducing legacy overhead", "description": "Too short."},
                {"headline": "Efficiency gains through basic standardization", "description": "A valid description that meets the minimum character and word count requirements for this field."}
            ],
            "risks": [
                {"headline": "High total cost from legacy infrastructure", "description": "Running large outdated systems at enterprise scale drives rising support licensing and hardware costs that conflict with cost reduction goals. Without a clear modernization path, these legacy systems will consume an increasing share of IT budget while delivering diminishing returns on reliability and performance across the organization."},
                {"headline": "Integration gaps that add avoidable costs", "description": "Siloed tools and limited interoperability increase rework risk and make secure integration harder for teams across the business. Each manual data handoff between disconnected platforms introduces errors that compound across the project portfolio, increasing operational overhead and slowing delivery timelines for critical modernization initiatives."}
            ],
            "recommendations": [
                {"title": "Modernize high-impact legacy workloads first", "description": "Target the most cost-intensive on-prem systems to reduce maintenance overhead and improve stability for distributed teams across regions. Focus on workloads where maintenance contracts are expiring or hardware refresh cycles are imminent, as these represent the clearest opportunities to reduce spend while improving system reliability."},
                {"title": "Standardize core infrastructure to reduce fragmentation", "description": "Adopt consistent tooling and platform standards across regions to lower integration effort and eliminate duplicated spend across project sites. This creates a unified environment that simplifies support, reduces training overhead, and accelerates new project onboarding across the organization."},
                {"title": "Build a scalable foundation for future workloads", "description": "Upgrade underlying compute and storage to support emerging design and planning tools without incurring higher costs from repeated work. Investing in scalable architecture now prevents the costly cycle of rework when new capabilities are layered onto infrastructure that cannot handle additional workload demands."}
            ]
        }

        result = validate_executive_review_content(content)
        assert result["passed"] is False

    def test_banned_phrase_in_headline_fails(self):
        """Headlines with banned phrases should fail."""
        from app.services.executive_review_service import validate_executive_review_content

        content = {
            "advantages": [
                {"headline": "Revolutionary gains in today's landscape", "description": "A valid description that meets the minimum character and word count requirements for the description field type. It includes sufficient detail about infrastructure systems and operational processes to satisfy the expanded content validation rules for executive review output sections."},
                {"headline": "Efficiency gains through basic standardization", "description": "A valid description that meets the minimum character and word count requirements for the description field. This expanded content provides sufficient detail about modernization approaches and system improvements to pass the updated character and word count validation thresholds."}
            ],
            "risks": [
                {"headline": "High total cost from legacy infrastructure", "description": "Running large outdated systems at enterprise scale drives rising support licensing and hardware costs that conflict with cost reduction goals. Without a clear modernization path, these legacy systems will consume an increasing share of IT budget while delivering diminishing returns on reliability and performance across the organization."},
                {"headline": "Integration gaps that add avoidable costs", "description": "Siloed tools and limited interoperability increase rework risk and make secure integration harder for teams across the business. Each manual data handoff between disconnected platforms introduces errors that compound across the project portfolio, increasing operational overhead and slowing delivery timelines for critical modernization initiatives."}
            ],
            "recommendations": [
                {"title": "Modernize high-impact legacy workloads first", "description": "Target the most cost-intensive on-prem systems to reduce maintenance overhead and improve stability for distributed teams across regions. Focus on workloads where maintenance contracts are expiring or hardware refresh cycles are imminent, as these represent the clearest opportunities to reduce spend while improving system reliability."},
                {"title": "Standardize core infrastructure to reduce fragmentation", "description": "Adopt consistent tooling and platform standards across regions to lower integration effort and eliminate duplicated spend across project sites. This creates a unified environment that simplifies support, reduces training overhead, and accelerates new project onboarding across the organization."},
                {"title": "Build a scalable foundation for future workloads", "description": "Upgrade underlying compute and storage to support emerging design and planning tools without incurring higher costs from repeated work. Investing in scalable architecture now prevents the costly cycle of rework when new capabilities are layered onto infrastructure that cannot handle additional workload demands."}
            ]
        }

        result = validate_executive_review_content(content)
        assert result["passed"] is False
        assert any("banned" in f["reason"].lower() for f in result["failures"])

    def test_em_dash_in_content_fails(self):
        """Content with em dashes should fail."""
        from app.services.executive_review_service import validate_executive_review_content

        content = {
            "advantages": [
                {"headline": "Cost savings from reducing legacy overhead", "description": "Retiring aging systems \u2014 including on-prem servers \u2014 lowers operating costs and reduces the maintenance burden across distributed teams significantly. This consolidation eliminates redundant licensing and support contracts while freeing budget for modernization priorities that deliver measurable operational improvements."},
                {"headline": "Efficiency gains through basic standardization", "description": "A valid description that meets the minimum character and word count requirements for the description field. This expanded content provides sufficient detail about modernization approaches and system improvements to pass the updated character and word count validation thresholds."}
            ],
            "risks": [
                {"headline": "High total cost from legacy infrastructure", "description": "Running large outdated systems at enterprise scale drives rising support licensing and hardware costs that conflict with cost reduction goals. Without a clear modernization path, these legacy systems will consume an increasing share of IT budget while delivering diminishing returns on reliability and performance across the organization."},
                {"headline": "Integration gaps that add avoidable costs", "description": "Siloed tools and limited interoperability increase rework risk and make secure integration harder for teams across the business. Each manual data handoff between disconnected platforms introduces errors that compound across the project portfolio, increasing operational overhead and slowing delivery timelines for critical modernization initiatives."}
            ],
            "recommendations": [
                {"title": "Modernize high-impact legacy workloads first", "description": "Target the most cost-intensive on-prem systems to reduce maintenance overhead and improve stability for distributed teams across regions. Focus on workloads where maintenance contracts are expiring or hardware refresh cycles are imminent, as these represent the clearest opportunities to reduce spend while improving system reliability."},
                {"title": "Standardize core infrastructure to reduce fragmentation", "description": "Adopt consistent tooling and platform standards across regions to lower integration effort and eliminate duplicated spend across project sites. This creates a unified environment that simplifies support, reduces training overhead, and accelerates new project onboarding across the organization."},
                {"title": "Build a scalable foundation for future workloads", "description": "Upgrade underlying compute and storage to support emerging design and planning tools without incurring higher costs from repeated work. Investing in scalable architecture now prevents the costly cycle of rework when new capabilities are layered onto infrastructure that cannot handle additional workload demands."}
            ]
        }

        result = validate_executive_review_content(content)
        assert result["passed"] is False
        assert any("em dash" in f["reason"].lower() or "banned" in f["reason"].lower() for f in result["failures"])

    def test_validation_returns_specific_field_failures(self):
        """Each failure should identify the exact field path."""
        from app.services.executive_review_service import validate_executive_review_content

        content = {
            "advantages": [
                {"headline": "Short", "description": "Short."},
                {"headline": "OK headline that is long enough here", "description": "A valid description with enough words and characters."}
            ],
            "risks": [
                {"headline": "OK headline for risk section here", "description": "A valid risk description with sufficient length."},
                {"headline": "OK headline for second risk item", "description": "A valid risk description with sufficient length."}
            ],
            "recommendations": [
                {"title": "OK title for recommendation here", "description": "A valid recommendation description."},
                {"title": "OK title for second recommendation", "description": "A valid recommendation description."},
                {"title": "OK title for third recommendation", "description": "A valid recommendation description."}
            ]
        }

        result = validate_executive_review_content(content)
        assert result["passed"] is False
        # Failures should identify field paths like "advantages[0].headline"
        assert any("advantages[0]" in f["field"] for f in result["failures"])


# =============================================================================
# TestAMDContentLoader
# =============================================================================

class TestAMDContentLoader:
    """Test loading AMD IP content from markdown files."""

    def test_loader_importable(self):
        from app.services.executive_review_service import load_amd_industry_context
        assert callable(load_amd_industry_context)

    def test_loads_healthcare_content(self):
        from app.services.executive_review_service import load_amd_industry_context
        content = load_amd_industry_context("Healthcare")
        assert content is not None
        assert len(content) > 100
        assert "EHR" in content or "clinical" in content.lower() or "patient" in content.lower()

    def test_loads_financial_services_content(self):
        from app.services.executive_review_service import load_amd_industry_context
        content = load_amd_industry_context("Financial Services")
        assert content is not None
        assert len(content) > 100

    def test_loads_retail_content(self):
        from app.services.executive_review_service import load_amd_industry_context
        content = load_amd_industry_context("Retail")
        assert content is not None
        assert len(content) > 100

    def test_loads_manufacturing_content(self):
        from app.services.executive_review_service import load_amd_industry_context
        content = load_amd_industry_context("Manufacturing")
        assert content is not None
        assert len(content) > 100

    def test_unknown_industry_returns_empty(self):
        from app.services.executive_review_service import load_amd_industry_context
        content = load_amd_industry_context("Underwater Basket Weaving")
        assert content == "" or content is None

    def test_content_is_condensed(self):
        """Content should be condensed, not the full 500+ line file."""
        from app.services.executive_review_service import load_amd_industry_context
        content = load_amd_industry_context("Healthcare")
        # Should be condensed to fit in LLM prompt - under 2000 chars
        assert len(content) <= 2000

    def test_persona_context_loadable(self):
        from app.services.executive_review_service import load_amd_persona_context
        content = load_amd_persona_context("ITDM")
        assert content is not None
        assert len(content) > 50

    def test_segment_context_loadable(self):
        from app.services.executive_review_service import load_amd_segment_context
        content = load_amd_segment_context("Enterprise")
        assert content is not None
        assert len(content) > 50


# =============================================================================
# TestToolUseSchema
# =============================================================================

class TestToolUseSchema:
    """Test that the Anthropic tool_use schema is properly defined."""

    def test_tool_schema_importable(self):
        from app.services.executive_review_service import EXECUTIVE_REVIEW_TOOL_SCHEMA
        assert isinstance(EXECUTIVE_REVIEW_TOOL_SCHEMA, dict)

    def test_tool_schema_has_name(self):
        from app.services.executive_review_service import EXECUTIVE_REVIEW_TOOL_SCHEMA
        assert "name" in EXECUTIVE_REVIEW_TOOL_SCHEMA
        assert EXECUTIVE_REVIEW_TOOL_SCHEMA["name"] == "generate_executive_review"

    def test_tool_schema_has_input_schema(self):
        from app.services.executive_review_service import EXECUTIVE_REVIEW_TOOL_SCHEMA
        assert "input_schema" in EXECUTIVE_REVIEW_TOOL_SCHEMA
        schema = EXECUTIVE_REVIEW_TOOL_SCHEMA["input_schema"]
        assert "properties" in schema

    def test_tool_schema_defines_advantages(self):
        from app.services.executive_review_service import EXECUTIVE_REVIEW_TOOL_SCHEMA
        props = EXECUTIVE_REVIEW_TOOL_SCHEMA["input_schema"]["properties"]
        assert "advantages" in props

    def test_tool_schema_headline_has_max_length(self):
        """Headlines should have maxLength in the tool schema."""
        from app.services.executive_review_service import EXECUTIVE_REVIEW_TOOL_SCHEMA
        props = EXECUTIVE_REVIEW_TOOL_SCHEMA["input_schema"]["properties"]
        adv_items = props["advantages"]["items"]["properties"]
        assert "maxLength" in adv_items["headline"]
        assert adv_items["headline"]["maxLength"] == HEADLINE_MAX_CHARS


# =============================================================================
# TestRetryLogic
# =============================================================================

class TestRetryLogic:
    """Test targeted retry for failing fields."""

    def setup_method(self):
        self.service = ExecutiveReviewService()

    def test_retry_method_exists(self):
        assert hasattr(self.service, '_retry_failing_fields')
        assert callable(self.service._retry_failing_fields)

    @pytest.mark.asyncio
    async def test_retry_fixes_over_limit_headline(self):
        """Retry should rewrite a single field that exceeds char limit."""
        failures = [
            {
                "field": "advantages[0].headline",
                "reason": "Exceeds max chars (70/65)",
                "value": "This headline is way too long and exceeds the maximum character limit set"
            }
        ]
        original_content = {
            "advantages": [
                {"headline": "This headline is way too long and exceeds the maximum character limit set", "description": "Valid desc."},
                {"headline": "Good headline here for test", "description": "Valid desc."}
            ],
            "risks": [
                {"headline": "Good risk headline here now", "description": "Valid desc."},
                {"headline": "Good risk headline two here", "description": "Valid desc."}
            ],
            "recommendations": [
                {"title": "Good title for recommendation", "description": "Valid desc."},
                {"title": "Good title for second rec here", "description": "Valid desc."},
                {"title": "Good title for third rec here", "description": "Valid desc."}
            ]
        }

        # Without API key, retry should fall back gracefully
        self.service.client = None
        result = await self.service._retry_failing_fields(
            original_content, failures, "TestCo", "Observer",
            "Technology", "Enterprise", "ITDM", "Reducing cost", "Legacy systems",
            "You are an expert business strategist."
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_fallback_to_example_on_double_failure(self):
        """If retry also fails, should fall back to few-shot example."""
        from app.services.executive_review_service import fallback_to_example
        result = fallback_to_example("TestCo", "Observer", "Technology", "Reducing cost", "Legacy systems")
        assert result is not None
        assert len(result["advantages"]) == 2
        assert len(result["risks"]) == 2
        assert len(result["recommendations"]) == 3

    def test_fallback_swaps_company_name(self):
        """Fallback should swap the example's company name with the actual company."""
        from app.services.executive_review_service import fallback_to_example
        result = fallback_to_example("Acme Corp", "Observer", "Technology", "Reducing cost", "Legacy systems")
        # Check that the company name appears in the content
        all_text = ""
        for adv in result["advantages"]:
            all_text += adv["headline"] + " " + adv["description"] + " "
        for rec in result["recommendations"]:
            all_text += rec["title"] + " " + rec["description"] + " "
        assert "Acme Corp" in all_text


# =============================================================================
# TestBannedPhrases
# =============================================================================

class TestBannedPhrases:
    """Test that AMD-specific banned phrases are caught."""

    def test_banned_phrases_importable(self):
        from app.services.executive_review_service import EXEC_REVIEW_BANNED_PHRASES
        assert isinstance(EXEC_REVIEW_BANNED_PHRASES, list)
        assert len(EXEC_REVIEW_BANNED_PHRASES) > 0

    def test_in_todays_landscape_banned(self):
        from app.services.executive_review_service import EXEC_REVIEW_BANNED_PHRASES
        assert any("today's landscape" in phrase for phrase in EXEC_REVIEW_BANNED_PHRASES)

    def test_revolutionary_banned(self):
        from app.services.executive_review_service import EXEC_REVIEW_BANNED_PHRASES
        assert any("revolutionary" in phrase for phrase in EXEC_REVIEW_BANNED_PHRASES)

    def test_game_changing_banned(self):
        from app.services.executive_review_service import EXEC_REVIEW_BANNED_PHRASES
        assert any("game" in phrase for phrase in EXEC_REVIEW_BANNED_PHRASES)

    def test_exclamation_mark_banned(self):
        """Exclamation marks should be caught by validation."""
        from app.services.executive_review_service import validate_executive_review_content

        content = {
            "advantages": [
                {"headline": "Amazing cost savings await you!", "description": "A valid description that meets the minimum character and word count requirements for the description field type. It includes sufficient detail about infrastructure systems and operational processes to satisfy the expanded content validation rules for executive review output sections."},
                {"headline": "Efficiency gains through basic standardization", "description": "A valid description that meets the minimum character and word count requirements for the description field. This expanded content provides sufficient detail about modernization approaches and system improvements to pass the updated character and word count validation thresholds."}
            ],
            "risks": [
                {"headline": "High total cost from legacy infrastructure", "description": "Running large outdated systems at enterprise scale drives rising support licensing and hardware costs that conflict with cost reduction goals. Without a clear modernization path, these legacy systems will consume an increasing share of IT budget while delivering diminishing returns on reliability and performance across the organization."},
                {"headline": "Integration gaps that add avoidable costs", "description": "Siloed tools and limited interoperability increase rework risk and make secure integration harder for teams across the business. Each manual data handoff between disconnected platforms introduces errors that compound across the project portfolio, increasing operational overhead and slowing delivery timelines for critical modernization initiatives."}
            ],
            "recommendations": [
                {"title": "Modernize high-impact legacy workloads first", "description": "Target the most cost-intensive on-prem systems to reduce maintenance overhead and improve stability for distributed teams across regions. Focus on workloads where maintenance contracts are expiring or hardware refresh cycles are imminent, as these represent the clearest opportunities to reduce spend while improving system reliability."},
                {"title": "Standardize core infrastructure to reduce fragmentation", "description": "Adopt consistent tooling and platform standards across regions to lower integration effort and eliminate duplicated spend across project sites. This creates a unified environment that simplifies support, reduces training overhead, and accelerates new project onboarding across the organization."},
                {"title": "Build a scalable foundation for future workloads", "description": "Upgrade underlying compute and storage to support emerging design and planning tools without incurring higher costs from repeated work. Investing in scalable architecture now prevents the costly cycle of rework when new capabilities are layered onto infrastructure that cannot handle additional workload demands."}
            ]
        }

        result = validate_executive_review_content(content)
        assert result["passed"] is False


# =============================================================================
# TestFewShotExamplesPassValidation
# =============================================================================

class TestFewShotExamplesPassValidation:
    """Verify that all existing gold standard examples pass the new validation."""

    def test_all_gold_standard_examples_pass(self):
        """Every few-shot example should pass validation - they ARE the gold standard."""
        from app.services.executive_review_service import validate_executive_review_content

        for stage, examples in FEW_SHOT_EXAMPLES_POOL.items():
            for i, example in enumerate(examples):
                result = validate_executive_review_content(example["output"])
                assert result["passed"] is True, (
                    f"Gold standard example {stage}[{i}] ({example['profile']['company']}) "
                    f"failed validation: {result['failures']}"
                )
