"""
News Analysis Service: Extracts structured insights from GNews articles.
Provides sentiment analysis, entity extraction, AI readiness signals, and crisis detection.
"""

import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Sentiment keyword sets
POSITIVE_KEYWORDS = {
    "growth", "revenue", "profit", "award", "innovation", "partnership",
    "expansion", "launch", "record", "success", "breakthrough", "milestone",
    "wins", "achievement", "leading", "strong", "surpass", "exceed",
    "improve", "gain", "positive", "accelerate", "momentum",
}

NEGATIVE_KEYWORDS = {
    "layoff", "layoffs", "restructuring", "decline", "loss", "investigation",
    "lawsuit", "breach", "hack", "fine", "penalty", "downturn", "cuts",
    "closure", "bankruptcy", "default", "scandal", "fraud", "probe",
    "setback", "downsizing", "struggling", "crisis", "failing",
}

# Technology entity patterns
TECH_KEYWORDS = {
    "aws", "azure", "gcp", "google cloud", "kubernetes", "docker",
    "ai", "machine learning", "deep learning", "generative ai",
    "cloud", "saas", "gpu", "cpu", "data center",
    "pytorch", "tensorflow", "llm", "nvidia", "amd", "intel",
    "oracle", "salesforce", "snowflake", "databricks",
}

# Competitor patterns (AMD context)
COMPETITOR_KEYWORDS = {
    "intel", "nvidia", "arm", "qualcomm", "broadcom",
}

# Partner patterns
PARTNER_KEYWORDS = {
    "partnership", "partner", "collaborate", "collaboration", "alliance",
    "joint venture", "agreement", "deal", "contract",
}

# AI readiness signal keywords
AI_EXPLORING_KEYWORDS = {"exploring ai", "exploring artificial intelligence", "ai strategy", "ai roadmap", "evaluating ai", "considering ai", "ai opportunity", "ai opportunities"}
AI_PILOTING_KEYWORDS = {"pilot", "proof of concept", "poc", "testing ai", "ai trial", "ai experiment", "piloting"}
AI_DEPLOYED_KEYWORDS = {"deployed", "in production", "ai-powered", "machine learning platform", "ai infrastructure", "ml pipeline", "ai at scale", "production ai", "production ml"}

# Crisis patterns
WORKFORCE_CRISIS = {"layoff", "layoffs", "downsizing", "job cuts", "workforce reduction", "restructuring"}
REGULATORY_CRISIS = {"investigation", "sec", "regulatory", "probe", "lawsuit", "compliance violation", "fine", "penalty"}
FINANCIAL_CRISIS = {"bankruptcy", "default", "debt", "insolvency", "financial distress", "revenue decline"}
SECURITY_CRISIS = {"breach", "hack", "data leak", "cybersecurity incident", "ransomware", "vulnerability"}


def _get_article_text(articles: List[Dict]) -> str:
    """Combine all article titles and content into one searchable string."""
    parts = []
    for article in articles:
        if not isinstance(article, dict):
            continue
        title = article.get("title", "")
        content = article.get("content", "")
        if title:
            parts.append(title)
        if content:
            parts.append(content)
    return " ".join(parts).lower()


def _count_keyword_hits(text: str, keywords: set) -> int:
    """Count how many keywords appear in text."""
    if not text:
        return 0
    text_lower = text.lower()
    return sum(1 for kw in keywords if kw in text_lower)


def detect_sentiment(articles: List[Dict]) -> Dict[str, Any]:
    """
    Analyze sentiment across news articles.

    Returns:
        Dict with overall sentiment, positive/negative counts, and key signals.
    """
    if not articles:
        return {
            "overall": "neutral",
            "positive_count": 0,
            "negative_count": 0,
            "signals": [],
        }

    combined_text = _get_article_text(articles)
    positive_count = _count_keyword_hits(combined_text, POSITIVE_KEYWORDS)
    negative_count = _count_keyword_hits(combined_text, NEGATIVE_KEYWORDS)

    signals = []
    if positive_count > 0:
        signals.append(f"{positive_count} positive indicators")
    if negative_count > 0:
        signals.append(f"{negative_count} negative indicators")

    if negative_count > positive_count and negative_count >= 2:
        overall = "negative"
    elif positive_count > negative_count and positive_count >= 2:
        overall = "positive"
    else:
        overall = "neutral"

    return {
        "overall": overall,
        "positive_count": positive_count,
        "negative_count": negative_count,
        "signals": signals,
    }


