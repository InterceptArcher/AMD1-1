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

# Canonical industry normalization map
# Keys are lowercase substrings to match; values are canonical industry names
INDUSTRY_NORMALIZATION = {
    # Technology
    "information technology": "technology",
    "software": "technology",
    "internet": "technology",
    "computer": "technology",
    "saas": "technology",
    "it services": "technology",
    # Financial Services
    "financial": "financial_services",
    "banking": "financial_services",
    "insurance": "financial_services",
    "investment": "financial_services",
    "capital markets": "financial_services",
    "fintech": "financial_services",
    # Healthcare
    "healthcare": "healthcare",
    "health care": "healthcare",
    "hospital": "healthcare",
    "medical": "healthcare",
    "pharmaceutical": "healthcare",
    "pharma": "healthcare",
    "biotech": "healthcare",
    "life science": "healthcare",
    # Manufacturing
    "manufacturing": "manufacturing",
    "automotive": "manufacturing",
    "industrial": "manufacturing",
    "aerospace": "manufacturing",
    # Retail
    "retail": "retail",
    "e-commerce": "retail",
    "ecommerce": "retail",
    "consumer goods": "retail",
    # Energy
    "energy": "energy",
    "oil": "energy",
    "utilities": "energy",
    "renewable": "energy",
    # Telecommunications
    "telecom": "telecommunications",
    "wireless": "telecommunications",
    "communications": "telecommunications",
    # Media
    "media": "media",
    "entertainment": "media",
    "publishing": "media",
    "broadcast": "media",
    # Government
    "government": "government",
    "federal": "government",
    "public sector": "government",
    "defense": "government",
    "military": "government",
    # Education
    "education": "education",
    "university": "education",
    "academic": "education",
    "higher education": "education",
    # Professional Services
    "consulting": "professional_services",
    "professional service": "professional_services",
    "legal": "professional_services",
    "accounting": "professional_services",
}

