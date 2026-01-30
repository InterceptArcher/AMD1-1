# RAD Integration Architecture Plan

## Executive Summary

This document outlines the complete integration architecture for connecting the RADTest enrichment framework with the AMD1-1_Alpha personalization application to achieve the Alpha Personalization scope.

**Goal**: Transform AMD1-1_Alpha from a 60% complete demo into a production-ready personalization engine with real RAD enrichment, template selection, and <60s SLA performance.

---

## Current State vs Target State

### Current State (60% Complete)
- Next.js frontend with email form
- Mock enrichment (5 hardcoded companies)
- Claude API generates content from scratch
- Basic Supabase schema
- Monolithic architecture (frontend + backend in Next.js)

### Target State (100% Complete)
- **RAD Enrichment**: Real-time company enrichment via RADTest APIs
- **Template Framework**: Rule-based template selection + LLM adaptation
- **Enhanced Schema**: Full enrichment data storage (news, intent, confidence scores)
- **Railway Backend**: Separate backend service for async processing
- **Performance**: <60s SLA with caching and optimization
- **Complete Personas**: Support for Exec, GTM, Technical, HR roles

---

## Integration Architecture

### High-Level Data Flow

```
User Form Submission
    ↓
Frontend (Vercel Next.js)
    ↓
API Route (/api/personalize)
    ↓
┌─────────────────────────────────────────────────────┐
│ ENRICHMENT PHASE (10-20s)                           │
├─────────────────────────────────────────────────────┤
│ 1. Extract domain from email                        │
│ 2. Call RAD Intelligence Gatherer (parallel)        │
│    - Apollo.io enrichment                           │
│    - PeopleDataLabs enrichment                      │
│ 3. RAD LLM Validator resolves conflicts             │
│ 4. Write enriched data to Supabase                  │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│ PERSONALIZATION PHASE (5-10s)                       │
├─────────────────────────────────────────────────────┤
│ 1. Template Selection Engine                        │
│    - Match persona + buyer stage + industry         │
│    - Score and rank templates                       │
│    - Select best-fit template                       │
│ 2. LLM Adaptation (Claude 3.5 Sonnet)              │
│    - Inject enriched data into template             │
│    - Adapt tone and messaging                       │
│    - Apply safety guardrails                        │
│ 3. Write personalized content to Supabase          │
└─────────────────────────────────────────────────────┘
    ↓
Frontend Displays Results (<60s total)
```

---

## Component Architecture

### 1. RAD Enrichment Service Integration

**Location**: `lib/enrichment/rad-client.ts` (NEW)

**Responsibilities**:
- Call RADTest Intelligence Gatherer API
- Handle Apollo.io and PeopleDataLabs responses
- Manage enrichment retries and timeouts
- Return normalized enrichment data

**API Contract**:

```typescript
interface RADEnrichmentRequest {
  domain: string;
  email?: string;
}

interface RADEnrichmentResponse {
  company_name: string;
  domain: string;
  industry: string;
  employee_count: number | string;
  company_size: 'startup' | 'SMB' | 'mid-market' | 'enterprise';
  headquarters: string;
  founded_year: number;
  technology: string[];
  news_summary?: string;
  intent_signal?: 'early' | 'mid' | 'late';
  confidence_score: number;
  sources_used: string[];
  enrichment_timestamp: string;
}
```

**Implementation Strategy**:

```typescript
// Option A: Direct API Integration (if RADTest exposes REST API)
export async function enrichCompanyData(domain: string): Promise<RADEnrichmentResponse> {
  const response = await fetch(`${RAD_API_URL}/profile-request`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${RAD_API_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ domain })
  });

  const { job_id } = await response.json();

  // Poll for results
  const result = await pollForJobCompletion(job_id);
  return normalizeRADResponse(result);
}

// Option B: Shared Module Integration (if using monorepo)
import { IntelligenceGatherer } from '@radtest/enrichment';

export async function enrichCompanyData(domain: string): Promise<RADEnrichmentResponse> {
  const gatherer = new IntelligenceGatherer({
    apolloApiKey: process.env.APOLLO_API_KEY!,
    pdlApiKey: process.env.PDL_API_KEY!
  });

  const results = await gatherer.gatherCompanyIntelligence({ domain });
  return normalizeRADResponse(results);
}
```

**Error Handling**:
- Timeout after 30 seconds
- Fallback to cached enrichment if available
- Fallback to generic templates if enrichment fails completely
- Log failures for debugging

---

### 2. Template Selection Engine

