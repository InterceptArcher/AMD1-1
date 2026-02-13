"""
Tests for news analysis service.
Validates sentiment analysis, entity extraction, and AI readiness signal detection
from GNews enrichment data.
"""

import pytest
from app.services.news_analysis_service import (
    analyze_news,
    detect_sentiment,
    extract_entities,
    detect_ai_readiness_signals,
    detect_crisis,
)


# === Sentiment Detection ===


class TestDetectSentiment:
    """Test sentiment detection from news articles."""

    def test_positive_sentiment(self):
        """Articles about growth and success should be positive."""
        articles = [
            {"title": "Company reports record revenue growth of 40%", "content": "Strong quarterly performance driven by expansion."},
            {"title": "Company wins innovation award", "content": "Recognized for breakthrough technology."},
        ]
        result = detect_sentiment(articles)
        assert result["overall"] == "positive"
        assert result["positive_count"] > result["negative_count"]

    def test_negative_sentiment(self):
        """Articles about layoffs and losses should be negative."""
        articles = [
            {"title": "Company announces 500 layoffs", "content": "Restructuring amid declining revenue."},
            {"title": "Company faces regulatory investigation", "content": "SEC probes accounting practices."},
        ]
        result = detect_sentiment(articles)
        assert result["overall"] == "negative"
        assert result["negative_count"] > result["positive_count"]

    def test_neutral_sentiment(self):
        """Mixed or bland articles should be neutral."""
        articles = [
            {"title": "Company appoints new board member", "content": "Experienced executive joins leadership team."},
        ]
        result = detect_sentiment(articles)
        assert result["overall"] in ["neutral", "positive"]

    def test_empty_articles(self):
        """No articles should return neutral sentiment."""
        result = detect_sentiment([])
        assert result["overall"] == "neutral"
        assert result["positive_count"] == 0
        assert result["negative_count"] == 0


# === Entity Extraction ===


class TestExtractEntities:
    """Test entity extraction from news articles."""

    def test_technology_entities(self):
        """Should detect technology mentions."""
        articles = [
            {"title": "Company deploys AWS cloud and Kubernetes for AI workloads"},
            {"title": "Partnership with Microsoft Azure expands data capabilities"},
        ]
        result = extract_entities(articles)
        assert "technologies" in result
        assert len(result["technologies"]) > 0

    def test_competitor_detection(self):
        """Should detect competitor mentions in context."""
        articles = [
            {"title": "Company competes with Intel and NVIDIA in data center market"},
        ]
        result = extract_entities(articles)
        assert "competitors" in result

    def test_empty_articles(self):
        """No articles should return empty entities."""
        result = extract_entities([])
        assert result["technologies"] == []
        assert result["competitors"] == []
        assert result["partners"] == []


# === AI Readiness Signal Detection ===


class TestDetectAIReadinessSignals:
    """Test AI readiness signal detection."""

    def test_exploring_ai(self):
        """Articles about exploring AI should detect exploring signal."""
        articles = [
            {"title": "Company begins exploring artificial intelligence opportunities"},
        ]
        result = detect_ai_readiness_signals(articles)
        assert result["stage"] in ["exploring", "piloting"]
        assert result["confidence"] > 0

    def test_deploying_ai(self):
        """Articles about AI deployment should detect deployment signal."""
        articles = [
            {"title": "Company deploys machine learning across production systems"},
            {"title": "AI-powered platform drives 30% efficiency gains"},
        ]
        result = detect_ai_readiness_signals(articles)
        assert result["stage"] == "deployed"
        assert result["confidence"] > 0.5

    def test_no_ai_signals(self):
        """Articles with no AI content should return no signals."""
        articles = [
            {"title": "Company opens new retail location"},
            {"title": "Annual report shows steady growth"},
        ]
        result = detect_ai_readiness_signals(articles)
        assert result["stage"] == "none"
        assert result["confidence"] == 0


# === Crisis Detection ===


class TestDetectCrisis:
    """Test crisis/negative event detection."""

    def test_layoff_crisis(self):
        """Layoff news should trigger crisis detection."""
        articles = [
            {"title": "Company announces massive layoffs affecting 2000 employees"},
        ]
        result = detect_crisis(articles)
        assert result["is_crisis"] is True
        assert result["type"] == "workforce"

    def test_regulatory_crisis(self):
        """Regulatory investigation should trigger crisis detection."""
        articles = [
            {"title": "SEC launches investigation into company's financial reporting"},
        ]
        result = detect_crisis(articles)
        assert result["is_crisis"] is True
        assert result["type"] == "regulatory"

    def test_no_crisis(self):
        """Normal business news should not trigger crisis."""
        articles = [
            {"title": "Company announces new product launch"},
            {"title": "CEO speaks at industry conference"},
        ]
        result = detect_crisis(articles)
        assert result["is_crisis"] is False


# === Full News Analysis ===


class TestAnalyzeNews:
    """Test the full news analysis pipeline."""

    def test_full_analysis_returns_all_fields(self):
        """analyze_news should return all expected sections."""
        articles = [
            {"title": "TechCo launches AI platform for healthcare", "content": "Partnership with AWS to deploy ML models."},
            {"title": "TechCo raises $50M Series C", "content": "Funding to expand AI capabilities."},
        ]
        result = analyze_news(articles)

        assert "sentiment" in result
        assert "entities" in result
        assert "ai_readiness" in result
        assert "crisis" in result

    def test_empty_analysis(self):
        """Analysis with no articles should return safe defaults."""
        result = analyze_news([])

        assert result["sentiment"]["overall"] == "neutral"
        assert result["entities"]["technologies"] == []
        assert result["ai_readiness"]["stage"] == "none"
        assert result["crisis"]["is_crisis"] is False

    def test_analysis_with_varied_content(self):
        """Analysis should handle a mix of positive and negative articles."""
        articles = [
            {"title": "Company wins major cloud contract", "content": "Signed $10M deal."},
            {"title": "Company faces supply chain delays", "content": "Production impacted by shortages."},
            {"title": "Company explores AI for manufacturing", "content": "Piloting machine learning."},
        ]
        result = analyze_news(articles)

        assert result["sentiment"]["overall"] in ["positive", "neutral", "mixed"]
        assert result["ai_readiness"]["stage"] in ["exploring", "piloting"]
