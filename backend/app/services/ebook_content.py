"""
AMD Ebook Content: OCR-extracted content with personalization slots.
Three personalization points:
1. Hook/Intro (Page 1) - Based on role, buying stage, company news
2. Case Study (Pages 11-13) - Selected based on industry
3. CTA (Pages 14-16) - Based on buying stage and role
"""

# Case studies mapped by industry relevance
CASE_STUDIES = {
    "telecom": {
        "title": "KT Cloud Expands AI Power with AMD Instinct Accelerators",
        "company": "KT Cloud",
        "industry": "Telecommunications / Cloud Services",
        "challenge": "KT Cloud delivers secure and reliable cloud-based solutions to businesses. The company needed to expand access to GPU compute resources for public cloud users in the form of Infrastructure-as-a-Service (IaaS).",
        "solution": "KT Cloud partnered with AMD and Moreh to create a new AI platform powered by AMD Instinct MI250 accelerators for a scalable AI cloud service with superior performance and significant cost reductions.",
        "quote": "With cost-effective AMD Instinct accelerators and a pay-as-you-go pricing model, KT Cloud expects to be able to reduce the effective price of its GPU cloud service by 70%.",
        "quote_author": "JooSung Kim, VP of KT Cloud",
        "result": "1.9 times higher throughput per dollar compared to NVIDIA cluster while improving results by up to 117%. KT Cloud announced construction of a new supercomputer cluster featuring 1,200 AMD Instinct MI250 GPUs.",
        "industries": ["telecommunications", "technology", "cloud", "gaming_media"]
    },
    "manufacturing": {
        "title": "Smurfit Westrock Saves AWS Costs for Innovation with AMD",
        "company": "Smurfit Westrock",
        "industry": "Manufacturing / Packaging",
        "challenge": "Smurfit Westrock has hundreds of AWS accounts supporting thousands of EC2 instances. The company needed to achieve cloud cost savings and optimization objectives while meeting sustainability goals.",
        "solution": "Switched to AWS cloud instances powered by AMD EPYC CPUs, starting with non-production workloads to test comfort levels.",
        "quote": "The utilization metrics did not change at all when we switched to AMD EPYC processor-powered AWS instances. The migration only took about three minutes in the AWS console.",
        "quote_author": "Thomas Burke, Senior Cloud Engineer, Smurfit Westrock",
        "result": "Reduced costs by 25% with 10% lower carbon footprint. Carbon emissions reduced from 14% increase to only 3.5% increase after AMD rollout.",
        "industries": ["manufacturing", "retail", "energy", "sustainability"]
    },
    "it_services": {
        "title": "PQR Offers Next-Gen IT Services Using AMD Solutions",
        "company": "PQR",
        "industry": "Managed IT Services",
        "challenge": "PQR is a leading IT systems integrator providing managed IT services through a Next-Gen platform that emphasizes security, scalability, and operational simplicity. The challenge was to deliver seamless service while managing operational costs.",
        "solution": "PQR embraced network modernization using HPE Aruba CX 10000 switches with AMD Pensando DPU technology, introducing a new network architecture with zero trust and rapid scalability.",
        "quote": "The idea is that everything can and will be automated, from onboarding to upscaling. That requires a state-of-the-art network with a new approach.",
        "quote_author": "Thierry Lubbers, Principal Consultant Networking, PQR",
        "result": "PQR expects savings of 50% while providing security where needed. The architecture enables seamless extension across three data centers with 800 Gb/s of distributed stateful firewall throughput.",
        "industries": ["technology", "financial_services", "healthcare", "government"]
    }
}

# Industry to case study mapping
# Maps all industries from uploaded content files to appropriate case studies
INDUSTRY_CASE_STUDY_MAP = {
    # Security/Compliance focus -> PQR (IT Services case study)
    "healthcare": "it_services",
    "financial_services": "it_services",
    "government": "it_services",
    "education": "it_services",
    "non_profit": "it_services",
    "non-profit": "it_services",

    # Cloud/GPU focus -> KT Cloud (Telecom case study)
    "technology": "telecom",
    "gaming_media": "telecom",
    "media": "telecom",
    "media_and_ent": "telecom",
    "media_and_entertainment": "telecom",
    "telecommunications": "telecom",

    # Cost optimization focus -> Smurfit Westrock (Manufacturing case study)
    "manufacturing": "manufacturing",
    "retail": "manufacturing",
    "energy": "manufacturing",
    "consumer_goods": "manufacturing",
    "consumer goods": "manufacturing",
}

