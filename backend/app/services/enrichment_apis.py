"""
Enrichment API integrations for RAD pipeline.
Real implementations for: Apollo, PDL, Hunter, Tavily, ZoomInfo.
All API keys loaded from environment variables.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import httpx
from abc import ABC, abstractmethod

from app.config import settings

logger = logging.getLogger(__name__)

# Default timeout for all API calls (seconds)
DEFAULT_TIMEOUT = 45.0

# Extended timeout for deep enrichment queries
DEEP_ENRICHMENT_TIMEOUT = 60.0


class EnrichmentAPIError(Exception):
    """Base exception for enrichment API errors."""

    def __init__(self, source: str, message: str, status_code: Optional[int] = None):
        self.source = source
        self.message = message
        self.status_code = status_code
        super().__init__(f"{source}: {message}")


class BaseEnrichmentAPI(ABC):
    """Base class for enrichment API integrations."""

    source_name: str = "unknown"

    @abstractmethod
    async def enrich(self, email: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """Enrich data for given email/domain."""
        pass

    def _handle_error(self, response: httpx.Response) -> None:
        """Handle API error response."""
        if response.status_code >= 400:
            raise EnrichmentAPIError(
                source=self.source_name,
                message=f"API returned {response.status_code}: {response.text[:200]}",
                status_code=response.status_code
            )


class ApolloAPI(BaseEnrichmentAPI):
    """
    Apollo.io People Enrichment API.
    Docs: https://apolloio.github.io/apollo-api-docs/
    """

    source_name = "apollo"
    base_url = "https://api.apollo.io/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.APOLLO_API_KEY
        if not self.api_key:
            logger.warning("Apollo API key not configured")

    async def enrich(self, email: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Enrich person data from Apollo.

        Args:
            email: Email address to look up
            domain: Company domain (optional)

        Returns:
            Enriched person data
        """
        if not self.api_key:
            return self._mock_response(email, domain)

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                response = await client.post(
                    f"{self.base_url}/people/match",
                    headers={
                        "Content-Type": "application/json",
                        "X-Api-Key": self.api_key
                    },
                    json={
                        "email": email,
                        "reveal_personal_emails": False,
                        "reveal_phone_number": False  # Never request phone numbers
                    }
                )

                self._handle_error(response)
                data = response.json()

                person = data.get("person", {})
                return {
                    "email": email,
                    "first_name": person.get("first_name"),
                    "last_name": person.get("last_name"),
                    "title": person.get("title"),
                    "linkedin_url": person.get("linkedin_url"),
                    "company_name": person.get("organization", {}).get("name"),
                    "domain": person.get("organization", {}).get("primary_domain"),
                    "industry": person.get("organization", {}).get("industry"),
                    "company_size": self._map_employee_count(
                        person.get("organization", {}).get("estimated_num_employees")
                    ),
                    "city": person.get("city"),
                    "state": person.get("state"),
                    "country": person.get("country"),
                    "seniority": person.get("seniority"),
                    "departments": person.get("departments", []),
                    "fetched_at": datetime.utcnow().isoformat()
                }

        except httpx.TimeoutException:
            logger.error(f"Apollo API timeout for {email}")
            raise EnrichmentAPIError(self.source_name, "Request timeout")
        except httpx.RequestError as e:
            logger.error(f"Apollo API request error for {email}: {e}")
            raise EnrichmentAPIError(self.source_name, str(e))

    def _mock_response(self, email: str, domain: Optional[str]) -> Dict[str, Any]:
        """Return mock data when API key not configured."""
        logger.info(f"Apollo: Using mock data for {email} (no API key)")
        username = email.split("@")[0]
        domain = domain or email.split("@")[1]
        return {
            "email": email,
            "first_name": username.split(".")[0].title() if "." in username else username.title(),
            "last_name": username.split(".")[-1].title() if "." in username else "User",
            "title": "Professional",
            "linkedin_url": f"https://linkedin.com/in/{username}",
            "company_name": f"Company at {domain}",
            "domain": domain,
            "industry": "Technology",
            "company_size": "50-200",
            "country": "US",
            "fetched_at": datetime.utcnow().isoformat(),
            "_mock": True
        }

    def _map_employee_count(self, count: Optional[int]) -> str:
        """Map employee count to size range."""
        if not count:
            return "Unknown"
        if count < 10:
            return "1-10"
        if count < 50:
            return "11-50"
        if count < 200:
            return "50-200"
        if count < 500:
            return "200-500"
        if count < 1000:
            return "500-1000"
        return "1000+"


