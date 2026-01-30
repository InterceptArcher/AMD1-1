"""
Enrichment routes: POST /rad/enrich and GET /rad/profile/{email}
Alpha endpoints for the personalization pipeline.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import Response
from app.models.schemas import (
    EnrichmentRequest,
    EnrichmentResponse,
    ProfileResponse,
    NormalizedProfile,
    PersonalizationContent,
    ErrorResponse
)
from app.services.supabase_client import SupabaseClient, get_supabase_client
from app.services.rad_orchestrator import RADOrchestrator
from app.services.llm_service import LLMService
from app.services.compliance import ComplianceService, validate_personalization
from app.services.pdf_service import PDFService
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rad", tags=["enrichment"])


@router.post(
    "/enrich",
    response_model=EnrichmentResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def enrich_profile(
    request: EnrichmentRequest,
    supabase: SupabaseClient = Depends(get_supabase_client)
) -> EnrichmentResponse:
    """
    POST /rad/enrich
    
    Kick off enrichment for a given email.
    Returns immediately with job_id for async tracking.
    
    In alpha: We run enrichment synchronously but return job_id for future async support.
    
    Args:
        request: EnrichmentRequest with email and optional domain
        supabase: Supabase client (injected)
        
    Returns:
        EnrichmentResponse with job_id and status
        
    Raises:
        HTTPException: 400 if email is invalid, 500 if processing fails
    """
    try:
        job_id = str(uuid.uuid4())
        logger.info(f"[{job_id}] Enrichment request for {request.email}")
        
        # Validate email format (Pydantic EmailStr already validates)
        email = request.email.lower().strip()
        domain = request.domain or email.split("@")[1]
        
        # Create services
        orchestrator = RADOrchestrator(supabase)
        llm_service = LLMService()
        compliance_service = ComplianceService()

        # Run enrichment (sync in alpha, could be async/queued later)
        finalized = await orchestrator.enrich(email, domain)

        # Override enriched data with user-provided name (more reliable)
        if request.firstName:
            finalized["first_name"] = request.firstName
        if request.lastName:
            finalized["last_name"] = request.lastName

        # Add user-provided context to the profile for LLM
        user_context = {
            "goal": request.goal,
            "persona": request.persona,
            "industry_input": request.industry,  # User-selected industry
            "first_name": request.firstName,
            "last_name": request.lastName,
        }

        # Generate personalization with user context
        use_opus = llm_service.should_use_opus(finalized)
        personalization = await llm_service.generate_personalization(
            finalized,
            use_opus=use_opus,
            user_context=user_context
        )

        intro_hook = personalization.get("intro_hook", "")
        cta = personalization.get("cta", "")

        # Run compliance check
        compliance_result = compliance_service.check(intro_hook, cta, auto_correct=True)

        if not compliance_result.passed and compliance_result.corrected_intro:
            # Use corrected content
            intro_hook = compliance_result.corrected_intro
            cta = compliance_result.corrected_cta
            logger.info(f"[{job_id}] Using compliance-corrected content")
        elif not compliance_result.passed:
            # Use safe fallback
            intro_hook = compliance_service.get_safe_intro(finalized)
            cta = compliance_service.get_safe_cta(finalized)
            logger.warning(f"[{job_id}] Compliance failed, using fallback content")

        # Update finalize_data with personalization
        supabase.upsert_finalize_data(
            email=email,
            normalized_data=finalized,
            intro=intro_hook,
            cta=cta,
            data_sources=orchestrator.data_sources
        )
        
        logger.info(f"[{job_id}] Enrichment completed for {email}")
        
        return EnrichmentResponse(
            job_id=job_id,
            email=email,
            status="completed",
            created_at=datetime.utcnow()
        )
        
    except ValueError as e:
        logger.warning(f"Validation error for enrichment: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Enrichment failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Enrichment processing failed"
        )


@router.get(
    "/profile/{email}",
    response_model=ProfileResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def get_profile(
    email: str,
    supabase: SupabaseClient = Depends(get_supabase_client)
) -> ProfileResponse:
    """
    GET /rad/profile/{email}
    
    Retrieve the finalized profile for an email.
    Returns normalized enrichment data + personalization content.
    
    Args:
        email: Email address to look up
        supabase: Supabase client (injected)
        
    Returns:
        ProfileResponse with normalized data and personalization
        
    Raises:
        HTTPException: 404 if email not found, 500 on DB error
    """
    try:
        email = email.lower().strip()
        logger.info(f"Profile lookup for {email}")
        
        # Fetch from finalize_data table
        finalized_record = supabase.get_finalize_data(email)
        
        if not finalized_record:
            logger.warning(f"Profile not found for {email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No profile found for {email}. Run POST /rad/enrich first."
            )
        
        # Map DB record to response model
        normalized_data = finalized_record.get("normalized_data", {})
        
        normalized_profile = NormalizedProfile(
            email=email,
            domain=normalized_data.get("domain"),
            first_name=normalized_data.get("first_name"),
            last_name=normalized_data.get("last_name"),
            company=normalized_data.get("company_name"),
            title=normalized_data.get("title"),
            industry=normalized_data.get("industry"),
            company_size=normalized_data.get("company_size"),
            country=normalized_data.get("country"),
            linkedin_url=normalized_data.get("linkedin_url"),
            data_quality_score=normalized_data.get("data_quality_score")
        )
        
        # Include personalization if available
        personalization = None
        if finalized_record.get("personalization_intro") or finalized_record.get("personalization_cta"):
            personalization = PersonalizationContent(
                intro_hook=finalized_record.get("personalization_intro", ""),
                cta=finalized_record.get("personalization_cta", "")
            )
        
        logger.info(f"Retrieved profile for {email}")
        
        return ProfileResponse(
            email=email,
            normalized_profile=normalized_profile,
            personalization=personalization,
            last_updated=datetime.fromisoformat(finalized_record.get("resolved_at", datetime.utcnow().isoformat()))
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve profile for {email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve profile"
        )


@router.get("/health")
async def health_check(supabase: SupabaseClient = Depends(get_supabase_client)) -> dict:
    """
    GET /rad/health

    Health check for the enrichment service.
    Verifies Supabase connectivity.
    """
    try:
        is_healthy = supabase.health_check()
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "service": "rad_enrichment",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )


@router.post(
    "/pdf/{email}",
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def generate_pdf(
    email: str,
    supabase: SupabaseClient = Depends(get_supabase_client)
) -> dict:
    """
    POST /rad/pdf/{email}

    Generate personalized PDF ebook for a profile.
    Requires the profile to exist in finalize_data.

    Args:
        email: Email address to generate PDF for
        supabase: Supabase client (injected)

    Returns:
        Dict with pdf_url, storage_path, file_size

    Raises:
        HTTPException: 404 if profile not found, 500 on generation failure
    """
    try:
        email = email.lower().strip()
        logger.info(f"PDF generation requested for {email}")

        # Fetch profile
        finalized_record = supabase.get_finalize_data(email)

        if not finalized_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No profile found for {email}. Run POST /rad/enrich first."
            )

        # Get job ID (if exists)
        job_id = finalized_record.get("id", 0)

        # Initialize PDF service
        pdf_service = PDFService(supabase)

        # Generate PDF
        result = await pdf_service.generate_pdf(
            job_id=job_id,
            profile=finalized_record.get("normalized_data", {}),
            intro_hook=finalized_record.get("personalization_intro", ""),
            cta=finalized_record.get("personalization_cta", "")
        )

        # Store PDF delivery record
        try:
            supabase.create_pdf_delivery(
                job_id=job_id,
                pdf_url=result.get("pdf_url"),
                storage_path=result.get("storage_path"),
                file_size_bytes=result.get("file_size_bytes")
            )
        except Exception as e:
            logger.warning(f"Failed to store PDF delivery record: {e}")

        logger.info(f"PDF generated for {email}: {result.get('file_size_bytes')} bytes")

        return {
            "email": email,
            "pdf_url": result.get("pdf_url"),
            "storage_path": result.get("storage_path"),
            "file_size_bytes": result.get("file_size_bytes"),
            "expires_at": result.get("expires_at"),
            "generated_at": result.get("generated_at")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF generation failed for {email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF generation failed"
        )


@router.post(
    "/deliver/{email}",
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def deliver_ebook(
    email: str,
    supabase: SupabaseClient = Depends(get_supabase_client)
) -> dict:
    """
    POST /rad/deliver/{email}

    Generate personalized PDF and send it via email.
    Returns email delivery status with download URL as fallback.

    Args:
        email: Email address to deliver ebook to
        supabase: Supabase client (injected)

    Returns:
        Dict with email_sent status, pdf_url fallback, delivery details

    Raises:
        HTTPException: 404 if profile not found, 500 on generation/delivery failure
    """
    try:
        email = email.lower().strip()
        logger.info(f"Ebook delivery requested for {email}")

        # Fetch profile
        finalized_record = supabase.get_finalize_data(email)

        if not finalized_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No profile found for {email}. Run POST /rad/enrich first."
            )

        profile = finalized_record.get("normalized_data", {})
        intro_hook = finalized_record.get("personalization_intro", "")
        cta = finalized_record.get("personalization_cta", "")
        job_id = finalized_record.get("id", 0)

        # Initialize services
        pdf_service = PDFService(supabase)
        email_service = EmailService()

        # Generate PDF (get raw bytes for email attachment)
        html_content = pdf_service._render_template(profile, intro_hook, cta)
        pdf_bytes = await pdf_service._html_to_pdf(html_content)

        if not pdf_bytes:
            raise ValueError("PDF generation returned empty content")

        # Try to send email
        email_result = await email_service.send_ebook(
            to_email=email,
            pdf_bytes=pdf_bytes,
            profile=profile,
            intro_hook=intro_hook,
            cta=cta
        )

        # Also store PDF for fallback download
        pdf_result = await pdf_service.generate_pdf(
            job_id=job_id,
            profile=profile,
            intro_hook=intro_hook,
            cta=cta
        )

        # Store delivery record
        try:
            supabase.create_pdf_delivery(
                job_id=job_id,
                pdf_url=pdf_result.get("pdf_url"),
                storage_path=pdf_result.get("storage_path"),
                file_size_bytes=pdf_result.get("file_size_bytes")
            )
        except Exception as e:
            logger.warning(f"Failed to store PDF delivery record: {e}")

        response = {
            "email": email,
            "email_sent": email_result.get("success", False),
            "email_provider": email_result.get("provider"),
            "message_id": email_result.get("message_id"),
            "pdf_url": pdf_result.get("pdf_url"),  # Fallback download URL
            "file_size_bytes": pdf_result.get("file_size_bytes"),
            "delivered_at": datetime.utcnow().isoformat()
        }

        if not email_result.get("success"):
            response["email_error"] = email_result.get("error", "Unknown error")
            logger.warning(f"Email delivery failed for {email}, fallback URL provided")
        else:
            logger.info(f"Ebook delivered to {email} via {email_result.get('provider')}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ebook delivery failed for {email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ebook delivery failed"
        )


@router.get(
    "/download/{email}",
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def download_pdf(
    email: str,
    supabase: SupabaseClient = Depends(get_supabase_client)
) -> Response:
    """
    GET /rad/download/{email}

    Download personalized PDF directly as a file.
    No storage required - generates and streams the PDF.

    Args:
        email: Email address to generate PDF for
        supabase: Supabase client (injected)

    Returns:
        PDF file as direct download
    """
    try:
        email = email.lower().strip()
        logger.info(f"PDF download requested for {email}")

        # Fetch profile
        finalized_record = supabase.get_finalize_data(email)

        if not finalized_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No profile found for {email}. Run POST /rad/enrich first."
            )

        profile = finalized_record.get("normalized_data", {})
        intro_hook = finalized_record.get("personalization_intro", "")
        cta = finalized_record.get("personalization_cta", "")

        # Initialize PDF service
        pdf_service = PDFService(supabase)

        # Generate PDF bytes directly
        html_content = pdf_service._render_template(profile, intro_hook, cta)
        pdf_bytes = await pdf_service._html_to_pdf(html_content)

        if not pdf_bytes:
            raise ValueError("PDF generation returned empty content")

        # Generate filename
        first_name = profile.get("first_name", "user")
        safe_name = "".join(c for c in first_name if c.isalnum()).lower()
        filename = f"personalized-ebook-{safe_name}.pdf"

        logger.info(f"Serving PDF download for {email}: {len(pdf_bytes)} bytes")

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(pdf_bytes))
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF download failed for {email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF download failed"
        )