# Buying stage context for personalization
BUYING_STAGE_CONTEXT = {
    "exploring": {
        "mindset": "early research phase, discovering options",
        "needs": "foundational understanding, industry trends, what's possible",
        "tone": "educational, inspiring, low-pressure",
        "cta_focus": "learn more, explore possibilities"
    },
    "evaluating": {
        "mindset": "comparing solutions, building shortlist",
        "needs": "concrete comparisons, proof points, differentiation",
        "tone": "factual, comparative, evidence-based",
        "cta_focus": "see how AMD compares, get technical specs"
    },
    "learning": {
        "mindset": "deepening expertise, understanding best practices",
        "needs": "detailed knowledge, implementation insights, expertise",
        "tone": "informative, expert, detailed",
        "cta_focus": "access expert resources, deep-dive content"
    },
    "building_case": {
        "mindset": "preparing internal proposal, needs justification",
        "needs": "ROI data, executive summaries, business cases",
        "tone": "business-focused, ROI-driven, persuasive",
        "cta_focus": "get ROI calculator, executive brief, business case template"
    }
}

# Role/persona context for personalization
PERSONA_CONTEXT = {
    "executive": {
        "focus": "strategic outcomes, competitive advantage, ROI",
        "language": "business impact, market position, organizational transformation",
        "concerns": "risk, investment justification, board-level metrics"
    },
    "it_infrastructure": {
        "focus": "technical implementation, performance, reliability",
        "language": "architecture, integration, operations, scalability",
        "concerns": "compatibility, migration complexity, support"
    },
    "security": {
        "focus": "data protection, compliance, threat mitigation",
        "language": "zero trust, encryption, compliance frameworks",
        "concerns": "vulnerabilities, audit requirements, security posture"
    },
    "data_ai": {
        "focus": "model performance, compute efficiency, data pipelines",
        "language": "GPU acceleration, training throughput, inference latency",
        "concerns": "hardware optimization, cost per training run, scalability"
    },
    "sales_gtm": {
        "focus": "revenue impact, customer experience, market speed",
        "language": "competitive wins, customer success, time-to-value",
        "concerns": "differentiation, customer references, proof points"
    },
    "hr_people": {
        "focus": "workforce enablement, talent attraction, productivity",
        "language": "employee experience, skills development, culture",
        "concerns": "change management, adoption, training"
    }
}

