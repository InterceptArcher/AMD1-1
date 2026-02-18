"""
Executive Review Service for AMD 2-page assessment generation.
Generates personalized content based on Stage, Industry, Segment, Persona, Priority, and Challenge.

Content Guardrails (Option C - Hybrid):
  1. Anthropic tool_use for structured output with character constraints
  2. Post-generation validator checks char limits, word counts, banned phrases
  3. Targeted retry for failing fields only
  4. Fallback to gold-standard few-shot example with company name swap
"""

import logging
import json
import os
import re
from pathlib import Path
from typing import Optional
from anthropic import AsyncAnthropic

from app.config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# FIELD SPECIFICATIONS (CHARACTER & WORD LIMITS)
# =============================================================================

FIELD_SPECS = {
    "headline": {
        "min_chars": 20,
        "max_chars": 80,
        "min_words": 4,
        "max_words": 12,
        "description": "Advantage/Risk headline",
    },
    "description": {
        "min_chars": 150,
        "max_chars": 400,
        "min_words": 25,
        "max_words": 65,
        "description": "Advantage/Risk description (2-3 sentences)",
    },
    "rec_title": {
        "min_chars": 20,
        "max_chars": 80,
        "min_words": 4,
        "max_words": 12,
        "description": "Recommendation title",
    },
    "rec_description": {
        "min_chars": 200,
        "max_chars": 550,
        "min_words": 35,
        "max_words": 90,
        "description": "Recommendation description (3-4 sentences)",
    },
    "executive_summary": {
        "min_chars": 200,
        "max_chars": 600,
        "min_words": 35,
        "max_words": 90,
        "description": "Executive summary paragraph",
    },
    "case_study_relevance": {
        "min_chars": 150,
        "max_chars": 500,
        "min_words": 25,
        "max_words": 80,
        "description": "Case study relevance explanation (2-4 sentences)",
    },
}


# =============================================================================
# BANNED PHRASES (AMD CONTENT RULES)
# =============================================================================

EXEC_REVIEW_BANNED_PHRASES = [
    # AI-tell filler phrases
    "in today's landscape",
    "in today's world",
    "in today's environment",
    "in the current landscape",
    "in an era of",
    "in this rapidly evolving",
    "rapidly evolving",
    "ever-changing",
    "ever-evolving",
    "fast-paced",
    "digital transformation journey",
    "unlock the power",
    "unlock the potential",
    "harness the power",
    "leverage the power",
    "paradigm shift",
    "synergy",
    "synergies",
    "cutting-edge",
    "cutting edge",
    "next-generation",
    "next generation",
    "state-of-the-art",
    "best-in-class",
    "world-class",
    # Hype / exaggeration
    "revolutionary",
    "groundbreaking",
    "game-changing",
    "game changer",
    "unprecedented",
    "unparalleled",
    "unmatched",
    "transformative",
    # Pressure tactics
    "act now",
    "don't miss",
    "limited time",
    "hurry",
]

# Characters that should not appear in executive review content
BANNED_CHARACTERS = [
    "\u2014",  # em dash
    "\u2013",  # en dash
    "!",       # exclamation mark
    ":",       # colon in headlines (descriptions OK)
]

# Characters banned only in headlines/titles
BANNED_IN_HEADLINES = [
    ":",  # no colons in headlines
]


# =============================================================================
# ANTHROPIC TOOL_USE SCHEMA
# =============================================================================

EXECUTIVE_REVIEW_TOOL_SCHEMA = {
    "name": "generate_executive_review",
    "description": "Generate a personalized executive review with executive summary, advantages, risks, recommendations, and case study relevance. Each field has strict character limits.",
    "input_schema": {
        "type": "object",
        "properties": {
            "executive_summary": {
                "type": "string",
                "description": "2-3 sentence personalized opening paragraph (35-90 words, 200-600 characters). Frame the assessment for the specific company, industry, and stage. Must mention the company name and their primary priority.",
                "minLength": 200,
                "maxLength": 600,
            },
            "advantages": {
                "type": "array",
                "description": "Exactly 2 advantages. First must relate to stated business priority.",
                "items": {
                    "type": "object",
                    "properties": {
                        "headline": {
                            "type": "string",
                            "description": "4-12 words, benefit-driven, no colons. 20-80 characters.",
                            "minLength": 20,
                            "maxLength": 80,
                        },
                        "description": {
                            "type": "string",
                            "description": "2-3 sentences, 25-65 words, professional tone. 150-400 characters. Include specific systems, metrics, or outcomes relevant to the industry.",
                            "minLength": 150,
                            "maxLength": 400,
                        },
                    },
                    "required": ["headline", "description"],
                },
                "minItems": 2,
                "maxItems": 2,
            },
            "risks": {
                "type": "array",
                "description": "Exactly 2 risks. First must reference consequences of stated challenge.",
                "items": {
                    "type": "object",
                    "properties": {
                        "headline": {
                            "type": "string",
                            "description": "4-12 words, consequence-focused, no colons. 20-80 characters.",
                            "minLength": 20,
                            "maxLength": 80,
                        },
                        "description": {
                            "type": "string",
                            "description": "2-3 sentences, 25-65 words, professional tone. 150-400 characters. Describe specific operational or business consequences.",
                            "minLength": 150,
                            "maxLength": 400,
                        },
                    },
                    "required": ["headline", "description"],
                },
                "minItems": 2,
                "maxItems": 2,
            },
            "recommendations": {
                "type": "array",
                "description": "Exactly 3 recommendations. Stage-appropriate actions.",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "4-12 words, imperative form, no colons. 20-80 characters.",
                            "minLength": 20,
                            "maxLength": 80,
                        },
                        "description": {
                            "type": "string",
                            "description": "3-4 sentences, 35-90 words, professional tone. 200-550 characters. Include actionable steps, expected outcomes, and specific implementation guidance.",
                            "minLength": 200,
                            "maxLength": 550,
                        },
                    },
                    "required": ["title", "description"],
                },
                "minItems": 3,
                "maxItems": 3,
            },
            "case_study_relevance": {
                "type": "string",
                "description": "2-4 sentences (25-80 words, 150-500 characters) explaining how the case study maps to this company's specific situation, industry challenges, and stated priorities.",
                "minLength": 150,
                "maxLength": 500,
            },
        },
        "required": ["executive_summary", "advantages", "risks", "recommendations", "case_study_relevance"],
    },
}


# =============================================================================
# CONTENT VALIDATOR
# =============================================================================

def validate_executive_review_content(
    content: dict,
    priority: str = "",
    challenge: str = "",
    industry: str = "",
) -> dict:
    """
    Validate executive review content against field specs, banned phrases,
    AMD content rules, and personalization requirements.

    Args:
        content: The generated executive review content dict
        priority: Business priority (e.g. "Reducing cost") — used for personalization check
        challenge: Challenge (e.g. "Legacy systems") — used for personalization check
        industry: Industry (e.g. "Healthcare") — used for relevance check

    Returns:
        {
            "passed": bool,
            "failures": [{"field": str, "reason": str, "value": str}, ...]
        }
    """
    failures = []

    # Validate executive summary
    exec_summary = content.get("executive_summary", "")
    if exec_summary:
        _validate_field(
            exec_summary,
            "executive_summary",
            FIELD_SPECS["executive_summary"],
            failures,
        )

    # Validate advantages
    for i, adv in enumerate(content.get("advantages", [])):
        _validate_field(
            adv.get("headline", ""),
            f"advantages[{i}].headline",
            FIELD_SPECS["headline"],
            failures,
            is_headline=True,
        )
        _validate_field(
            adv.get("description", ""),
            f"advantages[{i}].description",
            FIELD_SPECS["description"],
            failures,
        )

    # Validate risks
    for i, risk in enumerate(content.get("risks", [])):
        _validate_field(
            risk.get("headline", ""),
            f"risks[{i}].headline",
            FIELD_SPECS["headline"],
            failures,
            is_headline=True,
        )
        _validate_field(
            risk.get("description", ""),
            f"risks[{i}].description",
            FIELD_SPECS["description"],
            failures,
        )

    # Validate recommendations
    for i, rec in enumerate(content.get("recommendations", [])):
        _validate_field(
            rec.get("title", ""),
            f"recommendations[{i}].title",
            FIELD_SPECS["rec_title"],
            failures,
            is_headline=True,
        )
        _validate_field(
            rec.get("description", ""),
            f"recommendations[{i}].description",
            FIELD_SPECS["rec_description"],
            failures,
        )

    # Validate case_study_relevance with expanded spec
    relevance_text = content.get("case_study_relevance", "")
    if relevance_text:
        _validate_field(
            relevance_text,
            "case_study_relevance",
            FIELD_SPECS["case_study_relevance"],
            failures,
        )

    # Validate company name — must only appear in FIRST item of each section
    company_name = content.get("company_name", "")
    if company_name and len(company_name) > 2:
        cn_lower = company_name.lower()
        for section_key in ["advantages", "risks", "recommendations"]:
            items = content.get(section_key, [])
            for idx, item in enumerate(items):
                if idx == 0:
                    continue  # First item is allowed to have company name
                for field_val in item.values():
                    if isinstance(field_val, str) and cn_lower in field_val.lower():
                        failures.append({
                            "field": f"{section_key}[{idx}]",
                            "reason": f"Company name '{company_name}' appears in non-first item of {section_key} (only allowed in first item)",
                            "value": field_val[:80],
                        })
                        break  # One failure per item is enough

    # BLOCKING personalization: advantage[0] must reference priority
    if priority:
        advantages = content.get("advantages", [])
        if len(advantages) >= 1:
            adv0_text = (
                advantages[0].get("headline", "") + " " + advantages[0].get("description", "")
            ).lower()
            priority_keywords = _extract_keywords(priority)
            if not any(kw in adv0_text for kw in priority_keywords):
                failures.append({
                    "field": "advantages[0]",
                    "reason": f"First advantage does not reference the stated priority '{priority}'. Must contain at least one keyword: {priority_keywords}",
                    "value": advantages[0].get("headline", ""),
                })

    # BLOCKING personalization: risk[0] must reference challenge
    if challenge:
        risks = content.get("risks", [])
        if len(risks) >= 1:
            risk0_text = (
                risks[0].get("headline", "") + " " + risks[0].get("description", "")
            ).lower()
            challenge_keywords = _extract_keywords(challenge)
            if not any(kw in risk0_text for kw in challenge_keywords):
                failures.append({
                    "field": "risks[0]",
                    "reason": f"First risk does not reference the stated challenge '{challenge}'. Must contain at least one keyword: {challenge_keywords}",
                    "value": risks[0].get("headline", ""),
                })

    # BLOCKING: case_study_relevance must mention industry or challenge
    if industry or challenge:
        relevance = content.get("case_study_relevance", "")
        if relevance:
            relevance_lower = relevance.lower()
            industry_keywords = _extract_keywords(industry) if industry else []
            challenge_keywords = _extract_keywords(challenge) if challenge else []
            all_relevance_keywords = industry_keywords + challenge_keywords
            if all_relevance_keywords and not any(kw in relevance_lower for kw in all_relevance_keywords):
                failures.append({
                    "field": "case_study_relevance",
                    "reason": f"Case study relevance does not mention the user's industry ('{industry}') or challenge ('{challenge}')",
                    "value": relevance[:80],
                })

    return {
        "passed": len(failures) == 0,
        "failures": failures,
    }


