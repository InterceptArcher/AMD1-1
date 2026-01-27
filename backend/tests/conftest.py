"""
Pytest configuration and fixtures.
Provides mocked Supabase client and FastAPI test client.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient

# Import app and services
from app.main import app
from app.services.supabase_client import SupabaseClient
from app.services.rad_orchestrator import RADOrchestrator
from app.services.llm_service import LLMService


@pytest.fixture
def mock_supabase():
    """
    Fixture: Mocked Supabase client.
    All DB calls are mocked; no real Supabase connection.
    """
    client = MagicMock(spec=SupabaseClient)
    
    # Mock table operations
    client.table = MagicMock()
    
    # Mock store_raw_data
    client.store_raw_data = MagicMock(return_value={
        "email": "test@example.com",
        "source": "apollo",
        "payload": {"name": "John Doe"}
    })
    
    # Mock get_raw_data_for_email
    client.get_raw_data_for_email = MagicMock(return_value=[
        {"email": "test@example.com", "source": "apollo", "payload": {}}
    ])
    
    # Mock create_staging_record
    client.create_staging_record = MagicMock(return_value={
        "email": "test@example.com",
        "normalized_fields": {},
        "status": "resolving"
    })
    
    # Mock update_staging_record
    client.update_staging_record = MagicMock(return_value={
        "email": "test@example.com",
        "normalized_fields": {"name": "John Doe"},
        "status": "ready"
    })
    
    # Mock write_finalize_data
    client.write_finalize_data = MagicMock(return_value={
        "email": "test@example.com",
        "normalized_data": {"name": "John Doe", "company": "Acme"},
        "personalization_intro": "Hi John...",
        "personalization_cta": "Let's chat...",
        "data_sources": ["apollo", "pdl"]
    })
    
    # Mock get_finalize_data
    client.get_finalize_data = MagicMock(return_value={
        "email": "test@example.com",
        "normalized_data": {"name": "John Doe", "company": "Acme"},
        "personalization_intro": "Hi John...",
        "personalization_cta": "Let's chat...",
        "resolved_at": "2025-01-27T00:00:00"
    })
    
    # Mock health_check
    client.health_check = MagicMock(return_value=True)
    
    return client


@pytest.fixture
def test_client(mock_supabase):
    """
    Fixture: FastAPI TestClient with mocked Supabase.
    """
    # Patch the get_supabase_client dependency
    def mock_get_supabase():
        return mock_supabase
    
    from fastapi.testclient import TestClient
    from app.services.supabase_client import get_supabase_client
    
    app.dependency_overrides[get_supabase_client] = mock_get_supabase
    
    client = TestClient(app)
    
    yield client
    
    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
async def mock_rad_orchestrator(mock_supabase):
    """Fixture: RADOrchestrator with mocked Supabase."""
    return RADOrchestrator(mock_supabase)


@pytest.fixture
def mock_llm_service():
    """Fixture: LLMService (mocked, no API calls)."""
    return LLMService(api_key="mock-key")
