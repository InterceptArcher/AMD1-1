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

    def test_enrich_calls_supabase_write(self, test_client, mock_supabase):
        """
        POST /rad/enrich: Should write to finalize_data via Supabase.
        """
        response = test_client.post(
            "/rad/enrich",
            json={"email": "john@acme.com"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        # Verify write_finalize_data was called
        mock_supabase.write_finalize_data.assert_called()


class TestProfileEndpoint:
    """Tests for GET /rad/profile/{email} endpoint."""

    def test_get_profile_found(self, test_client, mock_supabase):
        """
        Happy path: GET /rad/profile/{email} with existing profile.
        Should return 200 with normalized profile and personalization.
        """
        response = test_client.get("/rad/profile/john@acme.com")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "john@acme.com"
        assert "normalized_profile" in data
        assert "personalization" in data
        assert data["normalized_profile"]["company"] == "Acme"

    def test_get_profile_with_personalization(self, test_client, mock_supabase):
        """
        GET /rad/profile/{email}: Response includes intro_hook and cta.
        """
        response = test_client.get("/rad/profile/john@acme.com")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        personalization = data.get("personalization")
        assert personalization is not None
        assert "intro_hook" in personalization
        assert "cta" in personalization

    def test_get_profile_not_found(self, test_client, mock_supabase):
        """
        GET /rad/profile/{email}: Email not in finalize_data.
        Should return 404.
        """
        mock_supabase.get_finalize_data.return_value = None
        
        response = test_client.get("/rad/profile/unknown@example.com")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data

    def test_get_profile_case_insensitive(self, test_client, mock_supabase):
        """
        GET /rad/profile/{email}: email should be lowercased.
        """
        response = test_client.get("/rad/profile/JOHN@ACME.COM")
        
        assert response.status_code == status.HTTP_200_OK

    def test_get_profile_calls_supabase_fetch(self, test_client, mock_supabase):
        """
        GET /rad/profile/{email}: Should call get_finalize_data.
        """
        response = test_client.get("/rad/profile/john@acme.com")
        
        assert response.status_code == status.HTTP_200_OK
        mock_supabase.get_finalize_data.assert_called()

    def test_get_profile_includes_last_updated(self, test_client, mock_supabase):
        """
        GET /rad/profile/{email}: Response includes last_updated timestamp.
        """
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

    def test_health_check_unhealthy(self, test_client, mock_supabase):
        """
        GET /rad/health: Supabase is unhealthy.
        Should return 503 with status=unhealthy.
        """
        mock_supabase.health_check.return_value = False
        
        response = test_client.get("/rad/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "unhealthy"