def extract_entities(articles: List[Dict]) -> Dict[str, List[str]]:
    """
    Extract technology, competitor, and partner entities from articles.

    Returns:
        Dict with lists of technologies, competitors, and partners found.
    """
    if not articles:
        return {"technologies": [], "competitors": [], "partners": []}

    combined_text = _get_article_text(articles)

    technologies = [kw for kw in TECH_KEYWORDS if kw in combined_text]
    competitors = [kw for kw in COMPETITOR_KEYWORDS if kw in combined_text]

    # Partner detection: look for partner keywords near company mentions
    partners = []
    if _count_keyword_hits(combined_text, PARTNER_KEYWORDS) > 0:
        partners.append("partnership_detected")

    return {
        "technologies": sorted(set(technologies)),
        "competitors": sorted(set(competitors)),
        "partners": partners,
    }


def detect_ai_readiness_signals(articles: List[Dict]) -> Dict[str, Any]:
    """
    Detect AI adoption stage from news articles.

    Stages: none -> exploring -> piloting -> deployed

    Returns:
        Dict with stage and confidence score.
    """
    if not articles:
        return {"stage": "none", "confidence": 0, "signals": []}

    combined_text = _get_article_text(articles)
    signals = []

    deployed_hits = _count_keyword_hits(combined_text, AI_DEPLOYED_KEYWORDS)
    piloting_hits = _count_keyword_hits(combined_text, AI_PILOTING_KEYWORDS)
    exploring_hits = _count_keyword_hits(combined_text, AI_EXPLORING_KEYWORDS)

    if deployed_hits >= 2:
        stage = "deployed"
        confidence = min(1.0, 0.5 + deployed_hits * 0.15)
        signals.append(f"AI deployment signals: {deployed_hits}")
    elif deployed_hits >= 1:
        stage = "deployed"
        confidence = 0.5 + deployed_hits * 0.1
        signals.append(f"AI deployment mention: {deployed_hits}")
    elif piloting_hits >= 1:
        stage = "piloting"
        confidence = 0.3 + piloting_hits * 0.15
        signals.append(f"AI piloting signals: {piloting_hits}")
    elif exploring_hits >= 1:
        stage = "exploring"
        confidence = 0.2 + exploring_hits * 0.1
        signals.append(f"AI exploration signals: {exploring_hits}")
    else:
        stage = "none"
        confidence = 0
        signals = []

    return {
        "stage": stage,
        "confidence": round(min(1.0, confidence), 2),
        "signals": signals,
    }


def detect_crisis(articles: List[Dict]) -> Dict[str, Any]:
    """
    Detect crisis/negative events that should influence messaging tone.

    Returns:
        Dict with is_crisis flag, type, and details.
    """
    if not articles:
        return {"is_crisis": False, "type": None, "details": None}

    combined_text = _get_article_text(articles)

    # Check each crisis type
    if _count_keyword_hits(combined_text, WORKFORCE_CRISIS) >= 1:
        return {"is_crisis": True, "type": "workforce", "details": "Workforce restructuring detected"}

    if _count_keyword_hits(combined_text, REGULATORY_CRISIS) >= 1:
        return {"is_crisis": True, "type": "regulatory", "details": "Regulatory issue detected"}

    if _count_keyword_hits(combined_text, FINANCIAL_CRISIS) >= 1:
        return {"is_crisis": True, "type": "financial", "details": "Financial distress detected"}

    if _count_keyword_hits(combined_text, SECURITY_CRISIS) >= 1:
        return {"is_crisis": True, "type": "security", "details": "Security incident detected"}

    return {"is_crisis": False, "type": None, "details": None}


def analyze_news(articles: List[Dict]) -> Dict[str, Any]:
    """
    Run full news analysis pipeline.

    Args:
        articles: List of news article dicts with 'title' and 'content' keys.

    Returns:
        Dict with sentiment, entities, ai_readiness, and crisis analysis.
    """
    if not articles:
        articles = []

    result = {
        "sentiment": detect_sentiment(articles),
        "entities": extract_entities(articles),
        "ai_readiness": detect_ai_readiness_signals(articles),
        "crisis": detect_crisis(articles),
    }

    logger.info(
        f"News analysis: sentiment={result['sentiment']['overall']}, "
        f"ai_stage={result['ai_readiness']['stage']}, "
        f"crisis={result['crisis']['is_crisis']}"
    )

    return result
