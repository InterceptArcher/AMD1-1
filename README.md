code# AMD1-1_Alpha: Personalization Pipeline

**A production-ready post-click personalization system for LinkedIn ebooks.**

## Overview

This system transforms visitor emails into personalized ebook experiences through:

1. **Multi-source Enrichment** - Apollo, PDL, Hunter, Tavily, ZoomInfo APIs
2. **Smart Resolution** - Priority-based field merging with fallback logic
3. **LLM Personalization** - Claude Haiku/Opus generates intro hooks + CTAs
4. **Compliance Validation** - Banned terms, claim checking, auto-correction
5. **PDF Generation** - Personalized ebook with signed download URLs
6. **Async Job Queue** - Supabase Edge Functions + polling

**Target SLA**: End-to-end in <60 seconds

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CLOUDFLARE (DNS/WAF)                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌──────────────────────────────┐    ┌──────────────────────────────────────┐
│     VERCEL (Next.js)         │    │        SUPABASE                      │
│  • Landing page + UTM parse  │───▶│  • Edge Functions (submit/status)   │
│  • Email + consent form      │    │  • PostgreSQL (jobs, outputs, data) │
│  • Loading states            │◀───│  • Storage (PDF bucket)             │
│  • Personalized content      │    │  • Queues (job processing)          │
└──────────────────────────────┘    └──────────────────────────────────────┘
                                                    │
                                                    ▼
                                    ┌──────────────────────────────────────┐
                                    │        RAILWAY (FastAPI)             │
                                    │  • /rad/enrich - orchestration       │
                                    │  • /rad/profile - data retrieval     │
                                    │  • /rad/pdf - ebook generation       │
                                    │                                      │
                                    │  Services:                           │
                                    │  • RADOrchestrator (5 API sources)   │
                                    │  • LLMService (Haiku/Opus)           │
                                    │  • ComplianceService                 │
                                    │  • PDFService                        │
                                    └──────────────────────────────────────┘
                                                    │
                    ┌───────────────┬───────────────┼───────────────┬───────────────┐
                    ▼               ▼               ▼               ▼               ▼
                 Apollo           PDL           Hunter          Tavily         ZoomInfo
                (People)       (People)        (Email)        (Search)       (Company)
```

### Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **CDN/WAF** | Cloudflare | DNS routing, DDoS protection |
| **Frontend** | Next.js 14 + TypeScript | Landing page, forms, polling |
| **Edge Functions** | Supabase Deno | Form submission, job status |
| **Backend** | FastAPI + Python | Enrichment, LLM, PDF generation |
| **Database** | Supabase PostgreSQL | Jobs, outputs, profiles |
| **Storage** | Supabase Storage | PDF file hosting |
| **LLM** | Claude Haiku/Opus | Personalization generation |

---

## Project Structure

```
/
├── frontend/                    # Next.js application
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx      # Root layout
│   │   │   ├── globals.css     # Tailwind styles
│   │   │   └── page.tsx        # Landing page with polling
│   │   └── components/
│   │       ├── EmailConsentForm.tsx
│   │       ├── LoadingSpinner.tsx
│   │       └── PersonalizedContent.tsx
│   └── __tests__/              # Jest tests (33 tests)
│
├── backend/                     # FastAPI application
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── routes/
│       │   └── enrichment.py   # /rad/* endpoints
│       └── services/
│           ├── supabase_client.py          # DB operations
│           ├── rad_orchestrator.py         # Multi-source enrichment
│           ├── enrichment_apis.py          # Apollo, PDL, Hunter, Tavily, ZoomInfo
│           ├── context_inference_service.py # Infers IT env, priority, challenge from data
│           ├── news_analysis_service.py     # Sentiment, entities, AI readiness from news
│           ├── executive_review_service.py  # AMD executive review generation
│           ├── llm_service.py              # Anthropic SDK integration
│           ├── compliance.py               # Content validation
│           └── pdf_service.py              # Ebook generation
│
├── supabase/
│   ├── config.toml             # Supabase configuration
│   ├── migrations/             # Database schema
│   │   ├── 20260127..._create_rad_tables.sql
│   │   └── 20260129..._add_personalization_tables.sql
│   └── functions/              # Edge Functions
│       ├── submit-form/        # POST form handler
│       └── get-job-status/     # GET polling endpoint
│
├── scripts/
│   ├── deploy-frontend-vercel.sh
│   ├── deploy-backend-railway.sh
│   ├── setup-supabase.sh
│   └── deploy-all.sh
│
└── docs/                        # Feature specifications
```

---

## Installation

### Prerequisites
- Node.js 18+ and npm
- Supabase account and project
- Anthropic API key (Claude access)
- Optional: Apollo.io and PeopleDataLabs API keys for real enrichment

### Setup

```bash
# 1. Frontend
cd frontend
npm install
npm run dev              # http://localhost:3000