**Location**: `lib/personalization/template-engine.ts` (NEW)

**Responsibilities**:
- Define template library for different persona/stage/industry combinations
- Score templates based on enrichment data
- Select best-fit template
- Provide fallback templates for low-confidence enrichment

**Template Structure**:

```typescript
interface PersonalizationTemplate {
  id: string;
  name: string;

  // Matching criteria
  personas: Persona[];
  buyer_stages: BuyerStage[];
  industries?: string[];
  company_sizes?: CompanySize[];

  // Template content
  intro_template: string;  // Variables: {{company_name}}, {{industry}}, {{news}}
  cta_template: string;    // Variables: {{persona}}, {{buyer_stage}}

  // Metadata
  priority: number;        // Higher = preferred
  confidence_threshold: number;  // Minimum confidence to use this template
}

// Example templates
const TEMPLATES: PersonalizationTemplate[] = [
  {
    id: 'exec-enterprise-evaluation',
    name: 'Executive - Enterprise - Evaluation Stage',
    personas: ['Exec'],
    buyer_stages: ['evaluation'],
    company_sizes: ['enterprise'],
    intro_template: 'As {{company_name}} evaluates solutions in {{industry}}, leadership teams like yours are looking for proven enterprise platforms that scale.',
    cta_template: 'Compare how leading enterprises achieve results',
    priority: 10,
    confidence_threshold: 0.8
  },
  {
    id: 'technical-mid-market-awareness',
    name: 'Technical - Mid-Market - Awareness Stage',
    personas: ['Technical'],
    buyer_stages: ['awareness'],
    company_sizes: ['mid-market'],
    intro_template: 'Technical teams at {{company_name}} are exploring modern solutions for {{industry}} challenges.',
    cta_template: 'Learn how it works',
    priority: 8,
    confidence_threshold: 0.7
  },
  // ... 20-30 more templates covering all combinations
];
```

**Selection Algorithm**:

```typescript
export function selectTemplate(
  enrichment: RADEnrichmentResponse,
  persona: Persona,
  buyerStage: BuyerStage
): PersonalizationTemplate {
  // Filter templates by criteria match
  const candidates = TEMPLATES.filter(t =>
    t.personas.includes(persona) &&
    t.buyer_stages.includes(buyerStage) &&
    (t.confidence_threshold <= enrichment.confidence_score)
  );

  // Score each candidate
  const scored = candidates.map(template => ({
    template,
    score: scoreTemplate(template, enrichment, persona, buyerStage)
  }));

  // Sort by score desc
  scored.sort((a, b) => b.score - a.score);

  // Return best match or fallback
  return scored[0]?.template ?? FALLBACK_TEMPLATE;
}

function scoreTemplate(
  template: PersonalizationTemplate,
  enrichment: RADEnrichmentResponse,
  persona: Persona,
  buyerStage: BuyerStage
): number {
  let score = template.priority;

  // Bonus points for industry match
  if (template.industries?.includes(enrichment.industry)) {
    score += 5;
  }

  // Bonus points for company size match
  if (template.company_sizes?.includes(enrichment.company_size)) {
    score += 3;
  }

  // Penalty for low confidence enrichment
  score *= enrichment.confidence_score;

  return score;
}
```

---

### 3. LLM Adaptation Layer

**Location**: `lib/personalization/llm-adapter.ts` (NEW)

**Responsibilities**:
- Take selected template + enrichment data
- Generate Claude prompt with strict constraints
- Adapt template to specific company context
- Validate output meets length/tone requirements

**Adaptation Prompt**:

```typescript
export async function adaptTemplate(
  template: PersonalizationTemplate,
  enrichment: RADEnrichmentResponse,
  persona: Persona,
  buyerStage: BuyerStage
): Promise<PersonalizedContent> {
  const systemPrompt = `You are a B2B marketing copy editor. Your job is to adapt a template with specific company context.

STRICT REQUIREMENTS:
- Output exactly 2 sentences for intro (30-50 words total)
- Output exactly 1 sentence for CTA (5-10 words)
- Tone: Professional, confident, not salesy
- DO NOT mention competitors
- DO NOT make unverifiable claims
- DO use company name naturally
- DO reference recent news if available
- DO tailor to persona (${persona}) and buyer stage (${buyerStage})

Template to adapt:
Intro: ${template.intro_template}
CTA: ${template.cta_template}

Company Context:
Name: ${enrichment.company_name}
Industry: ${enrichment.industry}
Size: ${enrichment.company_size}
News: ${enrichment.news_summary || 'No recent news'}
Intent: ${enrichment.intent_signal || 'Unknown'}

