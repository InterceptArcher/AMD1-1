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
        "max_chars": 65,
        "min_words": 4,
        "max_words": 10,
        "description": "Advantage/Risk headline",
    },
    "description": {
        "min_chars": 80,
        "max_chars": 220,
        "min_words": 13,
        "max_words": 35,
        "description": "Advantage/Risk description (one sentence)",
    },
    "rec_title": {
        "min_chars": 20,
        "max_chars": 65,
        "min_words": 4,
        "max_words": 10,
        "description": "Recommendation title",
    },
    "rec_description": {
        "min_chars": 80,
        "max_chars": 220,
        "min_words": 13,
        "max_words": 35,
        "description": "Recommendation description (one sentence)",
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
    "description": "Generate a personalized executive review with advantages, risks, and recommendations. Each field has strict character limits.",
    "input_schema": {
        "type": "object",
        "properties": {
            "advantages": {
                "type": "array",
                "description": "Exactly 2 advantages. First must relate to stated business priority.",
                "items": {
                    "type": "object",
                    "properties": {
                        "headline": {
                            "type": "string",
                            "description": "4-10 words, benefit-driven, no colons. 20-65 characters.",
                            "minLength": 20,
                            "maxLength": 65,
                        },
                        "description": {
                            "type": "string",
                            "description": "Single sentence, 13-35 words, professional tone. 80-220 characters.",
                            "minLength": 80,
                            "maxLength": 220,
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
                            "description": "4-10 words, consequence-focused, no colons. 20-65 characters.",
                            "minLength": 20,
                            "maxLength": 65,
                        },
                        "description": {
                            "type": "string",
                            "description": "Single sentence, 13-35 words, professional tone. 80-220 characters.",
                            "minLength": 80,
                            "maxLength": 220,
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
                            "description": "4-10 words, imperative form, no colons. 20-65 characters.",
                            "minLength": 20,
                            "maxLength": 65,
                        },
                        "description": {
                            "type": "string",
                            "description": "Single sentence, 13-35 words, professional tone. 80-220 characters.",
                            "minLength": 80,
                            "maxLength": 220,
                        },
                    },
                    "required": ["title", "description"],
                },
                "minItems": 3,
                "maxItems": 3,
            },
            "case_study_relevance": {
                "type": "string",
                "description": "One sentence (15-30 words) explaining why the selected case study is relevant to this company's specific situation, industry, and challenge.",
                "minLength": 60,
                "maxLength": 200,
            },
        },
        "required": ["advantages", "risks", "recommendations", "case_study_relevance"],
    },
}


# =============================================================================
# CONTENT VALIDATOR
# =============================================================================