# 2. Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. Run migrations
supabase link --project-ref YOUR_PROJECT_REF
supabase db push
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/rad/enrich` | POST | Start enrichment + personalization (accepts name, goal, persona, industry) |
| `/rad/profile/{email}` | GET | Retrieve finalized profile |
| `/rad/pdf/{email}` | POST | Generate personalized PDF |
| `/rad/deliver/{email}` | POST | Generate PDF and send via email (with download fallback) |
| `/rad/executive-review` | POST | Generate AMD Executive Review JSON (2-page assessment) |
| `/rad/executive-review-pdf` | POST | Generate and download Executive Review PDF with embedded JSON |
| `/rad/extract-pdf-json` | POST | Extract embedded JSON metadata from uploaded PDF |
| `/rad/health` | GET | Service health check |

**Example: Enrich an email**
```bash
curl -X POST http://localhost:8000/rad/enrich \
  -H "Content-Type: application/json" \
  -d '{"email": "john@acme.com"}'
```

---

## Features

### Enrichment Sources (5 APIs)

| Source | Data Type | Priority |
|--------|-----------|----------|
| **Apollo** | People: name, title, company, LinkedIn | 5 (highest) |
| **ZoomInfo** | Company: size, revenue, industry, tech stack | 4 |
| **PDL** | People: skills, experience, location | 3 |
| **Hunter** | Email: verification, deliverability | 2 |
| **Tavily** | Context: company news, search results | 1 |

### LLM Personalization

- **Model**: Claude Haiku (default) or Opus (high-quality profiles)
- **Output**: JSON with `intro_hook` + `cta`
- **Constraints**: Intro ≤200 chars, CTA ≤150 chars
- **Retry**: Auto-fixes malformed JSON

### Compliance Layer

**Blocked content:**
- Unsubstantiated claims ("guaranteed", "proven", "#1")
- Superlatives without evidence ("best", "fastest")
- Urgency tactics ("act now", "limited time")
- Competitive attacks

**Auto-correction:** Removes terms or falls back to safe copy.

### Minimal-Input Enrichment-First Design (v2)

The form now collects only **email** (required) and **journey stage** (optional). All other data is enriched automatically:

**How it works:**
1. User enters work email + consents
2. Backend enriches via 5 APIs (Apollo, PDL, Hunter, GNews, ZoomInfo)
3. **Context Inference Service** analyzes enrichment data to infer:
   - IT environment maturity (traditional/modernizing/modern)
   - Business priority (cost/performance/AI adoption)
   - Primary challenge (legacy/integration/skills/governance)
   - Urgency level (low/medium/high)
   - Journey stage (if not user-provided)
4. **News Analysis Service** extracts deeper insights:
   - Sentiment analysis (positive/negative/neutral)
   - Entity extraction (technologies, competitors, partners)
   - AI readiness stage (none/exploring/piloting/deployed)
   - Crisis detection (workforce, regulatory, financial, security)
5. Executive review is generated with full enrichment context

**Rationale:** Reducing form fields from 11 to 1 required field eliminates friction while enrichment APIs provide the same (or richer) data. The inference services use signal-based heuristics to determine what the user would have selected manually, resulting in comparable personalization quality with significantly reduced user effort.

**Previous design (v1):** 11 required fields including name, company, company size, industry, role, journey stage, IT environment, business priority, and challenge. This approach provided accurate self-reported data but created form friction.

### PDF Generation & Delivery

- **Dynamic Ebook Generation**: HTML template with personalization slots (name, company, title, industry, intro hook, CTA)
- **PDF Engine**: ReportLab with WeasyPrint as optional upgrade for production quality
- **Storage**: PDFs stored in Supabase Storage with signed URLs (7-day expiry)
- **Email Delivery**: Sends personalized PDF to user's email (supports SendGrid, Resend, SMTP)
- **Download Fallback**: Direct download button always available if email delivery fails
- **Fallback**: Minimal valid PDF generated even without PDF libraries installed

### Typography

The PDF ebook uses AMD-aligned typography:

| Purpose | Font | Notes |
|---------|------|-------|
| **Headings** | Roboto Condensed | Condensed sans-serif for impact (Google Fonts) |
| **AMD Logo** | Gill Sans | Classic humanist sans with fallbacks for Linux |
| **Body Text** | Source Sans 3 | Clean geometric sans-serif (Google Fonts) |

**Brand Colors:**
- Primary Accent: `#00c8aa` (AMD Cyan)
- Dark Background: `#0a0a12`
- Text: `#f0f0f5`

