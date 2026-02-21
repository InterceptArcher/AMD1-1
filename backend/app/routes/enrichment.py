"""
Enrichment routes: POST /rad/enrich and GET /rad/profile/{email}
Alpha endpoints for the personalization pipeline.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File
from fastapi.responses import Response, JSONResponse
from app.models.schemas import (
    EnrichmentRequest,
    EnrichmentResponse,
    ProfileResponse,
    NormalizedProfile,
    PersonalizationContent,
    ErrorResponse,
    QuickEnrichRequest,
)
from app.services.supabase_client import SupabaseClient, get_supabase_client
from app.services.rad_orchestrator import RADOrchestrator
from app.services.llm_service import LLMService
from app.services.compliance import ComplianceService, validate_personalization
from app.services.pdf_service import PDFService
from app.services.email_service import EmailService
from app.services.executive_review_service import (
    ExecutiveReviewService,
    map_company_size_to_segment,
    map_role_to_persona,
    map_it_environment_to_stage,
    map_priority_display,
    map_challenge_display,
    map_industry_display,
    get_stage_sidebar,
)
from app.services.context_inference_service import infer_context
from app.services.news_analysis_service import analyze_news
from app.services.enrichment_apis import ApolloAPI, PDLAPI

logger = logging.getLogger(__name__)

# Free email providers — skip enrichment for these domains
FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com",
    "icloud.com", "protonmail.com", "mail.com", "live.com", "msn.com",
    "ymail.com", "me.com", "zoho.com", "proton.me",
}

router = APIRouter(prefix="/rad", tags=["enrichment"])


# =============================================================================
# QUICK ENRICH (lightweight, for wizard pre-fill)
# =============================================================================

@router.post("/quick-enrich")
async def quick_enrich(request: QuickEnrichRequest):
    """
    POST /rad/quick-enrich

    Lightweight enrichment for wizard pre-fill. Only calls Apollo (person)
    and PDL Company (company data) in parallel. Returns in ~2-5 seconds.

    Skips free email providers (gmail, yahoo, etc.) immediately.
    Gracefully handles API failures — returns partial data or found=false.
    """
    email = request.email.lower().strip()

    # Extract domain
    if "@" not in email:
        return {"found": False}
    domain = email.split("@")[1]

    # Skip free email providers
    if domain in FREE_EMAIL_DOMAINS:
        return {"found": False}

    try:
        apollo_api = ApolloAPI()
        pdl_api = PDLAPI()

        # Run Apollo + PDL Company in parallel (15s timeout each)
        results = await asyncio.gather(
            apollo_api.enrich(email, domain),
            pdl_api.enrich_company(domain),
            return_exceptions=True,
        )

        apollo_data = results[0] if not isinstance(results[0], Exception) else {}
        pdl_data = results[1] if not isinstance(results[1], Exception) else {}

        if isinstance(results[0], Exception):
            logger.warning(f"Quick-enrich Apollo failed for {email}: {results[0]}")
        if isinstance(results[1], Exception):
            logger.warning(f"Quick-enrich PDL Company failed for {domain}: {results[1]}")

        # Merge: prefer PDL Company for company data, Apollo for person data
        company_name = (
            pdl_data.get("display_name")
            or pdl_data.get("name")
            or apollo_data.get("company_name")
            or ""
        )
        industry = pdl_data.get("industry") or apollo_data.get("industry") or ""
        employee_count = pdl_data.get("employee_count") or 0
        title = apollo_data.get("title") or ""
        seniority = apollo_data.get("seniority") or ""
        company_summary = pdl_data.get("summary") or ""
        founded_year = pdl_data.get("founded") or 0

        return {
            "found": bool(company_name),
            "company_name": company_name,
            "industry": industry,
            "employee_count": employee_count,
            "title": title,
            "seniority": seniority,
            "company_summary": company_summary,
            "founded_year": founded_year,
        }

    except Exception as e:
        logger.error(f"Quick-enrich failed for {email}: {e}")
        return {"found": False}


@router.post(
    "/enrich",
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

        # Check for existing enrichment data (cache)
        existing_record = supabase.get_finalize_data(email)
        if existing_record and not request.force_refresh:
            logger.info(f"[{job_id}] Using cached data for {email} (use force_refresh=true to re-enrich)")
            # Return cached data with cache indicator
            return {
                "job_id": job_id,
                "email": email,
                "status": "completed",
                "created_at": existing_record.get("resolved_at", datetime.utcnow().isoformat()),
                "cached": True,
                "data_quality_score": existing_record.get("normalized_data", {}).get("data_quality_score", 0),
                "message": "Using cached enrichment data. Set force_refresh=true to re-enrich."
            }

        # Create services
        orchestrator = RADOrchestrator(supabase)
        llm_service = LLMService()
        compliance_service = ComplianceService()

        # Run enrichment (sync in alpha, could be async/queued later)
        # Pass user-provided company so it's used for GNews search and company resolution
        finalized = await orchestrator.enrich(email, domain, user_company=request.company)

        # Log which data sources returned real vs mock data
        logger.info(f"[{job_id}] Data sources used: {orchestrator.data_sources}")
        logger.info(f"[{job_id}] Quality score: {finalized.get('data_quality_score', 0)}")

        # Run news analysis on enriched articles
        news_articles = finalized.get("recent_news", []) or []
        news_analysis = analyze_news(news_articles)
        finalized["news_analysis"] = {
            "sentiment": news_analysis["sentiment"]["overall"],
            "sentiment_detail": news_analysis["sentiment"],
            "ai_readiness": news_analysis["ai_readiness"]["stage"],
            "ai_readiness_detail": news_analysis["ai_readiness"],
            "crisis": news_analysis["crisis"],
            "entities": news_analysis["entities"],
        }

        if news_analysis["crisis"]["is_crisis"]:
            logger.warning(
                f"[{job_id}] Crisis detected for {email}: "
                f"{news_analysis['crisis']['type']} - {news_analysis['crisis']['details']}"
            )
            finalized["tone_guidance"] = "empathetic"

        # Override enriched data with user-provided info (when available)
        if request.firstName:
            finalized["first_name"] = request.firstName
        if request.lastName:
            finalized["last_name"] = request.lastName
        if request.company:
            finalized["company_name"] = request.company
        if request.companySize:
            finalized["company_size"] = request.companySize
        if request.industry:
            finalized["industry"] = request.industry
        if request.persona:
            finalized["title"] = request.persona

        # Run context inference to fill gaps
        inferred = infer_context(finalized, user_goal=request.goal)

        # Build user context from enriched + inferred data
        user_context = {
            "goal": request.goal or inferred["journey_stage"],
            "persona": request.persona or finalized.get("title"),
            "industry_input": request.industry or finalized.get("industry"),
            "company": request.company or finalized.get("company_name"),
            "company_size": request.companySize or finalized.get("company_size"),
            "first_name": request.firstName or finalized.get("first_name"),
            "last_name": request.lastName or finalized.get("last_name"),
            "inferred_context": inferred,
            "news_analysis": finalized.get("news_analysis"),
        }

        # Get company news from Tavily (if available in enrichment)
        company_news = finalized.get("company_context", "")

        # Generate AMD ebook personalization (3 sections)
        ebook_personalization = await llm_service.generate_ebook_personalization(
            profile=finalized,
            user_context=user_context,
            company_news=company_news
        )

        # Also generate legacy personalization for backward compatibility
        use_opus = llm_service.should_use_opus(finalized)
        personalization = await llm_service.generate_personalization(
            finalized,
            use_opus=use_opus,
            user_context=user_context
        )

        intro_hook = personalization.get("intro_hook", "")
        cta = personalization.get("cta", "")

        # Run compliance check on all personalized content
        compliance_service = ComplianceService()
        compliance_result = compliance_service.check(intro_hook, cta, auto_correct=True)

        if not compliance_result.passed and compliance_result.corrected_intro:
            intro_hook = compliance_result.corrected_intro
            cta = compliance_result.corrected_cta
            logger.info(f"[{job_id}] Using compliance-corrected content")
        elif not compliance_result.passed:
            intro_hook = compliance_service.get_safe_intro(finalized)
            cta = compliance_service.get_safe_cta(finalized)
            logger.warning(f"[{job_id}] Compliance failed, using fallback content")

        # Also check ebook personalization
        ebook_hook = ebook_personalization.get("personalized_hook", "")
        ebook_cta = ebook_personalization.get("personalized_cta", "")
        ebook_compliance = compliance_service.check(ebook_hook, ebook_cta, auto_correct=True)
        if not ebook_compliance.passed and ebook_compliance.corrected_intro:
            ebook_personalization["personalized_hook"] = ebook_compliance.corrected_intro
            ebook_personalization["personalized_cta"] = ebook_compliance.corrected_cta

        # Store ebook personalization in normalized_data for PDF generation
        finalized["ebook_personalization"] = ebook_personalization
        finalized["user_context"] = user_context

        # Update finalize_data with personalization (non-fatal - log error but continue)
        try:
            supabase.upsert_finalize_data(
                email=email,
                normalized_data=finalized,
                intro=intro_hook,
                cta=cta,
                data_sources=orchestrator.data_sources
            )
        except Exception as db_err:
            import traceback
            logger.error(f"[{job_id}] Failed to store finalize_data: {db_err}")
            logger.error(f"[{job_id}] DB error traceback: {traceback.format_exc()}")
        
        logger.info(f"[{job_id}] Enrichment completed for {email}")
        
        # Build response with data source info
        response = EnrichmentResponse(
            job_id=job_id,
            email=email,
            status="completed",
            created_at=datetime.utcnow()
        )

        # Add extra info about data sources and personalization (for frontend)
        return {
            **response.model_dump(),
            "data_sources": orchestrator.data_sources,
            "data_quality_score": finalized.get("data_quality_score", 0),
            "enriched_fields": {
                "first_name": finalized.get("first_name"),
                "company_name": finalized.get("company_name"),
                "title": finalized.get("title"),
                "industry": finalized.get("industry"),
                "employee_count": finalized.get("employee_count"),
                "latest_funding_stage": finalized.get("latest_funding_stage"),
                "news_themes": finalized.get("news_themes", []),
                "recent_news": finalized.get("recent_news", [])[:3],  # First 3 headlines
                "skills": finalized.get("skills", [])[:5],  # First 5 skills
            },
            # Include ebook personalization for frontend rendering
            "ebook_personalization": ebook_personalization,
            "user_context": user_context
        }
        
    except ValueError as e:
        logger.warning(f"Validation error for enrichment: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Enrichment failed for {request.email}: {type(e).__name__}: {e}")
        logger.error(f"Traceback: {error_traceback}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Enrichment processing failed: {type(e).__name__}: {str(e)[:200]}"
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
    Verifies Supabase connectivity and returns diagnostic info on failure.
    """
    try:
        is_healthy = supabase.health_check()
        result = {
            "status": "healthy" if is_healthy else "unhealthy",
            "service": "rad_enrichment",
            "mock_mode": supabase.mock_mode,
            "timestamp": datetime.utcnow().isoformat()
        }
        if not is_healthy:
            # Try individual table checks for diagnostics
            diagnostics = {}
            for table in ["finalize_data", "raw_data", "personalization_jobs"]:
                try:
                    supabase.client.table(table).select("id").limit(1).execute()
                    diagnostics[table] = "ok"
                except Exception as table_err:
                    diagnostics[table] = str(table_err)[:200]
            result["diagnostics"] = diagnostics
        return result
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "error": str(e)[:300],
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/test-apis/{email}")
async def test_apis(email: str) -> dict:
    """
    GET /rad/test-apis/{email}

    Directly test each API and show raw results or errors.
    For debugging API connectivity.
    """
    from app.services.enrichment_apis import get_enrichment_apis

    apis = get_enrichment_apis()
    domain = email.split("@")[1]
    results = {}

    for name, api in apis.items():
        try:
            data = await api.enrich(email, domain)
            is_mock = data.get("_mock", False)
            results[name] = {
                "status": "mock" if is_mock else "real_data",
                "fields_returned": list(data.keys())[:10],
                "sample": {k: str(v)[:50] for k, v in list(data.items())[:5]}
            }
        except Exception as e:
            results[name] = {
                "status": "error",
                "error": str(e)
            }

    return {
        "email": email,
        "domain": domain,
        "api_results": results
    }


