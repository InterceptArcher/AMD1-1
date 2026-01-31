"""
RAD Orchestrator: Coordinates enrichment workflow.
- Fetches data from external APIs (Apollo, PDL, Hunter, GNews, ZoomInfo)
- Applies resolution logic (source priority + merge rules)
- Writes normalized output to Supabase
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

from app.config import settings
from app.services.supabase_client import SupabaseClient
from app.services.enrichment_apis import (
    get_enrichment_apis,
    EnrichmentAPIError,
    ApolloAPI,
    PDLAPI,
    HunterAPI,
    GNewsAPI,
    ZoomInfoAPI
)

logger = logging.getLogger(__name__)

# Source trust priority (higher = more trusted)
SOURCE_PRIORITY = {
    "apollo": 5,
    "zoominfo": 4,
    "pdl_company": 4,  # PDL Company API is highly reliable for company data
    "pdl": 3,
    "hunter": 2,
    "gnews": 1
}


class RADOrchestrator:
    """
    Orchestrates the full enrichment pipeline for a given email.
    Fetches from multiple APIs in parallel, merges data with conflict resolution.
    """

    def __init__(self, supabase_client: SupabaseClient):
        """
        Initialize orchestrator.

        Args:
            supabase_client: Supabase data access layer
        """
        self.supabase = supabase_client
        self.data_sources: List[str] = []
        self.apis = get_enrichment_apis()

    async def enrich(
        self,
        email: str,
        domain: Optional[str] = None,
        job_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute full enrichment pipeline for an email.

        Flow:
          1. Fetch raw data from external APIs (parallel)
          2. Store raw data in Supabase
          3. Apply resolution logic (merge with priority)
          4. Return normalized profile (personalization added by LLM service)

        Args:
            email: Email address to enrich
            domain: Company domain (optional, extracted from email if not provided)
            job_id: Optional job ID for tracking

        Returns:
            Normalized profile dict with metadata
        """
        try:
            logger.info(f"Starting enrichment for {email}")
            self.data_sources = []

            # Extract domain from email if not provided
            if not domain:
                domain = email.split("@")[1]

            # Step 1: Fetch raw data from all APIs in parallel
            raw_data = await self._fetch_all_sources(email, domain)

            # Step 2: Store raw data in Supabase
            for source, data in raw_data.items():
                if data and not data.get("_error"):
                    self.supabase.store_raw_data(email, source, data)
                    self.data_sources.append(source)

            # Step 3: Apply resolution logic
            normalized = self._resolve_profile(email, domain, raw_data)

            # Add metadata
            normalized["email"] = email
            normalized["domain"] = domain
            normalized["resolved_at"] = datetime.utcnow().isoformat()
            normalized["data_sources"] = self.data_sources
            normalized["data_quality_score"] = self._calculate_quality_score(raw_data)

            logger.info(f"Enrichment complete for {email}: {len(self.data_sources)} sources")
            return normalized

        except Exception as e:
            logger.error(f"Enrichment failed for {email}: {e}")
            raise

    async def _fetch_all_sources(
        self,
        email: str,
        domain: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fetch data from all sources in parallel.
        Enhanced to include PDL company enrichment for deeper company insights.

        Args:
            email: Email address
            domain: Company domain

        Returns:
            Dict mapping source name to response data
        """
        # Phase 1: Fetch person data and news in parallel
        person_tasks = [
            self._fetch_with_fallback("apollo", email, domain),
            self._fetch_with_fallback("pdl", email, domain),
            self._fetch_with_fallback("hunter", email, domain),
            self._fetch_with_fallback("gnews", email, domain),
            self._fetch_with_fallback("zoominfo", email, domain),
        ]

        results = await asyncio.gather(*person_tasks, return_exceptions=True)

        raw_data = {}
        source_names = ["apollo", "pdl", "hunter", "gnews", "zoominfo"]

        for source_name, result in zip(source_names, results):
            if isinstance(result, Exception):
                logger.warning(f"{source_name} failed: {result}")
                raw_data[source_name] = {"_error": str(result)}
            else:
                raw_data[source_name] = result

        # Phase 2: Fetch deep company data from PDL
        # This provides much richer company context
        try:
            pdl_api = self.apis.get("pdl")
            if pdl_api and hasattr(pdl_api, 'enrich_company'):
                logger.info(f"Fetching deep company enrichment for {domain}")
                company_data = await pdl_api.enrich_company(domain)
                raw_data["pdl_company"] = company_data
                if not company_data.get("_error"):
                    self.data_sources.append("pdl_company")
        except Exception as e:
            logger.warning(f"PDL company enrichment failed: {e}")
            raw_data["pdl_company"] = {"_error": str(e)}

        return raw_data

    async def _fetch_with_fallback(
        self,
        source: str,
        email: str,
        domain: str
    ) -> Dict[str, Any]:
        """
        Fetch from a single source with error handling.

        Args:
            source: Source name
            email: Email address
            domain: Company domain

        Returns:
            Response data or error dict
        """
        api = self.apis.get(source)
        if not api:
            return {"_error": f"Unknown source: {source}"}

        try:
            return await api.enrich(email, domain)
        except EnrichmentAPIError as e:
            logger.warning(f"{source} API error: {e}")
            return {"_error": str(e)}
        except Exception as e:
            logger.error(f"{source} unexpected error: {e}")
            return {"_error": str(e)}

    def _resolve_profile(
        self,
        email: str,
        domain: str,
        raw_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Apply resolution logic to normalize and merge profile data.

        Resolution rules:
        1. Higher priority sources win on conflicts
        2. Non-null values preferred over null
        3. Arrays are merged and deduplicated
        4. Numeric values averaged when conflicting

        Args:
            email: Email address
            domain: Company domain
            raw_data: Aggregated raw data from APIs

        Returns:
            Normalized profile dict
        """
        normalized = {}

        # Define field mappings from each source
        field_mappings = self._get_field_mappings()

        # Process each field
        for field, sources in field_mappings.items():
            value = self._resolve_field(field, sources, raw_data)
            if value is not None:
                normalized[field] = value

        # Email verification from Hunter
        hunter_data = raw_data.get("hunter", {})
        if hunter_data and not hunter_data.get("_error"):
            normalized["email_verified"] = hunter_data.get("status") == "valid"
            normalized["email_score"] = hunter_data.get("score")
            normalized["email_deliverable"] = hunter_data.get("result") == "deliverable"

        # Company context from GNews (enhanced with categories and themes)
        gnews_data = raw_data.get("gnews", {})
        if gnews_data and not gnews_data.get("_error"):
            normalized["company_context"] = gnews_data.get("answer")
            normalized["recent_news"] = gnews_data.get("results", [])
            normalized["news_themes"] = gnews_data.get("themes", [])
            normalized["news_sentiment"] = gnews_data.get("sentiment_indicators", {})
            normalized["news_by_category"] = gnews_data.get("categorized", {})

        # Deep company data from PDL Company API
        pdl_company = raw_data.get("pdl_company", {})
        if pdl_company and not pdl_company.get("_error"):
            normalized["company_summary"] = pdl_company.get("summary")
            normalized["company_headline"] = pdl_company.get("headline")
            normalized["company_type"] = pdl_company.get("type")
            normalized["company_tags"] = pdl_company.get("tags", [])
            normalized["total_funding"] = pdl_company.get("total_funding_raised")
            normalized["latest_funding_stage"] = pdl_company.get("latest_funding_stage")
            normalized["employee_growth_rate"] = pdl_company.get("employee_growth_rate")
            normalized["inferred_revenue"] = pdl_company.get("inferred_revenue")
            normalized["company_linkedin"] = pdl_company.get("linkedin_url")
            # Merge employee count if not already set
            if not normalized.get("employee_count") and pdl_company.get("employee_count"):
                normalized["employee_count"] = pdl_company.get("employee_count")

        return normalized

    def _get_field_mappings(self) -> Dict[str, List[Tuple[str, str]]]:
        """
        Define field mappings from source fields to normalized fields.
        Enhanced to include PDL company data for richer company insights.

        Returns:
            Dict mapping normalized field to list of (source, source_field) tuples
        """
        return {
            "first_name": [
                ("apollo", "first_name"),
                ("pdl", "first_name"),
            ],
            "last_name": [
                ("apollo", "last_name"),
                ("pdl", "last_name"),
            ],
            "full_name": [
                ("pdl", "full_name"),
            ],
            "title": [
                ("apollo", "title"),
                ("pdl", "job_title"),
            ],
            "company_name": [
                ("pdl_company", "name"),
                ("apollo", "company_name"),
                ("zoominfo", "company_name"),
                ("pdl", "job_company_name"),
            ],
            "company_display_name": [
                ("pdl_company", "display_name"),
            ],
            "industry": [
                ("pdl_company", "industry"),
                ("apollo", "industry"),
                ("zoominfo", "industry"),
                ("pdl", "job_company_industry"),
            ],
            "company_size": [
                ("pdl_company", "size"),
                ("apollo", "company_size"),
                ("pdl", "job_company_size"),
            ],
            "employee_count": [
                ("pdl_company", "employee_count"),
                ("zoominfo", "employee_count"),
            ],
            "employee_count_range": [
                ("pdl_company", "employee_count_range"),
            ],
            "linkedin_url": [
                ("apollo", "linkedin_url"),
                ("pdl", "linkedin_url"),
            ],
            "city": [
                ("pdl_company", "locality"),
                ("apollo", "city"),
                ("zoominfo", "city"),
                ("pdl", "location_locality"),
            ],
            "state": [
                ("pdl_company", "region"),
                ("apollo", "state"),
                ("zoominfo", "state"),
                ("pdl", "location_region"),
            ],
            "country": [
                ("pdl_company", "country"),
                ("apollo", "country"),
                ("zoominfo", "country"),
                ("pdl", "location_country"),
            ],
            "seniority": [
                ("apollo", "seniority"),
            ],
            "skills": [
                ("pdl", "skills"),
            ],
            "interests": [
                ("pdl", "interests"),
            ],
            "experience": [
                ("pdl", "experience"),
            ],
            "company_description": [
                ("pdl_company", "summary"),
                ("zoominfo", "description"),
            ],
            "founded_year": [
                ("pdl_company", "founded"),
                ("zoominfo", "founded_year"),
            ],
            "company_type": [
                ("pdl_company", "type"),
            ],
            "ticker": [
                ("pdl_company", "ticker"),
            ],
            "naics_codes": [
                ("pdl_company", "naics"),
            ],
            "sic_codes": [
                ("pdl_company", "sic"),
            ],
        }

    def _resolve_field(
        self,
        field: str,
        sources: List[Tuple[str, str]],
        raw_data: Dict[str, Dict[str, Any]]
    ) -> Any:
        """
        Resolve a single field value from multiple sources.

        Uses source priority to pick the best value.

        Args:
            field: Normalized field name
            sources: List of (source, source_field) tuples
            raw_data: Raw data from all sources

        Returns:
            Resolved field value or None
        """
        candidates = []

        for source_name, source_field in sources:
            source_data = raw_data.get(source_name, {})
            if source_data and not source_data.get("_error"):
                value = source_data.get(source_field)
                if value is not None and value != "":
                    priority = SOURCE_PRIORITY.get(source_name, 0)
                    candidates.append((priority, value))

        if not candidates:
            return None

        # Sort by priority (descending) and return highest priority value
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    def _calculate_quality_score(self, raw_data: Dict[str, Dict[str, Any]]) -> float:
        """
        Calculate data quality score based on source coverage and data completeness.

        Args:
            raw_data: Raw data from all sources

        Returns:
            Quality score between 0.0 and 1.0
        """
        # Total sources now includes pdl_company
        total_sources = len(self.apis) + 1  # +1 for pdl_company
        successful_sources = sum(
            1 for data in raw_data.values()
            if data and not data.get("_error") and not data.get("_mock")
        )

        # Base score from source coverage
        coverage_score = successful_sources / total_sources

        # Bonus for high-priority sources
        priority_bonus = 0
        if raw_data.get("apollo") and not raw_data["apollo"].get("_error"):
            priority_bonus += 0.1
        if raw_data.get("zoominfo") and not raw_data["zoominfo"].get("_error"):
            priority_bonus += 0.1
        if raw_data.get("pdl_company") and not raw_data["pdl_company"].get("_error"):
            priority_bonus += 0.1

        # Bonus for rich news data
        gnews_data = raw_data.get("gnews", {})
        if gnews_data and not gnews_data.get("_error"):
            news_count = gnews_data.get("result_count", 0)
            if news_count >= 5:
                priority_bonus += 0.05
            if gnews_data.get("themes"):
                priority_bonus += 0.05

        # Cap at 1.0
        return min(1.0, coverage_score + priority_bonus)

    async def enrich_batch(
        self,
        emails: List[str],
        concurrency: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Enrich multiple emails with controlled concurrency.

        Args:
            emails: List of email addresses
            concurrency: Max concurrent enrichments

        Returns:
            List of enrichment results
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def enrich_with_semaphore(email: str) -> Dict[str, Any]:
            async with semaphore:
                try:
                    return await self.enrich(email)
                except Exception as e:
                    logger.error(f"Batch enrichment failed for {email}: {e}")
                    return {"email": email, "_error": str(e)}

        return await asyncio.gather(*[
            enrich_with_semaphore(email) for email in emails
        ])