### Executive Review JSON-Based PDFs

**NEW**: Generate structured 2-page AMD Executive Review assessments with embedded JSON metadata.

**Key Features:**
- **JSON-First Architecture**: All content is structured JSON (advantages, risks, recommendations)
- **Embedded Metadata**: JSON data is embedded as PDF metadata for programmatic access
- **Extraction API**: Upload any generated PDF to extract the original JSON data
- **Few-Shot LLM Generation**: Uses Claude with stage-specific examples (Observer/Challenger/Leader)

**Workflow:**
1. Submit company details, IT environment, business priority, and challenge
2. System maps inputs to AMD taxonomy (Stage, Segment, Persona)
3. Claude generates JSON with:
   - 2 Strategic Advantages
   - 2 Risks to Manage
   - 3 Recommended Next Steps
   - Relevant case study selection (KT Cloud, Smurfit Westrock, or PQR)
4. PDF is rendered with AMD branding + embedded JSON metadata
5. Users can extract JSON later via `/rad/extract-pdf-json`

**JSON Structure:**
```json
{
  "company_name": "Acme Corp",
  "stage": "Challenger",
  "stage_sidebar": "58% of Challengers are currently undertaking modernization initiatives.",
  "advantages": [
    {
      "headline": "Performance gains from upgrading core systems",
      "description": "Modernizing high-volume workloads improves responsiveness across operations."
    }
  ],
  "risks": [...],
  "recommendations": [...],
  "case_study": "KT Cloud Expands AI Power with AMD Instinct Accelerators",
  "case_study_description": "..."
}
```

**API Usage:**

Generate JSON only (minimal input - just email):
```bash
curl -X POST http://localhost:8000/rad/executive-review \
  -H "Content-Type: application/json" \
  -d '{"email": "john@acme.com", "goal": "consideration"}'
```

The endpoint enriches via APIs, infers context, and generates the executive review automatically.

Generate and download PDF:
```bash
curl -X POST http://localhost:8000/rad/executive-review-pdf \
  -H "Content-Type: application/json" \
  -d '{...}' \
  --output executive_review.pdf
```

Extract JSON from existing PDF:
```bash
curl -X POST http://localhost:8000/rad/extract-pdf-json \
  -F "file=@executive_review.pdf"
```

**Use Cases:**
- Programmatic PDF analysis and data extraction
- Integration with CRM systems (extract JSON, sync to Salesforce)
- A/B testing of content variations (compare JSON structures)
- Audit trails (track what content was delivered to each company)

### AcroForm PDF Personalization (In Progress)

A more advanced PDF personalization approach using AcroForm fields:

**Methodology:**
1. Designer creates PDF template with editable AcroForm text fields at personalization points
2. Backend fills fields with LLM-generated content based on reader profile
3. PDF is flattened so fields become static text (no visible form boxes)
4. Result: Pixel-perfect branded PDF with personalized content

**Three Personalization Points:**
| Location | Field | Personalized By |
|----------|-------|-----------------|
| Page 1 (Intro) | `personalized_hook` | Role, company news, buying stage |
| Pages 11-13 (Case Studies) | `case_study_X_framing` | Industry mapping |
| Pages 14, 16 (CTA) | `personalized_cta_*` | Buying stage, role |

**Content Library:** 16 markdown files in `/backend/assets/content/`:
- 9 industry guides (Healthcare, Manufacturing, Financial Services, etc.)
- 2 job function guides (BDM, ITDM)
- 4 segment guides (Enterprise, Mid-Market, SMB, Government)

**Status:** Waiting for designer to deliver `amdtemplate_with_fields.pdf`. See `backend/assets/DESIGNER_SPEC.md` for requirements.

---

## Environment Variables

### Vercel (Frontend)
```bash
NEXT_PUBLIC_API_URL=https://your-backend.railway.app
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE=eyJ...          # Server-side only
```