@router.get("/status")
async def api_status() -> dict:
    """
    GET /rad/status

    Check status of all configured APIs and services.
    Shows which APIs have real keys vs using mock data.
    """
    import os
    from app.config import settings

    def check_key(key: str) -> str:
        value = getattr(settings, key, None)
        if value and len(value) > 4:
            return f"configured ({value[:4]}...)"
        return "not set (using mock)"

    # Also check raw env vars to debug case sensitivity issues
    raw_env = {}
    for key in ["APOLLO_API_KEY", "Apollo_API_KEY", "HUNTER_API_KEY", "Hunter_API_KEY",
                "PDL_API_KEY", "Pdl_API_KEY", "GNEWS_API_KEY", "GNews_API_KEY",
                "ZOOMINFO_API_KEY", "ZoomInfo_API_KEY"]:
        val = os.getenv(key)
        if val:
            raw_env[key] = f"set ({val[:4]}...)" if len(val) > 4 else "set (short)"

    # Check email provider
    def check_email_provider() -> str:
        if os.getenv("SENDGRID_API_KEY"):
            return "sendgrid (configured)"
        elif os.getenv("RESEND_API_KEY"):
            return "resend (configured)"
        elif os.getenv("SMTP_HOST"):
            return "smtp (configured)"
        else:
            return "mock (no provider configured)"

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "enrichment_apis": {
            "apollo": check_key("APOLLO_API_KEY"),
            "pdl": check_key("PDL_API_KEY"),
            "hunter": check_key("HUNTER_API_KEY"),
            "gnews": check_key("GNEWS_API_KEY"),
            "zoominfo": check_key("ZOOMINFO_API_KEY"),
        },
        "llm_providers": {
            "anthropic": check_key("ANTHROPIC_API_KEY"),
            "openai": check_key("OPENAI_API_KEY"),
            "gemini": check_key("GEMINI_API_KEY"),
        },
        "email": {
            "provider": check_email_provider(),
            "from_address": os.getenv("EMAIL_FROM", "not set"),
        },
        "database": {
            "supabase_url": "configured" if settings.SUPABASE_URL else "not set",
            "supabase_key": "configured" if settings.SUPABASE_KEY else "not set",
        },
        "raw_env_vars_found": raw_env if raw_env else "none detected",
        "mode": "mock" if settings.MOCK_MODE else "production"
    }


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

        # Get profile data
        normalized_data = finalized_record.get("normalized_data", {})
        ebook_personalization = normalized_data.get("ebook_personalization", {})
        user_context = normalized_data.get("user_context", {})

        # Generate AMD ebook PDF with 3 personalization points
        if ebook_personalization:
            result = await pdf_service.generate_amd_ebook(
                job_id=job_id,
                profile=normalized_data,
                personalization=ebook_personalization,
                user_context=user_context
            )
        else:
            # Fallback to legacy template
            result = await pdf_service.generate_pdf(
                job_id=job_id,
                profile=normalized_data,
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
        ebook_personalization = profile.get("ebook_personalization", {})
        user_context = profile.get("user_context", {})

        # Initialize services
        pdf_service = PDFService(supabase)
        email_service = EmailService()

        # Generate PDF (get raw bytes for email attachment)
        if ebook_personalization:
            html_content = pdf_service._render_amd_ebook_template(
                profile=profile,
                personalized_hook=ebook_personalization.get("personalized_hook", ""),
                case_study=pdf_service._get_case_study_for_profile(profile, user_context),
                case_study_framing=ebook_personalization.get("case_study_framing", ""),
                personalized_cta=ebook_personalization.get("personalized_cta", ""),
                user_context=user_context
            )
        else:
            html_content = pdf_service._render_template(profile, intro_hook, cta)
        pdf_bytes = await pdf_service._html_to_pdf(html_content)

        if not pdf_bytes:
            raise ValueError("PDF generation returned empty content")

        # Try to send email
        email_result = await email_service.send_ebook(
            to_email=email,
            pdf_bytes=pdf_bytes,
            profile=profile,
            intro_hook=ebook_personalization.get("personalized_hook", intro_hook),
            cta=ebook_personalization.get("personalized_cta", cta)
        )

        # Also store PDF for fallback download
        if ebook_personalization:
            pdf_result = await pdf_service.generate_amd_ebook(
                job_id=job_id,
                profile=profile,
                personalization=ebook_personalization,
                user_context=user_context
            )
        else:
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


def _infer_persona_from_title(title: str, departments: Optional[list] = None) -> str:
    """
    Map an enriched job title to BDM or ITDM persona.
    Uses departments from Apollo as disambiguation when title is ambiguous.
    """
    if not title:
        if departments:
            return _persona_from_departments(departments)
        return "BDM"

    title_lower = title.lower()

    # Word-boundary signals (avoid "cto" matching inside "director")
    import re
    itdm_patterns = [
        r"\bcto\b", r"\bcio\b", r"\bciso\b", r"\bcdo\b",
        r"\bengineer", r"\bdeveloper", r"\barchitect",
        r"\bchief technology", r"\bchief information", r"\bchief security",
        r"\bchief data",
        r"\bit\b", r"\bdata\b", r"\bsecurity\b", r"\bdevops\b", r"\bsre\b",
        r"\binfrastructure", r"\bplatform\b", r"\bcloud\b", r"\btechnical",
        r"\bsoftware", r"\bsystems\b",
    ]
    bdm_patterns = [
        r"\bsales\b", r"\bmarketing\b", r"\brevenue\b", r"\bbusiness development",
        r"\baccount", r"\bcustomer success", r"\bgrowth\b", r"\bcommercial\b",
    ]

    itdm_match = any(re.search(p, title_lower) for p in itdm_patterns)
    bdm_match = any(re.search(p, title_lower) for p in bdm_patterns)

    if itdm_match and not bdm_match:
        return "ITDM"
    if bdm_match and not itdm_match:
        return "BDM"

    # Ambiguous title — use departments to disambiguate
    if departments:
        return _persona_from_departments(departments)

    return "BDM"


def _persona_from_departments(departments: list) -> str:
    """Infer persona from Apollo departments array."""
    if not departments:
        return "BDM"

    dept_text = " ".join(d.lower() for d in departments if d)
    itdm_depts = {"engineering", "information_technology", "it", "data", "security", "operations"}
    bdm_depts = {"sales", "marketing", "finance", "business_development", "management"}

    if any(d in dept_text for d in itdm_depts):
        return "ITDM"
    if any(d in dept_text for d in bdm_depts):
        return "BDM"

    return "BDM"


def _infer_segment_from_employee_count(count) -> str:
    """Map employee count to AMD segment."""
    if not count or not isinstance(count, (int, float)):
        return "Enterprise"
    if count < 200:
        return "SMB"
    elif count < 1000:
        return "Mid-Market"
    return "Enterprise"


@router.post(
    "/executive-review",
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def generate_executive_review(
    request: EnrichmentRequest,
    supabase: SupabaseClient = Depends(get_supabase_client)
) -> dict:
    """
    POST /rad/executive-review

    Generate personalized executive review content for AMD 2-page assessment.
    Now works with minimal input (email only + optional goal).
    Enriches data via APIs and infers context automatically.

    Args:
        request: EnrichmentRequest - only email is required. All other fields optional.

    Returns:
        ExecutiveReviewContent with all personalized sections + enrichment data
    """
    try:
        email = request.email.lower().strip()
        domain = request.domain or email.split("@")[1]
        logger.info(f"Executive review generation for {email}")

        # Step 1: Enrich from email via APIs
        orchestrator = RADOrchestrator(supabase)
        finalized = await orchestrator.enrich(email, domain, user_company=request.company)

        logger.info(f"Enrichment complete. Quality: {finalized.get('data_quality_score', 0)}, Sources: {orchestrator.data_sources}")

        # Step 2: Analyze news for deeper insights
        news_articles = finalized.get("recent_news", []) or []
        news_analysis = analyze_news(news_articles)

        # Step 3: Infer context from enrichment data
        inferred = infer_context(finalized, user_goal=request.goal)
        logger.info(f"Context inferred: {inferred}")

        # Step 4: Resolve final values - user input wins over API data
        # (APIs may return the person's CURRENT employer, not the company they entered)
        company_name = request.company or finalized.get("company_name") or domain.split(".")[0].title()
        raw_industry = finalized.get("industry") or request.industry or "technology"
        industry = map_industry_display(raw_industry)

        # Segment from employee count (enriched) or company size (form)
        employee_count = finalized.get("employee_count")
        if employee_count:
            segment = _infer_segment_from_employee_count(employee_count)
        else:
            segment = map_company_size_to_segment(request.companySize or "enterprise")

        # Persona from enriched title
        enriched_title = finalized.get("title") or ""
        if request.persona:
            persona = map_role_to_persona(request.persona)
        else:
            departments = finalized.get("departments") or []
            persona = _infer_persona_from_title(enriched_title, departments)

        # Stage, priority, challenge from context inference
        stage = map_it_environment_to_stage(inferred["it_environment"])
        priority = map_priority_display(inferred["business_priority"])
        challenge = map_challenge_display(inferred["primary_challenge"])

        logger.info(f"Resolved: company={company_name}, industry={industry}, segment={segment}, "
                     f"persona={persona}, stage={stage}, priority={priority}, challenge={challenge}")

        # Step 5: Generate executive review with enrichment context
        enrichment_context = {
            "employee_count": employee_count,
            "founded_year": finalized.get("founded_year"),
            "employee_growth_rate": finalized.get("employee_growth_rate"),
            "latest_funding_stage": finalized.get("latest_funding_stage"),
            "total_funding": finalized.get("total_funding_raised"),
            "company_summary": finalized.get("company_summary"),
            "recent_news": finalized.get("recent_news", []),
            "news_themes": finalized.get("news_themes", []),
            "title": enriched_title,
            "news_analysis": {
                "sentiment": news_analysis["sentiment"]["overall"],
                "ai_readiness": news_analysis["ai_readiness"]["stage"],
                "crisis": news_analysis["crisis"]["is_crisis"],
            },
        }

        service = ExecutiveReviewService()
        result = await service.generate_executive_review(
            company_name=company_name,
            industry=industry,
            segment=segment,
            persona=persona,
            stage=stage,
            priority=priority,
            challenge=challenge,
            enrichment_context=enrichment_context,
        )

        logger.info(f"Executive review generated for {company_name}")

        return {
            "success": True,
            "company_name": company_name,
            "inputs": {
                "industry": industry,
                "segment": segment,
                "persona": persona,
                "stage": stage,
                "priority": priority,
                "challenge": challenge,
            },
            "executive_review": result,
            # Include enrichment data for frontend display
            "enrichment": {
                "first_name": finalized.get("first_name"),
                "last_name": finalized.get("last_name"),
                "title": enriched_title,
                "company_name": company_name,
                "employee_count": employee_count,
                "founded_year": finalized.get("founded_year"),
                "industry": raw_industry,
                "data_quality_score": finalized.get("data_quality_score", 0),
                "news_themes": finalized.get("news_themes", []),
                "recent_news": (finalized.get("recent_news") or [])[:3],
            },
            "inferred_context": inferred,
            "news_analysis": {
                "sentiment": news_analysis["sentiment"]["overall"],
                "ai_readiness": news_analysis["ai_readiness"]["stage"],
                "crisis": news_analysis["crisis"]["is_crisis"],
            },
        }

    except Exception as e:
        import traceback
        logger.error(f"Executive review generation failed: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Executive review generation failed: {str(e)}"
        )


@router.post(
    "/executive-review-pdf",
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def generate_executive_review_pdf(
    request: EnrichmentRequest,
    embed_json: bool = True,
) -> Response:
    """
    POST /rad/executive-review-pdf

    Generate and download PDF for AMD Executive Review (2-page assessment).

    This endpoint combines the executive review JSON generation with PDF rendering,
    and optionally embeds the JSON data as PDF metadata for programmatic access.

    Args:
        request: EnrichmentRequest with company info and modernization details
        embed_json: Whether to embed the JSON data as PDF metadata (default: True)

    Returns:
        PDF file as direct download with Content-Disposition header
    """
    try:
        logger.info(f"Executive review PDF generation for {request.company}")

        # Map form inputs to AMD terminology
        company_name = request.company or "Your Company"
        industry = map_industry_display(request.industry or "technology")
        segment = map_company_size_to_segment(request.companySize or "enterprise")
        persona = map_role_to_persona(request.persona or "cto")
        stage = map_it_environment_to_stage(request.itEnvironment or "modernizing")
        priority = map_priority_display(request.businessPriority or "improving_performance")
        challenge = map_challenge_display(request.challenge or "integration_friction")

        # Generate executive review JSON
        review_service = ExecutiveReviewService()
        executive_review = await review_service.generate_executive_review(
            company_name=company_name,
            industry=industry,
            segment=segment,
            persona=persona,
            stage=stage,
            priority=priority,
            challenge=challenge,
        )

        # Generate PDF from JSON
        pdf_service = PDFService()
        pdf_bytes = await pdf_service.generate_executive_review_pdf(
            executive_review=executive_review,
            embed_json=embed_json
        )

        # Generate filename
        company_slug = company_name.lower().replace(" ", "_")[:30]
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        filename = f"amd_executive_review_{company_slug}_{timestamp}.pdf"

        logger.info(f"Executive review PDF generated for {company_name}: {len(pdf_bytes)} bytes")

        # Return PDF as download
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Company": company_name,
                "X-Stage": stage,
                "X-JSON-Embedded": "true" if embed_json else "false",
            }
        )

    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Executive review PDF generation failed: {type(e).__name__}: {e}")
        logger.error(f"Traceback: {error_traceback}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF generation failed: {str(e)}"
        )


@router.post(
    "/extract-pdf-json",
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def extract_pdf_json(
    file: UploadFile = File(..., description="PDF file with embedded JSON metadata")
) -> JSONResponse:
    """
    POST /rad/extract-pdf-json

    Extract embedded JSON metadata from an AMD Executive Review PDF.

    This endpoint reads a PDF file generated by /executive-review-pdf and extracts
    the embedded JSON data, allowing programmatic access to the structured content.

    Args:
        file: Uploaded PDF file

    Returns:
        JSONResponse with extracted executive review data

    Raises:
        HTTPException: 400 if file is not a PDF or has no embedded data
    """
    try:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be a PDF"
            )

        # Read file contents
        pdf_bytes = await file.read()

        if not pdf_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty PDF file"
            )

        logger.info(f"Extracting JSON from uploaded PDF: {file.filename} ({len(pdf_bytes)} bytes)")

        # Extract JSON metadata
        extracted_data = PDFService.extract_json_from_pdf(pdf_bytes)

        if not extracted_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No embedded JSON found in PDF. This PDF may not have been generated by the AMD Executive Review system."
            )

        logger.info(f"Successfully extracted JSON from PDF: {file.filename}")

        return JSONResponse(
            content={
                "success": True,
                "filename": file.filename,
                "data": extracted_data,
                "metadata": {
                    "company": extracted_data.get("company_name"),
                    "stage": extracted_data.get("stage"),
                    "extracted_at": datetime.utcnow().isoformat(),
                }
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"JSON extraction failed: {type(e).__name__}: {e}")
        logger.error(f"Traceback: {error_traceback}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract JSON from PDF: {str(e)}"
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

        # Get ebook personalization if available
        ebook_personalization = profile.get("ebook_personalization", {})
        user_context = profile.get("user_context", {})

        # Generate PDF bytes directly
        if ebook_personalization:
            html_content = pdf_service._render_amd_ebook_template(
                profile=profile,
                personalized_hook=ebook_personalization.get("personalized_hook", ""),
                case_study=pdf_service._get_case_study_for_profile(profile, user_context),
                case_study_framing=ebook_personalization.get("case_study_framing", ""),
                personalized_cta=ebook_personalization.get("personalized_cta", ""),
                user_context=user_context
            )
        else:
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
