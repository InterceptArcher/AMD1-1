"""
Tests for the lightweight /rad/quick-enrich endpoint.
Provides fast company pre-fill from email domain without full enrichment.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport

from app.main import app


# =============================================================================
# MOCK DATA
# =============================================================================

MOCK_APOLLO_RESULT = {
    "email": "jane@honeycomb.io",
    "first_name": "Jane",
    "last_name": "Doe",
    "title": "VP of Infrastructure Engineering",
    "company_name": "Honeycomb",
    "industry": "information technology and services",
    "seniority": "vp",
    "departments": ["engineering"],
    "fetched_at": "2026-02-18T00:00:00",
}

MOCK_PDL_COMPANY_RESULT = {
    "domain": "honeycomb.io",
    "name": "honeycomb",
    "display_name": "Honeycomb",
    "industry": "internet",
    "employee_count": 250,
    "founded": 2016,
    "summary": "Honeycomb is an observability platform that helps engineering teams debug production systems faster.",
    "tags": ["saas", "observability", "developer tools", "cloud"],
    "total_funding_raised": 97000000,
    "latest_funding_stage": "series c",
    "employee_growth_rate": 12.5,
    "fetched_at": "2026-02-18T00:00:00",
}


# =============================================================================
# Test: Endpoint returns enrichment data
# =============================================================================

class TestQuickEnrichEndpoint:
    """Quick-enrich should return company data from Apollo + PDL Company."""

    @pytest.mark.asyncio
    async def test_returns_company_data_from_apis(self):
        """Should return merged company data when APIs respond."""
        with patch("app.routes.enrichment.ApolloAPI") as MockApollo, \
             patch("app.routes.enrichment.PDLAPI") as MockPDL:

            mock_apollo = MockApollo.return_value
            mock_apollo.enrich = AsyncMock(return_value=MOCK_APOLLO_RESULT)

            mock_pdl = MockPDL.return_value
            mock_pdl.enrich_company = AsyncMock(return_value=MOCK_PDL_COMPANY_RESULT)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/rad/quick-enrich", json={"email": "jane@honeycomb.io"})

            assert resp.status_code == 200
            data = resp.json()
            assert data["found"] is True
            assert data["company_name"] == "Honeycomb"
            assert data["industry"] == "internet"
            assert data["employee_count"] == 250
            assert data["title"] == "VP of Infrastructure Engineering"
            assert data["company_summary"].startswith("Honeycomb is an observability")
            assert data["founded_year"] == 2016
            assert data["seniority"] == "vp"

    @pytest.mark.asyncio
    async def test_returns_found_false_for_free_email(self):
        """Should return found=false for free email providers (gmail, yahoo, etc.)."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/rad/quick-enrich", json={"email": "john@gmail.com"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["found"] is False

    @pytest.mark.asyncio
    async def test_handles_api_failures_gracefully(self):
        """Should return partial data when one API fails."""
        with patch("app.routes.enrichment.ApolloAPI") as MockApollo, \
             patch("app.routes.enrichment.PDLAPI") as MockPDL:

            mock_apollo = MockApollo.return_value
            mock_apollo.enrich = AsyncMock(side_effect=Exception("Apollo timeout"))

            mock_pdl = MockPDL.return_value
            mock_pdl.enrich_company = AsyncMock(return_value=MOCK_PDL_COMPANY_RESULT)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/rad/quick-enrich", json={"email": "jane@honeycomb.io"})

            assert resp.status_code == 200
            data = resp.json()
            assert data["found"] is True
            assert data["company_name"] == "Honeycomb"
            # Apollo failed, so title should be empty
            assert data["title"] == ""

    @pytest.mark.asyncio
    async def test_handles_both_apis_failing(self):
        """Should return found=false when both APIs fail."""
        with patch("app.routes.enrichment.ApolloAPI") as MockApollo, \
             patch("app.routes.enrichment.PDLAPI") as MockPDL:

            mock_apollo = MockApollo.return_value
            mock_apollo.enrich = AsyncMock(side_effect=Exception("Apollo down"))

            mock_pdl = MockPDL.return_value
            mock_pdl.enrich_company = AsyncMock(side_effect=Exception("PDL down"))

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/rad/quick-enrich", json={"email": "jane@honeycomb.io"})

            assert resp.status_code == 200
            data = resp.json()
            assert data["found"] is False

    @pytest.mark.asyncio
    async def test_prefers_pdl_display_name(self):
        """Should prefer PDL display_name over Apollo company_name."""
        with patch("app.routes.enrichment.ApolloAPI") as MockApollo, \
             patch("app.routes.enrichment.PDLAPI") as MockPDL:

            apollo_data = {**MOCK_APOLLO_RESULT, "company_name": "Honeycomb Inc."}
            mock_apollo = MockApollo.return_value
            mock_apollo.enrich = AsyncMock(return_value=apollo_data)

            mock_pdl = MockPDL.return_value
            mock_pdl.enrich_company = AsyncMock(return_value=MOCK_PDL_COMPANY_RESULT)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/rad/quick-enrich", json={"email": "jane@honeycomb.io"})

            data = resp.json()
            # PDL display_name "Honeycomb" preferred over Apollo "Honeycomb Inc."
            assert data["company_name"] == "Honeycomb"

    @pytest.mark.asyncio
    async def test_falls_back_to_apollo_when_pdl_empty(self):
        """Should use Apollo data when PDL returns empty."""
        with patch("app.routes.enrichment.ApolloAPI") as MockApollo, \
             patch("app.routes.enrichment.PDLAPI") as MockPDL:

            mock_apollo = MockApollo.return_value
            mock_apollo.enrich = AsyncMock(return_value=MOCK_APOLLO_RESULT)

            mock_pdl = MockPDL.return_value
            mock_pdl.enrich_company = AsyncMock(return_value={})

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/rad/quick-enrich", json={"email": "jane@honeycomb.io"})

            data = resp.json()
            assert data["found"] is True
            assert data["company_name"] == "Honeycomb"
            assert data["title"] == "VP of Infrastructure Engineering"

    @pytest.mark.asyncio
    async def test_cross_references_employee_count_uses_max(self):
        """Should use max(Apollo, PDL) for employee_count when both provide data."""
        with patch("app.routes.enrichment.ApolloAPI") as MockApollo, \
             patch("app.routes.enrichment.PDLAPI") as MockPDL:

            # Apollo says 5000, PDL says 1500 → should return 5000
            apollo_data = {**MOCK_APOLLO_RESULT, "estimated_num_employees": 5000}
            mock_apollo = MockApollo.return_value
            mock_apollo.enrich = AsyncMock(return_value=apollo_data)

            pdl_data = {**MOCK_PDL_COMPANY_RESULT, "employee_count": 1500}
            mock_pdl = MockPDL.return_value
            mock_pdl.enrich_company = AsyncMock(return_value=pdl_data)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/rad/quick-enrich", json={"email": "jane@honeycomb.io"})

            data = resp.json()
            assert data["employee_count"] == 5000

    @pytest.mark.asyncio
    async def test_cross_references_employee_count_falls_back_to_pdl(self):
        """Should fall back to PDL employee_count when Apollo has no count."""
        with patch("app.routes.enrichment.ApolloAPI") as MockApollo, \
             patch("app.routes.enrichment.PDLAPI") as MockPDL:

            # Apollo has no estimated_num_employees field
            mock_apollo = MockApollo.return_value
            mock_apollo.enrich = AsyncMock(return_value=MOCK_APOLLO_RESULT)

            mock_pdl = MockPDL.return_value
            mock_pdl.enrich_company = AsyncMock(return_value=MOCK_PDL_COMPANY_RESULT)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/rad/quick-enrich", json={"email": "jane@honeycomb.io"})

            data = resp.json()
            assert data["employee_count"] == 250  # PDL's value

    @pytest.mark.asyncio
    async def test_returns_employee_count_range(self):
        """Should return employee_count_range string from PDL data."""
        with patch("app.routes.enrichment.ApolloAPI") as MockApollo, \
             patch("app.routes.enrichment.PDLAPI") as MockPDL:

            mock_apollo = MockApollo.return_value
            mock_apollo.enrich = AsyncMock(return_value=MOCK_APOLLO_RESULT)

            pdl_data = {**MOCK_PDL_COMPANY_RESULT, "employee_count_range": "201-500"}
            mock_pdl = MockPDL.return_value
            mock_pdl.enrich_company = AsyncMock(return_value=pdl_data)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/rad/quick-enrich", json={"email": "jane@honeycomb.io"})

            data = resp.json()
            assert data["employee_count_range"] == "201-500"

    @pytest.mark.asyncio
    async def test_invalid_email_returns_400(self):
        """Should reject invalid email addresses."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/rad/quick-enrich", json={"email": "not-an-email"})

        assert resp.status_code == 422  # Pydantic validation error