def _extract_keywords(phrase: str) -> list:
    """Extract meaningful keywords from a priority/challenge/industry phrase.

    E.g. 'Reducing cost' -> ['reducing', 'cost']
         'Legacy systems' -> ['legacy', 'systems']
         'Integration friction' -> ['integration', 'friction']
         'Healthcare' -> ['healthcare']
    """
    if not phrase:
        return []
    stopwords = {"the", "a", "an", "of", "for", "and", "or", "in", "to", "is", "at", "by", "on"}
    words = phrase.lower().split()
    return [w for w in words if w not in stopwords and len(w) > 2]


def _validate_field(
    value: str,
    field_path: str,
    spec: dict,
    failures: list,
    is_headline: bool = False,
) -> None:
    """Validate a single field against its spec and banned content rules."""
    if not value:
        failures.append({"field": field_path, "reason": "Empty value", "value": ""})
        return

    char_count = len(value)
    word_count = len(value.split())

    # Character limits
    if char_count < spec["min_chars"]:
        failures.append({
            "field": field_path,
            "reason": f"Below min chars ({char_count}/{spec['min_chars']})",
            "value": value,
        })
    if char_count > spec["max_chars"]:
        failures.append({
            "field": field_path,
            "reason": f"Exceeds max chars ({char_count}/{spec['max_chars']})",
            "value": value,
        })

    # Word limits
    if word_count < spec["min_words"]:
        failures.append({
            "field": field_path,
            "reason": f"Below min words ({word_count}/{spec['min_words']})",
            "value": value,
        })
    if word_count > spec["max_words"]:
        failures.append({
            "field": field_path,
            "reason": f"Exceeds max words ({word_count}/{spec['max_words']})",
            "value": value,
        })

    # Banned phrases
    value_lower = value.lower()
    for phrase in EXEC_REVIEW_BANNED_PHRASES:
        if phrase.lower() in value_lower:
            failures.append({
                "field": field_path,
                "reason": f"Contains banned phrase: '{phrase}'",
                "value": value,
            })

    # Banned characters (em dash, exclamation, etc.)
    for char in BANNED_CHARACTERS:
        if char in value:
            char_name = {
                "\u2014": "em dash",
                "\u2013": "en dash",
                "!": "exclamation mark",
                ":": "colon",
            }.get(char, char)
            # Colon check only applies to headlines
            if char == ":" and not is_headline:
                continue
            failures.append({
                "field": field_path,
                "reason": f"Contains banned character: {char_name}",
                "value": value,
            })

    # Headlines-only: no colons
    if is_headline:
        for char in BANNED_IN_HEADLINES:
            if char in value and char not in [c for c in BANNED_CHARACTERS]:
                failures.append({
                    "field": field_path,
                    "reason": f"Headline contains banned character: colon",
                    "value": value,
                })


# =============================================================================
# AMD CONTENT LOADER
# =============================================================================

_CONTENT_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "content"

# Map display industry names to content file names
_INDUSTRY_FILE_MAP = {
    "Healthcare": "KP_Industry_Healthcare.md",
    "Financial Services": "KP_Industry_Financial Services.md",
    "Manufacturing": "KP_Industry_Manufacturing.md",
    "Retail": "KP_Industry_Retail.md",
    "Energy": "KP_Industry_Energy.md",
    "Education": "KP_Industry_Education.md",
    "Media": "KP_Industry_Media and Ent.md",
    # Closest matches for industries without dedicated files
    "Technology": None,
    "Telecommunications": None,
    "Government": None,
    "Professional Services": None,
    "Other": None,
}

_PERSONA_FILE_MAP = {
    "ITDM": "KP_Job Function_ITDM.md",
    "BDM": "KP_Job Function_BDM.md",
}

_SEGMENT_FILE_MAP = {
    "Enterprise": "KP_Segment_Enterprise.md",
    "Mid-Market": "KP_Segment_Mid-Market.md",
    "SMB": "KP_Segment_SMB.md",
}


def _load_and_condense(file_path: Path, max_chars: int = 1800) -> str:
    """Load a markdown file and extract the most relevant sections, condensed."""
    if not file_path.exists():
        return ""

    try:
        text = file_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to read content file {file_path}: {e}")
        return ""

    # Extract sections: focus on section 1 (context) and section 2 (tech priorities)
    lines = text.split("\n")
    relevant_lines = []
    in_relevant_section = False
    section_count = 0

    for line in lines:
        # Track section headers (## numbered sections)
        if re.match(r"^##\s+\d+\.", line) or re.match(r"^##\s+[IVX]+\.", line):
            section_count += 1
            if section_count <= 2:
                in_relevant_section = True
            else:
                in_relevant_section = False

        # Also capture the first header / executive summary
        if re.match(r"^##\s+(Executive Summary|Industry Context|Buyer Context|Navigating)", line, re.IGNORECASE):
            in_relevant_section = True

        if in_relevant_section:
            # Skip bullet formatting artifacts
            cleaned = line.strip()
            if cleaned and not cleaned.startswith("- ○") and len(cleaned) > 10:
                relevant_lines.append(cleaned)

    condensed = " ".join(relevant_lines)

    # Truncate to max chars at a sentence boundary
    if len(condensed) > max_chars:
        truncated = condensed[:max_chars]
        last_period = truncated.rfind(".")
        if last_period > max_chars * 0.5:
            truncated = truncated[:last_period + 1]
        condensed = truncated

    return condensed


def load_amd_industry_context(industry: str) -> str:
    """Load AMD's vetted industry content for use in LLM prompt grounding."""
    filename = _INDUSTRY_FILE_MAP.get(industry)
    if not filename:
        return ""
    file_path = _CONTENT_DIR / filename
    return _load_and_condense(file_path)


def load_amd_persona_context(persona: str) -> str:
    """Load AMD's vetted persona content (ITDM/BDM)."""
    filename = _PERSONA_FILE_MAP.get(persona)
    if not filename:
        return ""
    file_path = _CONTENT_DIR / filename
    return _load_and_condense(file_path, max_chars=800)


def load_amd_segment_context(segment: str) -> str:
    """Load AMD's vetted segment content (Enterprise/Mid-Market/SMB)."""
    filename = _SEGMENT_FILE_MAP.get(segment)
    if not filename:
        # Government has its own file
        if segment == "Government" or segment == "government":
            file_path = _CONTENT_DIR / "KP_Segment_Government.md"
            return _load_and_condense(file_path, max_chars=800)
        return ""
    file_path = _CONTENT_DIR / filename
    return _load_and_condense(file_path, max_chars=800)


# =============================================================================
# FALLBACK: EXAMPLE WITH COMPANY NAME SWAP
# =============================================================================

