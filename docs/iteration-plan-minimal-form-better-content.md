# Iteration Plan: Improve Content Quality with Minimal User Input

**Date:** 2026-02-13
**Branch:** beta
**Status:** In Progress

## Context
The current system asks users for **11 form fields** (name, email, company, company size, industry, role, journey stage, IT environment, business priority, challenge, consent) before generating personalized content. However, most of these fields can be enriched automatically via APIs (PDL, Apollo, GNews, etc.).

**The Problem:** Friction from lengthy forms reduces conversion, and we're not maximizing the rich enrichment data we already have access to.

**The Goal:** Reduce form fields to the bare minimum while improving content relevance by:
1. Leveraging enrichment APIs more aggressively
2. Inferring user context from enriched data (news, role, company signals)
3. Using LLM to synthesize insights from raw enrichment data
4. Eliminating redundant questions

---

## Current State (11 Fields Required)
1. First Name, Last Name, Work Email
2. Company, Company Size
3. Industry (13 options)
4. Role (27 options)
5. Journey Stage (4 options)
6. IT Environment (3 options)
7. Business Priority (3 options)
8. Challenge (6 options)
9. Consent checkbox

### Current Enrichment Coverage
| Data Point | Currently Asked | Can Enrich From APIs |
|------------|----------------|---------------------|
| **Name** | User form | Apollo, PDL |
| **Email** | User form (required) | N/A |
| **Company** | User form | Apollo, PDL, domain extraction |
| **Company Size** | User form | PDL Company, ZoomInfo, Apollo |
| **Industry** | User form | PDL Company, ZoomInfo, Apollo |
| **Role/Title** | User form | Apollo, PDL |
| **Journey Stage** | User form | Can infer from behavior |
| **IT Environment** | User form | Can infer from news, tech stack, company tags |
| **Business Priority** | User form | Can infer from news, industry, role |
| **Challenge** | User form | Can infer from news, industry, IT environment |

**Key Insight:** 8 out of 11 fields can be enriched or inferred.

---

## New Minimal Form Design

**Fields:**
1. **Email** (required) - Primary enrichment key
2. **Journey Stage** (optional dropdown) - Self-identified stage for power users
   - Options: "Just researching", "Evaluating options", "Ready to decide", "Already implementing"
   - Defaults to "consideration" if not provided
3. **Consent** (required) - Legal requirement

**Reduction:** 11 required fields -> 2 required + 1 optional (82% reduction!)

---

## Enhanced Enrichment Strategy

### Phase 1: Email-Based Enrichment (Parallel)
- Email -> Domain Extraction -> Company Name
- Apollo.io (Person + Company data)
- PDL Person API (Name, title, skills, experience)
- Hunter.io (Email verification)

### Phase 2: Company-Based Enrichment (Parallel)
- PDL Company API (Deep company data, funding, growth, tags)
- GNews (5 parallel queries: news, AI, tech, leadership, growth)
- ZoomInfo (Company details, tech stack)

### Phase 3: LLM-Based Context Inference (NEW)
All enrichment data analyzed by LLM to infer:
- IT Environment (traditional/modernizing/modern)
- Business Priority (cost/performance/AI)
- Primary Challenge (legacy/integration/skills/governance)
- Urgency Level (low/medium/high)
- Decision-Maker Likelihood (based on role)

---

## Context Inference Logic

### IT Environment Inference
- Company tags contain "AI", "cloud", "SaaS" -> modern
- News mentions "digital transformation", "modernization" -> modernizing
- Founded year >2015 + tech industry -> modern
- Founded year <2000 + traditional industry -> traditional
- Default: modernizing

### Business Priority Inference
- News mentions "cost reduction", "efficiency" -> reducing_cost
- News mentions "AI adoption", "machine learning" -> preparing_ai
- Role is Data/AI-related -> preparing_ai
- Growth rate >30% -> improving_performance
- Default: preparing_ai