# Static ebook content sections (OCR extracted)
EBOOK_SECTIONS = {
    "cover_title": "FROM OBSERVERS TO ENTERPRISE AI READINESS",

    "intro_section": """AI is a business imperative for modern enterprises. From product development and manufacturing to sales, marketing, and customer support, AI enhances decision-making, accelerates growth, and reduces operational costs. But the surge in AI workloads requires greater computing power and data storage. For data center operators, this growing demand creates tremendous pressure for more space and capacity.

Successful AI-fueled transformation relies on a modern, AI-ready infrastructure. Yet the demand often outpaces existing IT infrastructure capabilities. Traditional architectures and legacy systems often struggle to support existing workloads—and AI puts further strain on this infrastructure.

Many organizational leaders understand that data center modernization is a priority for reaching enterprise AI readiness. Two-thirds of surveyed organizations believe their IT environments require upgrades to meet future demand. However, upgrading infrastructure designed for lighter workloads requires significant financial investments. That's why organizations need a clear framework to assess AI readiness, prioritize investments, and move forward with confidence.""",

    "three_stages_intro": """A recent IDC survey commissioned by AMD found that organizations' approach, including their workload placement and their technology and vendor selection, varies based on their modernization status.

- 26% of organizations—data center Leaders—have fully modernized in the past 12 months
- 32% of organizations—data center Challengers—have started but have not completed their modernization
- 42% of organizations—data center Observers—plan to modernize within the next 2 years""",

    "leaders_section": """Gartner forecasts that by 2026, more than 80% of enterprises will have used generative AI technology. Before integrating AI into their production environment, organizations need to modernize their infrastructure. Leaders are ready for AI expansion.

Advantages for Leaders:
1. Operational Efficiency - They can reduce operational costs by allocating more time and budget to innovation. Leaders can also drive efficiency further through automation, streamlined asset management, and consolidation.
2. Agility and competitive advantage - Leaders can outpace competition through enhanced decision-making, faster product development, and innovative products and services.""",

    "challengers_section": """Challengers are those actively working toward data center transformation, navigating skill gaps, budget constraints, and infrastructure challenges. Even when AI makes it into production, 61% of surveyed organizations say that scaling AI across the business is their greatest challenge.

Advantages for Challengers:
1. Learning from others - Challengers can benefit from lessons learned by early adopters, avoiding mistakes proactively.
2. Cost advantages - Early adopters often pay a premium for emerging technologies. Challengers can avoid these extra expenses.""",

    "observers_section": """Observers have yet to embark on modernization and need time to build the foundation for more transformational change. Their most significant obstacle is a limited budget for strategic initiatives.

Advantages for Observers:
1. Leapfrog potential - Observers can leapfrog with modern, AI-centric designs while avoiding a rapid, "cobbled-up" approach.
2. Strategic focus - Observers can prioritize their resources better by adopting AI for high-impact use cases first.""",

    "path_to_leadership": """A holistic AI integration strategy—embedding AI into both IT and business processes for maximum impact—is integral to maturing enterprise AI readiness. The first step is to develop your strategic priorities, including aligning IT with your business vision and understanding the value of AI so you can justify your infrastructure investments.""",

    "modernization_models": """Two modernization strategies are the most common: "modernizing in place" and "refactoring and shifting."

Modernizing in place means updating existing applications on-premises to modern architectures and integrating AI. This can often be the best approach for cost-effective transformation.

Refactoring and shifting means rearchitecting applications for AI with cloud-native frameworks and migrating them to the cloud. This is an advanced, future-forward cloud strategy.""",

    "why_amd": """AI will become increasingly task-specific and industry-specialized, driving more optimized data, models, and compute solutions. AMD is a trusted partner that can guide you through AI adoption and innovation.

AMD offers an open ecosystem of CPU, GPU, and adaptive computing solutions that empowers you to build workload-optimized architectures without vendor lock-in. Design a solution around your goals with a customizable portfolio of AMD products: AMD EPYC™ processors, AMD Instinct™ accelerators, and AMD Pensando™ DPUs.

AMD allows you to choose the right-sized AI solutions that optimize cost efficiency without over-provisioning resources—whether cloud-based AI to preserve capital expenditures, on-prem AI to reduce operational expenses, or a hybrid approach to balance cost and security objectives.""",

    "assessment_questions": """Use these questions to assess where your organization stands on the modernization curve:

1. Do your long-term IT investments align with your enterprise AI strategy?

2. When was the last time your core infrastructure was meaningfully modernized?

3. Can your current IT environment support AI workloads without requiring major upgrades?

4. Are you measuring the ROI of your modernization efforts?

5. Do you have the skills to drive modernization and AI adoption at scale?

6. Is your AI strategy supported by a dedicated or protected budget?

7. What's your approach to application modernization?

8. Is your infrastructure resilient enough to handle the dynamic scaling needs of AI workloads?"""
}


def get_case_study_for_industry(industry: str) -> dict:
    """Get the most relevant case study for an industry."""
    industry_lower = industry.lower().replace(" ", "_") if industry else "technology"
    case_study_key = INDUSTRY_CASE_STUDY_MAP.get(industry_lower, "telecom")
    return CASE_STUDIES[case_study_key]


def get_buying_stage_context(stage: str) -> dict:
    """Get context for a buying stage."""
    return BUYING_STAGE_CONTEXT.get(stage, BUYING_STAGE_CONTEXT["exploring"])


def get_persona_context(persona: str) -> dict:
    """Get context for a persona/role."""
    return PERSONA_CONTEXT.get(persona, PERSONA_CONTEXT["executive"])


# --- Content File Loading ---
# Load detailed content from the uploaded markdown files

from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

CONTENT_DIR = Path(__file__).parent.parent.parent / "assets" / "content"

# Map normalized industry names to file names
INDUSTRY_FILE_MAP = {
    "healthcare": "KP_Industry_Healthcare.md",
    "financial_services": "KP_Industry_Financial Services.md",
    "manufacturing": "KP_Industry_Manufacturing.md",
    "energy": "KP_Industry_Energy.md",
    "retail": "KP_Industry_Retail.md",
    "education": "KP_Industry_Education.md",
    "consumer_goods": "KP_Industry_Consumer Goods.md",
    "media": "KP_Industry_Media and Ent.md",
    "media_and_ent": "KP_Industry_Media and Ent.md",
    "non_profit": "KP_Industry_Non-Profit.md",
}

