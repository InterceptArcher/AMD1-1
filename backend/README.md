# Backend Configuration for AMD1-1 Alpha

## Environment Variables (Secrets)

This backend requires the following secrets to be provided via environment variables:

### Supabase
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Supabase anon key (or service role key for backend)
- `SUPABASE_JWT_SECRET`: JWT secret for token validation

### External APIs (Optional; mocked in alpha)
- `APOLLO_API_KEY`: Apollo.io API key
- `PDL_API_KEY`: People Data Labs API key
- `HUNTER_API_KEY`: Hunter.io API key
- `GNEWS_API_KEY`: GNews API key

### LLM Integration
- `ANTHROPIC_API_KEY`: Anthropic API key (for Claude Haiku inference)

### Application
- `DEBUG`: Set to "true" for development mode (default: "false")
- `LOG_LEVEL`: Logging level (default: "INFO")

## Database Schema

The following Supabase tables are required. Create these via SQL in Supabase console:

### raw_data
Stores API responses from external providers.

```sql
CREATE TABLE raw_data (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    email VARCHAR(255) NOT NULL,
    source VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    fetched_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_raw_data_email ON raw_data(email);
CREATE INDEX idx_raw_data_source ON raw_data(source);
```

### staging_normalized
Tracks enrichment progress during resolution phase.

```sql
CREATE TABLE staging_normalized (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    email VARCHAR(255) NOT NULL UNIQUE,
    normalized_fields JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'resolving',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_staging_email ON staging_normalized(email);
```

### finalize_data
Final enriched profiles ready for frontend consumption.

```sql
CREATE TABLE finalize_data (
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

## Running the Backend

### Development

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Set environment variables (use .env.local for development)
export SUPABASE_URL=<your_url>
export SUPABASE_KEY=<your_key>

# Run locally
uvicorn app.main:app --reload --port 8000
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=app

# Run specific test file
pytest tests/test_enrichment_endpoints.py

# Run async tests
pytest tests/test_rad_orchestrator.py -v
```

### Production

```bash
# Install dependencies
pip install -r requirements.txt

# Run with production settings
DEBUG=false LOG_LEVEL=INFO uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Endpoints

### POST /rad/enrich
Kick off enrichment for an email.

Request:
```json
{
  "email": "user@company.com",
  "domain": "company.com"  // optional
}
```

Response:
```json
{
  "job_id": "uuid",
  "email": "user@company.com",
  "status": "completed",
  "created_at": "2025-01-27T00:00:00"
}
```

### GET /rad/profile/{email}
Retrieve enriched profile for an email.

Response:
```json
{
  "email": "user@company.com",
  "normalized_profile": {
    "first_name": "John",
    "last_name": "Doe",
    "company": "Acme",
    "title": "VP Sales",
    "industry": "SaaS",
    "country": "US",
    "data_quality_score": 0.85
  },
  "personalization": {
    "intro_hook": "Hi John...",
    "cta": "Let's chat..."
  },
  "last_updated": "2025-01-27T00:00:00"
}
```

### GET /rad/health
Service health check.

Response:
```json
{
  "status": "healthy",
  "service": "rad_enrichment",
  "timestamp": "2025-01-27T00:00:00"
}
```

## Architecture

### Services Layer
- `SupabaseClient`: Data persistence abstraction
- `RADOrchestrator`: Coordinates enrichment (fetch → resolve → finalize)
- `LLMService`: Generates personalization content

### Routes Layer
- `enrichment.py`: FastAPI endpoints for enrichment API

### Models Layer
- `schemas.py`: Pydantic request/response schemas

## Extending for Production

1. **Real API Calls**: Replace mock methods in `RADOrchestrator` with real httpx calls to Apollo, PDL, Hunter, GNews
2. **Resolution Rules**: Enhance `_resolve_profile()` with council-of-LLMs logic and conflict resolution
3. **Personalization**: Implement real Claude Haiku prompts in `LLMService.generate_personalization()`
4. **Error Handling**: Add retry logic, circuit breakers, dead-letter queues for failed enrichments
5. **Async Processing**: Convert to async job queue (e.g., Celery + Redis) for large-scale enrichment
6. **Monitoring**: Add OpenTelemetry instrumentation for production observability

## Notes for Development

- All external API calls are mocked in alpha for fast testing
- Supabase client uses environment variables (never hardcoded)
- Tests use mocked Supabase; no real DB calls in unit tests
- FastAPI dependency injection allows easy swapping of mocks in tests
- Async support is built in; all service methods are async-ready