def fallback_to_example(
    company_name: str,
    stage: str,
    industry: str,
    priority: str,
    challenge: str,
) -> dict:
    """
    Fall back to a gold-standard few-shot example with the company name swapped in.
    Uses industry/priority/challenge scoring to pick the best match, not just examples[0].
    Used when LLM output fails validation even after retry.
    """
    examples = FEW_SHOT_EXAMPLES_POOL.get(stage, FEW_SHOT_EXAMPLES_POOL["Challenger"])

    # Score examples by similarity to inputs (same logic as _select_best_example)
    best_example = examples[0]
    best_score = -1
    industry_groups = [
        {"healthcare", "life sciences", "pharma"},
        {"financial services", "banking", "insurance", "fintech"},
        {"retail", "ecommerce", "consumer goods"},
        {"manufacturing", "industrial", "automotive", "aec"},
        {"technology", "software", "telecommunications", "tech"},
        {"energy", "utilities", "oil and gas"},
    ]

    for example in examples:
        score = 0
        profile = example["profile"]
        p_industry = profile.get("industry", "").lower()
        if p_industry == industry.lower():
            score += 3
        else:
            for group in industry_groups:
                if any(t in p_industry for t in group) and any(t in industry.lower() for t in group):
                    score += 1
                    break
        if profile.get("priority", "").lower() == priority.lower():
            score += 2
        if profile.get("challenge", "").lower() == challenge.lower():
            score += 2
        if score > best_score:
            best_score = score
            best_example = example

    original_company = best_example["profile"]["company"]

    # Deep copy the output
    output = json.loads(json.dumps(best_example["output"]))

    # Swap company name in first item of each section
    def _swap_name(text: str) -> str:
        return text.replace(original_company, company_name)

    # Swap company name in executive summary
    if output.get("executive_summary"):
        output["executive_summary"] = _swap_name(output["executive_summary"])

    if output.get("advantages"):
        output["advantages"][0]["headline"] = _swap_name(output["advantages"][0]["headline"])
        output["advantages"][0]["description"] = _swap_name(output["advantages"][0]["description"])

    if output.get("risks"):
        output["risks"][0]["headline"] = _swap_name(output["risks"][0]["headline"])
        output["risks"][0]["description"] = _swap_name(output["risks"][0]["description"])

    if output.get("recommendations"):
        output["recommendations"][0]["description"] = _swap_name(output["recommendations"][0]["description"])

    # Swap in case_study_relevance
    if output.get("case_study_relevance"):
        output["case_study_relevance"] = _swap_name(output["case_study_relevance"])

    return output


# =============================================================================
# MAPPING FUNCTIONS
# =============================================================================

def map_company_size_to_segment(company_size: str) -> str:
    """Map company size to AMD segment (Enterprise/Mid-Market/SMB)."""
    mapping = {
        "startup": "SMB",
        "small": "SMB",
        "midmarket": "Mid-Market",
        "enterprise": "Enterprise",
        "large_enterprise": "Enterprise",
    }
    return mapping.get(company_size, "Enterprise")


def map_role_to_persona(role: str) -> str:
    """Map detailed role to AMD persona (BDM or ITDM)."""
    # Technical roles -> ITDM (IT Decision Maker)
    itdm_roles = {
        "cto", "cio", "ciso", "cdo",
        "vp_engineering", "vp_it", "vp_data", "vp_security",
        "eng_manager", "it_manager", "data_manager", "security_manager",
        "senior_engineer", "engineer", "sysadmin"
    }
    # Business roles -> BDM (Business Decision Maker)
    bdm_roles = {
        "ceo", "coo", "cfo", "c_suite_other",
        "vp_ops", "vp_finance",
        "ops_manager", "finance_manager", "procurement"
    }

    if role in itdm_roles:
        return "ITDM"
    elif role in bdm_roles:
        return "BDM"
    else:
        return "BDM"  # Default to BDM


def map_it_environment_to_stage(it_environment: str) -> str:
    """Map IT environment selection to modernization stage."""
    mapping = {
        "traditional": "Observer",
        "modernizing": "Challenger",
        "modern": "Leader",
    }
    return mapping.get(it_environment, "Challenger")


def get_stage_sidebar(stage: str) -> str:
    """Get the sidebar statistic for a stage."""
    sidebars = {
        "Observer": "9% of Observers plan to modernize within the next two years.",
        "Challenger": "58% of Challengers are currently undertaking modernization initiatives.",
        "Leader": "33% of Leaders have fully modernized in the past two years.",
    }
    return sidebars.get(stage, "")


def map_priority_display(priority: str) -> str:
    """Map priority code to display text."""
    mapping = {
        "reducing_cost": "Reducing cost",
        "improving_performance": "Improving workload performance",
        "preparing_ai": "Preparing for AI adoption",
    }
    return mapping.get(priority, priority)


def map_challenge_display(challenge: str) -> str:
    """Map challenge code to display text."""
    mapping = {
        "legacy_systems": "Legacy systems",
        "integration_friction": "Integration friction",
        "resource_constraints": "Resource constraints",
        "skills_gap": "Skills gap",
        "data_governance": "Data governance and compliance",
    }
    return mapping.get(challenge, challenge)


def map_industry_display(industry: str) -> str:
    """Map industry code to display text."""
    mapping = {
        "technology": "Technology",
        "financial_services": "Financial Services",
        "healthcare": "Healthcare",
        "manufacturing": "Manufacturing",
        "retail": "Retail",
        "energy": "Energy",
        "telecommunications": "Telecommunications",
        "media": "Media",
        "government": "Government",
        "education": "Education",
        "professional_services": "Professional Services",
        "other": "Other",
    }
    return mapping.get(industry, industry)


# =============================================================================
# CASE STUDY SELECTION
# =============================================================================

CASE_STUDIES = {
    "kt_cloud": {
        "name": "KT Cloud Expands AI Power with AMD Instinct Accelerators",
        "description": "KT Cloud built a scalable AI cloud service using AMD Instinct MI250 accelerators, increasing performance and reducing GPU service costs by up to 70%.",
        "link": "https://www.amd.com/en/resources/case-study/kt-cloud-expands-ai-power.html",  # TODO: verify exact URL
    },
    "smurfit_westrock": {
        "name": "Smurfit Westrock Saves AWS Costs for Innovation with AMD",
        "description": "Smurfit Westrock cut cloud costs by 25% and lowered its carbon footprint by 10% by transitioning to AWS instances powered by AMD EPYC CPUs.",
        "link": "https://www.amd.com/en/resources/case-study/smurfit-westrock-saves-aws-costs.html",  # TODO: verify exact URL
    },
    "pqr": {
        "name": "PQR Offers Next-Gen IT Services with AMD Pensando DPUs",
        "description": "PQR created a next-generation data center service emphasizing stronger security and operational simplicity using AMD Pensando DPU-enabled infrastructure.",
        "link": "https://www.amd.com/en/resources/case-study/pqr-next-gen-it-services.html",  # TODO: verify exact URL
    },
}


def select_case_study(stage: str, priority: str, industry: str, challenge: str = "") -> tuple[str, str, str]:
    """
    Select the most relevant case study based on stage, priority, industry, and challenge.
    Returns (case_study_name, case_study_description, case_study_link).

    Selection order:
    1. Priority "reducing_cost" → Smurfit Westrock (always)
    2. Security/compliance-heavy industries (healthcare, financial, government) → PQR
    3. Infrastructure/skills challenges for non-tech/retail industries → PQR
    4. Performance/AI priority for remaining industries → KT Cloud
    5. Stage-based default
    """
    # 1. Cost reduction always → Smurfit Westrock
    if priority == "reducing_cost":
        cs = CASE_STUDIES["smurfit_westrock"]
        return cs["name"], cs["description"], cs["link"]

    # 2. Security/compliance-heavy industries → PQR
    if industry in ["healthcare", "financial_services", "government"]:
        cs = CASE_STUDIES["pqr"]
        return cs["name"], cs["description"], cs["link"]

    # 3. Infrastructure/skills challenges for non-tech industries → PQR
    if challenge in ["skills_gap", "data_governance"] and industry not in ["technology", "telecommunications", "retail"]:
        cs = CASE_STUDIES["pqr"]
        return cs["name"], cs["description"], cs["link"]

    # 4. Performance/AI priority for remaining industries → KT Cloud
    if priority in ["improving_performance", "preparing_ai"]:
        cs = CASE_STUDIES["kt_cloud"]
        return cs["name"], cs["description"], cs["link"]

    # 5. Stage-based default
    if stage == "Observer":
        cs = CASE_STUDIES["smurfit_westrock"]
    elif stage == "Leader":
        cs = CASE_STUDIES["pqr"]
    else:
        cs = CASE_STUDIES["kt_cloud"]

    return cs["name"], cs["description"], cs["link"]


def build_stage_identification_text(company_name: str, stage: str) -> str:
    """Build the stage identification sentence matching AMD's format."""
    return f"Based on the information you shared, your organization best aligns with the {stage} stage of modernization."


# =============================================================================
# FEW-SHOT EXAMPLES
# =============================================================================