JOB_FUNCTION_FILE_MAP = {
    "bdm": "KP_Job Function_BDM.md",
    "itdm": "KP_Job Function_ITDM.md",
    "executive": "KP_Job Function_BDM.md",  # BDM is closest to executive
    "it_infrastructure": "KP_Job Function_ITDM.md",
    "security": "KP_Job Function_ITDM.md",
    "data_ai": "KP_Job Function_ITDM.md",
}

SEGMENT_FILE_MAP = {
    "enterprise": "KP_Segment_Enterprise.md",
    "government": "KP_Segment_Government.md",
    "mid_market": "KP_Segment_Mid-Market.md",
    "mid-market": "KP_Segment_Mid-Market.md",
    "smb": "KP_Segment_SMB.md",
    "small_business": "KP_Segment_SMB.md",
}


def load_industry_content(industry: str) -> Optional[str]:
    """
    Load detailed industry content from markdown files.

    Args:
        industry: Industry name (e.g., "healthcare", "financial_services")

    Returns:
        Full markdown content or None if not found
    """
    industry_normalized = industry.lower().replace(" ", "_").replace("-", "_")
    filename = INDUSTRY_FILE_MAP.get(industry_normalized)

    if not filename:
        logger.warning(f"No content file mapping for industry: {industry}")
        return None

    filepath = CONTENT_DIR / filename
    if not filepath.exists():
        logger.warning(f"Industry content file not found: {filepath}")
        return None

    try:
        return filepath.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Error reading industry content: {e}")
        return None


def load_job_function_content(job_function: str) -> Optional[str]:
    """
    Load job function content from markdown files.

    Args:
        job_function: Job function (e.g., "bdm", "itdm", "executive")

    Returns:
        Full markdown content or None if not found
    """
    function_normalized = job_function.lower().replace(" ", "_")
    filename = JOB_FUNCTION_FILE_MAP.get(function_normalized)

    if not filename:
        logger.warning(f"No content file mapping for job function: {job_function}")
        return None

    filepath = CONTENT_DIR / filename
    if not filepath.exists():
        logger.warning(f"Job function content file not found: {filepath}")
        return None

    try:
        return filepath.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Error reading job function content: {e}")
        return None


def load_segment_content(segment: str) -> Optional[str]:
    """
    Load segment content from markdown files.

    Args:
        segment: Company segment (e.g., "enterprise", "mid_market", "smb")

    Returns:
        Full markdown content or None if not found
    """
    segment_normalized = segment.lower().replace(" ", "_").replace("-", "_")
    filename = SEGMENT_FILE_MAP.get(segment_normalized)

    if not filename:
        logger.warning(f"No content file mapping for segment: {segment}")
        return None

    filepath = CONTENT_DIR / filename
    if not filepath.exists():
        logger.warning(f"Segment content file not found: {filepath}")
        return None

    try:
        return filepath.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Error reading segment content: {e}")
        return None


def extract_key_points(content: str, section: str = None, max_points: int = 5) -> list[str]:
    """
    Extract key bullet points from markdown content.

    Args:
        content: Full markdown content
        section: Optional section header to extract from
        max_points: Maximum number of points to return

    Returns:
        List of key points as strings
    """
    if not content:
        return []

    lines = content.split("\n")
    points = []

    in_section = section is None  # If no section specified, start collecting immediately

    for line in lines:
        # Check if we've reached the target section
        if section and line.startswith("## ") and section.lower() in line.lower():
            in_section = True
            continue

        # Check if we've left the section
        if in_section and section and line.startswith("## "):
            break

        # Collect bullet points
        if in_section and (line.strip().startswith("- ") or line.strip().startswith("* ")):
            point = line.strip().lstrip("-*").strip()
            if point and len(point) > 10:  # Skip very short points
                points.append(point)

            if len(points) >= max_points:
                break

    return points


def get_industry_key_insights(industry: str) -> dict:
    """
    Get key insights for an industry to use in personalization.

    Returns a structured dict with:
    - trends: Key industry trends
    - priorities: Technology priorities
    - challenges: Common challenges
    - messaging_tips: How to frame messaging

    Args:
        industry: Industry name

    Returns:
        Dict with categorized insights
    """
    content = load_industry_content(industry)
    if not content:
        return {
            "trends": [],
            "priorities": [],
            "challenges": [],
            "messaging_tips": []
        }

    return {
        "trends": extract_key_points(content, "Major trends", 3),
        "priorities": extract_key_points(content, "Technology Investment", 3),
        "challenges": extract_key_points(content, "challenges", 3),
        "messaging_tips": extract_key_points(content, "messaging", 3),
    }
