"""
Supabase client wrapper for RAD enrichment data persistence.
Abstracts database operations: raw_data, staging_normalized, finalize_data tables.
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

from supabase import create_client, Client
from app.config import settings

logger = logging.getLogger(__name__)


class SupabaseClient:
    """
    Wrapper around Supabase client to handle RAD enrichment data.
    Tables (to be created via migrations):
      - raw_data (email, source, payload, fetched_at)
      - staging_normalized (email, normalized_fields, status, created_at)
      - finalize_data (email, normalized_data, intro, cta, resolved_at)
    """

    def __init__(self):
        """Initialize Supabase client."""
        self.client: Client = create_client(
            supabase_url=settings.SUPABASE_URL,
            supabase_key=settings.SUPABASE_KEY
        )
        logger.info("Supabase client initialized")

    # ========================================================================
    # RAW_DATA TABLE (External API responses)
    # ========================================================================

    def store_raw_data(
        self,
        email: str,
        source: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Store raw API response for an email/source.
        
        Args:
            email: User email
            source: API source (apollo, pdl, hunter, gnews)
            payload: Raw response data
            
        Returns:
            Inserted record
        """
        data = {
            "email": email,
            "source": source,
            "payload": payload,
            "fetched_at": datetime.utcnow().isoformat()
        }
        
        try:
            result = self.client.table("raw_data").insert(data).execute()
            logger.info(f"Stored raw_data for {email} from {source}")
            return result.data[0] if result.data else data
        except Exception as e:
            logger.error(f"Error storing raw_data for {email}: {e}")
            raise

    def get_raw_data_for_email(self, email: str) -> List[Dict[str, Any]]:
        """
        Retrieve all raw data records for a given email.
        
        Args:
            email: User email
            
        Returns:
            List of raw_data records
        """
        try:
            result = self.client.table("raw_data").select("*").eq("email", email).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error fetching raw_data for {email}: {e}")
            return []

    # ========================================================================
    # STAGING_NORMALIZED TABLE (Resolution in progress)
    # ========================================================================

    def create_staging_record(
        self,
        email: str,
        normalized_fields: Dict[str, Any],
        status: str = "resolving"
    ) -> Dict[str, Any]:
        """
        Create a staging_normalized record for an email.
        Used during the enrichment process to track progress.
        
        Args:
            email: User email
            normalized_fields: Partial normalized profile
            status: 'resolving' or 'ready'
            
        Returns:
            Inserted record
        """
        data = {
            "email": email,
            "normalized_fields": normalized_fields,
            "status": status,
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            result = self.client.table("staging_normalized").insert(data).execute()
            logger.info(f"Created staging record for {email} with status={status}")
            return result.data[0] if result.data else data
        except Exception as e:
            logger.error(f"Error creating staging record for {email}: {e}")
            raise

    def update_staging_record(
        self,
        email: str,
        normalized_fields: Dict[str, Any],
        status: str = "ready"
    ) -> Dict[str, Any]:
        """
        Update existing staging_normalized record.
        
        Args:
            email: User email
            normalized_fields: Updated normalized profile
            status: New status
            
        Returns:
            Updated record
        """
        data = {
            "normalized_fields": normalized_fields,
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        try:
            result = self.client.table("staging_normalized").update(data).eq("email", email).execute()
            logger.info(f"Updated staging record for {email}")
            return result.data[0] if result.data else data
        except Exception as e:
            logger.error(f"Error updating staging record for {email}: {e}")
            raise

    # ========================================================================
    # FINALIZE_DATA TABLE (Final output for personalization)
    # ========================================================================

    def write_finalize_data(
        self,
        email: str,
        normalized_data: Dict[str, Any],
        intro: Optional[str] = None,
        cta: Optional[str] = None,
        data_sources: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Write finalized profile + personalization content.
        This is the table consumed by the frontend for ebook rendering.
        
        Args:
            email: User email
            normalized_data: Complete normalized profile
            intro: LLM-generated intro hook (optional in alpha)
            cta: LLM-generated CTA (optional in alpha)
            data_sources: List of APIs that contributed to this record
            
        Returns:
            Inserted record
        """
        data = {
            "email": email,
            "normalized_data": normalized_data,
            "personalization_intro": intro,
            "personalization_cta": cta,
            "data_sources": data_sources or [],
            "resolved_at": datetime.utcnow().isoformat()
        }
        
        try:
            result = self.client.table("finalize_data").insert(data).execute()
            logger.info(f"Wrote finalize_data for {email}")
            return result.data[0] if result.data else data
        except Exception as e:
            logger.error(f"Error writing finalize_data for {email}: {e}")
            raise

    def get_finalize_data(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve finalized profile for a given email.
        
        Args:
            email: User email
            
        Returns:
            finalize_data record, or None if not found
        """
        try:
            result = self.client.table("finalize_data").select("*").eq("email", email).order("resolved_at", desc=True).limit(1).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error fetching finalize_data for {email}: {e}")
            return None

    # ========================================================================
    # HEALTH CHECK
    # ========================================================================

    def health_check(self) -> bool:
        """
        Verify Supabase connection is alive.
        
        Returns:
            True if connection is healthy
        """
        try:
            # Try a simple query to verify connection
            self.client.table("finalize_data").select("*").limit(1).execute()
            logger.info("Supabase health check passed")
            return True
        except Exception as e:
            logger.error(f"Supabase health check failed: {e}")
            return False


# Global instance (lazy-loaded in routes)
_supabase_client: Optional[SupabaseClient] = None


def get_supabase_client() -> SupabaseClient:
    """Get or create the global Supabase client."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = SupabaseClient()
    return _supabase_client
