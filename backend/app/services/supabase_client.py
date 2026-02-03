"""
Supabase client wrapper for RAD enrichment data persistence.
Abstracts database operations for:
  - raw_data, staging_normalized, finalize_data (enrichment pipeline)
  - personalization_jobs, personalization_outputs (job tracking)
  - pdf_deliveries (PDF generation tracking)
"""

import json
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Check if we're in mock mode (for local testing without real Supabase)
MOCK_MODE = os.environ.get("MOCK_SUPABASE", "false").lower() == "true" or \
            settings.SUPABASE_URL == "http://localhost:54321" or \
            "mock" in settings.SUPABASE_KEY.lower()


class SupabaseClient:
    """
    Wrapper around Supabase client to handle RAD enrichment data.
    Tables (to be created via migrations):
      - raw_data (email, source, payload, fetched_at)
      - staging_normalized (email, normalized_fields, status, created_at)
      - finalize_data (email, normalized_data, intro, cta, resolved_at)

    Supports mock mode for local testing without real Supabase credentials.
    """

    def __init__(self):
        """Initialize Supabase client (or mock storage for local testing)."""
        self.mock_mode = MOCK_MODE

        if self.mock_mode:
            logger.info("Supabase client initialized in MOCK MODE (local testing)")
            # In-memory storage for mock mode
            self._mock_raw_data: List[Dict[str, Any]] = []
            self._mock_staging: List[Dict[str, Any]] = []
            self._mock_finalize: List[Dict[str, Any]] = []
            self._mock_jobs: List[Dict[str, Any]] = []
            self._mock_outputs: List[Dict[str, Any]] = []
            self._mock_pdfs: List[Dict[str, Any]] = []
            self.client = None
        else:
            from supabase import create_client, Client
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
            "id": str(uuid.uuid4()),
            "email": email,
            "source": source,
            "payload": payload,
            "fetched_at": datetime.utcnow().isoformat()
        }

        if self.mock_mode:
            self._mock_raw_data.append(data)
            logger.info(f"[MOCK] Stored raw_data for {email} from {source}")
            return data

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
        if self.mock_mode:
            return [r for r in self._mock_raw_data if r["email"] == email]

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

        if self.mock_mode:
            self._mock_staging.append(data)
            logger.info(f"[MOCK] Created staging record for {email}")
            return data

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

        if self.mock_mode:
            for record in self._mock_staging:
                if record["email"] == email:
                    record.update(data)
                    logger.info(f"[MOCK] Updated staging record for {email}")
                    return record
            return data

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

        if self.mock_mode:
            # Remove any existing record for this email
            self._mock_finalize = [r for r in self._mock_finalize if r["email"] != email]
            self._mock_finalize.append(data)
            logger.info(f"[MOCK] Wrote finalize_data for {email}")
            return data

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
        if self.mock_mode:
            records = [r for r in self._mock_finalize if r["email"] == email]
            return records[-1] if records else None

        try:
            result = self.client.table("finalize_data").select("*").eq("email", email).order("resolved_at", desc=True).limit(1).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error fetching finalize_data for {email}: {e}")
            return None

    def upsert_finalize_data(
        self,
        email: str,
        normalized_data: Dict[str, Any],
        intro: Optional[str] = None,
        cta: Optional[str] = None,
        data_sources: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Upsert finalized profile (update if exists, insert if not).

        Args:
            email: User email
            normalized_data: Complete normalized profile
            intro: LLM-generated intro hook
            cta: LLM-generated CTA
            data_sources: List of APIs that contributed

        Returns:
            Upserted record
        """
        data = {
            "email": email,
            "normalized_data": normalized_data,
            "personalization_intro": intro,
            "personalization_cta": cta,
            "data_sources": data_sources or [],
            "resolved_at": datetime.utcnow().isoformat()
        }

        if self.mock_mode:
            # Remove existing and add new
            self._mock_finalize = [r for r in self._mock_finalize if r["email"] != email]
            self._mock_finalize.append(data)
            logger.info(f"[MOCK] Upserted finalize_data for {email}")
            return data

        try:
            result = self.client.table("finalize_data").upsert(
                data,
                on_conflict="email"
            ).execute()
            logger.info(f"Upserted finalize_data for {email}")
            return result.data[0] if result.data else data
        except Exception as e:
            logger.error(f"Error upserting finalize_data for {email}: {e}")
            raise

    # ========================================================================
    # PERSONALIZATION_JOBS TABLE (Job tracking)
    # ========================================================================

    def create_job(
        self,
        email: str,
        domain: Optional[str] = None,
        cta: Optional[str] = None,
        persona: Optional[str] = None,
        buyer_stage: Optional[str] = None,
        company_name: Optional[str] = None,
        industry: Optional[str] = None,
        company_size: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new personalization job.

        Args:
            email: User email
            domain: Company domain
            cta: Call-to-action type
            persona: Inferred persona
            buyer_stage: Buyer journey stage
            company_name: Company name
            industry: Industry sector
            company_size: Company size range

        Returns:
            Created job record with id
        """
        job_id = str(uuid.uuid4())
        data = {
            "id": job_id,
            "email": email,
            "domain": domain,
            "cta": cta,
            "persona": persona,
            "buyer_stage": buyer_stage,
            "company_name": company_name,
            "industry": industry,
            "company_size": company_size,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }

        if self.mock_mode:
            self._mock_jobs.append(data)
            logger.info(f"[MOCK] Created job {job_id} for {email}")
            return data

        try:
            result = self.client.table("personalization_jobs").insert(data).execute()
            logger.info(f"Created job for {email}")
            return result.data[0] if result.data else data
        except Exception as e:
            logger.error(f"Error creating job for {email}: {e}")
            raise

    def update_job_status(
        self,
        job_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update job status.

        Args:
            job_id: Job ID
            status: New status (pending, processing, completed, failed)
            error_message: Error message if failed

        Returns:
            Updated job record
        """
        data = {"status": status}

        if status == "processing":
            data["started_at"] = datetime.utcnow().isoformat()
        elif status in ("completed", "failed"):
            data["completed_at"] = datetime.utcnow().isoformat()

        if error_message:
            data["error_message"] = error_message

        if self.mock_mode:
            for job in self._mock_jobs:
                if job["id"] == job_id:
                    job.update(data)
                    logger.info(f"[MOCK] Updated job {job_id} status to {status}")
                    return job
            return data

        try:
            result = self.client.table("personalization_jobs").update(data).eq("id", job_id).execute()
            logger.info(f"Updated job {job_id} status to {status}")
            return result.data[0] if result.data else data
        except Exception as e:
            logger.error(f"Error updating job {job_id}: {e}")
            raise

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job by ID.

        Args:
            job_id: Job ID

        Returns:
            Job record or None
        """
        if self.mock_mode:
            for job in self._mock_jobs:
                if job["id"] == job_id:
                    return job
            return None

        try:
            result = self.client.table("personalization_jobs").select("*").eq("id", job_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error fetching job {job_id}: {e}")
            return None

    def get_pending_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get pending jobs for processing.

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List of pending job records
        """
        if self.mock_mode:
            pending = [j for j in self._mock_jobs if j["status"] == "pending"]
            return pending[:limit]

        try:
            result = self.client.table("personalization_jobs").select("*").eq(
                "status", "pending"
            ).order("created_at").limit(limit).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error fetching pending jobs: {e}")
            return []

    # ========================================================================
    # PERSONALIZATION_OUTPUTS TABLE (LLM outputs)
    # ========================================================================

    def store_personalization_output(
        self,
        job_id: int,
        output_json: Dict[str, Any],
        intro_hook: Optional[str] = None,
        cta: Optional[str] = None,
        model_used: Optional[str] = None,
        tokens_used: Optional[int] = None,
        latency_ms: Optional[int] = None,
        compliance_passed: bool = True,
        compliance_issues: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Store LLM personalization output.

        Args:
            job_id: Associated job ID
            output_json: Full LLM response
            intro_hook: Extracted intro hook
            cta: Extracted CTA
            model_used: LLM model name
            tokens_used: Total tokens consumed
            latency_ms: LLM call latency
            compliance_passed: Whether output passed compliance
            compliance_issues: List of compliance issues if any

        Returns:
            Stored output record
        """
        data = {
            "job_id": job_id,
            "output_json": output_json,
            "intro_hook": intro_hook,
            "cta": cta,
            "model_used": model_used,
            "tokens_used": tokens_used,
            "latency_ms": latency_ms,
            "compliance_passed": compliance_passed,
            "compliance_issues": compliance_issues or [],
            "created_at": datetime.utcnow().isoformat()
        }

        if self.mock_mode:
            self._mock_outputs.append(data)
            logger.info(f"[MOCK] Stored personalization output for job {job_id}")
            return data

        try:
            result = self.client.table("personalization_outputs").insert(data).execute()
            logger.info(f"Stored personalization output for job {job_id}")
            return result.data[0] if result.data else data
        except Exception as e:
            logger.error(f"Error storing output for job {job_id}: {e}")
            raise

    def get_output_for_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get personalization output for a job.

        Args:
            job_id: Job ID

        Returns:
            Output record or None
        """
        if self.mock_mode:
            outputs = [o for o in self._mock_outputs if o["job_id"] == job_id]
            return outputs[-1] if outputs else None

        try:
            result = self.client.table("personalization_outputs").select("*").eq(
                "job_id", job_id
            ).order("created_at", desc=True).limit(1).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error fetching output for job {job_id}: {e}")
            return None

    # ========================================================================
    # PDF_DELIVERIES TABLE (PDF tracking)
    # ========================================================================

    def create_pdf_delivery(
        self,
        job_id: str,
        pdf_url: Optional[str] = None,
        storage_path: Optional[str] = None,
        file_size_bytes: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create PDF delivery record.

        Args:
            job_id: Associated job ID
            pdf_url: Public URL to PDF
            storage_path: Storage bucket path
            file_size_bytes: File size

        Returns:
            Created delivery record
        """
        data = {
            "job_id": job_id,
            "pdf_url": pdf_url,
            "storage_path": storage_path,
            "file_size_bytes": file_size_bytes,
            "delivery_status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }

        if self.mock_mode:
            self._mock_pdfs.append(data)
            logger.info(f"[MOCK] Created PDF delivery for job {job_id}")
            return data

        try:
            result = self.client.table("pdf_deliveries").insert(data).execute()
            logger.info(f"Created PDF delivery for job {job_id}")
            return result.data[0] if result.data else data
        except Exception as e:
            logger.error(f"Error creating PDF delivery for job {job_id}: {e}")
            raise

    def update_pdf_delivery(
        self,
        delivery_id: str,
        status: str,
        delivery_channel: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update PDF delivery status.

        Args:
            delivery_id: Delivery record ID
            status: New status (pending, delivered, failed)
            delivery_channel: Channel used (email, webhook, etc)
            error_message: Error if failed

        Returns:
            Updated delivery record
        """
        data = {"delivery_status": status}

        if status == "delivered":
            data["delivered_at"] = datetime.utcnow().isoformat()

        if delivery_channel:
            data["delivery_channel"] = delivery_channel

        if error_message:
            data["error_message"] = error_message

        if self.mock_mode:
            for pdf in self._mock_pdfs:
                if pdf["id"] == delivery_id:
                    pdf.update(data)
                    logger.info(f"[MOCK] Updated PDF delivery {delivery_id} to {status}")
                    return pdf
            return data

        try:
            result = self.client.table("pdf_deliveries").update(data).eq("id", delivery_id).execute()
            logger.info(f"Updated PDF delivery {delivery_id} to {status}")
            return result.data[0] if result.data else data
        except Exception as e:
            logger.error(f"Error updating PDF delivery {delivery_id}: {e}")
            raise

    # ========================================================================
    # HEALTH CHECK
    # ========================================================================

    def health_check(self) -> bool:
        """
        Verify Supabase connection is alive.

        Returns:
            True if connection is healthy
        """
        if self.mock_mode:
            logger.info("[MOCK] Supabase health check passed (mock mode)")
            return True

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