# Multiple examples per stage for variety in few-shot prompting
FEW_SHOT_EXAMPLES_POOL = {
    "Observer": [
        {
            "profile": {
                "company": "AECOM",
                "industry": "AEC",
                "segment": "Enterprise",
                "persona": "ITDM",
                "stage": "Observer",
                "priority": "Reducing cost",
                "challenge": "Legacy systems"
            },
            "output": {
                "executive_summary": "AECOM's infrastructure portfolio spans thousands of project sites running legacy BIM, CAD, and ERP systems that drive escalating maintenance costs. This assessment identifies where targeted modernization of high-cost legacy workloads can deliver measurable savings while building a foundation for future capabilities.",
                "advantages": [
                    {
                        "headline": "Cost savings from reducing legacy system overhead",
                        "description": "Retiring aging on-prem storage and compute tied to BIM and CAD workflows lowers operating costs across AECOM's globally distributed project teams. By consolidating redundant infrastructure, IT can redirect budget toward modernization priorities while reducing the maintenance hours spent on end-of-life hardware and software licensing."
                    },
                    {
                        "headline": "Efficiency gains through standardizing project data environments",
                        "description": "Unifying fragmented BIM, CAD, and project data platforms across regions creates immediate workflow efficiencies without requiring major architectural change. Standardized environments reduce onboarding time for distributed teams and eliminate the duplicated tooling costs that come from each project site running its own infrastructure stack."
                    }
                ],
                "risks": [
                    {
                        "headline": "High total cost of ownership from legacy infrastructure",
                        "description": "Running large, outdated on-prem systems at enterprise scale drives rising support, licensing, and hardware refresh costs that directly conflict with cost-reduction goals. Without a clear modernization path, these legacy systems will consume an increasing share of IT budget while delivering diminishing returns on reliability and performance."
                    },
                    {
                        "headline": "Integration gaps that add avoidable project costs",
                        "description": "Siloed tools and limited interoperability across field, design, and ERP systems increase rework risk on major construction projects. Each manual data handoff between disconnected platforms introduces errors that compound across AECOM's global project portfolio, making secure integration harder for IT teams to manage."
                    }
                ],
                "recommendations": [
                    {
                        "title": "Modernize the highest-cost legacy workloads first",
                        "description": "Target the most cost-intensive on-prem systems, starting with storage and compute tied to BIM and CAD workflows. Focus on the workloads where maintenance contracts are expiring or hardware refresh cycles are imminent, as these represent the clearest opportunities to reduce spend while improving stability for distributed project teams."
                    },
                    {
                        "title": "Standardize core infrastructure to reduce regional fragmentation",
                        "description": "Adopt consistent tooling and platform standards across AECOM's regional offices to lower integration effort for ITDM teams. This eliminates duplicated licensing spend across project sites and creates a unified environment that simplifies support, reduces training overhead, and accelerates new project onboarding."
                    },
                    {
                        "title": "Build a scalable foundation for future AI-driven design tools",
                        "description": "Upgrade underlying compute and storage infrastructure to support emerging AI-driven design, planning, and project management tools. Investing in scalable architecture now prevents the costly cycle of repeated rework that occurs when new capabilities are layered onto infrastructure that cannot handle the additional workload."
                    }
                ],
                "case_study_relevance": "Smurfit Westrock's 25% infrastructure cost reduction demonstrates what enterprise-scale legacy modernization delivers when executed with clear prioritization. Like AECOM, they operated distributed facilities with aging on-prem systems driving escalating maintenance costs. Their phased approach to consolidation and standardization mirrors the path AECOM can follow to reduce technical debt across its global project portfolio.",
                "case_study": "Smurfit Westrock"
            }
        },
        {
            "profile": {
                "company": "Allbirds",
                "industry": "Consumer Goods",
                "segment": "SMB",
                "persona": "BDM",
                "stage": "Observer",
                "priority": "Reducing cost",
                "challenge": "Resource constraints"
            },
            "output": {
                "executive_summary": "Allbirds operates with lean teams supporting a growing mix of ecommerce, retail, and supply chain systems that are becoming harder to maintain cost-effectively. This assessment identifies where simplifying and modernizing core platforms can reduce operational spend while freeing limited resources to focus on growth priorities.",
                "advantages": [
                    {
                        "headline": "Lower operating costs by modernizing high-expense systems",
                        "description": "Replacing or consolidating aging ecommerce and inventory infrastructure reduces ongoing maintenance spend and helps Allbirds stretch limited resources further. By targeting the platforms with the highest licensing and support costs first, the business can see measurable savings within the first quarter while improving system reliability for daily retail operations."
                    },
                    {
                        "headline": "Quick efficiency gains from simplifying fragmented environments",
                        "description": "Streamlining the disconnected systems behind ecommerce, inventory, and fulfillment operations cuts redundant manual work and reduces the burden on lean teams. Fewer platforms to manage means less context-switching for staff and faster resolution when issues arise, freeing capacity for growth-focused initiatives."
                    }
                ],
                "risks": [
                    {
                        "headline": "Rising costs from continuing to maintain outdated platforms",
                        "description": "Legacy ecommerce and operations platforms require increasing support effort and licensing spend as they age. For a lean organization like Allbirds, these rising costs consume budget that could otherwise fund modernization, creating a cycle where resource constraints make it harder to address the root cause of the spending."
                    },
                    {
                        "headline": "Resource constraints slow progress on foundational modernization",
                        "description": "Without additional support or simplification of the current technology stack, the organization may struggle to execute the upgrades needed to reduce cost and improve efficiency. Delayed modernization compounds the maintenance burden on already stretched teams, making each quarter harder than the last."
                    }
                ],
                "recommendations": [
                    {
                        "title": "Modernize the systems driving the highest operational costs",
                        "description": "Update or consolidate the platforms behind Allbirds' ecommerce, inventory, and fulfillment operations to reduce maintenance spend. Prioritize the systems with the most expensive support contracts or the highest manual intervention requirements, as these deliver the fastest return on modernization investment."
                    },
                    {
                        "title": "Simplify the tech stack to reduce workload on lean teams",
                        "description": "Standardize tools and remove redundant systems so limited staff can focus on the core platforms that directly support growth. A simpler stack reduces training requirements for new hires and makes it easier to maintain operational continuity when team members are unavailable."
                    },
                    {
                        "title": "Adopt solutions that deliver quick, low-effort efficiency gains",
                        "description": "Choose modernization steps with clear cost savings and minimal implementation lift so the organization can reduce spend without straining its small IT and operations teams. Quick wins build internal confidence and create budget headroom for larger modernization investments down the road."
                    }
                ],
                "case_study_relevance": "Smurfit Westrock achieved a 25% reduction in infrastructure costs through strategic consolidation of fragmented systems across distributed operations. Like Allbirds, they faced rising maintenance costs from a complex technology landscape that was absorbing resources needed for growth. Their approach of targeting the highest-cost platforms first and building momentum from early wins is directly applicable to a lean organization working with limited IT staff.",
                "case_study": "Smurfit Westrock"
            }
        }
    ],
    "Challenger": [
        {
            "profile": {
                "company": "Target",
                "industry": "Retail",
                "segment": "Enterprise",
                "persona": "BDM",
                "stage": "Challenger",
                "priority": "Improving workload performance",
                "challenge": "Integration friction"
            },
            "output": {
                "executive_summary": "Target's retail infrastructure handles massive transaction volumes across POS, ecommerce, and supply chain systems that must perform consistently during peak demand periods. This assessment focuses on where improving workload performance and reducing integration friction across core retail platforms can strengthen customer experience and protect revenue.",
                "advantages": [
                    {
                        "headline": "Performance gains from upgrading core retail transaction systems",
                        "description": "Modernizing the compute infrastructure behind Target's highest-volume POS, ecommerce, and inventory workloads improves responsiveness during peak shopping periods. Faster transaction processing reduces checkout abandonment rates and enables real-time inventory visibility that prevents the stockout and overstock conditions that directly impact revenue."
                    },
                    {
                        "headline": "Faster throughput by eliminating integration bottlenecks",
                        "description": "Improving data flow between merchandising, inventory, and digital platforms enables more consistent performance for customer-facing processes. When pricing updates, promotions, and inventory changes propagate in near-real-time across all channels, the organization can execute omnichannel retail strategies without the delays that frustrate customers and erode margins."
                    }
                ],
                "risks": [
                    {
                        "headline": "Persistent slowdowns from fragmented system integrations",
                        "description": "If integration friction between POS, ecommerce, and supply chain systems remains unresolved, performance bottlenecks will continue to surface during high-traffic periods. These slowdowns directly affect revenue during critical shopping events and degrade the customer experience that Target has invested heavily in building across its omnichannel retail presence."
                    },
                    {
                        "headline": "Competitors advance with more unified retail platforms",
                        "description": "Retailers who have already consolidated their commerce platforms can push promotions, adjust pricing, and fulfill orders faster than organizations still managing fragmented integrations. Each quarter of delay in improving system performance widens the gap in operational speed and customer responsiveness that defines competitive positioning in retail."
                    }
                ],
                "recommendations": [
                    {
                        "title": "Prioritize performance upgrades for high-volume retail workloads",
                        "description": "Focus modernization on the transactional systems that power POS, ecommerce, and inventory management during peak demand periods. Benchmark current response times against Target's peak traffic volumes and set measurable performance targets that align with revenue-critical shopping events like back-to-school, holiday, and promotional campaigns."
                    },
                    {
                        "title": "Strengthen integration across core retail and supply chain platforms",
                        "description": "Improve data consistency and flow between store systems, digital platforms, and supply chain management to eliminate the performance delays that impact customer experience. Prioritize the integration points where data latency causes the most visible customer-facing issues, such as inventory availability and order fulfillment accuracy."
                    },
                    {
                        "title": "Adopt scalable infrastructure to support unified commerce operations",
                        "description": "Move toward flexible compute and storage environments that can scale dynamically with Target's seasonal demand patterns. Infrastructure that auto-scales during peak traffic prevents the performance degradation that occurs when fixed-capacity systems are pushed beyond their design limits during critical revenue periods."
                    }
                ],
                "case_study_relevance": "KT Cloud's infrastructure modernization demonstrates how large-scale organizations achieve measurable performance improvements across high-volume transaction systems. Like Target, they needed to handle massive throughput demands while maintaining consistent responsiveness. Their approach to upgrading core compute and streamlining platform integrations parallels Target's need to improve POS and ecommerce performance while reducing retail supply chain friction.",
                "case_study": "KT Cloud"
            }
        },
        {
            "profile": {
                "company": "Caterpillar",
                "industry": "Manufacturing",
                "segment": "Enterprise",
                "persona": "BDM",
                "stage": "Challenger",
                "priority": "Improving workload performance",
                "challenge": "Skills gap"
            },
            "output": {
                "executive_summary": "Caterpillar's manufacturing operations depend on complex OT and IT systems that support equipment monitoring, production analytics, and global supply chain coordination. This assessment identifies where improving workload performance and addressing skills gaps can strengthen operational reliability and competitive positioning across global manufacturing sites.",
                "advantages": [
                    {
                        "headline": "Performance gains from modernizing critical industrial workloads",
                        "description": "Upgrading compute environments that support Caterpillar's equipment monitoring and production analytics improves reliability across global manufacturing operations. Faster data processing from plant-floor sensors and OT systems enables earlier detection of equipment issues, reducing unplanned downtime that costs millions in lost production capacity annually."
                    },
                    {
                        "headline": "Fewer delays by reducing friction between OT and IT systems",
                        "description": "Improving integration across factory equipment, ERP, and analytics platforms enables more consistent performance and faster issue resolution for production teams. When OT data flows reliably into IT analytics systems, manufacturing managers can make decisions based on current production conditions rather than waiting for batch reports that may already be outdated."
                    }
                ],
                "risks": [
                    {
                        "headline": "Operational slowdowns if legacy OT connections remain unaddressed",
                        "description": "If outdated interfaces between plant-floor equipment and enterprise IT systems are not modernized, performance issues will continue to impact production output, equipment uptime, and downstream supply chain operations. These slowdowns compound across Caterpillar's global manufacturing footprint, where minutes of unplanned downtime on critical production lines translate directly to revenue loss."
                    },
                    {
                        "headline": "Skills gaps limiting the impact of modernization investments",
                        "description": "Without enough talent experienced in both OT and IT systems, performance improvements may stall at individual sites rather than scaling across the enterprise. Manufacturing organizations that invest in infrastructure modernization without simultaneously building internal capabilities often see adoption bottlenecks that prevent the full return on their technology investments."
                    }
                ],
                "recommendations": [
                    {
                        "title": "Prioritize modernization of core production monitoring systems",
                        "description": "Focus upgrades on the equipment monitoring, analytics, and plant-floor workloads that have the greatest impact on Caterpillar's production uptime and output quality. Start with the manufacturing sites that have the highest downtime costs, as these provide the clearest business case and fastest payback on infrastructure modernization investment."
                    },
                    {
                        "title": "Strengthen integration across OT and IT environments",
                        "description": "Standardize data platforms and improve the flow between factory equipment, ERP, and analytics tools to reduce the delays that undermine operational reliability. Prioritize the OT-IT integration points where data latency or format inconsistencies create the most significant production planning blind spots across manufacturing sites."
                    },
                    {
                        "title": "Invest in training programs that close critical OT-IT skills gaps",
                        "description": "Expand internal training programs and bring in specialized expertise so modernization work can scale across manufacturing sites and support integrated OT-IT operations. Partner with equipment vendors and technology providers to create role-specific certification paths that build the skills needed to maintain modernized infrastructure independently."
                    }
                ],
                "case_study_relevance": "PQR's infrastructure modernization in an industrial environment demonstrates how manufacturing organizations can improve system performance while managing the skills challenges that come with OT-IT convergence. Their phased approach to upgrading production-critical systems while building internal capabilities mirrors the path Caterpillar needs to follow to scale performance improvements across a global manufacturing footprint without creating dependency on external consultants.",
                "case_study": "PQR"
            }
        }
    ],
    "Leader": [
        {
            "profile": {
                "company": "HCA Healthcare",
                "industry": "Healthcare",
                "segment": "Enterprise",
                "persona": "ITDM",
                "stage": "Leader",
                "priority": "Preparing for AI adoption",
                "challenge": "Data governance and compliance"
            },
            "output": {
                "executive_summary": "HCA Healthcare's IT infrastructure is well-positioned for AI adoption, with modern compute environments and established data governance across EHR, imaging, and clinical systems. This assessment identifies where strengthening data foundations and expanding governance frameworks can accelerate the safe deployment of clinical AI at enterprise scale while maintaining HIPAA compliance.",
                "advantages": [
                    {
                        "headline": "Strong infrastructure readiness for advanced clinical AI workloads",
                        "description": "HCA's modern, scalable compute environment gives IT teams the foundation to support clinical AI models requiring high-performance processing and reliable patient data access at enterprise scale. The existing infrastructure handles GPU-intensive diagnostic imaging AI and predictive analytics without the costly rearchitecture that organizations at earlier stages must undertake first."
                    },
                    {
                        "headline": "Tighter governance accelerates HIPAA-compliant AI deployment",
                        "description": "With established data controls across EHR, PACS imaging, and operational systems, the organization can evaluate and deploy AI use cases confidently within strict HIPAA boundaries. This governance maturity means HCA can move from AI pilots to production deployment faster than competitors still building the data quality and audit infrastructure that regulators require."
                    }
                ],
                "risks": [
                    {
                        "headline": "Data governance gaps threaten AI accuracy and patient safety",
                        "description": "If interoperability or data quality issues persist across clinical and administrative systems, AI models may produce unreliable outputs that increase compliance risk. In healthcare, inaccurate AI-driven insights can affect patient care decisions, making data governance not just a technical requirement but a patient safety imperative that regulators scrutinize closely."
                    },
                    {
                        "headline": "Regulatory complexity can slow enterprise-scale AI deployment",
                        "description": "Healthcare's regulatory environment requires rigorous validation, documentation, and ongoing monitoring for every AI system that touches patient data. This compliance overhead may extend timelines for operationalizing AI at scale, particularly when different clinical departments have varying data standards and governance practices that must be harmonized."
                    }
                ],
                "recommendations": [
                    {
                        "title": "Strengthen data foundations for clinical AI across EHR systems",
                        "description": "Improve data quality, standardization, and interoperability across EHR, PACS imaging, and operational systems to ensure AI models receive consistent, accurate inputs. Prioritize the HL7 FHIR integration points that connect clinical data sources, as these determine whether AI tools can access the comprehensive patient records needed for reliable diagnostic and predictive outputs."
                    },
                    {
                        "title": "Expand governance frameworks for safe clinical AI deployment",
                        "description": "Enhance validation, documentation, and audit controls so HCA's IT teams can deploy AI tools that meet HIPAA and FDA requirements for clinical decision support. Build governance templates that can be replicated across departments and facilities, reducing the time and effort needed to bring each new AI use case through the regulatory approval process."
                    },
                    {
                        "title": "Scale high-performance infrastructure for GPU-intensive AI models",
                        "description": "Increase GPU compute and storage capacity to run demanding clinical AI models for diagnostic imaging, patient risk scoring, and operational optimization. Right-size infrastructure investments to the specific AI workloads that HCA is prioritizing, avoiding over-provisioning while ensuring enough capacity to support concurrent model training and inference across facilities."
                    }
                ],
                "case_study_relevance": "PQR's healthcare infrastructure modernization demonstrates how large health systems build the data foundations and governance controls needed for compliant AI adoption at scale. Like HCA, they needed to ensure that clinical AI systems met strict HIPAA requirements while delivering reliable outputs across EHR and imaging systems. Their phased approach to strengthening data quality before scaling AI deployment directly parallels HCA's path to enterprise-wide clinical AI readiness.",
                "case_study": "PQR"
            }
        },
        {
            "profile": {
                "company": "JPMorgan Chase",
                "industry": "Financial Services",
                "segment": "Enterprise",
                "persona": "BDM",
                "stage": "Leader",
                "priority": "Improving workload performance",
                "challenge": "Data governance and compliance"
            },
            "output": {
                "executive_summary": "JPMorgan Chase operates at the frontier of financial technology, where milliseconds of latency in trading systems and transaction processing directly translate to competitive advantage or lost revenue. This assessment identifies where optimizing workload performance and streamlining governance can strengthen market positioning while maintaining the regulatory compliance that protects the institution's reputation.",
                "advantages": [
                    {
                        "headline": "Performance optimization drives measurable competitive trading advantages",
                        "description": "JPMorgan Chase can leverage optimized compute infrastructure to execute transactions faster and more reliably than competitors in latency-sensitive markets. In high-frequency trading environments, infrastructure performance improvements measured in microseconds can translate to millions in additional revenue capture, making compute optimization one of the highest-ROI investments available."
                    },
                    {
                        "headline": "Strong governance enables compliant innovation at enterprise scale",
                        "description": "Mature data controls and automated audit capabilities allow the organization to deploy new trading algorithms and analytics systems while maintaining compliance with SEC, FINRA, and global regulatory requirements. This governance maturity means the institution can innovate faster than competitors who must build compliance infrastructure from scratch for each new system or product launch."
                    }
                ],
                "risks": [
                    {
                        "headline": "Compliance overhead may constrain trading performance gains",
                        "description": "If governance requirements add latency or complexity to critical trading and risk management systems, the institution may not fully realize performance benefits of infrastructure modernization. Maintaining the audit trail, data lineage, and regulatory reporting that regulators demand without introducing processing overhead that erodes competitive advantage remains an ongoing challenge."
                    },
                    {
                        "headline": "Fintech competitors move faster with lighter regulatory burdens",
                        "description": "Newer financial technology firms with simpler regulatory obligations can iterate on performance improvements and deploy new capabilities more rapidly. While compliance protects JPMorgan Chase's market position, the operational overhead of maintaining it across thousands of systems creates a speed disadvantage that compounds with each new regulatory requirement."
                    }
                ],
                "recommendations": [
                    {
                        "title": "Optimize infrastructure for latency-sensitive trading workloads",
                        "description": "Focus performance improvements on the compute and networking systems that directly impact execution speed in JPMorgan Chase's highest-revenue trading operations. Benchmark current latency against tier-one competitors and set measurable performance targets that translate directly to quantifiable revenue impact in high-frequency and algorithmic trading."
                    },
                    {
                        "title": "Streamline regulatory compliance without sacrificing audit controls",
                        "description": "Implement automated governance and real-time audit capabilities that maintain SEC, FINRA, and global regulatory compliance while reducing the manual processing overhead that adds latency to critical systems. Modernize compliance infrastructure so that regulatory requirements are met through efficient automation rather than performance-constraining manual processes."
                    },
                    {
                        "title": "Deploy AI for real-time risk assessment and fraud prevention",
                        "description": "Leverage optimized compute infrastructure to run advanced AI models that improve risk management and fraud detection accuracy without adding transaction processing latency. Position these AI capabilities as competitive differentiators that simultaneously strengthen compliance posture and improve the speed and accuracy of critical financial decisions."
                    }
                ],
                "case_study_relevance": "PQR's approach to modernizing performance-critical infrastructure while maintaining strict regulatory compliance demonstrates the path large financial institutions must follow. Like JPMorgan Chase, they needed to improve system performance where every change requires regulatory validation. Their success in automating compliance controls while delivering measurable performance improvements provides a proven framework for balancing speed and governance.",
                "case_study": "PQR"
            }
        }
    ]
}