# Field importance tiers for completeness report
CRITICAL_FIELDS = ["company_name", "industry", "title", "employee_count"]
IMPORTANT_FIELDS = ["company_summary", "founded_year", "seniority", "recent_news"]
NICE_TO_HAVE_FIELDS = [
    "skills", "employee_growth_rate", "total_funding",
    "latest_funding_stage", "company_tags", "news_themes",
]


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

            # Step 2: Store raw data in Supabase (non-fatal - continue even if storage fails)
            for source, data in raw_data.items():
                if data and not data.get("_error"):
                    try:
                        self.supabase.store_raw_data(email, source, data)
                    except Exception as storage_err:
                        logger.warning(f"Failed to store raw data for {source}: {storage_err} - continuing anyway")
                    self.data_sources.append(source)

            # Step 3: Apply resolution logic
            normalized = self._resolve_profile(email, domain, raw_data)

            # Add metadata
            normalized["email"] = email
            normalized["domain"] = domain
            normalized["resolved_at"] = datetime.utcnow().isoformat()
            normalized["data_sources"] = self.data_sources
            normalized["data_quality_score"] = self._calculate_quality_score(raw_data)
            normalized["completeness_report"] = self._build_completeness_report(normalized)

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
        Fetch data from all sources in two phases.

        Phase 1 (parallel): Apollo + PDL(person) + Hunter + ZoomInfo + PDL Company
          - All only need email/domain, no interdependency
        Phase 2: GNews using resolved company name from Phase 1
          - Uses real company name for better search results

        Args:
            email: Email address
            domain: Company domain

        Returns:
            Dict mapping source name to response data
        """
        # Phase 1: Person data + company data in parallel
        phase1_tasks = [
            self._fetch_with_fallback("apollo", email, domain),
            self._fetch_with_fallback("pdl", email, domain),
            self._fetch_with_fallback("hunter", email, domain),
            self._fetch_with_fallback("zoominfo", email, domain),
            self._fetch_pdl_company(domain),
        ]

        results = await asyncio.gather(*phase1_tasks, return_exceptions=True)

        raw_data = {}
        source_names = ["apollo", "pdl", "hunter", "zoominfo", "pdl_company"]

        for source_name, result in zip(source_names, results):
            if isinstance(result, Exception):
                logger.warning(f"{source_name} failed: {result}")
                raw_data[source_name] = {"_error": str(result)}
            else:
                raw_data[source_name] = result

        # Phase 2: GNews with resolved company name from Phase 1
        resolved_name = self._resolve_company_name(raw_data, domain)
        logger.info(f"Resolved company name for GNews: '{resolved_name}' (domain: {domain})")
        raw_data["gnews"] = await self._fetch_gnews_with_name(email, domain, resolved_name)

        return raw_data

    async def _fetch_pdl_company(self, domain: str) -> Dict[str, Any]:
        """Fetch PDL Company data in Phase 1 (parallel with person APIs)."""
        try:
            pdl_api = self.apis.get("pdl")
            if pdl_api and hasattr(pdl_api, 'enrich_company'):
                return await pdl_api.enrich_company(domain)
            return {"_error": "PDL company enrichment not available"}
        except Exception as e:
            logger.warning(f"PDL company enrichment failed: {e}")
            return {"_error": str(e)}

    def _resolve_company_name(
        self,
        raw_data: Dict[str, Dict[str, Any]],
        domain: str
    ) -> str:
        """
        Resolve the best company name from Phase 1 results.
        Priority: PDL Company display_name > PDL Company name > Apollo >
                  ZoomInfo > PDL person > domain fallback.
        Skips mock data sources.
        """
        # Prefer display_name (human-readable, e.g., "Google" not "Alphabet Inc.")
        pdl_company = raw_data.get("pdl_company", {})
        if pdl_company and not pdl_company.get("_error") and not pdl_company.get("_mock"):
            display = pdl_company.get("display_name")
            if display:
                return display
            name = pdl_company.get("name")
            if name:
                return name

        # Apollo
        apollo = raw_data.get("apollo", {})
        if apollo and not apollo.get("_error") and not apollo.get("_mock"):
            name = apollo.get("company_name")
            if name:
                return name

        # ZoomInfo
        zoominfo = raw_data.get("zoominfo", {})
        if zoominfo and not zoominfo.get("_error") and not zoominfo.get("_mock"):
            name = zoominfo.get("company_name")
            if name:
                return name

        # PDL person
        pdl = raw_data.get("pdl", {})
        if pdl and not pdl.get("_error") and not pdl.get("_mock"):
            name = pdl.get("job_company_name")
            if name:
                return name

        # Fallback: derive from domain with title case
        return domain.split(".")[0].title()

    async def _fetch_gnews_with_name(
        self,
        email: str,
        domain: str,
        company_name: str
    ) -> Dict[str, Any]:
        """Fetch GNews using the resolved company name instead of domain extraction."""
        gnews_api = self.apis.get("gnews")
        if not gnews_api:
            return {"_error": "GNews API not available"}
        try:
            return await gnews_api.enrich_with_name(email, domain, company_name)
        except EnrichmentAPIError as e:
            logger.warning(f"GNews API error: {e}")
            return {"_error": str(e)}
        except Exception as e:
            logger.error(f"GNews unexpected error: {e}")
            return {"_error": str(e)}

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

        # Normalize industry to canonical form
        if normalized.get("industry"):
            normalized["industry_raw"] = normalized["industry"]
            normalized["industry"] = self._normalize_industry(normalized["industry"])

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

        # Fallback: estimate employee_count from range strings if still missing
        # This prevents mock data (e.g., ZoomInfo mock = 100) from being used
        if not normalized.get("employee_count"):
            # Try employee_count_range first (e.g., "1001-5000")
            range_str = normalized.get("employee_count_range")
            if range_str:
                estimated = self._estimate_employee_count_from_range(range_str)
                if estimated:
                    normalized["employee_count"] = estimated
                    normalized["employee_count_estimated"] = True
                    logger.info(f"Estimated employee_count={estimated} from range '{range_str}'")

            # Fallback to company_size (e.g., "51-200")
            if not normalized.get("employee_count"):
                size_str = normalized.get("company_size")
                if size_str:
                    estimated = self._estimate_employee_count_from_range(size_str)
                    if estimated:
                        normalized["employee_count"] = estimated
                        normalized["employee_count_estimated"] = True
                        logger.info(f"Estimated employee_count={estimated} from company_size '{size_str}'")

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
                ("pdl_company", "display_name"),
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
            "departments": [
                ("apollo", "departments"),
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
            # Skip sources with errors or mock data (mock data has hardcoded values)
            if source_data and not source_data.get("_error") and not source_data.get("_mock"):
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

    def _estimate_employee_count_from_range(self, range_str: str) -> Optional[int]:
        """
        Parse an employee count range string and return an estimated count.

        Handles formats like:
        - "1001-5000" -> 3000 (midpoint)
        - "51-200" -> 125 (midpoint)
        - "10001+" -> 15000 (estimate for open-ended)
        - "1-10" -> 5 (midpoint)

        Args:
            range_str: Employee count range string

        Returns:
            Estimated employee count or None if unparseable
        """
        if not range_str or not isinstance(range_str, str):
            return None

        # Clean up the string
        range_str = range_str.strip().replace(",", "").replace(" ", "")

        # Handle open-ended ranges like "10001+" or "5000+"
        if range_str.endswith("+"):
            try:
                base = int(range_str[:-1])
                # Estimate 1.5x the base for open-ended ranges
                return int(base * 1.5)
            except ValueError:
                return None

        # Handle range formats like "1001-5000"
        if "-" in range_str:
            parts = range_str.split("-")
            if len(parts) == 2:
                try:
                    low = int(parts[0])
                    high = int(parts[1])
                    # Return midpoint
                    return (low + high) // 2
                except ValueError:
                    return None

        # Try parsing as a single number
        try:
            return int(range_str)
        except ValueError:
            return None

    def _normalize_industry(self, raw_industry: Optional[str]) -> Optional[str]:
        """
        Normalize raw industry strings from various APIs to canonical form.
        Uses substring matching against INDUSTRY_NORMALIZATION map.

        Args:
            raw_industry: Raw industry string (e.g., "information technology and services")

        Returns:
            Canonical industry string (e.g., "technology") or lowercased original
        """
        if not raw_industry or not raw_industry.strip():
            return None

        raw_lower = raw_industry.lower().strip()

        # Exact match first
        if raw_lower in INDUSTRY_NORMALIZATION:
            return INDUSTRY_NORMALIZATION[raw_lower]

        # Substring match (longer patterns first for specificity)
        sorted_keys = sorted(INDUSTRY_NORMALIZATION.keys(), key=len, reverse=True)
        for pattern in sorted_keys:
            if pattern in raw_lower:
                return INDUSTRY_NORMALIZATION[pattern]

        # No match — return cleaned original
        return raw_lower.replace(" ", "_").replace("-", "_")

    def _build_completeness_report(
        self, normalized: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build a structured completeness report for the enriched profile.
        Weighted scoring: critical fields count 3x, important 2x, nice-to-have 1x.

        Returns:
            Dict with score, field lists, and coverage summary
        """
        present = []
        missing_critical = []
        missing_important = []
        missing_nice = []

        for field in CRITICAL_FIELDS:
            val = normalized.get(field)
            if val and val != "" and val != []:
                present.append(field)
            else:
                missing_critical.append(field)

        for field in IMPORTANT_FIELDS:
            val = normalized.get(field)
            if val and val != "" and val != []:
                present.append(field)
            else:
                missing_important.append(field)

        for field in NICE_TO_HAVE_FIELDS:
            val = normalized.get(field)
            if val and val != "" and val != []:
                present.append(field)
            else:
                missing_nice.append(field)

        total_fields = len(CRITICAL_FIELDS) + len(IMPORTANT_FIELDS) + len(NICE_TO_HAVE_FIELDS)
        weighted_total = len(CRITICAL_FIELDS) * 3 + len(IMPORTANT_FIELDS) * 2 + len(NICE_TO_HAVE_FIELDS)
        weighted_present = (
            (len(CRITICAL_FIELDS) - len(missing_critical)) * 3
            + (len(IMPORTANT_FIELDS) - len(missing_important)) * 2
            + (len(NICE_TO_HAVE_FIELDS) - len(missing_nice))
        )

        score = round(weighted_present / weighted_total, 2) if weighted_total > 0 else 0

        return {
            "score": score,
            "present": present,
            "missing_critical": missing_critical,
            "missing_important": missing_important,
            "missing_nice": missing_nice,
            "field_coverage": f"{len(present)}/{total_fields}",
        }

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
