# AMD1-1_Alpha: Personalization Pipeline

**A minimal, test-driven implementation of RAD enrichment + LLM personalization for LinkedIn ebooks.**

## 📋 Overview

This repo transforms RAD (Rapid Automated Data) orchestration into an alpha pipeline that:

1. **Enriches** email/domain via external APIs (Apollo, PDL, Hunter, GNews)
2. **Resolves** profiles using a council-of-LLMs + fallback logic
3. **Personalizes** LinkedIn ebook content with Haiku-class LLM (1-2 sec intro, CTA)
4. **Persists** normalized data in Supabase for frontend consumption

**Target SLA**: End-to-end enrichment + personalization in <60 seconds.

---

## 🏗 Architecture

### Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js + TypeScript | Vercel-hosted SPA for ebook rendering |
| **Backend** | FastAPI + Python | Railway-hosted REST API for enrichment |
| **Database** | Supabase (PostgreSQL) | Stores raw_data, staging_normalized, finalize_data |
| **LLM** | Claude Haiku (Anthropic) | Fast inference for intro + CTA generation |

### Data Flow

```
Email Input
    ↓
POST /rad/enrich
    ↓
[RADOrchestrator]
  ├→ Fetch raw_data (Apollo, PDL, Hunter, GNews) → store in raw_data table
  ├→ Resolution logic (merge, conflict resolution) → staging_normalized
  ├→ LLMService.generate_personalization() → intro_hook, cta
  └→ Write finalize_data table
    ↓
GET /rad/profile/{email}
    ↓
[Frontend] Reads finalize_data → Renders personalized ebook
```

### Module Layout

```
/backend/
├── app/
│   ├── main.py              # FastAPI app initialization
│   ├── config.py            # Environment config (Supabase, LLM, APIs)
│   ├── models/
│   │   └── schemas.py       # Pydantic request/response schemas
│   ├── services/
│   │   ├── supabase_client.py    # Data access layer (raw_data, staging, finalize)
│   │   ├── rad_orchestrator.py   # Enrichment pipeline orchestration
│   │   └── llm_service.py        # Personalization content generation
│   └── routes/
│       └── enrichment.py    # FastAPI endpoints
├── tests/
│   ├── conftest.py          # Pytest fixtures (mocked Supabase)
│   ├── test_enrichment_endpoints.py
│   ├── test_supabase_client.py
│   ├── test_rad_orchestrator.py
│   └── test_llm_service.py
├── requirements.txt         # Python dependencies
├── pyproject.toml          # Build config + tool settings
├── README.md               # Backend-specific docs
└── scripts/
    └── migrate-supabase.sh # DB schema initialization
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- pip / venv
- Supabase project
- Environment variables set (see [backend/README.md](backend/README.md))

### Install & Run

```bash
# Backend
cd backend
pip install -r requirements.txt

# Set environment variables
export SUPABASE_URL=<your_url>
export SUPABASE_KEY=<your_key>

# Run FastAPI server
uvicorn app.main:app --reload --port 8000

# In another terminal, run tests
pytest --cov=app
```

### API Usage

**Enrich an email:**
```bash
curl -X POST http://localhost:8000/rad/enrich \
  -H "Content-Type: application/json" \
  -d '{"email": "user@company.com"}'
```

**Retrieve profile:**
```bash
curl http://localhost:8000/rad/profile/user@company.com
```

**Health check:**
```bash
curl http://localhost:8000/rad/health
```

---

## 🧪 Testing

All tests use **mocked Supabase** and **mocked external APIs**—no real calls, instant feedback.

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_enrichment_endpoints.py -v

# Run async tests
pytest tests/test_rad_orchestrator.py::TestRADOrchestrator -v
```

### Test Coverage

- ✅ **Endpoints** (POST /rad/enrich, GET /rad/profile)
- ✅ **Data access** (Supabase CRUD operations)
- ✅ **Enrichment logic** (API mocking, profile resolution)
- ✅ **LLM service** (personalization generation)
- ✅ **Error handling** (invalid emails, not found, DB failures)

---

