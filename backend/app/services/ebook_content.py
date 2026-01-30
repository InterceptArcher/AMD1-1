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
INDUSTRY_CASE_STUDY_MAP = {
    "healthcare": "it_services",
    "financial_services": "it_services",
    "technology": "telecom",
    "gaming_media": "telecom",
    "manufacturing": "manufacturing",
    "retail": "manufacturing",
    "government": "it_services",
    "energy": "manufacturing",
    "telecommunications": "telecom",
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

    "leaders_section": """DATA CENTER LEADERS

Gartner forecasts that by 2026, more than 80% of enterprises will have used generative AI technology. Before integrating AI into their production environment, organizations need to modernize their infrastructure. Leaders are ready for AI expansion.

ADVANTAGES FOR LEADERS:
1. Operational Efficiency - They can reduce operational costs by allocating more time and budget to innovation. Leaders can also drive efficiency further through automation, streamlined asset management, and consolidation.
2. Agility and competitive advantage - Leaders can outpace competition through enhanced decision-making, faster product development, and innovative products and services.""",

    "challengers_section": """DATA CENTER CHALLENGERS

Challengers are those actively working toward data center transformation, navigating skill gaps, budget constraints, and infrastructure challenges. Even when AI makes it into production, 61% of surveyed organizations say that scaling AI across the business is their greatest challenge.

ADVANTAGES FOR CHALLENGERS:
1. Learning from others - Challengers can benefit from lessons learned by early adopters, avoiding mistakes proactively.
2. Cost advantages - Early adopters often pay a premium for emerging technologies. Challengers can avoid these extra expenses.""",

    "observers_section": """DATA CENTER OBSERVERS

Observers have yet to embark on modernization and need time to build the foundation for more transformational change. Their most significant obstacle is a limited budget for strategic initiatives.

ADVANTAGES FOR OBSERVERS:
1. Leapfrog potential - Observers can leapfrog with modern, AI-centric designs while avoiding a rapid, "cobbled-up" approach.
2. Strategic focus - Observers can prioritize their resources better by adopting AI for high-impact use cases first.""",

    "path_to_leadership": """THE PATH TO LEADERSHIP: MOVING THROUGH THE STAGES

A holistic AI integration strategy—embedding AI into both IT and business processes for maximum impact—is integral to maturing enterprise AI readiness. The first step is to develop your strategic priorities, including aligning IT with your business vision and understanding the value of AI so you can justify your infrastructure investments.

OVERCOMING BARRIERS:
- Legacy infrastructure: Existing IT infrastructure does not sufficiently support a modern AI data center
- Data security and privacy: Security and data privacy are the top two barriers to GenAI adoption
- Skill gaps: The lack of in-house AI expertise is a significant technical challenge""",

    "modernization_models": """MODERNIZATION MODELS

Two modernization strategies are the most common: "modernizing in place" and "refactoring and shifting."

MODERNIZING IN PLACE: Updating existing applications on-premises to modern architectures and integrating AI. This can often be the best approach for cost-effective transformation.

REFACTORING AND SHIFTING: Rearchitecting applications for AI with cloud-native frameworks and migrating them to the cloud. This is an advanced, future-forward cloud strategy.""",

    "why_amd": """WHY AMD: YOUR STRATEGIC PARTNER FOR DATA CENTER AND AI INNOVATION

AI will become increasingly task-specific and industry-specialized, driving more optimized data, models, and compute solutions. AMD is a trusted partner that can guide you through AI adoption and innovation.

AMD offers an open ecosystem of CPU, GPU, and adaptive computing solutions that empowers you to build workload-optimized architectures without vendor lock-in. Design a solution around your goals with a customizable portfolio of AMD products: AMD EPYC (CPUs), AMD Instinct (GPUs), and AMD Pensando (DPUs).

AMD allows you to choose the right-sized AI solutions that optimize cost efficiency without over-provisioning resources—whether cloud-based AI to preserve capital expenditures, on-prem AI to reduce operational expenses, or a hybrid approach to balance cost and security objectives.""",

    "assessment_questions": """WHERE DO YOU STAND ON THE MODERNIZATION CURVE?

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