Output JSON:
{
  "intro": "...",
  "cta": "..."
}`;

  const result = await generatePersonalization({
    prompt: systemPrompt,
    schema: PersonalizationOutputSchema,
    maxTokens: 200,
    temperature: 0.7
  });

  return result;
}
```

---

### 4. Enhanced Supabase Schema

**Location**: `supabase/migrations/002_add_enrichment_fields.sql` (NEW)

**Schema Updates**:

```sql
-- Add enrichment fields to personalization_jobs
ALTER TABLE personalization_jobs
ADD COLUMN company_name VARCHAR(255),
ADD COLUMN industry VARCHAR(100),
ADD COLUMN company_size VARCHAR(50),
ADD COLUMN employee_count VARCHAR(50),
ADD COLUMN headquarters VARCHAR(255),
ADD COLUMN founded_year INTEGER,
ADD COLUMN technology JSONB,
ADD COLUMN news_summary TEXT,
ADD COLUMN intent_signal VARCHAR(20),
ADD COLUMN confidence_score FLOAT,
ADD COLUMN enrichment_sources JSONB,
ADD COLUMN enrichment_timestamp TIMESTAMP,
ADD COLUMN enrichment_error TEXT;

-- Add template metadata to personalization_outputs
ALTER TABLE personalization_outputs
ADD COLUMN template_id VARCHAR(100),
ADD COLUMN template_name VARCHAR(255),
ADD COLUMN llm_tokens_used INTEGER,
ADD COLUMN llm_latency_ms INTEGER,
ADD COLUMN total_latency_ms INTEGER;

-- Add indexes for querying enriched data
CREATE INDEX idx_personalization_jobs_company_name ON personalization_jobs(company_name);
CREATE INDEX idx_personalization_jobs_industry ON personalization_jobs(industry);
CREATE INDEX idx_personalization_jobs_company_size ON personalization_jobs(company_size);
CREATE INDEX idx_personalization_jobs_confidence_score ON personalization_jobs(confidence_score);

-- Create enrichment cache table (optional performance optimization)
CREATE TABLE enrichment_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain VARCHAR(255) UNIQUE NOT NULL,
  enriched_data JSONB NOT NULL,
  confidence_score FLOAT NOT NULL,
  cached_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP NOT NULL,
  cache_hits INTEGER DEFAULT 0
);

CREATE INDEX idx_enrichment_cache_domain ON enrichment_cache(domain);
CREATE INDEX idx_enrichment_cache_expires_at ON enrichment_cache(expires_at);
```

---

### 5. Railway Backend Service

**Location**: Root directory (NEW files)

**Files to Create**:

1. **`Procfile`** - Process definition
```
web: npm run start:backend
```

2. **`railway.json`** - Railway configuration
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "npm install && npm run build:backend"
  },
  "deploy": {
    "startCommand": "npm run start:backend",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 30
  }
}
```

3. **`backend/server.ts`** - Express server (NEW)
```typescript
import express from 'express';
import { enrichAndPersonalize } from './services/personalization';

const app = express();
app.use(express.json());

