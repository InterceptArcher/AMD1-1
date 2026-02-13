"""
Executive Review Service for AMD 2-page assessment generation.
Generates personalized content based on Stage, Industry, Segment, Persona, Priority, and Challenge.
"""

import logging
import json
from typing import Any, Dict, List, Optional
from anthropic import Anthropic

from app.config import settings

logger = logging.getLogger(__name__)


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
    },
    "smurfit_westrock": {
        "name": "Smurfit Westrock Saves AWS Costs for Innovation with AMD",
        "description": "Smurfit Westrock cut cloud costs by 25% and lowered its carbon footprint by 10% by transitioning to AWS instances powered by AMD EPYC CPUs.",
    },
    "pqr": {
        "name": "PQR Offers Next-Gen IT Services with AMD Pensando DPUs",
        "description": "PQR created a next-generation data center service emphasizing stronger security and operational simplicity using AMD Pensando DPU-enabled infrastructure.",
    },
}


def select_case_study(
    stage: str,
    priority: str,
    industry: str,
    challenge: str = "",
    employee_count: Optional[int] = None,
    growth_rate: Optional[float] = None,
) -> tuple[str, str]:
    """
    Select the most relevant case study using multi-factor weighted scoring.

    Factors and weights:
    - Industry match: 40%
    - Challenge match: 25%
    - Company size match: 15%
    - Growth stage match: 10%
    - Tech maturity match: 10%

    Returns (case_study_name, case_study_description).
    """
    # Define case study profiles for scoring
    case_study_profiles = {
        "kt_cloud": {
            "industries": {"technology", "telecommunications", "media"},
            "challenges": {"skills_gap", "integration_friction"},
            "priorities": {"preparing_ai", "improving_performance"},
            "stages": {"Challenger", "Leader"},
            "size": "large",  # Large scale deployment
        },
        "smurfit_westrock": {
            "industries": {"manufacturing", "retail", "energy", "professional_services"},
            "challenges": {"legacy_systems", "resource_constraints"},
            "priorities": {"reducing_cost", "improving_performance"},
            "stages": {"Observer", "Challenger"},
            "size": "large",  # Enterprise cost optimization
        },
        "pqr": {
            "industries": {"healthcare", "financial_services", "government", "education"},
            "challenges": {"data_governance", "integration_friction"},
            "priorities": {"preparing_ai", "reducing_cost"},
            "stages": {"Leader", "Challenger"},
            "size": "mid",  # Security-focused
        },
    }

    industry_lower = industry.lower()
    challenge_lower = challenge.lower() if challenge else ""

    best_key = "smurfit_westrock"  # Default
    best_score = -1

    for key, profile in case_study_profiles.items():
        score = 0.0

        # Industry match (40%)
        if any(ind in industry_lower for ind in profile["industries"]):
            score += 0.4

        # Challenge match (25%)
        if any(ch in challenge_lower for ch in profile["challenges"]):
            score += 0.25

        # Priority match (10% bonus)
        if priority.lower().replace(" ", "_") in {p.replace(" ", "_") for p in profile["priorities"]}:
            score += 0.1

        # Stage match (10%)
        if stage in profile["stages"]:
            score += 0.1

        # Size match (15%)
        if employee_count:
            if employee_count >= 1000 and profile["size"] == "large":
                score += 0.15
            elif 200 <= employee_count < 1000 and profile["size"] == "mid":
                score += 0.15
            elif employee_count < 200 and profile["size"] in ("mid", "large"):
                score += 0.05

        if score > best_score:
            best_score = score
            best_key = key

    cs = CASE_STUDIES[best_key]
    return cs["name"], cs["description"]


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
                        "description": "Upgrade underlying compute and storage so the organization can support emerging AI-driven design and planning tools without incurring higher costs from repeated rework."
                    }
                ],
                "case_study": "Smurfit Westrock"
            }
        },
        {
            "profile": {
                "company": "Caterpillar",
                "industry": "Manufacturing",
                "segment": "Enterprise",
                "persona": "BDM",
                "stage": "Observer",
                "priority": "Reducing cost",
                "challenge": "Resource constraints"
            },
            "output": {
                "advantages": [
                    {
                        "headline": "Lower operational costs through infrastructure consolidation",
                        "description": "Caterpillar can reduce spending on redundant systems by consolidating manufacturing and supply chain platforms onto modern, efficient infrastructure."
                    },
                    {
                        "headline": "Better resource utilization across global operations",
                        "description": "Standardizing compute and storage environments helps the organization do more with existing resources while reducing waste across facilities."
                    }
                ],
                "risks": [
                    {
                        "headline": "Resource constraints limit ability to modernize effectively",
                        "description": "Without adequate budget and staff allocation, modernization efforts will stall and the company will continue paying premium costs for aging systems."
                    },
                    {
                        "headline": "Competitors gain efficiency advantages with modern platforms",
                        "description": "Manufacturing rivals investing in updated infrastructure can produce at lower cost and respond faster to market demands than the organization."
                    }
                ],
                "recommendations": [
                    {
                        "title": "Identify quick-win consolidation opportunities",
                        "description": "Focus initial modernization on redundant systems where consolidation delivers immediate cost savings without requiring major capital investment or staff expansion."
                    },
                    {
                        "title": "Prioritize workloads with highest cost-to-value ratio",
                        "description": "Target manufacturing execution and supply chain systems that consume disproportionate resources relative to their business value for early modernization."
                    },
                    {
                        "title": "Build phased roadmap aligned with budget cycles",
                        "description": "Create a multi-year modernization plan that spreads investment across fiscal periods to work within existing resource constraints while maintaining momentum."
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
                        "description": "Modernizing high-volume retail workloads improves responsiveness across POS, ecommerce, and supply chain operations at Target."
                    },
                    {
                        "headline": "Faster throughput by reducing integration friction",
                        "description": "Improving data flow between merchandising, inventory, and digital platforms enables more consistent performance for customer-facing processes."
                    }
                ],
                "risks": [
                    {
                        "headline": "Persistent slowdowns from integration bottlenecks",
                        "description": "If integration issues remain unresolved, performance bottlenecks will continue to affect revenue, customer experience, and store operations."
                    },
                    {
                        "headline": "Competitors advance with more unified retail platforms",
                        "description": "Delays in improving system performance allow faster, better-integrated retailers to gain an advantage in speed and reliability."
                    }
                ],
                "recommendations": [
                    {
                        "title": "Prioritize performance upgrades for high-volume systems",
                        "description": "Focus modernization on the transactional workloads that power POS, ecommerce, and inventory to improve speed and reduce friction during peak demand."
                    },
                    {
                        "title": "Strengthen integration across core retail platforms",
                        "description": "Improve data consistency and flow between store, digital, and supply chain systems to eliminate performance delays that impact customer experience."
                    },
                    {
                        "title": "Adopt scalable infrastructure for unified commerce",
                        "description": "Move toward flexible compute and storage environments to handle growing performance demands across omnichannel operations without added complexity."
                    }
                ],
                "case_study": "KT Cloud"
            }
        },
        {
            "profile": {
                "company": "Allbirds",
                "industry": "Retail",
                "segment": "Mid-Market",
                "persona": "ITDM",
                "stage": "Challenger",
                "priority": "Preparing for AI adoption",
                "challenge": "Skills gap"
            },
            "output": {
                "advantages": [
                    {
                        "headline": "AI-ready infrastructure accelerates competitive positioning",
                        "description": "Allbirds can leverage modern compute platforms to deploy AI-driven personalization and demand forecasting ahead of larger but slower-moving competitors."
                    },
                    {
                        "headline": "Streamlined systems reduce complexity for lean teams",
                        "description": "Consolidated, well-integrated infrastructure allows the IT team to manage AI workloads effectively without requiring significant headcount expansion."
                    }
                ],
                "risks": [
                    {
                        "headline": "Skills gap delays AI implementation timelines",
                        "description": "Without specialized AI and ML expertise, the organization may struggle to operationalize advanced analytics and lose ground to better-resourced competitors."
                    },
                    {
                        "headline": "Rapid retail AI adoption raises competitive pressure",
                        "description": "Competitors deploying AI for inventory optimization and customer experience will capture market share while the company builds internal capabilities."
                    }
                ],
                "recommendations": [
                    {
                        "title": "Deploy managed AI services to bridge skills gap",
                        "description": "Adopt cloud-based AI platforms that reduce the technical expertise required to implement machine learning for demand forecasting and personalization."
                    },
                    {
                        "title": "Modernize data infrastructure for AI readiness",
                        "description": "Upgrade data pipelines and storage to support the volume and velocity requirements of AI workloads across ecommerce and supply chain systems."
                    },
                    {
                        "title": "Build targeted AI expertise through focused hiring",
                        "description": "Prioritize recruiting for specific AI roles that address the highest-value use cases rather than attempting broad capability building across all areas."
                    }
                ],
                "case_study": "KT Cloud"
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
            self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def generate_executive_review(
        self,
        company_name: str,
        industry: str,
        segment: str,
        persona: str,
        stage: str,
        priority: str,
        challenge: str,
        enrichment_context: Optional[Dict[str, Any]] = None,
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
            enrichment_context: Optional enrichment data for richer personalization

        Returns:
            Dict with stage, advantages, risks, recommendations, case_study
        """
        if not self.client:
            logger.warning("No Anthropic client - returning mock executive review")
            return self._get_mock_response(company_name, stage, priority, industry)

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
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                system=system_prompt
            )

            # Parse the response
            content = response.content[0].text
            return self._parse_response(content, company_name, stage, priority, industry)

        except Exception as e:
            logger.error(f"Executive review generation failed: {e}")
            return self._get_mock_response(company_name, stage, priority, industry)

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
            {"retail", "ecommerce", "consumer"},
            {"healthcare", "life sciences", "pharma", "medical"},
            {"financial services", "banking", "insurance", "fintech"},
            {"manufacturing", "industrial", "automotive"},
            {"technology", "software", "telecommunications", "tech"},
            {"energy", "utilities", "oil and gas"},
        ]

        i1_lower = industry1.lower()
        i2_lower = industry2.lower()

        for group in industry_groups:
            if any(term in i1_lower for term in group) and any(term in i2_lower for term in group):
                return True
        return False

    def _build_system_prompt(self) -> str:
        """Build the system prompt with AMD content rules."""
        return """You are an expert business strategist creating personalized executive reviews for AMD's Data Center Modernization program.

Your output must follow these strict rules:

CONTENT STRUCTURE:
- Headlines: 4-8 words, imperative or benefit-driven, no colons
- Descriptions: One single sentence, 22-30 words, human and professional tone
- No jargon, buzzwords, hype, or filler phrases like "in today's landscape"
- No em dashes, no exclamation marks, no emojis

COMPANY NAME RULES:
- Use the company name exactly ONCE in each section (advantages, risks, recommendations)
- The name should appear in the FIRST item of each section
- After first mention, use pronouns: "their environment", "the company", "the organization", "their teams"
- Never repeat the company name across every line (this is an AI tell)

PERSONALIZATION REQUIREMENTS (CRITICAL):
You MUST incorporate ALL of these inputs into the content:
- INDUSTRY: Reference industry-specific workloads, systems, and use cases (e.g., "EHR systems" for healthcare, "POS systems" for retail)
- PERSONA: Tailor language for the reader (ITDM = technical infrastructure focus, BDM = business outcomes focus)
- PRIORITY: The first advantage and first recommendation MUST directly address the stated priority
- CHALLENGE: The first risk MUST directly reference the stated challenge and its consequences

STAGE-SPECIFIC FOCUS:
- Observer: low-lift, cost-saving steps, foundational efficiency, reducing technical debt
- Challenger: performance optimization, integration improvements, scalability, competitive positioning
- Leader: governance, AI readiness, optimization at scale, maintaining competitive advantage

OUTPUT FORMAT:
Return valid JSON only, no markdown, no explanation. Match the exact structure shown in the example."""

    def _build_enrichment_section(self, ctx: Dict[str, Any]) -> str:
        """Build an enrichment context section for the prompt."""
        if not ctx:
            return ""

        parts = ["\nCOMPANY INTELLIGENCE (use this to make content specific and relevant):"]

        if ctx.get("employee_count"):
            parts.append(f"- Employee count: ~{ctx['employee_count']:,}")
        if ctx.get("founded_year"):
            parts.append(f"- Founded: {ctx['founded_year']}")
        if ctx.get("employee_growth_rate"):
            rate = ctx["employee_growth_rate"]
            if rate > 0.3:
                parts.append(f"- Growth: Rapidly growing ({rate:.0%} employee growth)")
            elif rate > 0:
                parts.append(f"- Growth: Growing ({rate:.0%} employee growth)")
            else:
                parts.append(f"- Growth: Stable/contracting ({rate:.0%})")
        if ctx.get("latest_funding_stage"):
            parts.append(f"- Funding stage: {ctx['latest_funding_stage']}")
        if ctx.get("total_funding"):
            parts.append(f"- Total funding: ${ctx['total_funding']:,.0f}")
        if ctx.get("company_summary"):
            parts.append(f"- About: {ctx['company_summary'][:200]}")

        # News context
        news = ctx.get("recent_news", [])
        if news:
            parts.append("\nRECENT NEWS (reference specific headlines for relevance):")
            for article in news[:3]:
                if isinstance(article, dict):
                    parts.append(f"  - {article.get('title', 'N/A')}")

        themes = ctx.get("news_themes", [])
        if themes:
            parts.append(f"\nNEWS THEMES: {', '.join(themes[:5])}")

        # News analysis
        analysis = ctx.get("news_analysis", {})
        if analysis:
            sentiment = analysis.get("sentiment")
            if sentiment and sentiment != "neutral":
                parts.append(f"\nSENTIMENT: Company news is predominantly {sentiment}")
            ai_stage = analysis.get("ai_readiness")
            if ai_stage and ai_stage != "none":
                parts.append(f"AI READINESS: Company appears to be {ai_stage} AI")
            if analysis.get("crisis"):
                parts.append("NOTE: Company may be facing challenges - use empathetic, solution-oriented framing")

        # Title context
        if ctx.get("title"):
            parts.append(f"\nREADER'S TITLE: {ctx['title']}")

        if len(parts) <= 1:
            return ""

        return "\n".join(parts)

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
        enrichment_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build the user prompt with few-shot example and enrichment context."""
        persona_guidance = {
            "ITDM": "Focus on infrastructure, systems, technical architecture, and IT operational efficiency.",
            "BDM": "Focus on business outcomes, revenue impact, competitive positioning, and operational results."
        }

        enrichment_section = self._build_enrichment_section(enrichment_context or {})

        return f"""Generate an executive review for this profile:

Company: {company_name}
Industry: {industry}
Segment: {segment}
Persona: {persona} - {persona_guidance.get(persona, persona_guidance["BDM"])}
Stage: {stage}
Business Priority: {priority}
Challenge: {challenge}
{enrichment_section}

PERSONALIZATION CHECKLIST (you must address ALL of these):
1. First advantage headline MUST relate to "{priority}"
2. First risk headline MUST reference consequences of "{challenge}"
3. Content MUST use {industry}-specific terminology and systems
4. Language MUST be appropriate for a {persona} reader
5. Recommendations MUST be {stage}-appropriate ({"foundational, cost-focused" if stage == "Observer" else "performance, integration-focused" if stage == "Challenger" else "optimization, AI-readiness focused"})
6. If company intelligence is available above, reference SPECIFIC details (employee count, growth, news) in descriptions

Here is an example of excellent output for a {stage} stage company:

INPUT:
{json.dumps(example["profile"], indent=2)}

OUTPUT:
{json.dumps(example["output"], indent=2)}

Now generate the executive review for {company_name}. The content must be clearly personalized to their specific industry ({industry}), priority ({priority}), and challenge ({challenge}).
{"Reference specific company intelligence data points in your descriptions to demonstrate deep analysis." if enrichment_context else ""}

Return ONLY valid JSON matching the output structure above."""

    def _parse_response(self, content: str, company_name: str, stage: str, priority: str, industry: str) -> dict:
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

            # Get case study
            case_study_name, case_study_desc = select_case_study(stage, priority, industry)

            return {
                "company_name": company_name,
                "stage": stage,
                "stage_sidebar": get_stage_sidebar(stage),
                "advantages": data.get("advantages", []),
                "risks": data.get("risks", []),
                "recommendations": data.get("recommendations", []),
                "case_study": case_study_name,
                "case_study_description": case_study_desc,
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse executive review JSON: {e}")
            return self._get_mock_response(company_name, stage, priority, industry)

    def _get_mock_response(self, company_name: str, stage: str, priority: str, industry: str) -> dict:
        """Return a mock response when LLM is unavailable."""
        example = FEW_SHOT_EXAMPLES.get(stage, FEW_SHOT_EXAMPLES["Challenger"])
        case_study_name, case_study_desc = select_case_study(stage, priority, industry)

        return {
            "company_name": company_name,
            "stage": stage,
            "stage_sidebar": get_stage_sidebar(stage),
            "advantages": example["output"]["advantages"],
            "risks": example["output"]["risks"],
            "recommendations": example["output"]["recommendations"],
            "case_study": case_study_name,
            "case_study_description": case_study_desc,
        }