# Default to first example for each stage (maintains backward compatibility)
FEW_SHOT_EXAMPLES = {
    stage: examples[0] for stage, examples in FEW_SHOT_EXAMPLES_POOL.items()
}


# =============================================================================
# EXECUTIVE REVIEW GENERATION
# =============================================================================

class ExecutiveReviewService:
    """Service for generating AMD Executive Review content."""

    def __init__(self):
        self.client = None
        if settings.ANTHROPIC_API_KEY:
            self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def generate_executive_review(
        self,
        company_name: str,
        industry: str,
        segment: str,
        persona: str,
        stage: str,
        priority: str,
        challenge: str,
        enrichment_context: dict | None = None,
    ) -> dict:
        """
        Generate executive review content using few-shot prompting.

        Args:
            company_name: Company name
            industry: Industry (display text)
            segment: Segment (Enterprise/Mid-Market/SMB)
            persona: Persona (BDM/ITDM)
            stage: Modernization stage (Observer/Challenger/Leader)
            priority: Business priority (display text)
            challenge: Challenge (display text)

        Returns:
            Dict with stage, advantages, risks, recommendations, case_study,
            case_study_link, stage_identification_text
        """
        if not self.client:
            logger.warning("No Anthropic client - returning mock executive review")
            return self._get_mock_response(company_name, stage, priority, industry, challenge)

        # Get the best matching few-shot example based on stage and other inputs
        example = self._select_best_example(stage, industry, priority, challenge)

        # Build the prompt
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            company_name=company_name,
            industry=industry,
            segment=segment,
            persona=persona,
            stage=stage,
            priority=priority,
            challenge=challenge,
            example=example,
            enrichment_context=enrichment_context,
        )

        try:
            response = await self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                system=system_prompt,
                tools=[EXECUTIVE_REVIEW_TOOL_SCHEMA],
                tool_choice={"type": "tool", "name": "generate_executive_review"},
            )

            # Extract structured data from tool_use response
            result_data = None
            for block in response.content:
                if block.type == "tool_use":
                    result_data = block.input
                    break

            if not result_data:
                logger.error("No tool_use block in response, falling back")
                return self._get_mock_response(company_name, stage, priority, industry, challenge)

            # Build the full result with case study and stage info
            case_study_name, case_study_desc, case_study_link = select_case_study(stage, priority, industry, challenge)
            result = {
                "company_name": company_name,
                "stage": stage,
                "stage_sidebar": get_stage_sidebar(stage),
                "stage_identification_text": build_stage_identification_text(company_name, stage),
                "executive_summary": result_data.get("executive_summary", ""),
                "advantages": result_data.get("advantages", []),
                "risks": result_data.get("risks", []),
                "recommendations": result_data.get("recommendations", []),
                "case_study": case_study_name,
                "case_study_description": case_study_desc,
                "case_study_link": case_study_link,
                "case_study_relevance": result_data.get("case_study_relevance", ""),
            }

            # Run content validation (personalization checks are now blocking)
            validation = validate_executive_review_content(
                result, priority=priority, challenge=challenge, industry=industry
            )
            if not validation["passed"]:
                logger.warning(f"Content validation failed ({len(validation['failures'])} issues): {validation['failures']}")
                # Attempt targeted retry for failing fields
                result = await self._retry_failing_fields(
                    result, validation["failures"], company_name, stage,
                    industry, segment, persona, priority, challenge, system_prompt
                )

            return result

        except Exception as e:
            logger.error(f"Executive review generation failed: {e}")
            return self._get_mock_response(company_name, stage, priority, industry, challenge)

    def _select_best_example(self, stage: str, industry: str, priority: str, challenge: str) -> dict:
        """Select the most relevant few-shot example based on inputs."""
        examples = FEW_SHOT_EXAMPLES_POOL.get(stage, FEW_SHOT_EXAMPLES_POOL["Challenger"])

        if len(examples) == 1:
            return examples[0]

        # Score each example based on similarity to inputs
        best_example = examples[0]
        best_score = 0

        for example in examples:
            score = 0
            profile = example["profile"]

            # Industry match (highest weight)
            if profile.get("industry", "").lower() == industry.lower():
                score += 3
            elif self._industries_similar(profile.get("industry", ""), industry):
                score += 1

            # Priority match
            if profile.get("priority", "").lower() in priority.lower() or priority.lower() in profile.get("priority", "").lower():
                score += 2

            # Challenge match
            if profile.get("challenge", "").lower() in challenge.lower() or challenge.lower() in profile.get("challenge", "").lower():
                score += 2

            if score > best_score:
                best_score = score
                best_example = example

        return best_example

    def _industries_similar(self, industry1: str, industry2: str) -> bool:
        """Check if two industries are in the same category."""
        industry_groups = [
            {"retail", "ecommerce", "consumer", "consumer goods"},
            {"healthcare", "life sciences", "pharma", "medical"},
            {"financial services", "banking", "insurance", "fintech"},
            {"manufacturing", "industrial", "automotive", "aec"},
            {"technology", "software", "telecommunications", "tech"},
            {"energy", "utilities", "oil and gas"},
        ]

        i1_lower = industry1.lower()
        i2_lower = industry2.lower()

        for group in industry_groups:
            if any(term in i1_lower for term in group) and any(term in i2_lower for term in group):
                return True
        return False

    async def _retry_failing_fields(
        self,
        result: dict,
        failures: list,
        company_name: str,
        stage: str,
        industry: str,
        segment: str,
        persona: str,
        priority: str,
        challenge: str,
        system_prompt: str,
        max_retries: int = 2,
    ) -> dict:
        """
        Retry only the specific fields that failed validation.
        If retry fails, fall back to gold-standard example content for those fields.
        """
        if not self.client or not failures:
            return self._apply_fallback_fields(result, failures, company_name, stage, industry, priority, challenge)

        # Group failures by section (advantages[0].headline -> advantages)
        failing_sections = set()
        for f in failures:
            section = f["field"].split("[")[0]
            failing_sections.add(section)

        for attempt in range(max_retries):
            # Build a targeted retry prompt
            failure_details = "\n".join(
                f"- {f['field']}: {f['reason']} (current value: \"{f['value']}\")"
                for f in failures
            )
            retry_prompt = f"""The following fields in the executive review for {company_name} ({industry}) failed validation:

{failure_details}

Please regenerate ONLY the sections that contain failures: {', '.join(failing_sections)}.
Keep the same personalization (industry={industry}, priority={priority}, challenge={challenge}, stage={stage}).
Headlines must be 4-12 words (20-80 characters). Descriptions must be 25-65 words (150-400 characters), 2-3 sentences each.
No colons in headlines, no em dashes, no exclamation marks, no banned filler phrases."""

            try:
                response = await self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1500,
                    messages=[{"role": "user", "content": retry_prompt}],
                    system=system_prompt,
                    tools=[EXECUTIVE_REVIEW_TOOL_SCHEMA],
                    tool_choice={"type": "tool", "name": "generate_executive_review"},
                )

                retry_data = None
                for block in response.content:
                    if block.type == "tool_use":
                        retry_data = block.input
                        break

                if not retry_data:
                    continue

                # Merge only the failing sections back in
                for section in failing_sections:
                    if section in retry_data and retry_data[section]:
                        result[section] = retry_data[section]

                # Re-validate
                validation = validate_executive_review_content(result)
                if validation["passed"]:
                    logger.info(f"Retry {attempt + 1} fixed all validation failures")
                    return result
                failures = validation["failures"]
                logger.warning(f"Retry {attempt + 1} still has {len(failures)} failures")

            except Exception as e:
                logger.error(f"Retry {attempt + 1} failed with error: {e}")
                break

        # All retries exhausted — fall back to example content for failing fields
        logger.warning("All retries exhausted, applying fallback for failing fields")
        return self._apply_fallback_fields(result, failures, company_name, stage, industry, priority, challenge)

    def _apply_fallback_fields(
        self,
        result: dict,
        failures: list,
        company_name: str,
        stage: str,
        industry: str,
        priority: str,
        challenge: str,
    ) -> dict:
        """Replace only failing fields with gold-standard example content."""
        fb = fallback_to_example(company_name, stage, industry, priority, challenge)

        failing_sections = set()
        for f in failures:
            section = f["field"].split("[")[0]
            failing_sections.add(section)

        for section in failing_sections:
            if section in fb:
                result[section] = fb[section]
                logger.info(f"Replaced failing section '{section}' with fallback example content")

        return result

    def _build_system_prompt(self) -> str:
        """Build the system prompt with AMD content rules."""
        return """You are an expert business strategist creating personalized executive reviews for AMD's Data Center Modernization program.

Your output must follow these strict rules:

CONTENT STRUCTURE:
- Executive Summary: 2-3 sentences (35-90 words) framing the assessment for this specific company
- Headlines: 4-12 words, imperative or benefit-driven, no colons
- Advantage/Risk Descriptions: 2-3 sentences, 25-65 words, human and professional tone with specific systems and outcomes
- Recommendation Descriptions: 3-4 sentences, 35-90 words, detailed actionable guidance with implementation specifics and expected outcomes
- Case Study Relevance: 2-4 sentences explaining how the case study maps to the company's situation
- No jargon, buzzwords, hype, or filler phrases like "in today's landscape"
- No em dashes, no exclamation marks, no emojis

COMPANY NAME RULES:
- Use the company name in the executive summary and FIRST item of each section (advantages, risks, recommendations)
- After first mention in each section, use pronouns: "their environment", "the company", "the organization", "their teams"
- Never repeat the company name across every line (this is an AI tell)

PERSONALIZATION REQUIREMENTS (CRITICAL):
You MUST incorporate ALL of these inputs into the content:
- INDUSTRY: Reference industry-specific workloads, systems, and use cases using the terminology table below
- PERSONA: Tailor language for the reader (ITDM = technical infrastructure focus, BDM = business outcomes focus)
- PRIORITY: The executive summary, first advantage, and first recommendation MUST directly address the stated priority
- CHALLENGE: The first risk MUST directly reference the stated challenge and its consequences
- COMPANY INTELLIGENCE: When company-specific data is provided (employee count, growth rate, funding, news, AI readiness), you MUST weave these facts into the narrative. Reference specific numbers, recent initiatives, and market signals. This is what makes each review unique to the company rather than generic to the industry.

INDUSTRY TERMINOLOGY (use these terms in your output):
- Healthcare: EHR systems, clinical AI, imaging systems, HIPAA compliance, patient data
- Financial Services: trading systems, fraud detection, regulatory compliance, transaction processing
- Retail: POS systems, ecommerce platforms, inventory management, supply chain, omnichannel
- Manufacturing: OT systems, equipment monitoring, plant-floor workloads, ERP, production systems
- Technology: cloud infrastructure, developer platforms, CI/CD pipelines, microservices
- Telecommunications: network infrastructure, 5G, service delivery platforms, subscriber management
- Energy: SCADA systems, grid management, operational technology, asset monitoring
- Government: citizen services, secure infrastructure, compliance frameworks, data sovereignty
- Education: learning platforms, research computing, student information systems
- AEC: BIM, CAD, project data, distributed project teams, field systems

STAGE-SPECIFIC FOCUS:
- Observer: low-lift, cost-saving steps, foundational efficiency, reducing technical debt
- Challenger: performance optimization, integration improvements, scalability, competitive positioning
- Leader: governance, AI readiness, optimization at scale, maintaining competitive advantage

OUTPUT FORMAT:
Return valid JSON only, no markdown, no explanation. Match the exact structure shown in the example."""

    def _build_user_prompt(
        self,
        company_name: str,
        industry: str,
        segment: str,
        persona: str,
        stage: str,
        priority: str,
        challenge: str,
        example: dict,
        enrichment_context: dict | None = None,
    ) -> str:
        """Build the user prompt with few-shot example, AMD IP context, and enrichment data."""
        # Get persona-specific language guidance
        persona_guidance = {
            "ITDM": "Focus on infrastructure, systems, technical architecture, and IT operational efficiency.",
            "BDM": "Focus on business outcomes, revenue impact, competitive positioning, and operational results."
        }

        # Load AMD IP content for grounding
        amd_context_parts = []
        industry_ctx = load_amd_industry_context(industry)
        if industry_ctx:
            amd_context_parts.append(f"AMD INDUSTRY CONTEXT ({industry}):\n{industry_ctx}")
        persona_ctx = load_amd_persona_context(persona)
        if persona_ctx:
            amd_context_parts.append(f"AMD PERSONA CONTEXT ({persona}):\n{persona_ctx}")
        segment_ctx = load_amd_segment_context(segment)
        if segment_ctx:
            amd_context_parts.append(f"AMD SEGMENT CONTEXT ({segment}):\n{segment_ctx}")

        amd_context_block = ""
        if amd_context_parts:
            amd_context_block = "\n\n---\nAMD REFERENCE MATERIAL (use to ground your recommendations in AMD's actual capabilities):\n\n" + "\n\n".join(amd_context_parts) + "\n---\n"

        # Build company-specific intelligence block from enrichment data
        company_intel_block = self._build_company_intelligence_block(enrichment_context)

        return f"""Generate an executive review for this profile:

Company: {company_name}
Industry: {industry}
Segment: {segment}
Persona: {persona} - {persona_guidance.get(persona, persona_guidance["BDM"])}
Stage: {stage}
Business Priority: {priority}
Challenge: {challenge}
{company_intel_block}{amd_context_block}
PERSONALIZATION CHECKLIST (you must address ALL of these):
1. Executive summary MUST mention {company_name} and frame around "{priority}"
2. First advantage headline MUST relate to "{priority}"
3. First risk headline MUST reference consequences of "{challenge}"
4. Content MUST use {industry}-specific terminology and systems
5. Language MUST be appropriate for a {persona} reader
6. Recommendations MUST be {stage}-appropriate ({"foundational, cost-focused" if stage == "Observer" else "performance, integration-focused" if stage == "Challenger" else "optimization, AI-readiness focused"})
7. Recommendation descriptions MUST be 3-4 sentences with specific implementation guidance and expected outcomes
8. Case study relevance MUST explain the connection to {company_name}'s specific {industry} challenges
9. Content MUST reference specific company intelligence where available (news, headcount, growth, funding, AI readiness signals)

Here is an example of excellent output for a {stage} stage company:

INPUT:
{json.dumps(example["profile"], indent=2)}

OUTPUT:
{json.dumps(example["output"], indent=2)}

Now generate the executive review for {company_name}. The content must be clearly personalized to their specific industry ({industry}), priority ({priority}), and challenge ({challenge}). Where company intelligence is provided above, weave specific facts (employee count, growth rate, recent initiatives, funding stage) into the narrative to make it unmistakably about this company.

Use the generate_executive_review tool to return your response."""

    def _build_company_intelligence_block(self, enrichment_context: dict | None) -> str:
        """Build a COMPANY-SPECIFIC INTELLIGENCE section from enrichment data for the LLM prompt."""
        if not enrichment_context:
            return ""

        parts = []

        # Company overview
        company_summary = enrichment_context.get("company_summary")
        if company_summary:
            parts.append(f"Company Overview: {company_summary}")

        # Contact's role
        title = enrichment_context.get("title")
        if title:
            parts.append(f"Contact's Title: {title}")

        # Company metrics
        metrics = []
        employee_count = enrichment_context.get("employee_count")
        if employee_count:
            metrics.append(f"{employee_count:,} employees" if isinstance(employee_count, (int, float)) else f"{employee_count} employees")
        founded_year = enrichment_context.get("founded_year")
        if founded_year:
            metrics.append(f"Founded {founded_year}")
        growth_rate = enrichment_context.get("employee_growth_rate")
        if growth_rate:
            metrics.append(f"Employee growth: {growth_rate}%")
        funding_stage = enrichment_context.get("latest_funding_stage")
        if funding_stage:
            metrics.append(f"Funding stage: {funding_stage}")
        total_funding = enrichment_context.get("total_funding")
        if total_funding:
            if isinstance(total_funding, (int, float)) and total_funding >= 1_000_000:
                metrics.append(f"Total funding: ${total_funding / 1_000_000:.0f}M")
            else:
                metrics.append(f"Total funding: {total_funding}")
        if metrics:
            parts.append(f"Company Metrics: {' | '.join(metrics)}")

        # News intelligence
        news_analysis = enrichment_context.get("news_analysis", {})
        ai_readiness = news_analysis.get("ai_readiness")
        sentiment = news_analysis.get("sentiment")
        crisis = news_analysis.get("crisis")

        signals = []
        if ai_readiness and ai_readiness != "none":
            signals.append(f"AI readiness: {ai_readiness}")
        if sentiment:
            signals.append(f"News sentiment: {sentiment}")
        if crisis:
            signals.append("Crisis signals detected")
        if signals:
            parts.append(f"Market Signals: {' | '.join(signals)}")

        # News themes
        news_themes = enrichment_context.get("news_themes", [])
        if news_themes:
            parts.append(f"News Themes: {', '.join(news_themes)}")

        # Recent news headlines
        recent_news = enrichment_context.get("recent_news", [])
        if recent_news:
            headlines = []
            for article in recent_news[:5]:
                title_text = article.get("title", "")
                source = article.get("source", "")
                category = article.get("query_category", "")
                if title_text:
                    entry = f"- {title_text}"
                    if source:
                        entry += f" ({source})"
                    if category:
                        entry += f" [{category}]"
                    headlines.append(entry)
            if headlines:
                parts.append("Recent News:\n" + "\n".join(headlines))

        if not parts:
            return ""

        return "\n\n---\nCOMPANY-SPECIFIC INTELLIGENCE (use these facts to make content specific to this company):\n" + "\n".join(parts) + "\n---\n"

    def _parse_response(self, content: str, company_name: str, stage: str, priority: str, industry: str, challenge: str = "") -> dict:
        """Parse the LLM response into structured output."""
        try:
            # Try to extract JSON from the response
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            data = json.loads(content)

            # Get case study (now returns 3-tuple with link)
            case_study_name, case_study_desc, case_study_link = select_case_study(stage, priority, industry, challenge)

            result = {
                "company_name": company_name,
                "stage": stage,
                "stage_sidebar": get_stage_sidebar(stage),
                "stage_identification_text": build_stage_identification_text(company_name, stage),
                "executive_summary": data.get("executive_summary", ""),
                "advantages": data.get("advantages", []),
                "risks": data.get("risks", []),
                "recommendations": data.get("recommendations", []),
                "case_study": case_study_name,
                "case_study_description": case_study_desc,
                "case_study_link": case_study_link,
                "case_study_relevance": data.get("case_study_relevance", ""),
            }

            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse executive review JSON: {e}")
            return self._get_mock_response(company_name, stage, priority, industry, challenge)

    def _get_mock_response(self, company_name: str, stage: str, priority: str, industry: str, challenge: str = "") -> dict:
        """Return a mock response when LLM is unavailable, with company name swapped."""
        example = FEW_SHOT_EXAMPLES.get(stage, FEW_SHOT_EXAMPLES["Challenger"])
        example_company = example["profile"]["company"]
        case_study_name, case_study_desc, case_study_link = select_case_study(stage, priority, industry, challenge)

        def swap_company(text: str) -> str:
            """Replace the example company name with the actual company name."""
            if not text or not example_company:
                return text
            # Replace full name and possessive forms
            text = text.replace(f"{example_company}'s", f"{company_name}'s")
            text = text.replace(example_company, company_name)
            return text

        def swap_in_items(items: list, fields: list) -> list:
            """Deep-copy list of dicts, swapping company name in specified fields."""
            result = []
            for item in items:
                new_item = dict(item)
                for field in fields:
                    if field in new_item and isinstance(new_item[field], str):
                        new_item[field] = swap_company(new_item[field])
                result.append(new_item)
            return result

        return {
            "company_name": company_name,
            "stage": stage,
            "stage_sidebar": get_stage_sidebar(stage),
            "stage_identification_text": build_stage_identification_text(company_name, stage),
            "executive_summary": swap_company(example["output"].get("executive_summary", f"This assessment evaluates {company_name}'s current infrastructure position and identifies opportunities for modernization aligned with their {priority.lower()} goals.")),
            "advantages": swap_in_items(example["output"]["advantages"], ["headline", "description"]),
            "risks": swap_in_items(example["output"]["risks"], ["headline", "description"]),
            "recommendations": swap_in_items(example["output"]["recommendations"], ["title", "description"]),
            "case_study": case_study_name,
            "case_study_description": case_study_desc,
            "case_study_link": case_study_link,
            "case_study_relevance": swap_company(example["output"].get("case_study_relevance", f"This case study demonstrates how organizations in {industry} can address {challenge.lower()} through data center modernization, following a phased approach that delivers measurable results while managing the operational risks of infrastructure change.")),
        }

    async def judge_content_specificity(
        self,
        content: dict,
        industry: str,
        persona: str,
    ) -> dict:
        """
        LLM-as-judge: score whether the generated content is specific to the
        stated industry and persona, or if it reads as generic filler.

        Uses a fast model (Haiku) for speed. Returns:
            {"is_specific": bool, "score": int (1-5), "reason": str}
        """
        if not self.client:
            # No API key — assume specific (skip judge in mock mode)
            return {"is_specific": True, "score": 5, "reason": "Skipped (no API client)"}

        # Build a concise representation of the content for judging
        text_parts = []
        for adv in content.get("advantages", []):
            text_parts.append(f"Advantage: {adv.get('headline', '')} — {adv.get('description', '')}")
        for risk in content.get("risks", []):
            text_parts.append(f"Risk: {risk.get('headline', '')} — {risk.get('description', '')}")
        for rec in content.get("recommendations", []):
            text_parts.append(f"Recommendation: {rec.get('title', '')} — {rec.get('description', '')}")
        content_text = "\n".join(text_parts)

        judge_prompt = f"""You are a content quality judge. Score the following executive review content on INDUSTRY SPECIFICITY.

Industry: {industry}
Persona: {persona}

Content:
{content_text}

Score 1-5:
1 = Completely generic, could apply to any industry
2 = Mostly generic with one vague reference
3 = Some industry references but still broadly applicable
4 = Clearly tailored to the industry with specific terminology
5 = Highly specific with industry jargon, systems, and use cases

Respond with ONLY a JSON object: {{"score": <int>, "reason": "<one sentence>"}}"""

        try:
            response = await self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=150,
                messages=[{"role": "user", "content": judge_prompt}],
            )

            response_text = response.content[0].text.strip()
            # Parse JSON from response — handle markdown fencing
            import json as json_mod
            json_text = response_text
            if "```" in json_text:
                # Extract JSON from markdown code block
                json_match = re.search(r'\{[^}]+\}', json_text)
                if json_match:
                    json_text = json_match.group()
            elif not json_text.startswith("{"):
                # Try to find JSON object in response
                json_match = re.search(r'\{[^}]+\}', json_text)
                if json_match:
                    json_text = json_match.group()
            judge_result = json_mod.loads(json_text)
            score = int(judge_result.get("score", 3))
            reason = judge_result.get("reason", "")

            is_specific = score >= 3
            if not is_specific:
                logger.warning(f"LLM judge flagged content as generic (score={score}): {reason}")

            return {"is_specific": is_specific, "score": score, "reason": reason}

        except Exception as e:
            logger.error(f"LLM judge failed: {e}")
            # On judge failure, don't block — assume specific
            return {"is_specific": True, "score": 3, "reason": f"Judge error: {e}"}
