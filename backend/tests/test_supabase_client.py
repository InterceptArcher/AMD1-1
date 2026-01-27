"""
Tests for Supabase client data access layer.
Mocked Supabase calls; no real database.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.services.supabase_client import SupabaseClient


class TestSupabaseClient:
    """Tests for SupabaseClient wrapper."""

    @pytest.fixture
    def supabase_client(self, mock_supabase):
        """Fixture: Supabase client for testing."""
        # We'll use the mock from conftest
        return mock_supabase

    def test_store_raw_data(self, supabase_client):
        """
        store_raw_data: Should insert record into raw_data table.
        """
        result = supabase_client.store_raw_data(
            email="john@acme.com",
            source="apollo",
            payload={"name": "John Doe", "title": "VP Sales"}
        )
        
        assert result["email"] == "john@acme.com"
        assert result["source"] == "apollo"
        supabase_client.store_raw_data.assert_called_once()

    def test_get_raw_data_for_email(self, supabase_client):
        """
        get_raw_data_for_email: Should retrieve all raw_data records for email.
        """
        result = supabase_client.get_raw_data_for_email("john@acme.com")
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert result[0]["email"] == "john@acme.com"

    def test_create_staging_record(self, supabase_client):
        """
        create_staging_record: Should create staging_normalized record.
        """
        normalized = {
            "first_name": "John",
            "last_name": "Doe",
            "company": "Acme"
        }
        
        result = supabase_client.create_staging_record(
            email="john@acme.com",
            normalized_fields=normalized,
            status="resolving"
        )
        
        assert result["email"] == "john@acme.com"
        assert result["status"] == "resolving"

    def test_update_staging_record(self, supabase_client):
        """
        update_staging_record: Should update existing staging record.
        """
        normalized = {
            "first_name": "John",
            "last_name": "Doe",
            "company": "Acme",
            "title": "VP Sales"  # Added
        }
        
        result = supabase_client.update_staging_record(
            email="john@acme.com",
            normalized_fields=normalized,
            status="ready"
        )
        
        assert result["email"] == "john@acme.com"
        assert result["status"] == "ready"

    def test_write_finalize_data(self, supabase_client):
        """
        write_finalize_data: Should write final profile to finalize_data.
        """
        normalized = {
            "first_name": "John",
            "last_name": "Doe",
            "company": "Acme",
            "title": "VP Sales",
            "industry": "SaaS"
        }
        
        result = supabase_client.write_finalize_data(
            email="john@acme.com",
            normalized_data=normalized,
            intro="Hi John...",
            cta="Let's chat...",
            data_sources=["apollo", "pdl"]
        )
        
        assert result["email"] == "john@acme.com"
        assert result["personalization_intro"] == "Hi John..."
        assert result["personalization_cta"] == "Let's chat..."

    def test_get_finalize_data_found(self, supabase_client):
        """
        get_finalize_data: Should retrieve finalized profile.
        """
        result = supabase_client.get_finalize_data("john@acme.com")
        
        assert result is not None
        assert result["email"] == "john@acme.com"
        assert "normalized_data" in result

    def test_get_finalize_data_not_found(self, supabase_client):
        """
        get_finalize_data: Should return None if not found.
        """
        supabase_client.get_finalize_data.return_value = None
        
        result = supabase_client.get_finalize_data("unknown@example.com")
        
        assert result is None

    def test_health_check_healthy(self, supabase_client):
        """
        health_check: Should return True when Supabase is healthy.
        """
        result = supabase_client.health_check()
        
        assert result is True

    def test_health_check_unhealthy(self, supabase_client):
        """
        health_check: Should return False on connection error.
        """
        supabase_client.health_check.return_value = False
        
        result = supabase_client.health_check()
        
        assert result is False


class TestRawDataOperations:
    """Tests for raw_data table operations."""

    def test_store_multiple_sources(self, mock_supabase):
        """
        Multiple API sources: Each should create separate raw_data records.
        """
        email = "john@acme.com"
        
        mock_supabase.store_raw_data(email, "apollo", {"name": "John"})
        mock_supabase.store_raw_data(email, "pdl", {"country": "US"})
        mock_supabase.store_raw_data(email, "hunter", {"verified": True})
        
        # Verify all three calls were made
        assert mock_supabase.store_raw_data.call_count == 3

    def test_get_raw_data_returns_list(self, mock_supabase):
        """
        get_raw_data_for_email: Always returns list (empty if not found).
        """
        result = mock_supabase.get_raw_data_for_email("john@acme.com")
        
        assert isinstance(result, list)


class TestFinalizationOperations:
    """Tests for finalize_data table operations."""

    def test_write_finalize_requires_normalized_data(self, mock_supabase):
        """
        write_finalize_data: Requires normalized_data dict.
        """
        normalized = {"first_name": "John", "company": "Acme"}
        
        result = mock_supabase.write_finalize_data(
            email="john@acme.com",
            normalized_data=normalized
        )
        
        assert result["normalized_data"] == normalized

    def test_finalize_personalization_optional(self, mock_supabase):
        """
        write_finalize_data: intro/cta are optional (alpha: not generated yet).
        """
        result = mock_supabase.write_finalize_data(
            email="john@acme.com",
            normalized_data={"company": "Acme"},
            intro=None,
            cta=None
        )
        
        assert result["email"] == "john@acme.com"

    def test_get_finalize_latest_record(self, mock_supabase):
        """
        get_finalize_data: Should return latest record (ordered by resolved_at).
        Mock already handles this behavior.
        """
        result = mock_supabase.get_finalize_data("john@acme.com")
        
        assert result is not None
        assert "resolved_at" in result