class PDLAPI(BaseEnrichmentAPI):
    """
    People Data Labs API.
    Docs: https://docs.peopledatalabs.com/
    """

    source_name = "pdl"
    base_url = "https://api.peopledatalabs.com/v5"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.PDL_API_KEY
        if not self.api_key:
            logger.warning("PDL API key not configured")

    async def enrich(self, email: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Enrich person data from People Data Labs.

        Args:
            email: Email address to look up
            domain: Company domain (optional)

        Returns:
            Enriched person data
        """
        if not self.api_key:
            return self._mock_response(email, domain)

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                response = await client.get(
                    f"{self.base_url}/person/enrich",
                    headers={"X-Api-Key": self.api_key},
                    params={"email": email}
                )

                self._handle_error(response)
                data = response.json()

                return {
                    "email": email,
                    "first_name": data.get("first_name"),
                    "last_name": data.get("last_name"),
                    "full_name": data.get("full_name"),
                    "linkedin_url": data.get("linkedin_url"),
                    "job_title": data.get("job_title"),
                    "job_company_name": data.get("job_company_name"),
                    "job_company_industry": data.get("job_company_industry"),
                    "job_company_size": data.get("job_company_size"),
                    "location_country": data.get("location_country"),
                    "location_region": data.get("location_region"),
                    "location_locality": data.get("location_locality"),
                    "skills": data.get("skills", [])[:10],  # Limit skills
                    "interests": data.get("interests", [])[:10],
                    "experience": self._extract_recent_experience(data.get("experience", [])),
                    "fetched_at": datetime.utcnow().isoformat()
                }

        except httpx.TimeoutException:
            logger.error(f"PDL API timeout for {email}")
            raise EnrichmentAPIError(self.source_name, "Request timeout")
        except httpx.RequestError as e:
            logger.error(f"PDL API request error for {email}: {e}")
            raise EnrichmentAPIError(self.source_name, str(e))

    def _mock_response(self, email: str, domain: Optional[str]) -> Dict[str, Any]:
        """Return mock data when API key not configured."""
        logger.info(f"PDL: Using mock data for {email} (no API key)")
        return {
            "email": email,
            "location_country": "United States",
            "job_company_industry": "Software",
            "job_company_size": "51-200",
            "skills": ["Sales", "Marketing", "Strategy"],
            "fetched_at": datetime.utcnow().isoformat(),
            "_mock": True
        }

    def _extract_recent_experience(self, experience: List[Dict]) -> List[Dict]:
        """Extract recent work experience (last 3 positions)."""
        return experience[:3] if experience else []

    async def enrich_company(self, domain: str) -> Dict[str, Any]:
        """
        Enrich company data from People Data Labs Company API.
        Provides much deeper company insights than person enrichment.

        Args:
            domain: Company domain to look up

        Returns:
            Enriched company data
        """
        if not self.api_key:
            return self._mock_company_response(domain)

        try:
            async with httpx.AsyncClient(timeout=DEEP_ENRICHMENT_TIMEOUT) as client:
                response = await client.get(
                    f"{self.base_url}/company/enrich",
                    headers={"X-Api-Key": self.api_key},
                    params={"website": domain}
                )

                self._handle_error(response)
                data = response.json()

                return {
                    "domain": domain,
                    "name": data.get("name"),
                    "display_name": data.get("display_name"),
                    "size": data.get("size"),
                    "employee_count": data.get("employee_count"),
                    "employee_count_range": data.get("employee_count_range"),
                    "founded": data.get("founded"),
                    "industry": data.get("industry"),
                    "naics": data.get("naics", []),
                    "sic": data.get("sic", []),
                    "location": data.get("location"),
                    "locality": data.get("locality"),
                    "region": data.get("region"),
                    "country": data.get("country"),
                    "type": data.get("type"),  # private, public, nonprofit, etc.
                    "ticker": data.get("ticker"),
                    "linkedin_url": data.get("linkedin_url"),
                    "linkedin_id": data.get("linkedin_id"),
                    "facebook_url": data.get("facebook_url"),
                    "twitter_url": data.get("twitter_url"),
                    "profiles": data.get("profiles", []),
                    "tags": data.get("tags", [])[:15],  # Industry tags
                    "headline": data.get("headline"),
                    "summary": data.get("summary"),
                    "alternative_names": data.get("alternative_names", []),
                    "affiliated_profiles": data.get("affiliated_profiles", [])[:5],
                    "total_funding_raised": data.get("total_funding_raised"),
                    "latest_funding_stage": data.get("latest_funding_stage"),
                    "last_funding_date": data.get("last_funding_date"),
                    "number_funding_rounds": data.get("number_funding_rounds"),
                    "inferred_revenue": data.get("inferred_revenue"),
                    "direct_phone_numbers": len(data.get("direct_phone_numbers", [])),  # Count only, not actual numbers
                    "employee_growth_rate": data.get("employee_growth_rate"),
                    "fetched_at": datetime.utcnow().isoformat()
                }

        except httpx.TimeoutException:
            logger.error(f"PDL Company API timeout for {domain}")
            raise EnrichmentAPIError(self.source_name, "Company request timeout")
        except httpx.RequestError as e:
            logger.error(f"PDL Company API request error for {domain}: {e}")
            raise EnrichmentAPIError(self.source_name, str(e))

    def _mock_company_response(self, domain: str) -> Dict[str, Any]:
        """Return mock company data when API key not configured."""
        logger.info(f"PDL Company: Using mock data for {domain} (no API key)")
        return {
            "domain": domain,
            "name": f"Company at {domain}",
            "industry": "Technology",
            "size": "51-200",
            "employee_count": 150,
            "country": "United States",
            "type": "private",
            "tags": ["technology", "software", "enterprise"],
            "summary": f"A technology company operating at {domain}.",
            "fetched_at": datetime.utcnow().isoformat(),
            "_mock": True
        }


class HunterAPI(BaseEnrichmentAPI):
    """
    Hunter.io Email Verification API.
    Docs: https://hunter.io/api-documentation/v2
    """

    source_name = "hunter"
    base_url = "https://api.hunter.io/v2"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.HUNTER_API_KEY
        if not self.api_key:
            logger.warning("Hunter API key not configured")

    async def enrich(self, email: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify email and get additional data from Hunter.

        Args:
            email: Email address to verify
            domain: Company domain (optional)

        Returns:
            Email verification data
        """
        if not self.api_key:
            return self._mock_response(email, domain)

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                response = await client.get(
                    f"{self.base_url}/email-verifier",
                    params={
                        "email": email,
                        "api_key": self.api_key
                    }
                )

                self._handle_error(response)
                data = response.json().get("data", {})

                return {
                    "email": email,
                    "status": data.get("status"),  # valid, invalid, accept_all, webmail, disposable, unknown
                    "result": data.get("result"),  # deliverable, undeliverable, risky, unknown
                    "score": data.get("score"),  # 0-100
                    "regexp": data.get("regexp"),
                    "gibberish": data.get("gibberish"),
                    "disposable": data.get("disposable"),
                    "webmail": data.get("webmail"),
                    "mx_records": data.get("mx_records"),
                    "smtp_server": data.get("smtp_server"),
                    "smtp_check": data.get("smtp_check"),
                    "accept_all": data.get("accept_all"),
                    "block": data.get("block"),
                    "fetched_at": datetime.utcnow().isoformat()
                }

        except httpx.TimeoutException:
            logger.error(f"Hunter API timeout for {email}")
            raise EnrichmentAPIError(self.source_name, "Request timeout")
        except httpx.RequestError as e:
            logger.error(f"Hunter API request error for {email}: {e}")
            raise EnrichmentAPIError(self.source_name, str(e))

    def _mock_response(self, email: str, domain: Optional[str]) -> Dict[str, Any]:
        """Return mock data when API key not configured."""
        logger.info(f"Hunter: Using mock data for {email} (no API key)")
        return {
            "email": email,
            "status": "valid",
            "result": "deliverable",
            "score": 90,
            "disposable": False,
            "webmail": "@gmail" in email or "@yahoo" in email or "@hotmail" in email,
            "fetched_at": datetime.utcnow().isoformat(),
            "_mock": True
        }


class GNewsAPI(BaseEnrichmentAPI):
    """
    GNews API for company news and context.
    Docs: https://gnews.io/docs/v4

    Enhanced to run multiple search queries for comprehensive news coverage:
    - Company general news
    - Company + AI/technology news
    - Company + industry trends
    - Company + leadership/strategy
    """

    source_name = "gnews"
    base_url = "https://gnews.io/api/v4"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GNEWS_API_KEY
        if not self.api_key:
            logger.warning("GNews API key not configured")

    async def enrich(self, email: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Search for company news using GNews with multiple queries.

        Args:
            email: Email address (used to extract domain if not provided)
            domain: Company domain

        Returns:
            News articles and company context from multiple angles
        """
        if not self.api_key:
            return self._mock_response(email, domain)

        domain = domain or email.split("@")[1]
        # Extract company name from domain (e.g., microsoft.com -> microsoft)
        company_name = domain.split(".")[0]

        try:
            # Run multiple search queries in parallel for comprehensive coverage
            all_articles = await self._fetch_multi_query_news(company_name)

            # Deduplicate articles by URL
            seen_urls = set()
            unique_articles = []
            for article in all_articles:
                url = article.get("url")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_articles.append(article)

            # Build comprehensive summary
            answer = self._build_news_summary(company_name, unique_articles)

            # Categorize articles
            categorized = self._categorize_articles(unique_articles)

            return {
                "domain": domain,
                "company_name": company_name,
                "answer": answer,
                "results": unique_articles[:10],  # Top 10 unique articles
                "categorized": categorized,
                "result_count": len(unique_articles),
                "themes": self._extract_themes(unique_articles),
                "sentiment_indicators": self._analyze_sentiment_keywords(unique_articles),
                "fetched_at": datetime.utcnow().isoformat()
            }

        except httpx.TimeoutException:
            logger.error(f"GNews API timeout for {domain}")
            raise EnrichmentAPIError(self.source_name, "Request timeout")
        except httpx.RequestError as e:
            logger.error(f"GNews API request error for {domain}: {e}")
            raise EnrichmentAPIError(self.source_name, str(e))

    async def _fetch_multi_query_news(self, company_name: str) -> List[Dict[str, Any]]:
        """
        Fetch news from multiple search queries in parallel.

        Args:
            company_name: Company name to search for

        Returns:
            Combined list of articles from all queries
        """
        search_queries = [
            f'"{company_name}"',  # Exact company name match
            f"{company_name} AI artificial intelligence",
            f"{company_name} technology innovation",
            f"{company_name} strategy leadership CEO",
            f"{company_name} expansion growth partnership",
        ]

        async with httpx.AsyncClient(timeout=DEEP_ENRICHMENT_TIMEOUT) as client:
            tasks = []
            for query in search_queries:
                tasks.append(
                    client.get(
                        f"{self.base_url}/search",
                        params={
                            "token": self.api_key,
                            "q": query,
                            "lang": "en",
                            "max": 5,
                            "sortby": "relevance"
                        }
                    )
                )

            responses = await asyncio.gather(*tasks, return_exceptions=True)

            all_articles = []
            for i, response in enumerate(responses):
                if isinstance(response, Exception):
                    logger.warning(f"GNews query {i} failed: {response}")
                    continue
                try:
                    if response.status_code == 200:
                        data = response.json()
                        articles = data.get("articles", [])
                        for article in articles:
                            all_articles.append({
                                "title": article.get("title"),
                                "url": article.get("url"),
                                "content": article.get("description", "")[:800],
                                "full_content": article.get("content", "")[:1500],
                                "published_at": article.get("publishedAt"),
                                "source": article.get("source", {}).get("name"),
                                "source_url": article.get("source", {}).get("url"),
                                "image": article.get("image"),
                                "query_category": self._get_query_category(i)
                            })
                except Exception as e:
                    logger.warning(f"Failed to parse GNews response {i}: {e}")

            return all_articles

    def _get_query_category(self, query_index: int) -> str:
        """Map query index to category name."""
        categories = [
            "general",
            "ai_technology",
            "innovation",
            "leadership",
            "growth"
        ]
        return categories[query_index] if query_index < len(categories) else "other"

    def _build_news_summary(self, company_name: str, articles: List[Dict]) -> str:
        """Build a comprehensive news summary from articles."""
        if not articles:
            return f"No recent news found for {company_name}."

        # Group by category
        by_category = {}
        for article in articles:
            cat = article.get("query_category", "general")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(article.get("title", ""))

        summary_parts = [f"Recent news coverage for {company_name}:"]

        if "general" in by_category:
            summary_parts.append(f"General: {'; '.join(by_category['general'][:2])}")
        if "ai_technology" in by_category:
            summary_parts.append(f"AI/Tech: {'; '.join(by_category['ai_technology'][:2])}")
        if "leadership" in by_category:
            summary_parts.append(f"Leadership: {'; '.join(by_category['leadership'][:2])}")
        if "growth" in by_category:
            summary_parts.append(f"Growth: {'; '.join(by_category['growth'][:2])}")

        return " | ".join(summary_parts)

    def _categorize_articles(self, articles: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorize articles by topic."""
        categorized = {
            "ai_technology": [],
            "leadership": [],
            "growth": [],
            "general": []
        }

        for article in articles:
            cat = article.get("query_category", "general")
            if cat in categorized:
                categorized[cat].append(article)
            else:
                categorized["general"].append(article)

        return categorized

    def _extract_themes(self, articles: List[Dict]) -> List[str]:
        """Extract key themes from article titles and content."""
        themes = set()
        theme_keywords = {
            "AI adoption": ["ai", "artificial intelligence", "machine learning", "ml"],
            "Cloud transformation": ["cloud", "aws", "azure", "gcp", "saas"],
            "Digital transformation": ["digital", "transformation", "modernization"],
            "Data strategy": ["data", "analytics", "insights", "big data"],
            "Growth & expansion": ["growth", "expansion", "revenue", "market"],
            "Partnership": ["partnership", "collaboration", "joint venture"],
            "Innovation": ["innovation", "r&d", "research", "breakthrough"],
            "Sustainability": ["sustainability", "esg", "green", "carbon"],
            "Security": ["security", "cybersecurity", "privacy", "compliance"],
            "Workforce": ["hiring", "workforce", "talent", "employees"]
        }

        combined_text = " ".join([
            (a.get("title", "") + " " + a.get("content", "")).lower()
            for a in articles
        ])

        for theme, keywords in theme_keywords.items():
            if any(kw in combined_text for kw in keywords):
                themes.add(theme)

        return list(themes)[:5]

    def _analyze_sentiment_keywords(self, articles: List[Dict]) -> Dict[str, int]:
        """Analyze sentiment indicators from articles."""
        positive = ["growth", "success", "expansion", "innovation", "award", "leading", "record"]
        negative = ["layoff", "decline", "lawsuit", "investigation", "loss", "struggling"]
        neutral = ["announce", "report", "update", "release", "partner"]

        combined_text = " ".join([
            (a.get("title", "") + " " + a.get("content", "")).lower()
            for a in articles
        ])

        return {
            "positive": sum(1 for word in positive if word in combined_text),
            "negative": sum(1 for word in negative if word in combined_text),
            "neutral": sum(1 for word in neutral if word in combined_text)
        }

    def _mock_response(self, email: str, domain: Optional[str]) -> Dict[str, Any]:
        """Return mock data when API key not configured."""
        domain = domain or email.split("@")[1]
        company_name = domain.split(".")[0]
        logger.info(f"GNews: Using mock data for {domain} (no API key)")
        return {
            "domain": domain,
            "company_name": company_name,
            "answer": f"{company_name.title()} is an innovative company focused on digital transformation and technology solutions.",
            "results": [
                {
                    "title": f"{company_name.title()} announces new AI initiative",
                    "content": f"{company_name.title()} is investing in artificial intelligence to improve customer experiences.",
                    "published_at": datetime.utcnow().isoformat(),
                    "source": "Tech News Daily",
                    "query_category": "ai_technology"
                },
                {
                    "title": f"{company_name.title()} reports strong Q4 growth",
                    "content": "The company exceeded analyst expectations with double-digit revenue growth.",
                    "published_at": datetime.utcnow().isoformat(),
                    "source": "Business Wire",
                    "query_category": "growth"
                }
            ],
            "categorized": {
                "ai_technology": [],
                "leadership": [],
                "growth": [],
                "general": []
            },
            "result_count": 2,
            "themes": ["AI adoption", "Growth & expansion"],
            "sentiment_indicators": {"positive": 3, "negative": 0, "neutral": 1},
            "fetched_at": datetime.utcnow().isoformat(),
            "_mock": True
        }


class ZoomInfoAPI(BaseEnrichmentAPI):
    """
    ZoomInfo Company Enrichment API.
    Docs: https://api-docs.zoominfo.com/
    """

    source_name = "zoominfo"
    base_url = "https://api.zoominfo.com"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.ZOOMINFO_API_KEY
        if not self.api_key:
            logger.warning("ZoomInfo API key not configured")

    async def enrich(self, email: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Enrich company data from ZoomInfo.

        Args:
            email: Email address (used to extract domain if not provided)
            domain: Company domain

        Returns:
            Company data from ZoomInfo
        """
        if not self.api_key:
            return self._mock_response(email, domain)

        domain = domain or email.split("@")[1]

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                # ZoomInfo requires OAuth token, simplified here
                response = await client.post(
                    f"{self.base_url}/search/company",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "matchCompanyInput": [{"companyWebsite": domain}],
                        "outputFields": [
                            "id", "name", "website", "industry", "subIndustry",
                            "employeeCount", "revenue", "city", "state", "country",
                            "description", "foundedYear", "techStackIds"
                        ]
                    }
                )

                self._handle_error(response)
                data = response.json()
                company = data.get("data", [{}])[0] if data.get("data") else {}

                return {
                    "domain": domain,
                    "company_name": company.get("name"),
                    "website": company.get("website"),
                    "industry": company.get("industry"),
                    "sub_industry": company.get("subIndustry"),
                    "employee_count": company.get("employeeCount"),
                    "revenue": company.get("revenue"),
                    "city": company.get("city"),
                    "state": company.get("state"),
                    "country": company.get("country"),
                    "description": company.get("description"),
                    "founded_year": company.get("foundedYear"),
                    "tech_stack": company.get("techStackIds", []),
                    "fetched_at": datetime.utcnow().isoformat()
                }

        except httpx.TimeoutException:
            logger.error(f"ZoomInfo API timeout for {domain}")
            raise EnrichmentAPIError(self.source_name, "Request timeout")
        except httpx.RequestError as e:
            logger.error(f"ZoomInfo API request error for {domain}: {e}")
            raise EnrichmentAPIError(self.source_name, str(e))

    def _mock_response(self, email: str, domain: Optional[str]) -> Dict[str, Any]:
        """Return mock data when API key not configured."""
        domain = domain or email.split("@")[1]
        logger.info(f"ZoomInfo: Using mock data for {domain} (no API key)")
        return {
            "domain": domain,
            "company_name": f"Company at {domain}",
            "industry": "Technology",
            "employee_count": 100,
            "country": "United States",
            "fetched_at": datetime.utcnow().isoformat(),
            "_mock": True
        }


# Convenience factory function
def get_enrichment_apis() -> Dict[str, BaseEnrichmentAPI]:
    """
    Get all configured enrichment API clients.

    Returns:
        Dict mapping source name to API client
    """
    return {
        "apollo": ApolloAPI(),
        "pdl": PDLAPI(),
        "hunter": HunterAPI(),
        "gnews": GNewsAPI(),
        "zoominfo": ZoomInfoAPI()
    }