## 📊 Database Schema

Three tables in Supabase PostgreSQL:

### `raw_data`
Stores responses from external APIs.
```sql
id | email | source | payload | fetched_at
```

### `staging_normalized`
Tracks enrichment progress.
```sql
id | email | normalized_fields | status | created_at | updated_at
```

### `finalize_data`
Final profiles ready for frontend.
```sql
id | email | normalized_data | personalization_intro | personalization_cta | resolved_at
```

See [backend/README.md](backend/README.md) for full SQL schema.

---

## 🔌 Extending for Production

### Real API Calls
Replace mock methods in `RADOrchestrator`:
```python
async def _fetch_apollo(self, email: str, domain: str):
    # Use httpx + APOLLO_API_KEY instead of synthetic data
    async with httpx.AsyncClient() as client:
        response = await client.get(...)
        return response.json()
```

### Resolution Logic
Enhance `_resolve_profile()` with council-of-LLMs:
```python
def _resolve_profile(self, email, raw_data):
    # Compare contradictions between Apollo/PDL
    # Ask Claude for conflict resolution
    # Assign trust scores per source
    # Return merged profile
```

### Real LLM Prompts
Implement in `LLMService.generate_personalization()`:
```python
async def generate_personalization(self, profile):
    prompt = f"""
    Generate a personalized intro (1-2 sentences) and CTA for:
    Name: {profile['first_name']}
    Company: {profile['company']}
    Title: {profile['title']}
    """
    # Call Anthropic API with structured output
    response = await client.messages.create(...)
    return {"intro_hook": ..., "cta": ...}
```

### Async Job Queue
For large-scale enrichment:
- Move enrichment to async job queue (Celery + Redis)
- Return job_id immediately, poll for status
- Implement exponential backoff for API retries

### Monitoring & Observability
- Add OpenTelemetry instrumentation
- Log all enrichment milestones
- Track data quality scores over time
- Monitor LLM latency and cost

---

## 🔐 Security & Secrets

Following [CLAUDE.md](CLAUDE.md):

- ✅ **No secrets in code**: All API keys loaded from environment
- ✅ **No `.env` files committed**: Use platform secret managers
- ✅ **Supabase RLS policies**: Restrict data access by user
- ✅ **Input validation**: Pydantic schemas + email verification
- ✅ **No SQL injection**: Using Supabase SDK (parameterized queries)

Required environment variables:
```bash
SUPABASE_URL
SUPABASE_KEY
SUPABASE_JWT_SECRET
ANTHROPIC_API_KEY
APOLLO_API_KEY       (optional in alpha)
PDL_API_KEY          (optional in alpha)
HUNTER_API_KEY       (optional in alpha)
GNEWS_API_KEY        (optional in alpha)
```

---

## 📚 Documentation

- [backend/README.md](backend/README.md) — Backend setup, API docs, configuration
- [setup/stack.json](setup/stack.json) — Infrastructure stack definition
- [docs/](docs/) — Feature specs and technical architecture notes
- [CLAUDE.md](CLAUDE.md) — Engineering rulebook for AI code generation

---

## 🛣 Roadmap

**Phase 1 (Current - Alpha)**
- ✅ Basic FastAPI endpoints
- ✅ Mocked API calls + Supabase integration
- ✅ Comprehensive pytest suite
- ✅ Placeholder LLM service

**Phase 2 (Beta)**
- Real Apollo, PDL, Hunter, GNews API calls
- Council-of-LLMs conflict resolution
- Real Claude Haiku prompts
- Async job queue for bulk enrichment

**Phase 3 (Production)**
- Advanced fallback logic
- Multi-language support
- Rate limiting + circuit breakers
- Full observability (traces, metrics, logs)
- Deployment automation (Railway, Vercel, Supabase)

---

## 🤝 Contributing

1. Follow the rules in [CLAUDE.md](CLAUDE.md)
2. Write tests first (TDD discipline)
3. Keep code idiomatic and well-commented
4. Use existing FastAPI + Supabase setup (no new infrastructure)

---

## 📝 License

ISC