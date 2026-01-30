# AMD1-1_Alpha: LinkedIn Post-Click Personalization Engine

A sophisticated B2B lead personalization system that transforms LinkedIn ebook gate form submissions into highly personalized content experiences using RAD (Retrieval-Augmented Data) enrichment and AI-powered template adaptation.

**Target SLA:** <60 seconds from form submission to personalized content delivery

---

## Recent Updates (2026-01-27)

### Guided Experience with Dropdown Menus

**Transformed Form to Guided Chat Experience:**
- Replaced simple email form with comprehensive guided experience
- Added 4 key dropdown inputs for signal capture:
  1. **Company** (text input) - Company name
  2. **Role** (dropdown) - Business Leader, IT, Finance, Operations, Security
  3. **Modernization Stage** (dropdown) - Exploring/Evaluating/Ready to Implement
  4. **AI Priority** (dropdown) - Infrastructure, AI/ML, Cloud Migration, Data Center, Performance, Cost Optimization
- Email field (required) for enrichment
- Name field (optional) at bottom for personalization

**Data Flow Updates:**
- User selections from dropdowns directly set persona and buyer_stage (no inference needed)
- Company name from form overrides enriched company data
- AI Priority stored in database for future analytics
- All fields validated before submission

**Schema Changes:**
- Updated `PersonalizeRequestSchema` to include new required fields
- Added `ai_priority` column to `personalization_jobs` table (migration 003)
- Metadata now includes company and ai_priority for display

**UX Improvements:**
- Clear field labels with contextual descriptions
- Form only submits when all required fields are filled
- Red color scheme matches AMD branding
- Title changed from "LinkedIn Personalization" to "AMD Campaign Experience"

**Files Modified:**
- `/workspaces/AMD1-1_Alpha/app/components/EmailForm.tsx:1` - Complete form redesign
- `/workspaces/AMD1-1_Alpha/lib/schemas.ts:4` - Added new validation fields
- `/workspaces/AMD1-1_Alpha/app/api/personalize/route.ts:34` - Uses dropdown values instead of inference
- `/workspaces/AMD1-1_Alpha/app/components/PersonalizedResults.tsx:17` - Displays company and AI priority badges
- `/workspaces/AMD1-1_Alpha/supabase/migrations/003_add_ai_priority_field.sql` - New database field

### Build Fixes and UX Improvements

