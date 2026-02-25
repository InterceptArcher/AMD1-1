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
│   │       ├── EmailConsentForm.tsx  # Wizard orchestrator
│   │       ├── LoadingSpinner.tsx
│   │       ├── PersonalizedContent.tsx
│   │       └── wizard/
│   │           ├── wizardTypes.ts        # Types, constants, validators
│   │           ├── SelectionCard.tsx     # Reusable card primitive
│   │           ├── WizardProgressDots.tsx
│   │           ├── StepContainer.tsx     # Animated step wrapper
│   │           └── steps/
│   │               ├── StepAboutYou.tsx  # Step 1
│   │               ├── StepCompany.tsx   # Step 2
│   │               └── StepRole.tsx      # Step 3
│   └── __tests__/              # Jest tests (33 tests)
│
├── backend/                     # FastAPI application
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── routes/
│       │   └── enrichment.py   # /rad/* endpoints
│       └── services/
│           ├── supabase_client.py    # DB operations
│           ├── rad_orchestrator.py   # Multi-source enrichment
│           ├── enrichment_apis.py    # Apollo, PDL, Hunter, Tavily, ZoomInfo
│           ├── llm_service.py        # Anthropic SDK integration
│           ├── compliance.py         # Content validation
│           └── pdf_service.py        # Ebook generation
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

### Multi-Step Wizard UX

Replaced the original single-page dropdown form with a 4-step guided card-based wizard. Same data collected, entirely different experience.

**Rationale:** Stakeholders found the original 11-field form ("a wall of dropdowns") unintuitive. The wizard breaks the experience into focused steps with visual card selections, progress dots, and slide transitions. Questions are framed as relatable scenarios rather than survey-style categories — users describe their situation rather than filling in database fields.

**The 4 Steps:**
| Step | Title | What it collects |
|------|-------|-----------------|
| 1 | "Let's get started" | First name, last name, work email |
| 2 | "About your company" | Company name, size (3 cards), industry (12 tiles) |
| 3 | "What's your role?" | Role group (8 cards, auto-advances) |
| 4 | "Your situation" | IT environment + priority + challenge + consent |

**UX Enhancements:**
- **Auto-advance** on single-select steps (Role) — click a card, see it glow, auto-transition to next step
- **Thinking micro-moments** — contextual messages ("Tailoring for your role...") shown between step transitions with spinner animation
- **Email domain company extraction** — typing `john@stripe.com` auto-fills "Stripe" as company name, with a "Detected from your email" banner on Step 2
- **Social proof lines** — after each card selection, contextual validation appears ("58% of companies are actively in this stage")
- **Assessment preview** — before submit, a summary card shows the deduced profile ("Tech Executive at Stripe — Challenger Stage — Focus: Free up budget")
- **Adaptive challenge filtering** — if user selects "Modern" IT environment, "Legacy systems" challenge is hidden (contradicts their situation)
- **Scenario-style framing** — "Which sounds most like your day-to-day?" instead of "Select your IT environment"

**Architecture:** Zero backend changes. Same `UserInputs` interface and `onSubmit` contract. All card values map to existing backend mapping functions. Components organized under `frontend/src/components/wizard/`.

**Key files:**
- `wizard/wizardTypes.ts` — types, card option constants, validators, social proof messages, helpers
- `wizard/SelectionCard.tsx` — reusable clickable card (sm/md/lg sizes, selected state with cyan glow)
- `wizard/WizardProgressDots.tsx` — progress indicator with connecting lines
- `wizard/StepContainer.tsx` — animated wrapper (slide-right forward, slide-left back)
- `wizard/steps/StepAboutYou.tsx` — Step 1 with email domain extraction
- `wizard/steps/StepCompany.tsx` — Step 2 with "detected from email" banner
- `wizard/steps/StepRole.tsx` — Step 3 with auto-advance callback
- `EmailConsentForm.tsx` — wizard orchestrator with Steps 4 inline, thinking moments, social proof, assessment preview

### Context-Aware Wizard

The wizard now reacts to enrichment data in real time, making the entire form context-aware rather than static.

**What changed:**

| Feature | Before | After |
|---------|--------|-------|
| Employee count | PDL only (single source, often inaccurate) | `max(Apollo, PDL)` cross-reference for accuracy |
| Role pre-fill | Not used | Seniority + title → role auto-mapped (e.g., VP + "Infrastructure Engineering" → Tech Leadership) |
| Company logo | Checkmark icon | Clearbit logo from email domain (free, no key), graceful fallback |
| Step titles | Static ("About your company") | Dynamic ("About Honeycomb") with company name |
| Company summary | Not shown | 1-2 line PDL summary in banner |
| Employee display | Raw count ("250 employees") | Range preferred when available ("201-500 employees") |
| Live preview | None until Step 4 | Progressive preview card on Steps 2-3 builds as fields fill |
| Role suggestion | None | Hint text "Suggested from your profile — change anytime" |

**Rationale:**
- **Cross-referenced employee count** prevents single-source inaccuracies (e.g., PDL reporting 1,500 when Apollo reports 5,000 for the same company)
- **Role pre-selection** reduces clicks by 1 step for enriched users without auto-skipping — users still see their selection and can change it
- **Company logo + summary** creates recognition and builds trust (users see "we know your company")
- **Live preview card** gives progressive feedback so users understand what they're building before they reach Step 4
- **Dynamic step titles** make the form feel personalized from the moment enrichment fires

**Key files:**
- `backend/app/services/enrichment_apis.py` — Apollo now returns `estimated_num_employees` raw integer
- `backend/app/routes/enrichment.py` — Cross-references counts, returns `employee_count_range`
- `frontend/src/components/wizard/wizardTypes.ts` — `mapSeniorityToRole()`, `extractFullDomainFromEmail()`, updated `getAdaptiveStepTitle()`
- `frontend/src/components/wizard/LivePreviewCard.tsx` — Progressive assessment preview
- `frontend/src/components/wizard/steps/StepCompany.tsx` — Logo, summary, range display
- `frontend/src/components/wizard/steps/StepRole.tsx` — Suggested role hint

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

# Executive Review tests only (88 tests)
pytest tests/test_executive_review_service.py -v
```

### Executive Review Test Coverage
| Test Class | Count | Covers |
|------------|-------|--------|
| TestMappingFunctions | 25 | All 7 mapping functions (segment, persona, stage, sidebar, priority, challenge, industry) |
| TestCaseStudySelection | 20 | Priority-based, industry-based, challenge-based, stage-based defaults |
| TestFewShotExampleSelection | 8 | Scoring logic, industry similarity matching |
| TestResponseParsing | 8 | Valid JSON, markdown-fenced JSON, invalid JSON fallback, new fields |
| TestMockResponse | 5 | Structure validation, field counts, company name |
| TestStageIdentificationText | 4 | All stages, AMD format matching |
| TestGenerateExecutiveReview | 5 | Mock fallback integration, all stages, field completeness |
| TestFewShotExamplesPool | 4 | Structure validation, Caterpillar/Allbirds placement |

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

### Executive Review Dynamic Fields (Complete)
- Stage identification text matching AMD gold standard format
- Case study link URLs for "Read the case study" clickthrough
- Refined case study selection: challenge now influences selection (e.g., manufacturing + skills_gap -> PQR)
- Updated few-shot examples to match AMD's 5 gold standard examples (Caterpillar -> Challenger, Allbirds -> Observer)
- Industry terminology reference in LLM prompt (Healthcare -> EHR, Retail -> POS, etc.)
- 88 tests covering all executive review service functions

### Phase 2 - Beta
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
