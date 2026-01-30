# Quick Start Guide: AMD1-1 Alpha

Get the personalization pipeline running in 5 minutes.

---

## Prerequisites

- Python 3.10+
- Supabase account (free tier OK for alpha)
- Git

---

## Step 1: Clone & Setup

```bash
# Clone the repo (you already have it)
cd /workspaces/AMD1-1_Alpha

# Create Python venv
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
cd backend
pip install -r requirements.txt
```

---

## Step 2: Get Supabase Credentials

1. Go to [supabase.com](https://supabase.com) and create a project
2. In **Settings → API**, copy:
   - `Project URL` → Set as `SUPABASE_URL`
   - `anon public` key → Set as `SUPABASE_KEY`
   - `JWT Secret` → Set as `SUPABASE_JWT_SECRET` (optional for alpha)

---

## Step 3: Create Database Tables

In Supabase **SQL Editor**, run:

```sql
-- raw_data table
CREATE TABLE IF NOT EXISTS raw_data (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    email VARCHAR(255) NOT NULL,
    source VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    fetched_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_raw_data_email ON raw_data(email);
CREATE INDEX idx_raw_data_source ON raw_data(source);

-- staging_normalized table
CREATE TABLE IF NOT EXISTS staging_normalized (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    email VARCHAR(255) NOT NULL UNIQUE,
    normalized_fields JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'resolving',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_staging_email ON staging_normalized(email);

-- finalize_data table
CREATE TABLE IF NOT EXISTS finalize_data (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    email VARCHAR(255) NOT NULL,
    normalized_data JSONB NOT NULL,
    personalization_intro TEXT,
    personalization_cta TEXT,
    data_sources TEXT[] DEFAULT '{}',
    resolved_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_finalize_email ON finalize_data(email);
CREATE INDEX idx_finalize_resolved_at ON finalize_data(resolved_at DESC);
```

---

## Step 4: Set Environment Variables

```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="eyJhbGciOiJIUzI1NiIsInR..."
export SUPABASE_JWT_SECRET="your-jwt-secret-here"
export DEBUG="true"
export LOG_LEVEL="INFO"
```

---

## Step 5: Run Tests

```bash
cd backend
pytest --cov=app -v

# Should see: 52 passed in ~1s
```

---

## Step 6: Start the Server

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Open [http://localhost:8000/docs](http://localhost:8000/docs) to see interactive API docs.

---

## Step 7: Test the Endpoints

### Enrich an email

```bash
curl -X POST http://localhost:8000/rad/enrich \
  -H "Content-Type: application/json" \
  -d '{"email": "john@acme.com"}'

# Response:
# {
#   "job_id": "550e8400-e29b-41d4-a716-446655440000",
#   "email": "john@acme.com",
#   "status": "completed",
#   "created_at": "2025-01-27T..."
# }
```

### Get the profile

```bash
curl http://localhost:8000/rad/profile/john@acme.com

# Response:
# {
#   "email": "john@acme.com",
#   "normalized_profile": {
#     "first_name": "John",
#     "company": "Company from acme.com",
#     "title": "VP of Sales",
#     "industry": "SaaS",
#     "country": "US",
#     "data_quality_score": 1.0
#   },
#   "personalization": {
#     "intro_hook": "Hi John, I noticed you're building out sales infrastructure...",
#     "cta": "Ready to see how other VPs of Sales are scaling? Let's chat..."
#   },
#   "last_updated": "2025-01-27T..."
# }
```

### Health check

```bash
curl http://localhost:8000/rad/health

# Response:
# {
#   "status": "healthy",
#   "service": "rad_enrichment",
#   "timestamp": "2025-01-27T..."
# }
```

---

## What's Happening?

1. **POST /rad/enrich** kicks off the enrichment pipeline:
   - Fetches data from 4 sources (Apollo, PDL, Hunter, GNews) — **mocked in alpha**
   - Applies resolution logic (merge + priority ranking)
   - Generates personalization (intro + CTA) — **synthetic in alpha**
   - Writes finalized profile to Supabase `finalize_data` table

2. **GET /rad/profile/{email}** reads back the enriched profile from `finalize_data`

3. **GET /rad/health** verifies Supabase is connected

---

## Next Steps

### For Development

- **Read tests** in `backend/tests/` to understand the data flow
- **Replace mock methods** in `backend/app/services/rad_orchestrator.py` with real API calls
- **Design prompts** in `backend/app/services/llm_service.py` for Claude Haiku integration
- **Add async job queue** for bulk enrichment (Celery + Redis)

### For Deployment

- **Railway**: Set `SUPABASE_*` environment variables → Deploy `backend/`
- **Vercel**: Build Next.js frontend → Deploy frontend to Vercel
- **Supabase**: Run migrations via `/backend/scripts/migrate-supabase.sh`

---

## Architecture Reference

```
Email Input
    ↓
POST /rad/enrich
    ↓
RADOrchestrator:
  1. Fetch raw_data (Apollo, PDL, Hunter, GNews)
  2. Resolve profile (merge, priority ranking)
  3. Generate personalization (intro + CTA)
    ↓
Write to Supabase finalize_data
    ↓
GET /rad/profile/{email}
    ↓
Return normalized profile + personalization
    ↓
Frontend renders personalized ebook
```

---

## Debugging

### Check if Supabase is connected

```bash
curl http://localhost:8000/rad/health
```

### See detailed logs

```bash
export LOG_LEVEL="DEBUG"
uvicorn app.main:app --reload --port 8000
```

### Run a single test

```bash
pytest tests/test_enrichment_endpoints.py::TestEnrichmentEndpoint::test_enrich_valid_email -v
```

### Check database from Supabase dashboard

1. Go to Supabase console
2. Click **SQL Editor**
3. Run:
   ```sql
   SELECT * FROM finalize_data ORDER BY resolved_at DESC LIMIT 1;
   ```

---

## Common Issues

### "SUPABASE_URL not set"

```bash
# Make sure env vars are exported
export SUPABASE_URL="https://..."
export SUPABASE_KEY="..."

# Or add to .env.local and source it
source .env.local
```

### "Module not found: app"

```bash
# Run from backend/ directory
cd backend
uvicorn app.main:app --reload
```

### "Connection refused" to Supabase

- Check your `SUPABASE_URL` is correct (should be `https://...supabase.co`)
- Check internet connection
- Verify Supabase project is active

### Tests failing

```bash
# Reinstall pytest plugins
pip install -U pytest pytest-asyncio pytest-cov

# Run with verbose output
pytest -vv tests/
```

---

## Documentation

- **Full README**: [README.md](../README.md)
- **Backend API Docs**: [backend/README.md](backend/README.md)
- **Implementation Summary**: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- **Engineering Rules**: [CLAUDE.md](CLAUDE.md)

---

## Next: Make It Production-Ready

Once you're comfortable with the alpha:

1. **Real API Calls** — Integrate Apollo, PDL, Hunter, GNews SDKs
2. **Council-of-LLMs** — Call Claude to resolve conflicts
3. **Real Prompts** — Design intro/CTA prompts for Claude Haiku
4. **Deployment** — Railway (backend), Vercel (frontend), Supabase (DB)

---

**Questions?** Check the docs or run tests to understand the flow.

**Ready to extend?** See `backend/app/services/rad_orchestrator.py` for where to plug in real API calls.