### Railway (Backend)
```bash
# Required
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...                   # service_role key
ANTHROPIC_API_KEY=sk-ant-...

# Email Delivery (pick one - uses mock if none configured)
SENDGRID_API_KEY=SG...               # SendGrid
RESEND_API_KEY=re_...                # Resend
# Or SMTP:
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASS=...
EMAIL_FROM=noreply@yourdomain.com
EMAIL_FROM_NAME=Your Ebook

# Enrichment APIs (optional - uses mocks if missing)
APOLLO_API_KEY=...
PDL_API_KEY=...
HUNTER_API_KEY=...
TAVILY_API_KEY=...
ZOOMINFO_API_KEY=...

# Development
MOCK_SUPABASE=true                   # Enable mock mode for local testing
```

### Supabase (Edge Functions)
```bash
SUPABASE_URL           # Auto-set
SUPABASE_SERVICE_ROLE_KEY  # Auto-set
RAILWAY_BACKEND_URL=https://your-backend.railway.app
```

---

## Database Schema

### Core Tables

```sql
-- Job tracking
personalization_jobs (id, email, domain, cta, status, created_at, completed_at)

-- LLM outputs
personalization_outputs (job_id, intro_hook, cta, model_used, tokens_used, compliance_passed)

-- PDF delivery
pdf_deliveries (job_id, pdf_url, storage_path, delivery_status)

-- Enrichment data
raw_data (email, source, payload, fetched_at)
staging_normalized (email, normalized_fields, status)
finalize_data (email, normalized_data, personalization_intro, personalization_cta)
```

Run migrations:
```bash
supabase db push
```

---

## Deployment

### Automated Deployment

```bash
# Deploy everything
./scripts/deploy-all.sh

# Or individually
./scripts/setup-supabase.sh
./scripts/deploy-backend-railway.sh
./scripts/deploy-frontend-vercel.sh
```

### Manual Deployment

**Vercel:**
```bash
cd frontend
vercel --prod
```

**Railway:**
```bash
cd backend
railway up
```

---

## Testing

### Frontend (Jest)
```bash
cd frontend
npm test              # 37 tests
npm run test:coverage
```

### Backend (Pytest)
```bash
cd backend
pytest                # All tests
pytest --cov=app      # With coverage
```

---

## Roadmap

### Phase 1 - Alpha (Complete)
- ✅ Next.js frontend with email form
- ✅ FastAPI backend with /rad/* endpoints
- ✅ Multi-source enrichment (5 APIs)
- ✅ Real Anthropic SDK integration
- ✅ Compliance validation layer
- ✅ PDF generation service
- ✅ Supabase Edge Functions
- ✅ Deployment scripts

### Phase 2 - Beta (Enrichment Improvements)
- [x] **Two-Phase Enrichment** - Phase 1 runs person + company APIs in parallel, Phase 2 runs GNews with the resolved company name for better news search results (e.g., "JPMorgan Chase" instead of "jpmorgan")
- [x] **Industry Normalization** - Maps 40+ raw industry strings from APIs to 12 canonical categories for consistent case study matching and context inference
- [x] **News Analysis in Main Enrichment** - Sentiment, AI readiness stage, crisis detection, and entity extraction now run during regular enrichment (not just executive review)
- [x] **Smart Company Name Resolution** - Prefers PDL `display_name` over legal entity name (e.g., "Google" instead of "Alphabet Inc."), with 6-level fallback chain
- [x] **Tech Stack Extraction from Tags** - Categorizes PDL company tags into cloud/AI-ML/traditional/security/data signals for better IT environment inference
- [x] **Department-Aware Persona Inference** - Uses Apollo departments data to disambiguate ITDM vs BDM when job title is ambiguous (e.g., "Director")
- [x] **Enrichment Completeness Report** - Weighted scoring (critical 3x, important 2x, nice-to-have 1x) with actionable missing-field lists replaces the opaque quality score
- [ ] Supabase Queues for durable jobs
- [ ] Batch enrichment endpoint
- [ ] Rate limiting + circuit breakers
- [ ] OpenTelemetry instrumentation
- [ ] Marketing automation webhook

### Phase 3 - Production
- [ ] A/B testing for LLM prompts
- [ ] Multi-language support
- [ ] Advanced PDF templates
- [ ] Chaos testing suite
- [ ] Cost optimization dashboard

---

## Security

Per [CLAUDE.md](CLAUDE.md):

- ✅ No secrets in code
- ✅ No `.env` files committed
- ✅ Input validation (Pydantic + email regex)
- ✅ Parameterized queries (Supabase SDK)
- ✅ Compliance checks on LLM output

---

## Contributing

1. Follow [CLAUDE.md](CLAUDE.md) rules
2. Write tests first (TDD)
3. Keep code simple and focused
4. Document new features in README

---

## License

ISC
