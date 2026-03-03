"""
Tests for enrichment endpoints.
POST /rad/enrich and GET /rad/profile/{email}
"""

import pytest
from datetime import datetime
from fastapi import status


class TestEnrichmentEndpoint:
    """Tests for POST /rad/enrich endpoint."""

    def test_enrich_valid_email(self, test_client, mock_supabase):
        """
        Happy path: POST /rad/enrich with valid email.
        Should return 200 with job_id and status=completed.
        """
        response = test_client.post(
            "/rad/enrich",
            json={"email": "john@acme.com"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "job_id" in data
        assert data["email"] == "john@acme.com"
        assert data["status"] == "completed"
        assert "created_at" in data

    def test_enrich_with_domain(self, test_client, mock_supabase):
        """
        POST /rad/enrich with explicit domain.
        Should pass domain to orchestrator.
        """
        response = test_client.post(
            "/rad/enrich",
            json={
                "email": "john@acme.com",
                "domain": "acme.io"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "john@acme.com"

    def test_enrich_invalid_email_format(self, test_client):
        """
        POST /rad/enrich with invalid email.
        Should return 422 (Pydantic validation error).
        """
        response = test_client.post(
            "/rad/enrich",
            json={"email": "not-an-email"}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_enrich_missing_email(self, test_client):
        """
        POST /rad/enrich without email.
        Should return 422.
        """
        response = test_client.post(
            "/rad/enrich",
            json={}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_enrich_case_insensitive(self, test_client, mock_supabase):
        """
        POST /rad/enrich: email should be lowercased.
        """
        response = test_client.post(
            "/rad/enrich",
            json={"email": "JOHN@ACME.COM"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "john@acme.com"

    def test_enrich_does_not_store_finalize_data(self, test_client, mock_supabase):
        """
        POST /rad/enrich: Must NOT write PII to finalize_data.
        Analytics are stored instead (verified in test_session_analytics.py).
        """
        response = test_client.post(
            "/rad/enrich",
            json={"email": "john@acme.com"}
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify NO data was written to finalize_data (PII table)
        finalized = mock_supabase.get_finalize_data("john@acme.com")
        assert finalized is None
        assert len(mock_supabase._mock_finalize) == 0


class TestProfileEndpoint:
    """Tests for GET /rad/profile/{email} endpoint.

    NOTE: Since PII is no longer persisted to finalize_data during enrichment,
    the profile endpoint will return 404 unless data is pre-seeded directly
    into the mock store. Tests below verify both the 404 behavior (no PII
    persisted) and the happy path when data is pre-seeded.
    """

    def test_get_profile_returns_404_after_enrich(self, test_client, mock_supabase):
        """
        GET /rad/profile/{email}: Enrichment no longer writes PII to finalize_data.
        Profile lookup should return 404 since no PII is persisted.
        """
        # Enrich the profile (no longer writes to finalize_data)
        test_client.post("/rad/enrich", json={"email": "john@acme.com"})

        # Profile should NOT be found — PII is not persisted
        response = test_client.get("/rad/profile/john@acme.com")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_profile_found_when_preseeded(self, test_client, mock_supabase):
        """
        GET /rad/profile/{email}: Returns 200 when finalize_data is pre-seeded.
        This path exists for legacy/admin use only.
        """
        # Pre-seed finalize_data directly (simulates legacy data)
        mock_supabase.write_finalize_data(
            email="john@acme.com",
            normalized_data={"first_name": "John", "company_name": "Acme"},
            intro="Hello John",
            cta="Get started",
            data_sources=["pdl"],
        )

        response = test_client.get("/rad/profile/john@acme.com")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "john@acme.com"
        assert "normalized_profile" in data
        assert "personalization" in data

    def test_get_profile_not_found(self, test_client, mock_supabase):
        """
        GET /rad/profile/{email}: Email not in finalize_data.
        Should return 404.
        """
        response = test_client.get("/rad/profile/unknown@example.com")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data

    def test_get_profile_case_insensitive(self, test_client, mock_supabase):
        """
        GET /rad/profile/{email}: email should be lowercased.
        """
        # Pre-seed with lowercase
        mock_supabase.write_finalize_data(
            email="john@acme.com",
            normalized_data={"first_name": "John"},
        )

        # Fetch with uppercase
        response = test_client.get("/rad/profile/JOHN@ACME.COM")
        assert response.status_code == status.HTTP_200_OK

    def test_get_profile_includes_last_updated(self, test_client, mock_supabase):
        """
        GET /rad/profile/{email}: Response includes last_updated timestamp.
        """
        # Pre-seed data
        mock_supabase.write_finalize_data(
            email="john@acme.com",
            normalized_data={"first_name": "John"},
        )

        response = test_client.get("/rad/profile/john@acme.com")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "last_updated" in data


class TestHealthEndpoint:
    """Tests for GET /rad/health endpoint."""

    def test_health_check_healthy(self, test_client, mock_supabase):
        """
        GET /rad/health: Supabase is healthy.
        Should return 200 with status=healthy.
        """
        response = test_client.get("/rad/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "rad_enrichment"

    def test_health_check_returns_timestamp(self, test_client, mock_supabase):
        """
        GET /rad/health: Response includes timestamp.
        """
        response = test_client.get("/rad/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "timestamp" in data


class TestPDFEndpoint:
    """Tests for POST /rad/pdf/{email} endpoint."""

    def test_generate_pdf_success(self, test_client, mock_supabase):
        """
        POST /rad/pdf/{email}: Should generate PDF for existing profile.
        Requires pre-seeded finalize_data since enrich no longer persists PII.
        """
        # Pre-seed finalize_data directly (enrich no longer writes PII)
        mock_supabase.write_finalize_data(
            email="john@acme.com",
            normalized_data={
                "first_name": "John",
                "last_name": "Smith",
                "company_name": "Acme Corp",
                "industry": "technology",
            },
            intro="Hello John",
            cta="Get started with AMD",
            data_sources=["pdl"],
        )

        # Then generate PDF — route now returns streamed PDF bytes
        response = test_client.post("/rad/pdf/john@acme.com")

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "application/pdf"
        assert int(response.headers["content-length"]) > 0
        # Response body is raw PDF bytes, not JSON
        assert response.content[:5] == b"%PDF-"

    def test_generate_pdf_not_found(self, test_client, mock_supabase):
        """
        POST /rad/pdf/{email}: Profile not found.
        Should return 404.
        """
        response = test_client.post("/rad/pdf/unknown@example.com")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_generate_pdf_no_delivery_record_stored(self, test_client, mock_supabase):
        """
        POST /rad/pdf/{email}: Must NOT store pdf_deliveries record (PII-adjacent).
        """
        mock_supabase.write_finalize_data(
            email="john@acme.com",
            normalized_data={"first_name": "John", "company_name": "Acme"},
        )

        response = test_client.post("/rad/pdf/john@acme.com")
        assert response.status_code == status.HTTP_200_OK
        # No PDF delivery records should be stored
        assert len(mock_supabase._mock_pdfs) == 0
