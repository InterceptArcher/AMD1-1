"""Tests for anonymized session analytics storage and PDF streaming."""
import pytest
from fastapi import status
from app.services.supabase_client import SupabaseClient
from app.services.pdf_service import PDFService


class TestSessionAnalytics:
    """Verify session_analytics stores only anonymized data."""

    def test_store_session_analytics_returns_record(self, mock_supabase):
        result = mock_supabase.store_session_analytics(
            industry="healthcare",
            company_size="enterprise",
            stage="challenger",
            persona="ITDM",
            challenge="legacy_integration",
            enrichment_sources=["apollo", "pdl"],
            llm_source="llm",
            llm_latency_ms=3200,
            enrichment_latency_ms=4500,
            total_latency_ms=7700,
        )
        assert result is not None
        assert "id" in result
        assert result["industry"] == "healthcare"
        assert result["llm_source"] == "llm"

    def test_store_session_analytics_has_no_pii(self, mock_supabase):
        result = mock_supabase.store_session_analytics(
            industry="technology",
            company_size="mid_market",
            stage="observer",
            persona="BDM",
        )
        assert "email" not in result
        assert "name" not in result
        assert "first_name" not in result
        assert "last_name" not in result
        assert "company_name" not in result
        assert "company" not in result
        assert "domain" not in result
        assert "linkedin_url" not in result

    def test_store_session_analytics_minimal_fields(self, mock_supabase):
        result = mock_supabase.store_session_analytics(
            industry="financial_services",
            company_size="smb",
        )
        assert result is not None
        assert result["industry"] == "financial_services"
        assert result["stage"] is None
        assert result["persona"] is None

    def test_store_session_analytics_accumulates(self, mock_supabase):
        mock_supabase.store_session_analytics(industry="healthcare", company_size="enterprise")
        mock_supabase.store_session_analytics(industry="technology", company_size="smb")
        assert len(mock_supabase._mock_analytics) == 2


class TestRoutesNoPiiWrites:
    """Verify enrichment routes do NOT write PII to Supabase."""

    def test_enrich_route_no_finalize_write(self, test_client, mock_supabase):
        """POST /rad/enrich must NOT write to finalize_data (PII table)."""
        response = test_client.post("/rad/enrich", json={"email": "test@example.com"})
        assert response.status_code == status.HTTP_200_OK
        assert len(mock_supabase._mock_finalize) == 0

    def test_enrich_route_writes_analytics(self, test_client, mock_supabase):
        """POST /rad/enrich should write anonymized analytics instead of PII."""
        response = test_client.post("/rad/enrich", json={
            "email": "test@example.com",
            "industry": "healthcare",
            "companySize": "enterprise",
        })
        assert response.status_code == status.HTTP_200_OK
        assert len(mock_supabase._mock_analytics) >= 1
        analytics = mock_supabase._mock_analytics[0]
        assert "email" not in analytics
        assert "name" not in analytics

    def test_pdf_route_no_delivery_record(self, test_client, mock_supabase):
        """POST /rad/pdf/{email} must NOT write pdf_deliveries (contains job_id linked to PII)."""
        # Pre-seed finalize_data (enrich no longer writes PII)
        mock_supabase.write_finalize_data(
            email="john@acme.com",
            normalized_data={"first_name": "John", "company_name": "Acme"},
        )
        # Generate PDF
        response = test_client.post("/rad/pdf/john@acme.com")
        assert response.status_code == status.HTTP_200_OK
        assert len(mock_supabase._mock_pdfs) == 0


class TestPdfNoStorage:
    """Verify PDFs are generated in-memory, not stored."""

    @pytest.mark.asyncio
    async def test_generate_pdf_returns_bytes(self):
        """generate_pdf must return pdf_bytes in its result dict."""
        service = PDFService()
        result = await service.generate_pdf(
            job_id=0,
            profile={"company_name": "Test Corp", "industry": "technology"},
            intro_hook="Welcome to AI readiness",
            cta="Learn more about AMD solutions",
        )
        assert "pdf_bytes" in result
        assert isinstance(result["pdf_bytes"], bytes)
        assert len(result["pdf_bytes"]) > 0
        assert result["file_size_bytes"] == len(result["pdf_bytes"])

    @pytest.mark.asyncio
    async def test_generate_amd_ebook_returns_bytes(self):
        """generate_amd_ebook must return pdf_bytes in its result dict."""
        service = PDFService()
        result = await service.generate_amd_ebook(
            job_id=0,
            profile={"company_name": "Acme", "industry": "healthcare"},
            personalization={
                "personalized_hook": "Opening hook",
                "case_study_framing": "Case study frame",
                "personalized_cta": "Call to action",
            },
        )
        assert "pdf_bytes" in result
        assert isinstance(result["pdf_bytes"], bytes)
        assert len(result["pdf_bytes"]) > 0
        assert "case_study_used" in result

    @pytest.mark.asyncio
    async def test_generate_executive_review_pdf_returns_dict(self):
        """generate_executive_review_pdf must return a dict with pdf_bytes."""
        service = PDFService()
        result = await service.generate_executive_review_pdf(
            executive_review={
                "company_name": "Test Corp",
                "stage": "Challenger",
                "stage_sidebar": "62% of mid-market firms are Challengers",
                "advantages": [{"headline": "Adv1", "description": "Desc1"}],
                "risks": [{"headline": "Risk1", "description": "Desc1"}],
                "recommendations": [{"title": "Rec1", "description": "Desc1"}],
                "case_study": "KT Cloud",
                "case_study_description": "KT Cloud case study",
            },
            embed_json=False,
        )
        assert isinstance(result, dict)
        assert "pdf_bytes" in result
        assert isinstance(result["pdf_bytes"], bytes)
        assert len(result["pdf_bytes"]) > 0
        assert result["file_size_bytes"] == len(result["pdf_bytes"])

    @pytest.mark.asyncio
    async def test_generate_pdf_no_supabase_upload(self):
        """PDF generation must NOT attempt Supabase storage upload."""
        service = PDFService()  # No supabase_client passed
        result = await service.generate_pdf(
            job_id=0,
            profile={"company_name": "No Storage Inc"},
            intro_hook="Hook",
            cta="CTA",
        )
        # No pdf_url or storage_path in result — bytes only
        assert "pdf_url" not in result
        assert "storage_path" not in result
        assert "pdf_bytes" in result