**Color Scheme Update:**
- Changed primary color from LinkedIn blue (#0A66C2) to red (#DC2626)
- Updated all UI elements: buttons, headers, badges, accents
- Maintained white background with red highlights
- Hover states use darker red (#B91C1C)
- Metadata badges use light red backgrounds (#FEE2E2, #FECACA, #FEF2F2)

**Fixed Client-Side Schema Mismatch:**
- Updated `PersonalizedResults` component to match API response schema
- Changed from `value_propositions` array to individual `value_prop_1/2/3` fields
- Ensures consistency with ClaudeOutput schema across the application
- Resolves "Application error: a client-side exception has occurred" issue

**Form Field Reordering:**
- Moved email field before name field for better UX
- Email is now the first field (required, primary enrichment input)
- Name is now the second field (optional, secondary personalization)
- Improves form completion flow and user expectations

**Type Safety Improvements:**
- Added proper TypeScript types for `Persona` and `BuyerStage`
- Fixed `inferPersona()` and `inferBuyerStage()` return types in `/workspaces/AMD1-1_Alpha/lib/utils/email.ts:19`
- Mapped 'Revenue' persona to 'Business Leader' for type compatibility
- Lowercased buyer stage values to match schema ('awareness', 'evaluation', 'decision')

**API Client Enhancements:**
- Added `generatePersonalization()` function to `/workspaces/AMD1-1_Alpha/lib/anthropic/client.ts:27`
- Supports custom prompt-based template adaptation
- Maintains consistent JSON schema validation

**Database Query Optimization:**
- Removed unsupported `supabase.sql` usage for cache hit tracking
- Simplified enrichment cache updates for compatibility

---

## Overview

When a user clicks a LinkedIn ad and submits their work email, AMD1-1_Alpha:

1. **Enriches** company data via Apollo.io and PeopleDataLabs APIs
2. **Infers** persona (Exec, GTM, Technical, HR) and buying stage (awareness, evaluation, decision)
3. **Selects** the best-fit template from a library of 20+ pre-written templates
4. **Adapts** the template using Claude 3.5 Sonnet to create natural, personalized messaging
5. **Delivers** customized headline, subheadline, value props, and CTA

---

## Key Features

### 1. RAD Enrichment Integration

**Enriches company data from work email domain:**
- Company name, industry, size classification
- Employee count, headquarters, founded year
- Technology stack
- Recent company news (GTM/AI/modernization focus)
- Buying intent signals (early/mid/late stage)

**Implementation:**
- Parallel API calls to Apollo.io and PeopleDataLabs
- LLM-based conflict resolution for data discrepancies
- Confidence scoring (0.0-1.0) for enrichment quality
- 24-hour caching to reduce API costs and improve performance
- Graceful fallback to mock enrichment if APIs unavailable

**Performance:**
- Target: 10-20 seconds for enrichment
- Cache hit rate optimization reduces repeated lookups
- Timeout handling ensures SLA compliance

**Files:**
- `lib/enrichment/rad-client.ts` - RAD enrichment client
- `supabase/migrations/002_add_enrichment_fields.sql` - Enrichment schema

---

### 2. Template Selection Engine

**Rule-based template matching:**
- 20+ pre-written templates for persona/stage/industry/size combinations
- Scoring algorithm ranks templates by relevance
- Template variables: `{{company_name}}`, `{{industry}}`, `{{news}}`, etc.
- Fallback templates for low-confidence enrichment

**Supported Personas:**
- Business Leader (Exec)
- IT (Technical)
- Finance
- Operations
- Security

**Supported Buyer Stages:**
- Awareness (early stage - educating, exploring)
- Evaluation (mid stage - comparing options)
- Decision (late stage - ready to purchase)

**Example Templates:**
- "As {{company_name}} evaluates enterprise solutions in {{industry}}..."
- "Technical teams at {{company_name}} are exploring modern {{industry}} solutions..."
- "Security professionals in {{industry}} companies like {{company_name}}..."

**Files:**
- `lib/personalization/template-engine.ts` - Template library and selection logic

---

### 3. LLM Adaptation Layer

**Claude-powered template adaptation:**
- Takes selected template + enrichment data
- Adapts messaging to company-specific context
- Maintains strict tone and length requirements
- Applies safety guardrails (no competitors, no superlatives)

**Constraints:**
- Headline: 6-12 words
- Subheadline: 15-25 words
- CTA: 3-6 words
- Value Props: 8-15 words each

**Safety Rules:**
- No competitor mentions
- No unverifiable claims ("best", "#1", "revolutionary")
- No marketing jargon ("synergy", "disrupt")
- No exclamation marks or emoji
- Professional and confident tone

**Files:**
- `lib/personalization/llm-adapter.ts` - LLM adaptation logic
- `lib/anthropic/client.ts` - Claude API integration

---

### 4. Enhanced Data Schema

**Supabase tables:**

**personalization_jobs** (user submissions + enrichment):
- User data: email, name (optional), domain
- Persona and buyer stage inference
- Full RAD enrichment fields:
  - company_name, industry, company_size
  - employee_count, headquarters, founded_year
  - technology (JSONB array)
  - news_summary, intent_signal
  - confidence_score, enrichment_sources
  - enrichment_timestamp, enrichment_duration_ms

**personalization_outputs** (generated content):
- Personalized content: headline, subheadline, CTA, value props
- Template metadata: template_id, template_name
- Performance metrics: llm_latency_ms, total_latency_ms
- Model information: llm_model, llm_tokens_used

**enrichment_cache** (performance optimization):
- domain (unique key)
- enriched_data (JSONB)
- 24-hour TTL
- cache_hits tracking

**Files:**
- `supabase/migrations/001_create_personalization_tables.sql` - Base schema
- `supabase/migrations/002_add_enrichment_fields.sql` - Enrichment fields
- `lib/supabase/queries.ts` - Database operations

---

### 5. Performance Optimization (<60s SLA)

**Latency Breakdown:**
- RAD enrichment: 10-20s (parallel API calls)
- LLM conflict resolution: 2-5s (if needed)
- Template selection: <100ms (rule-based)
- Claude adaptation: 5-10s
- Database writes: 1-2s
- Network latency: 1-2s
- **Total: 20-40s typical, <60s guaranteed**

**Optimization Strategies:**
- Parallel processing (Apollo + PeopleDataLabs)
- 24-hour enrichment cache per domain
- Async database writes
- Vercel Edge functions for low latency

**Monitoring:**
- `total_latency_ms` tracked per request
- `sla_met` boolean flag for analysis
- Performance logs for debugging

---

### 6. Email Form with Optional Name Field

**Form Features:**
- **Work email field** (required) - appears first for enrichment
- **Name field** (optional) - appears second for light personalization
- **Consent checkbox** (required) - for compliance
- Real-time validation with visual feedback
- Submit button enabled only when valid

**Validation:**
- HTML5 email validation
- Regex pattern matching
- XSS protection via React escaping
- Consent requirement enforcement

**UX Design:**
- Email field prioritized (appears first) as it's the critical enrichment input
- Name field secondary (appears second) as it's optional
- Clear "(optional)" label on name field

**Files:**
- `app/components/EmailForm.tsx` - Form component with name field

---

### 7. Content Display Schema

**PersonalizedResults Component:**
- Displays personalized content matching Claude API schema
- Schema uses individual value prop fields (`value_prop_1`, `value_prop_2`, `value_prop_3`)
- Simplified display without separate titles/descriptions
- Consistent with ClaudeOutput schema from `/lib/schemas.ts`

**Data Structure:**
```typescript
interface PersonalizedContent {
  headline: string;
  subheadline: string;
  value_prop_1: string;  // Complete value proposition
  value_prop_2: string;  // Complete value proposition
  value_prop_3: string;  // Complete value proposition
  cta_text: string;
  personalization_rationale?: string;
}
```

**Rationale:**
- Matches ClaudeOutput schema for consistency
- Simplifies API contract (no nested arrays)
- Reduces LLM prompt complexity
- Each value prop is self-contained (8-15 words)

**Files:**
- `app/components/PersonalizedResults.tsx` - Results display component

---

## Tech Stack

### Frontend
- **Framework:** Next.js 14.2+ with App Router
- **Language:** TypeScript 5.9+
- **Runtime:** React 18.3+
- **Styling:** Inline styles
- **Deployment:** Vercel (serverless)

### Backend Services
- **RAD Enrichment:** Apollo.io + PeopleDataLabs APIs
- **LLM:** Claude 3.5 Sonnet (Anthropic)
- **Database:** Supabase (PostgreSQL)
- **Caching:** Supabase enrichment_cache table

### Testing
- **Framework:** Playwright 1.58+
- **Coverage:** Landing page, email form, API endpoints
- **Test Types:** Functional, validation, security, performance

---

## Project Structure

```
app/
├── page.tsx                        # Main landing page
├── layout.tsx                      # Root layout
├── api/
│   └── personalize/
│       └── route.ts               # Main API endpoint (RAD + template + LLM)
└── components/
    ├── EmailForm.tsx              # Email + name form
    ├── PersonalizedResults.tsx    # Results display
    └── LoadingState.tsx           # Loading indicator

lib/
├── enrichment/
│   └── rad-client.ts              # RAD enrichment integration
├── personalization/
│   ├── template-engine.ts         # Template selection engine
│   └── llm-adapter.ts             # LLM adaptation layer
├── anthropic/
│   ├── client.ts                  # Claude API client
│   └── mock-client.ts             # Mock for testing
├── supabase/
│   ├── client.ts                  # Supabase client
│   └── queries.ts                 # Database queries + caching
├── utils/
│   ├── email.ts                   # Email/persona/stage utils
│   └── enrichment.ts              # Legacy mock enrichment
└── schemas.ts                     # Zod validation schemas

supabase/
└── migrations/
    ├── 001_create_personalization_tables.sql  # Base schema
    └── 002_add_enrichment_fields.sql          # Enrichment fields

scripts/
├── deploy-backend-supabase.sh    # Deploy Supabase migrations
└── deploy-frontend-vercel.sh     # Deploy Vercel frontend

tests/
├── landing-page.spec.ts          # Query string parsing tests
├── email-form.spec.ts            # Form validation tests
└── api-personalize.spec.ts       # API endpoint tests

docs/
├── README.md                      # This file
├── INTEGRATION_PLAN.md            # RAD integration architecture
├── FULL_EXPLANATION.md            # Comprehensive project explanation
├── IMPLEMENTATION_SUMMARY.md      # Implementation details
├── FILE_LOCATIONS.md              # File location guide
├── MOCK_VS_REAL_COMPARISON.md     # Mock vs real comparison
└── CLAUDE.md                      # AI engineering rulebook
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
# Clone repository
git clone https://github.com/InterceptArcher/AMD1-1_Alpha.git
cd AMD1-1_Alpha

# Install dependencies
npm install

# Install Playwright browsers (for testing)
npx playwright install --with-deps chromium

# Create .env file
cp .env.example .env
```

### Environment Variables

```bash
# Required for production
ANTHROPIC_API_KEY=sk-ant-...
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_KEY=eyJhbGc...

# Optional for real RAD enrichment
RAD_API_URL=https://radtest-backend.railway.app
RAD_API_KEY=...
APOLLO_API_KEY=...
PDL_API_KEY=...

# Optional for testing/development
MOCK_MODE=true                    # Skip real APIs, use mocks
USE_MOCK_ENRICHMENT=true          # Skip RAD APIs, use mock data
ENRICHMENT_CACHE_TTL=86400        # Cache TTL in seconds (24h)

# Deployment
VERCEL_TOKEN=...
VERCEL_PROJECT_ID=...
VERCEL_ORG_ID=...
SUPABASE_PROJECT_REF=...
```

---

## Development

### Run Development Server

```bash
npm run dev
# Open http://localhost:3000
```

### Test with Query Parameters

```bash
# Test with specific CTA value
http://localhost:3000/?cta=compare   # Evaluation stage
http://localhost:3000/?cta=demo      # Decision stage
http://localhost:3000/?cta=learn     # Awareness stage

# Test default behavior (no parameter)
http://localhost:3000/
```

### Run in Mock Mode

```bash
# Skip real APIs for local development
MOCK_MODE=true npm run dev
```

---

## Testing

### Run All Tests

```bash
npm test
```

### Run Specific Test Suites

```bash
npm test -- tests/landing-page.spec.ts
npm test -- tests/email-form.spec.ts
npm test -- tests/api-personalize.spec.ts
```

### Run Tests with UI

```bash
npm run test:headed
```

### Test Coverage
- Landing page: Query parameter parsing, UI rendering
- Email form: Validation, consent, submission flow
- API endpoint: Request validation, enrichment, personalization
- Security: XSS prevention, input sanitization

---

## Deployment

### Prerequisites
- Vercel account and CLI
- Supabase account and CLI
- Environment variables configured

### Deploy Supabase (Database)

```bash
# Run migrations
./scripts/deploy-backend-supabase.sh

# Verify migrations
supabase migration list
```

### Deploy Vercel (Frontend + API)

```bash
# Deploy to preview
./scripts/deploy-frontend-vercel.sh

# Deploy to production
./scripts/deploy-frontend-vercel.sh --production
```

### Post-Deployment

1. Verify environment variables in Vercel dashboard
2. Test deployed URL with sample email
3. Monitor Supabase logs for enrichment success rate
4. Check `total_latency_ms` to ensure <60s SLA

---

## Usage Example

### User Flow

1. User clicks LinkedIn ad → Lands on `/?cta=compare`
2. Sees "AMD Campaign Experience" with guided form
3. Fills out guided experience:
   - Company: "Microsoft"
   - Role: "IT / Technical"
   - Modernization Stage: "Evaluating & Comparing (Mid Stage)"
   - AI Priority: "AI/ML Workloads"
   - Email: `john@microsoft.com`
   - Name (optional): "John Smith"
4. Clicks "Get Personalized Content"
5. Loading indicator shows progress (20-40s typical)
6. Sees personalized content:
   - Headline: "Enterprise Platform Evaluation for Microsoft"
   - Subheadline: Company-specific messaging with context
   - 3 Value propositions tailored to persona (IT) and stage (evaluation)
   - CTA button: "Compare technical capabilities"

### API Request Example

```bash
curl -X POST http://localhost:3000/api/personalize \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@microsoft.com",
    "name": "John Smith",
    "company": "Microsoft",
    "role": "IT",
    "modernization_stage": "evaluation",
    "ai_priority": "AI/ML Workloads",
    "cta": "compare"
  }'
```

### API Response Example

```json
{
  "success": true,
  "jobId": 12345,
  "data": {
    "headline": "Enterprise Platform Evaluation for Microsoft",
    "subheadline": "As Microsoft's technical teams evaluate cloud-native platforms, see how enterprise leaders ensure seamless integration with Azure and Office 365 ecosystems.",
    "cta_text": "Compare integration capabilities",
    "value_prop_1": "Native Azure integration with zero-config deployment for enterprise scale",
    "value_prop_2": "Office 365 SSO and Teams integration for Microsoft-first organizations",
    "value_prop_3": "Enterprise security and compliance built for regulated industries"
  },
  "enrichment": {
    "company_name": "Microsoft Corporation",
    "industry": "Technology",
    "company_size": "enterprise",
    "employee_count": "221,000",
    "confidence_score": 0.92,
    "sources_used": ["apollo", "peopledatalabs"]
  },
  "metadata": {
    "persona": "IT",
    "buyer_stage": "evaluation",
    "company": "Microsoft",
    "ai_priority": "AI/ML Workloads",
    "template_id": "technical-enterprise-evaluation",
    "template_name": "Technical - Enterprise - Evaluation Stage",
    "enrichment_duration_ms": 15000,
    "llm_latency_ms": 8000,
    "total_latency_ms": 24000,
    "sla_met": true
  }
}
```

---

## Architecture

### Data Flow

```
User Form → API Route → RAD Enrichment → Template Selection → LLM Adaptation → Response
                              ↓                                      ↓
                        Supabase Cache                         Supabase Storage
```

### Performance Budget

| Phase | Target | Typical |
|-------|--------|---------|
| RAD Enrichment | <20s | 10-15s |
| Template Selection | <1s | <100ms |
| LLM Adaptation | <10s | 5-8s |
| Database Operations | <2s | 1s |
| Total | <60s | 20-30s |

---

## Methodology

### Test-Driven Development (TDD)
All features follow TDD:
1. Write failing test
2. Implement minimal code to pass
3. Refactor and optimize

### Security-First Design
- No hardcoded secrets
- Input validation with Zod schemas
- XSS protection via React escaping
- Row-level security (RLS) in Supabase
- API rate limiting and timeout handling

### Performance Optimization
- Parallel API calls (Apollo + PeopleDataLabs)
- 24-hour enrichment caching
- Async database writes
- Edge function deployment
- Monitoring and logging for SLA tracking

---

## Engineering Principles

See `CLAUDE.md` for comprehensive engineering rulebook including:
- Stack awareness (read `stack.json` before writing infra code)
- Security first (zero tolerance for hardcoded secrets)
- Test-driven development (mandatory tests before implementation)
- Code quality standards
- Deployment discipline

---

## Support

- **Documentation:** See `/docs` directory for detailed guides
- **Issues:** https://github.com/InterceptArcher/AMD1-1_Alpha/issues
- **Integration Plan:** See `INTEGRATION_PLAN.md` for RAD architecture
- **Full Explanation:** See `FULL_EXPLANATION.md` for comprehensive overview

---

## License

Proprietary - Intercept Corporation

---

**Last Updated:** 2026-01-27
**Version:** Alpha 1.0
**Status:** Active Development with RAD Integration Complete