app.post('/api/personalize', async (req, res) => {
  try {
    const { email, name, cta } = req.body;
    const result = await enrichAndPersonalize(email, name, cta);
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/health', (req, res) => {
  res.json({ status: 'healthy' });
});

app.listen(process.env.PORT || 3001);
```

**Note**: This is optional. We can keep the monolithic architecture and just enhance the existing Next.js API routes, which is simpler for Alpha.

---

## Performance Optimization Strategy

### Goal: <60s SLA

**Current Estimated Latency**:
- Email validation: <100ms
- RAD enrichment (parallel Apollo + PDL): 10-20s
- LLM conflict resolution: 5-10s
- Template selection: <100ms
- Claude adaptation: 5-10s
- Supabase writes: 1-2s
- **Total**: ~25-45s (within SLA)

**Optimization Techniques**:

1. **Parallel Processing**:
   - Run enrichment and persona inference simultaneously
   - Batch Supabase writes

2. **Caching**:
   - Cache enrichment for 24-48 hours per domain
   - Cache template selections
   - Cache frequently accessed company data

3. **Async Background Jobs**:
   - Write audit logs asynchronously
   - Generate slideshows in background
   - Send notification emails asynchronously

4. **Progressive Response**:
   - Return immediately with job ID
   - Poll for completion
   - Stream partial results if available

**Implementation**:

```typescript
// Check cache first
const cached = await getCachedEnrichment(domain);
if (cached && !isExpired(cached)) {
  return cached;
}

// Otherwise, fetch and cache
const enriched = await enrichCompanyData(domain);
await cacheEnrichment(domain, enriched, { ttl: 86400 }); // 24 hour TTL
return enriched;
```

---

## API Contracts

### Frontend → Backend

**POST /api/personalize**

Request:
```json
{
  "email": "john@microsoft.com",
  "name": "John Smith",  // Optional
  "cta": "compare",      // CTA from LinkedIn parameter
  "consent": true
}
```

Response:
```json
{
  "success": true,
  "job_id": "uuid",
  "enrichment": {
    "company_name": "Microsoft Corporation",
    "industry": "Technology",
    "company_size": "enterprise",
    "employee_count": "221,000",
    "confidence_score": 0.92
  },
  "personalization": {
    "headline": "Personalized headline...",
    "subheadline": "Personalized subheadline...",
    "cta_text": "See enterprise comparison",
    "template_used": "exec-enterprise-evaluation"
  },
  "latency_ms": 28400
}
```

---

## Fallback Strategies

### When RAD Enrichment Fails

**Scenario 1: Complete API Failure**
- Use generic templates
- Show "We couldn't personalize your experience" message
- Still capture email and send standard ebook
- Log failure for debugging

**Scenario 2: Low Confidence Enrichment**
- Use broader templates (e.g., "Technology companies like yours...")
- Avoid specific claims
- Default to safest persona (Business Leader)
- Show content but flag for manual review

**Scenario 3: Partial Enrichment**
- Use available fields only
- Fill missing fields with "N/A" or omit
- Adjust template selection to match available data
- Maintain quality over personalization depth

---

## Configuration Management

**Environment Variables Required**:

```bash
# Existing
ANTHROPIC_API_KEY=sk-...
SUPABASE_URL=https://...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_KEY=...

# New for RAD Integration
RAD_API_URL=https://radtest-backend.railway.app
RAD_API_KEY=...
APOLLO_API_KEY=...
PDL_API_KEY=...

# Optional
ENRICHMENT_CACHE_TTL=86400  # 24 hours
USE_MOCK_ENRICHMENT=false   # Toggle for testing
```

**Security**:
- All API keys from environment only
- Never commit secrets
- Use Railway's secret management
- Rotate keys quarterly

---

## Testing Strategy

### Unit Tests
- Template selection algorithm
- Enrichment data normalization
- LLM prompt generation
- Fallback logic

### Integration Tests
- RAD API calls (mocked and real)
- Supabase writes
- End-to-end personalization flow

### Performance Tests
- Measure latency for each phase
- Validate <60s SLA under load
- Test cache effectiveness
- Test with slow enrichment APIs

### Test Files to Create
- `tests/enrichment.spec.ts` - RAD integration tests
- `tests/template-selection.spec.ts` - Template engine tests
- `tests/performance.spec.ts` - SLA validation
- `tests/fallback.spec.ts` - Error handling tests

---

## Migration Path

### Phase 1: Foundation (Days 1-2)
1. Create enhanced Supabase schema
2. Implement RAD client wrapper
3. Update API route to call RAD
4. Add optional name field to form
5. Test with mock enrichment

### Phase 2: Template Engine (Days 3-4)
1. Define template library (20-30 templates)
2. Implement template selection algorithm
3. Create LLM adaptation layer
4. Update Claude prompts
5. Test template matching

### Phase 3: Optimization (Days 5-6)
1. Implement enrichment caching
2. Add performance monitoring
3. Optimize Supabase queries
4. Test <60s SLA
5. Add progressive loading UI

### Phase 4: Documentation & Deployment (Day 7)
1. Update all documentation
2. Create deployment runbooks
3. Deploy to staging
4. Validate end-to-end
5. Deploy to production

---

## Success Metrics

**Alpha Success Criteria**:
- ✅ 95% enrichment success rate (Apollo + PDL)
- ✅ <60s p95 latency for full flow
- ✅ 90%+ template match confidence
- ✅ 0 hardcoded secrets in codebase
- ✅ Full test coverage (>80%)
- ✅ Complete documentation
- ✅ Successful Railway deployment

---

## Next Steps

1. Review and approve this plan
2. Begin Phase 1 implementation
3. Create detailed subtasks in project tracker
4. Schedule check-ins for each phase
5. Assign ownership for each component

---

**Document Status**: DRAFT
**Last Updated**: 2026-01-27
**Owner**: Development Team
**Reviewers**: Product, Engineering