### Challenge Inference
- Founded year <2005 + traditional industry -> legacy_systems
- News mentions "integration", "interoperability" -> integration_friction
- Small company (<200 employees) -> resource_constraints
- News mentions "talent", "hiring", "skills" -> skills_gap
- Industry = Healthcare/Financial -> data_governance
- Default: legacy_systems

### Journey Stage (if not provided)
- C-level role + news mentions "investment" -> decision
- Recent funding round -> consideration
- News mentions "pilot", "testing" -> implementation
- No strong signals -> consideration (default)

---

## Content Quality Improvements

### 1. Richer News Analysis
- Sentiment analysis per article (positive/neutral/negative/crisis)
- Entity extraction (competitors, technologies, partners)
- AI readiness signal detection
- Urgency signal detection

### 2. Smart Case Study Selection (Multi-Factor)
| Factor | Weight | Signals |
|--------|--------|---------|
| Industry match | 40% | Direct industry alignment |
| Challenge match | 25% | Inferred challenge vs case study solution |
| Company size match | 15% | Case study company size vs user company |
| Growth stage match | 10% | Funding stage, growth rate |
| Tech maturity match | 10% | IT environment vs case study tech level |

### 3. Dynamic Hook Generation
- Crisis-aware hooks (empathetic if negative news)
- Momentum-aware hooks (capitalize on growth)
- Role-specific angles (technical depth vs business outcomes)
- Urgency injection (growth rate, funding events)

### 4. Personalized Section Length
- Senior roles (C-level, VP) -> Shorter, punchier
- Technical roles (Engineers, Architects) -> Longer, detailed
- Mid-level -> Medium (current defaults)

---

## Fallback Strategy

### Tier 1: Full Enrichment Success
- All APIs return data, quality score >= 0.7
- Use Claude Opus for personalization

### Tier 2: Partial Enrichment
- Some APIs fail, quality score 0.4-0.7
- Use Claude Haiku, available data + generic backups

### Tier 3: Enrichment Failure
- Most APIs fail, quality score < 0.4
- Mock personalization with email domain insights

### Tier 4: Complete Failure
- No enrichment possible
- Generic but professional content, infer from email domain

---

## Files Changed

### New Files
- [x] `backend/app/services/context_inference_service.py` - LLM-based context inference
- [x] `backend/app/services/news_analysis_service.py` - News sentiment/entity analysis
- [x] `backend/tests/test_context_inference.py` - Context inference tests (43 tests passing)
- [x] `backend/tests/test_news_analysis.py` - News analysis tests

### Modified Files
- [x] `frontend/src/components/EmailConsentForm.tsx` - Simplified form (email + optional stage + consent)
- [x] `frontend/src/app/page.tsx` - Updated payload handling
- [x] `frontend/src/components/LoadingSpinner.tsx` - Updated for enrichment-focused loading
- [x] `backend/app/routes/enrichment.py` - Enrichment-first flow with context inference
- [x] `backend/app/services/executive_review_service.py` - Enrichment context in prompts + multi-factor case study
- [x] `backend/app/services/pdf_service.py` - Fixed nested f-string syntax errors

---

## API Payload Changes

### Old Payload (11 fields)
```json
{
  "email": "john@acme.com",
  "firstName": "John",
  "lastName": "Doe",
  "company": "Acme Corp",
  "companySize": "enterprise",
  "industry": "technology",
  "persona": "cto",
  "goal": "consideration",
  "itEnvironment": "modernizing",
  "businessPriority": "preparing_ai",
  "challenge": "legacy_systems"
}
```

### New Payload (2-3 fields)
```json
{
  "email": "john@acme.com",
  "goal": "consideration"
}
```

---

## Verification Checklist
- [ ] Email-only submission works end-to-end
- [ ] Optional journey stage field works
- [ ] Context inference produces reasonable results
- [ ] News sentiment analysis extracts insights
- [ ] Multi-factor case study selection improves relevance
- [ ] Fallbacks work at each tier (partial data, no data)
- [ ] Personalization quality equal or better than before
- [ ] Frontend form is clean and minimal
- [ ] Loading states are appropriate
- [ ] Error handling is graceful