def validate_executive_review_content(content: dict) -> dict:
    """
    Validate executive review content against field specs, banned phrases,
    and AMD content rules.

    Returns:
        {
            "passed": bool,
            "failures": [{"field": str, "reason": str, "value": str}, ...]
        }
    """
    failures = []

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

    # Validate company name repetition (max once per section)
    company_name = content.get("company_name", "")
    if company_name and len(company_name) > 2:
        for section_key in ["advantages", "risks", "recommendations"]:
            items = content.get(section_key, [])
            name_count = 0
            for item in items:
                for field_val in item.values():
                    if isinstance(field_val, str) and company_name.lower() in field_val.lower():
                        name_count += 1
            if name_count > 2:
                failures.append({
                    "field": section_key,
                    "reason": f"Company name '{company_name}' appears {name_count} times in {section_key} (max 2 — once in headline, once in description of first item)",
                    "value": f"{name_count} occurrences",
                })

    return {
        "passed": len(failures) == 0,
        "failures": failures,
    }


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

    if output.get("advantages"):
        output["advantages"][0]["headline"] = _swap_name(output["advantages"][0]["headline"])
        output["advantages"][0]["description"] = _swap_name(output["advantages"][0]["description"])

    if output.get("risks"):
        output["risks"][0]["headline"] = _swap_name(output["risks"][0]["headline"])
        output["risks"][0]["description"] = _swap_name(output["risks"][0]["description"])

    if output.get("recommendations"):
        output["recommendations"][0]["description"] = _swap_name(output["recommendations"][0]["description"])

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
                "advantages": [
                    {
                        "headline": "Cost savings from reducing legacy system overhead",
                        "description": "Retiring aging on-prem systems lowers operating costs and reduces the maintenance burden across AECOM's globally distributed project teams."
                    },
                    {
                        "headline": "Efficiency gains through basic standardization",
                        "description": "Unifying fragmented BIM, CAD, and project data environments creates quick workflow efficiencies without requiring major architectural change."
                    }
                ],
                "risks": [
                    {
                        "headline": "High total cost of ownership from legacy infrastructure",
                        "description": "Running large, outdated systems at enterprise scale drives rising support, licensing, and hardware costs that conflict with cost-reduction goals."
                    },
                    {
                        "headline": "Integration gaps that add avoidable project costs",
                        "description": "Siloed tools and limited interoperability across field, design, and ERP systems increase rework risk and make secure integration harder for IT."
                    }
                ],
                "recommendations": [
                    {
                        "title": "Modernize high-impact legacy workloads first",
                        "description": "Target the most cost-intensive on-prem systems, such as storage and compute tied to BIM and CAD, to reduce maintenance overhead and improve stability for distributed project teams."
                    },
                    {
                        "title": "Standardize core infrastructure to reduce fragmentation",
                        "description": "Adopt consistent tooling and platform standards across regions to lower integration effort for ITDM teams and eliminate duplicated spend across project sites."
                    },
                    {
                        "title": "Build a scalable foundation for future AI workloads",
                        "description": "Upgrade underlying compute and storage so AECOM can support emerging AI-driven design and planning tools without incurring higher costs from repeated rework."
                    }
                ],
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
                "advantages": [
                    {
                        "headline": "Lower operating costs by modernizing high-expense systems",
                        "description": "Replacing or consolidating aging infrastructure reduces ongoing maintenance spend and helps Allbirds stretch limited resources further across its growing digital and retail operations."
                    },
                    {
                        "headline": "Quick efficiency gains from simplifying fragmented environments",
                        "description": "Streamlining ecommerce, inventory, and operations systems cuts redundant work and reduces the burden on Allbirds' lean teams."
                    }
                ],
                "risks": [
                    {
                        "headline": "Rising costs from continuing to maintain outdated systems",
                        "description": "Legacy platforms require increasing support and licensing effort, making it harder for Allbirds to manage expenses with limited staffing capacity."
                    },
                    {
                        "headline": "Resource constraints slow progress on foundational modernization",
                        "description": "Without added support or simplification, Allbirds may struggle to execute essential upgrades that reduce cost and improve efficiency."
                    }
                ],
                "recommendations": [
                    {
                        "title": "Modernize the systems that drive the highest operational costs",
                        "description": "Update or consolidate the platforms behind ecommerce, inventory, and fulfillment to reduce maintenance spend and improve day-to-day efficiency."
                    },
                    {
                        "title": "Simplify the tech stack to reduce workload on lean teams",
                        "description": "Standardize tools and remove redundant systems so Allbirds' resources can focus on the core platforms that support growth."
                    },
                    {
                        "title": "Adopt solutions that deliver quick, low-effort efficiency gains",
                        "description": "Choose modernization steps with clear savings and minimal lift so Allbirds can reduce cost without straining its small IT and operations teams."
                    }
                ],
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
                "advantages": [
                    {
                        "headline": "Performance gains from upgrading core systems",
                        "description": "Modernizing high-volume retail workloads improves responsiveness across POS, ecommerce, and supply chain operations."
                    },
                    {
                        "headline": "Faster throughput by reducing integration friction",
                        "description": "Improving data flow between merchandising, inventory, and digital platforms enables more consistent performance for customer-facing processes."
                    }
                ],
                "risks": [
                    {
                        "headline": "Persistent slowdowns from legacy system connections",
                        "description": "If integration issues remain unresolved, performance bottlenecks will continue to affect revenue, customer experience, and store operations."
                    },
                    {
                        "headline": "Competitors advance with more unified retail platforms",
                        "description": "Delays in improving system performance allow faster, better-integrated retailers to gain an advantage in speed and reliability."
                    }
                ],
                "recommendations": [
                    {
                        "title": "Prioritize performance upgrades for high-volume retail systems",
                        "description": "Focus modernization on the transactional workloads that power POS, ecommerce, and inventory to improve speed and reduce friction during peak demand."
                    },
                    {
                        "title": "Strengthen integration across core retail platforms",
                        "description": "Improve data consistency and flow between store, digital, and supply chain systems to eliminate performance delays that impact customer experience and revenue."
                    },
                    {
                        "title": "Adopt scalable infrastructure to support unified commerce",
                        "description": "Move toward more flexible compute and storage environments so Target can handle growing performance demands across omnichannel operations without added complexity."
                    }
                ],
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
                "advantages": [
                    {
                        "headline": "Performance gains from modernizing critical industrial workloads",
                        "description": "Upgrading compute environments that support equipment monitoring and production systems improves reliability and throughput across global manufacturing operations."
                    },
                    {
                        "headline": "Fewer delays by reducing friction between OT and IT systems",
                        "description": "Improving integration across factory equipment, ERP, and analytics platforms enables more consistent performance and faster issue resolution for production teams."
                    }
                ],
                "risks": [
                    {
                        "headline": "Operational slowdowns if legacy OT connections remain in place",
                        "description": "If outdated interfaces are not modernized, performance issues will continue to impact production output, equipment uptime, and downstream supply chain operations."
                    },
                    {
                        "headline": "Skills gaps can limit the impact of modernization efforts",
                        "description": "Without enough talent to support new tools and integrated OT-IT workflows, performance improvements may stall or fail to scale across manufacturing sites."
                    }
                ],
                "recommendations": [
                    {
                        "title": "Prioritize modernization of core production systems",
                        "description": "Focus upgrades on equipment monitoring, analytics, and plant-floor workloads that have the greatest impact on performance and uptime."
                    },
                    {
                        "title": "Strengthen integration across OT and IT environments",
                        "description": "Standardize platforms and improve data flow between factory equipment, ERP, and analytics tools to reduce delays and improve operational reliability."
                    },
                    {
                        "title": "Invest in capabilities that close critical skills gaps",
                        "description": "Expand training and bring in specialized expertise so modernization work can scale across manufacturing sites and support more reliable, integrated operations."
                    }
                ],
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
                "advantages": [
                    {
                        "headline": "Stronger readiness for advanced AI workloads",
                        "description": "HCA's modern, scalable infrastructure gives IT teams the foundation to support clinical AI models that require high performance and reliable data access at enterprise scale."
                    },
                    {
                        "headline": "Tighter governance accelerates compliant AI adoption",
                        "description": "With established data controls across EHR, imaging, and operational systems, the organization can evaluate and deploy AI use cases confidently within strict regulatory boundaries."
                    }
                ],
                "risks": [
                    {
                        "headline": "Data governance gaps threaten AI accuracy and safety",
                        "description": "If interoperability or data quality issues persist across clinical and administrative systems, AI models may underperform or increase compliance risk for IT."
                    },
                    {
                        "headline": "Regulatory complexity can slow enterprise AI deployment",
                        "description": "Highly regulated environments like healthcare require rigorous validation and documentation, which may extend timelines to operationalize AI at scale."
                    }
                ],
                "recommendations": [
                    {
                        "title": "Strengthen data foundations for clinical AI",
                        "description": "Improve data quality and interoperability across EHR, imaging, and operational systems to ensure AI models are accurate, reliable, and compliant."
                    },
                    {
                        "title": "Expand governance frameworks for safe AI use",
                        "description": "Enhance validation, documentation, and audit controls so IT teams can deploy AI tools that meet strict healthcare regulatory requirements."
                    },
                    {
                        "title": "Scale infrastructure for high-performance AI workloads",
                        "description": "Increase compute and storage capacity to run demanding AI models consistently across clinical and administrative environments."
                    }
                ],
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
                "advantages": [
                    {
                        "headline": "Performance optimization drives competitive trading advantages",
                        "description": "JPMorgan Chase can leverage optimized infrastructure to execute transactions faster and more reliably than competitors in latency-sensitive markets."
                    },
                    {
                        "headline": "Strong governance enables compliant innovation at scale",
                        "description": "Mature data controls and audit capabilities allow the organization to deploy new trading and analytics systems while maintaining regulatory compliance."
                    }
                ],
                "risks": [
                    {
                        "headline": "Compliance overhead may constrain performance gains",
                        "description": "If governance requirements add latency or complexity to critical trading systems, the company may not fully realize performance optimization benefits."
                    },
                    {
                        "headline": "Fintech competitors move faster with fewer constraints",
                        "description": "Newer financial technology firms with lighter regulatory burdens can iterate and deploy performance improvements more rapidly than established institutions."
                    }
                ],
                "recommendations": [
                    {
                        "title": "Optimize high-frequency trading infrastructure",
                        "description": "Focus performance improvements on the systems that directly impact revenue generation and competitive positioning in time-sensitive financial markets."
                    },
                    {
                        "title": "Streamline compliance without sacrificing controls",
                        "description": "Implement automated governance and audit capabilities that maintain regulatory compliance while reducing the performance overhead of manual processes."
                    },
                    {
                        "title": "Deploy AI for real-time risk and fraud detection",
                        "description": "Leverage optimized compute infrastructure to run advanced AI models that improve risk management and fraud prevention without adding transaction latency."
                    }
                ],
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
            example=example
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
                "advantages": result_data.get("advantages", []),
                "risks": result_data.get("risks", []),
                "recommendations": result_data.get("recommendations", []),
                "case_study": case_study_name,
                "case_study_description": case_study_desc,
                "case_study_link": case_study_link,
                "case_study_relevance": result_data.get("case_study_relevance", ""),
            }

            # Run content validation
            self._validate_personalization(result, industry, priority, challenge)
            validation = validate_executive_review_content(result)
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
Headlines must be 4-10 words (20-65 characters). Descriptions must be 13-35 words (80-220 characters).
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
- Headlines: 4-10 words, imperative or benefit-driven, no colons
- Descriptions: One single sentence, 13-35 words, human and professional tone
- No jargon, buzzwords, hype, or filler phrases like "in today's landscape"
- No em dashes, no exclamation marks, no emojis

