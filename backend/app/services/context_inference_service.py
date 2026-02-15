"""
Context Inference Service: Infers user context from enrichment data.
Replaces form fields that users previously had to fill in manually.

Infers:
- IT environment (traditional/modernizing/modern)
- Business priority (reducing_cost/improving_performance/preparing_ai)
- Primary challenge (legacy_systems/integration_friction/resource_constraints/skills_gap/data_governance)
- Urgency level (low/medium/high)
- Journey stage (awareness/consideration/decision/implementation)
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Keywords for signal detection
AI_CLOUD_KEYWORDS = {"ai", "artificial intelligence", "machine learning", "cloud", "saas", "cloud computing", "deep learning", "neural", "gpu"}
MODERN_TECH_KEYWORDS = {"kubernetes", "docker", "microservices", "devops", "serverless", "cloud-native"}
TRANSFORMATION_KEYWORDS = {"digital transformation", "modernization", "migration", "cloud migration", "transformation"}
COST_KEYWORDS = {"cost reduction", "cost savings", "efficiency", "cost optimization", "budget", "expense"}
AI_ADOPTION_KEYWORDS = {"ai adoption", "machine learning", "artificial intelligence", "generative ai", "llm", "ai strategy"}
GROWTH_KEYWORDS = {"expansion", "growth", "scaling", "acquisition", "new market"}
TALENT_KEYWORDS = {"talent", "hiring", "skills gap", "workforce", "recruitment", "skills shortage"}
INTEGRATION_KEYWORDS = {"integration", "interoperability", "compatibility", "migration", "legacy"}
INVESTMENT_KEYWORDS = {"investment", "funding", "capital", "acquisition", "strategic investment", "secures", "raises", "raised", "series"}
PILOT_KEYWORDS = {"pilot", "proof of concept", "poc", "testing", "trial", "prototype"}
DATA_AI_ROLE_KEYWORDS = {"data", "ai", "ml", "analytics", "machine learning", "artificial intelligence"}
REGULATED_INDUSTRIES = {"healthcare", "financial_services", "government", "banking", "insurance", "pharma"}

# Tech stack signal categories for tag analysis
CLOUD_TAGS = {"cloud", "cloud computing", "aws", "azure", "gcp", "google cloud", "saas", "iaas", "paas"}
AI_ML_TAGS = {"artificial intelligence", "machine learning", "deep learning", "data science", "neural network", "nlp", "computer vision", "generative ai"}
TRADITIONAL_TAGS = {"mainframe", "on-premise", "on-premises", "legacy", "cobol", "erp"}
SECURITY_TAGS = {"cybersecurity", "security", "information security", "compliance", "zero trust", "identity management"}
DATA_TAGS = {"big data", "analytics", "data warehouse", "data lake", "business intelligence", "data engineering"}


def extract_tech_signals_from_tags(tags: List[str]) -> Dict[str, Any]:
    """
    Categorize company tags into technology signal groups.

    Args:
        tags: List of company tags from PDL Company API

    Returns:
        Dict with categorized tech signals and maturity level
    """
    if not tags:
        return {
            "cloud": [],
            "ai_ml": [],
            "traditional": [],
            "security": [],
            "data": [],
            "maturity": "unknown",
        }

    tags_lower = [t.lower().strip() for t in tags if t]

    def _match_tag(tag: str, category: set) -> bool:
        """Match a tag against a category using exact or word-boundary matching."""
        if tag in category:
            return True
        # Only match multi-word keywords as substrings (avoid "erp" matching "enterprise")
        return any(kw in tag for kw in category if len(kw) > 4)

    cloud = [t for t in tags_lower if _match_tag(t, CLOUD_TAGS)]
    ai_ml = [t for t in tags_lower if _match_tag(t, AI_ML_TAGS)]
    traditional = [t for t in tags_lower if _match_tag(t, TRADITIONAL_TAGS)]
    security = [t for t in tags_lower if _match_tag(t, SECURITY_TAGS)]
    data = [t for t in tags_lower if _match_tag(t, DATA_TAGS)]

    # Determine overall tech maturity
    if ai_ml and cloud:
        maturity = "advanced"
    elif cloud or ai_ml:
        maturity = "modern"
    elif traditional:
        maturity = "traditional"
    else:
        maturity = "mixed"

    return {
        "cloud": list(set(cloud)),
        "ai_ml": list(set(ai_ml)),
        "traditional": list(set(traditional)),
        "security": list(set(security)),
        "data": list(set(data)),
        "maturity": maturity,
    }


def _search_text(text: str, keywords: set) -> bool:
    """Check if any keyword appears in text (case-insensitive)."""
    if not text:
        return False
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


def _search_articles(articles: List[Dict], keywords: set) -> bool:
    """Check if any keyword appears in article titles or content."""
    if not articles:
        return False
    for article in articles:
        if not isinstance(article, dict):
            continue
        title = (article.get("title") or "").lower()
        content = (article.get("content") or "").lower()
        if any(kw in title or kw in content for kw in keywords):
            return True
    return False


def _search_themes(themes: List[str], keywords: set) -> bool:
    """Check if any theme matches keywords."""
    if not themes:
        return False
    for theme in themes:
        if not theme:
            continue
        if any(kw in theme.lower() for kw in keywords):
            return True
    return False


def _search_tags(tags: List[str], keywords: set) -> bool:
    """Check if any company tag matches keywords."""
    return _search_themes(tags, keywords)


def infer_it_environment(profile: Dict[str, Any]) -> str:
    """
    Infer IT environment maturity from enrichment data.

    Signals for MODERN:
    - Structured tech signals show advanced maturity (cloud + AI tags)
    - Company tags contain AI/cloud/SaaS
    - Founded after 2015 in tech industry
    - News themes show cloud-native or AI deployment

    Signals for TRADITIONAL:
    - Structured tech signals show traditional maturity (mainframe/legacy tags)
    - Founded before 2000 in non-tech industry
    - No cloud/AI tags

    Default: modernizing
    """
    tags = profile.get("company_tags", []) or []
    themes = profile.get("news_themes", []) or []
    industry = (profile.get("industry") or "").lower()
    founded = profile.get("founded_year")

    # Use structured tech signals if tags available
    if tags:
        tech_signals = extract_tech_signals_from_tags(tags)
        if tech_signals["maturity"] == "advanced":
            return "modern"
        if tech_signals["maturity"] == "traditional":
            return "traditional"

    # Modern signals (keyword fallback)
    if _search_tags(tags, AI_CLOUD_KEYWORDS | MODERN_TECH_KEYWORDS):
        return "modern"

    if founded and isinstance(founded, (int, float)):
        if founded > 2015 and industry in ("technology", "software", "saas", "cloud"):
            return "modern"

    # Modernizing signals
    if _search_themes(themes, TRANSFORMATION_KEYWORDS):
        return "modernizing"

    if _search_themes(themes, AI_CLOUD_KEYWORDS):
        return "modernizing"

    # Traditional signals
    if founded and isinstance(founded, (int, float)):
        if founded < 2000 and industry not in ("technology", "software", "saas", "cloud"):
            return "traditional"

    return "modernizing"


def infer_business_priority(profile: Dict[str, Any]) -> str:
    """
    Infer primary business priority from enrichment data.

    Signals for reducing_cost:
    - News about cost reduction, efficiency

    Signals for preparing_ai:
    - Data/AI-related role title
    - News about AI adoption/ML
    - Company tags with AI signals

    Signals for improving_performance:
    - High employee growth rate (>30%)
    - News about scaling, expansion

    Default: preparing_ai (AMD's primary message)
    """
    themes = profile.get("news_themes", []) or []
    articles = profile.get("recent_news", []) or []
    title = (profile.get("title") or "").lower()
    tags = profile.get("company_tags", []) or []
    growth_rate = profile.get("employee_growth_rate")

    # Cost reduction signals
    if _search_themes(themes, COST_KEYWORDS) or _search_articles(articles, COST_KEYWORDS):
        return "reducing_cost"

    # AI preparation signals
    if _search_text(title, DATA_AI_ROLE_KEYWORDS):
        return "preparing_ai"

    if _search_themes(themes, AI_ADOPTION_KEYWORDS) or _search_articles(articles, AI_ADOPTION_KEYWORDS):
        return "preparing_ai"

    if _search_tags(tags, AI_CLOUD_KEYWORDS):
        return "preparing_ai"

    # Performance/growth signals
    if growth_rate and isinstance(growth_rate, (int, float)) and growth_rate > 0.3:
        return "improving_performance"

    if _search_themes(themes, GROWTH_KEYWORDS) or _search_articles(articles, GROWTH_KEYWORDS):
        return "improving_performance"

    return "preparing_ai"


def infer_challenge(profile: Dict[str, Any]) -> str:
    """
    Infer primary challenge from enrichment data.

    Signals for legacy_systems:
    - Old company (founded before 2005) in non-tech industry

    Signals for skills_gap:
    - News about talent/hiring/skills

    Signals for resource_constraints:
    - Small company (<200 employees)

    Signals for data_governance:
    - Healthcare or financial services industry

    Signals for integration_friction:
    - News about integration challenges

    Default: legacy_systems
    """
    industry = (profile.get("industry") or "").lower()
    founded = profile.get("founded_year")
    employee_count = profile.get("employee_count")
    articles = profile.get("recent_news", []) or []
    themes = profile.get("news_themes", []) or []

    # Data governance - regulated industries
    if any(ind in industry for ind in ("health", "financial", "banking", "insurance", "pharma")):
        return "data_governance"

    # Skills gap - talent-related news
    if _search_articles(articles, TALENT_KEYWORDS) or _search_themes(themes, TALENT_KEYWORDS):
        return "skills_gap"

    # Resource constraints - small companies
    if employee_count and isinstance(employee_count, (int, float)) and employee_count < 200:
        return "resource_constraints"

    # Integration friction - integration news
    if _search_articles(articles, INTEGRATION_KEYWORDS) or _search_themes(themes, INTEGRATION_KEYWORDS):
        return "integration_friction"

    # Legacy systems - old non-tech companies
    if founded and isinstance(founded, (int, float)):
        if founded < 2005 and industry not in ("technology", "software", "saas", "cloud"):
            return "legacy_systems"

    return "legacy_systems"


def infer_urgency_level(profile: Dict[str, Any]) -> str:
    """
    Infer urgency level from enrichment data.

    HIGH:
    - Rapid growth (>40%)
    - Recent funding event
    - Crisis situation

    LOW:
    - Small stable company with no growth
    - Negative growth

    Default: medium
    """
    growth_rate = profile.get("employee_growth_rate")
    funding_stage = profile.get("latest_funding_stage")
    total_funding = profile.get("total_funding")
    employee_count = profile.get("employee_count")

    # High urgency signals
    if growth_rate and isinstance(growth_rate, (int, float)) and growth_rate > 0.4:
        return "high"

    if funding_stage and total_funding:
        return "high"

    # Low urgency signals
    if growth_rate and isinstance(growth_rate, (int, float)) and growth_rate < 0:
        return "low"

    if employee_count and isinstance(employee_count, (int, float)) and employee_count < 100:
        if not growth_rate or (isinstance(growth_rate, (int, float)) and growth_rate <= 0):
            return "low"

    return "medium"


def infer_journey_stage(profile: Dict[str, Any]) -> str:
    """
    Infer buying journey stage when not user-provided.

    decision: C-level role + investment/funding news
    implementation: News about pilots, testing, deployment
    consideration: Recent funding round, active evaluation signals
    awareness: Default

    Default: consideration
    """
    seniority = (profile.get("seniority") or "").lower()
    title = (profile.get("title") or "").lower()
    articles = profile.get("recent_news", []) or []
    funding_stage = profile.get("latest_funding_stage")

    # Decision stage: C-level + investment signals
    is_c_level = seniority in ("c_suite", "cxo") or any(
        t in title for t in ("ceo", "cto", "cio", "cfo", "ciso", "coo", "chief")
    )
    has_investment_news = _search_articles(articles, INVESTMENT_KEYWORDS)

    if is_c_level and has_investment_news:
        return "decision"

    # Implementation stage: pilot/testing signals
    if _search_articles(articles, PILOT_KEYWORDS):
        return "implementation"

    # Consideration: recent funding
    if funding_stage:
        return "consideration"

    return "consideration"


def _calculate_confidence(profile: Dict[str, Any]) -> float:
    """
    Calculate confidence score for inferred context.
    More data points = higher confidence.
    """
    score = 0.2  # Base confidence

    signals = [
        profile.get("company_tags"),
        profile.get("news_themes"),
        profile.get("recent_news"),
        profile.get("founded_year"),
        profile.get("employee_count"),
        profile.get("employee_growth_rate"),
        profile.get("latest_funding_stage"),
        profile.get("title"),
        profile.get("seniority"),
        profile.get("industry"),
        profile.get("company_summary"),
    ]

    present = sum(1 for s in signals if s)
    score += (present / len(signals)) * 0.7

    # Bonus for rich news data
    news = profile.get("recent_news", [])
    if isinstance(news, list) and len(news) >= 3:
        score += 0.1

    return min(1.0, score)


def infer_context(
    profile: Dict[str, Any],
    user_goal: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run full context inference pipeline on enrichment data.

    Args:
        profile: Normalized enrichment data from APIs
        user_goal: User-provided journey stage (optional, takes priority)

    Returns:
        Dict with inferred context fields, tech signals, and confidence score
    """
    it_env = infer_it_environment(profile)
    priority = infer_business_priority(profile)
    challenge = infer_challenge(profile)
    urgency = infer_urgency_level(profile)

    # Use user-provided goal if available, otherwise infer
    if user_goal and user_goal.strip():
        stage = user_goal
    else:
        stage = infer_journey_stage(profile)

    confidence = _calculate_confidence(profile)

    result = {
        "it_environment": it_env,
        "business_priority": priority,
        "primary_challenge": challenge,
        "urgency_level": urgency,
        "journey_stage": stage,
        "confidence_score": round(confidence, 2),
    }

    # Include structured tech signals if company tags are available
    tags = profile.get("company_tags", []) or []
    if tags:
        result["tech_signals"] = extract_tech_signals_from_tags(tags)

    logger.info(
        f"Context inferred: env={it_env}, priority={priority}, "
        f"challenge={challenge}, urgency={urgency}, stage={stage}, "
        f"confidence={confidence:.2f}"
    )

    return result
