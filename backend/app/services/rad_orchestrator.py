"""
RAD Orchestrator: Coordinates enrichment workflow.
- Fetches data from external APIs (mocked in alpha)
- Applies resolution logic (council of LLMs + fallback)
- Writes normalized output to Supabase
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
import httpx

from app.config import settings
from app.services.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)


class RADOrchestrator:
    """
    Orchestrates the full enrichment pipeline for a given email.
    Alpha version: Mocked external APIs, placeholder resolution logic.
    """

    def __init__(self, supabase_client: SupabaseClient):
        """
        Initialize orchestrator.
        
        Args:
            supabase_client: Supabase data access layer
        """
        self.supabase = supabase_client
        self.data_sources: List[str] = []

    async def enrich(self, email: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute full enrichment pipeline for an email.
        Alpha flow:
          1. Fetch raw data from external APIs (mocked)
          2. Apply resolution logic
          3. Generate placeholder personalization
          4. Write finalize_data
        
        Args:
            email: Email address to enrich
            domain: Company domain (optional)
            
        Returns:
            Finalized profile dict with metadata
        """
        try:
            logger.info(f"Starting enrichment for {email}")
            
            # Extract domain from email if not provided
            if not domain:
                domain = email.split("@")[1]
            
            # Step 1: Fetch raw data from external APIs (mocked)
            raw_data = await self._fetch_raw_data(email, domain)
            
            # Step 2: Apply resolution logic
            normalized = self._resolve_profile(email, raw_data)
            
            # Step 3: Write to finalize_data (personalization added later by LLM service)
            finalized = self.supabase.write_finalize_data(
                email=email,
                normalized_data=normalized,
                intro=None,  # To be filled by LLM service
                cta=None,    # To be filled by LLM service
                data_sources=self.data_sources
            )
            
            logger.info(f"Enrichment complete for {email}: {len(self.data_sources)} sources")
            return finalized
            
        except Exception as e:
            logger.error(f"Enrichment failed for {email}: {e}")
            raise

    async def _fetch_raw_data(
        self,
        email: str,
        domain: str
    ) -> Dict[str, Any]:
        """
        Fetch raw data from external APIs.
        Alpha: Mocked responses; real API calls added later.
        
        Args:
            email: Email address
            domain: Company domain
            
        Returns:
            Aggregated raw data
        """
        raw_data = {}
        
        # Mock Apollo API call
        apollo_mock = await self._mock_apollo_fetch(email, domain)
        if apollo_mock:
            raw_data["apollo"] = apollo_mock
            self.data_sources.append("apollo")
            self.supabase.store_raw_data(email, "apollo", apollo_mock)
        
        # Mock People Data Labs call
        pdl_mock = await self._mock_pdl_fetch(email)
        if pdl_mock:
            raw_data["pdl"] = pdl_mock
            self.data_sources.append("pdl")
            self.supabase.store_raw_data(email, "pdl", pdl_mock)
        
        # Mock Hunter.io call
        hunter_mock = await self._mock_hunter_fetch(email)
        if hunter_mock:
            raw_data["hunter"] = hunter_mock
            self.data_sources.append("hunter")
            self.supabase.store_raw_data(email, "hunter", hunter_mock)
        
        # Mock GNews call (company news)
        gnews_mock = await self._mock_gnews_fetch(domain)
        if gnews_mock:
            raw_data["gnews"] = gnews_mock
            self.data_sources.append("gnews")
            self.supabase.store_raw_data(email, "gnews", gnews_mock)
        
        logger.info(f"Fetched raw data from {len(self.data_sources)} sources for {email}")
        return raw_data

    async def _mock_apollo_fetch(self, email: str, domain: str) -> Dict[str, Any]:
        """
        Mock Apollo API response.
        Real implementation: Use httpx to call Apollo with APOLLO_API_KEY.
        """
        # Alpha: Return synthetic data
        return {
            "email": email,
            "domain": domain,
            "company_name": f"Company from {domain}",
            "first_name": "John",
            "last_name": "Doe",
            "title": "VP of Sales",
            "linkedin_url": f"https://linkedin.com/in/{email.split('@')[0]}"
        }

    async def _mock_pdl_fetch(self, email: str) -> Dict[str, Any]:
        """Mock People Data Labs response."""
        # Alpha: Return synthetic data
        return {
            "email": email,
            "country": "US",
            "industry": "SaaS",
            "company_size": "100-500",
            "company_annual_revenue": "10M-50M"
        }

    async def _mock_hunter_fetch(self, email: str) -> Dict[str, Any]:
        """Mock Hunter.io response."""
        # Alpha: Return synthetic data
        return {
            "email": email,
            "verification_status": "verified",
            "email_provider": False  # Not a generic provider
        }

    async def _mock_gnews_fetch(self, domain: str) -> Dict[str, Any]:
        """Mock GNews response (company news)."""
        # Alpha: Return synthetic data
        return {
            "domain": domain,
            "recent_news_count": 5,
            "latest_news_date": datetime.utcnow().isoformat(),
            "news_summary": "Recent company news placeholder"
        }

    def _resolve_profile(
        self,
        email: str,
        raw_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply resolution logic to normalize profile.
        Alpha: Simple merge of raw_data; real logic (council of LLMs) added later.
        
        Args:
            email: Email address
            raw_data: Aggregated raw data from APIs
            
        Returns:
            Normalized profile dict
        """
        # Start with Apollo data (trust it most)
        normalized = raw_data.get("apollo", {}).copy()
        
        # Merge PDL data
        pdl_data = raw_data.get("pdl", {})
        if pdl_data:
            if "country" not in normalized:
                normalized["country"] = pdl_data.get("country")
            if "industry" not in normalized:
                normalized["industry"] = pdl_data.get("industry")
            if "company_size" not in normalized:
                normalized["company_size"] = pdl_data.get("company_size")
        
        # Add Hunter verification
        hunter_data = raw_data.get("hunter", {})
        if hunter_data:
            normalized["email_verified"] = hunter_data.get("verification_status") == "verified"
        
        # Add news info
        gnews_data = raw_data.get("gnews", {})
        if gnews_data:
            normalized["recent_news_count"] = gnews_data.get("recent_news_count", 0)
        
        # Add metadata
        normalized["email"] = email
        normalized["resolved_at"] = datetime.utcnow().isoformat()
        normalized["data_sources"] = self.data_sources
        
        # Placeholder data quality score
        normalized["data_quality_score"] = min(1.0, len(self.data_sources) / 4.0)
        
        return normalized