COMPANY NAME RULES:
- Use the company name exactly ONCE in each section (advantages, risks, recommendations)
- The name should appear in the FIRST item of each section
- After first mention, use pronouns: "their environment", "the company", "the organization", "their teams"
- Never repeat the company name across every line (this is an AI tell)

PERSONALIZATION REQUIREMENTS (CRITICAL):
You MUST incorporate ALL of these inputs into the content:
- INDUSTRY: Reference industry-specific workloads, systems, and use cases using the terminology table below
- PERSONA: Tailor language for the reader (ITDM = technical infrastructure focus, BDM = business outcomes focus)
- PRIORITY: The first advantage and first recommendation MUST directly address the stated priority
- CHALLENGE: The first risk MUST directly reference the stated challenge and its consequences

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
        example: dict
    ) -> str:
        """Build the user prompt with few-shot example and AMD IP context."""
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

        return f"""Generate an executive review for this profile:

Company: {company_name}
Industry: {industry}
Segment: {segment}
Persona: {persona} - {persona_guidance.get(persona, persona_guidance["BDM"])}
Stage: {stage}
Business Priority: {priority}
Challenge: {challenge}
{amd_context_block}
PERSONALIZATION CHECKLIST (you must address ALL of these):
1. First advantage headline MUST relate to "{priority}"
2. First risk headline MUST reference consequences of "{challenge}"
3. Content MUST use {industry}-specific terminology and systems
4. Language MUST be appropriate for a {persona} reader
5. Recommendations MUST be {stage}-appropriate ({"foundational, cost-focused" if stage == "Observer" else "performance, integration-focused" if stage == "Challenger" else "optimization, AI-readiness focused"})

Here is an example of excellent output for a {stage} stage company:

INPUT:
{json.dumps(example["profile"], indent=2)}

OUTPUT:
{json.dumps(example["output"], indent=2)}

Now generate the executive review for {company_name}. The content must be clearly personalized to their specific industry ({industry}), priority ({priority}), and challenge ({challenge}).

Use the generate_executive_review tool to return your response."""

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
                "advantages": data.get("advantages", []),
                "risks": data.get("risks", []),
                "recommendations": data.get("recommendations", []),
                "case_study": case_study_name,
                "case_study_description": case_study_desc,
                "case_study_link": case_study_link,
                "case_study_relevance": data.get("case_study_relevance", ""),
            }

            self._validate_personalization(result, industry, priority, challenge)
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse executive review JSON: {e}")
            return self._get_mock_response(company_name, stage, priority, industry, challenge)

    def _get_mock_response(self, company_name: str, stage: str, priority: str, industry: str, challenge: str = "") -> dict:
        """Return a mock response when LLM is unavailable."""
        example = FEW_SHOT_EXAMPLES.get(stage, FEW_SHOT_EXAMPLES["Challenger"])
        case_study_name, case_study_desc, case_study_link = select_case_study(stage, priority, industry, challenge)

        return {
            "company_name": company_name,
            "stage": stage,
            "stage_sidebar": get_stage_sidebar(stage),
            "stage_identification_text": build_stage_identification_text(company_name, stage),
            "advantages": example["output"]["advantages"],
            "risks": example["output"]["risks"],
            "recommendations": example["output"]["recommendations"],
            "case_study": case_study_name,
            "case_study_description": case_study_desc,
            "case_study_link": case_study_link,
            "case_study_relevance": f"This case study demonstrates how organizations in {industry} can address {challenge.lower()} through data center modernization.",
        }

    def _validate_personalization(self, result: dict, industry: str, priority: str, challenge: str) -> None:
        """Non-blocking validation that logs warnings for weak personalization."""
        advantages = result.get("advantages", [])
        risks = result.get("risks", [])
        recommendations = result.get("recommendations", [])

        if len(advantages) < 2:
            logger.warning("Executive review has fewer than 2 advantages")
        if len(risks) < 2:
            logger.warning("Executive review has fewer than 2 risks")
        if len(recommendations) < 3:
            logger.warning("Executive review has fewer than 3 recommendations")
