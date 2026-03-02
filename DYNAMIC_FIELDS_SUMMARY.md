# AMD Executive Review - Dynamic Fields Summary

## Overview
The Executive Review generates a personalized 2-page assessment based on user inputs. All highlighted/dynamic content from the AMD PDF guidelines is now implemented.

---

## Input Fields (User-Provided)
| Field | Form Question | Maps To |
|-------|---------------|---------|
| Company Name | "Company" text field | Used directly |
| Industry | Dropdown selection | Industry-specific content |
| Company Size | Dropdown (startup → large enterprise) | **Segment** (SMB / Mid-Market / Enterprise) |
| Role | Dropdown (CTO, CEO, etc.) | **Persona** (ITDM or BDM) |
| IT Environment | Dropdown (traditional/modernizing/modern) | **Stage** (Observer / Challenger / Leader) |
| Business Priority | Dropdown | First advantage & recommendation focus |
| Challenge | Dropdown | First risk focus |

---

## Dynamic Output Fields (LLM-Generated)

### 1. Stage Identification
- **Stage**: Observer / Challenger / Leader (mapped from IT environment)
- **Stage Sidebar Stat**:
  - Observer: "9% of Observers plan to modernize within the next two years."
  - Challenger: "58% of Challengers are currently undertaking modernization initiatives."
  - Leader: "33% of Leaders have fully modernized in the past two years."
- **Stage Color**: Amber (Observer) / Blue (Challenger) / Emerald (Leader)

### 2. Advantages (2 items)
Each advantage contains:
- **Headline**: 4-8 words, benefit-driven (e.g., "Performance gains from upgrading core systems")
- **Description**: Single sentence, 22-30 words

**Personalization Rules**:
- First advantage headline MUST relate to the stated business priority
- Content uses industry-specific terminology
- Company name appears once (in first advantage only)

### 3. Risks (2 items)
Each risk contains:
- **Headline**: 4-8 words (e.g., "Persistent slowdowns from integration bottlenecks")
- **Description**: Single sentence, 22-30 words

**Personalization Rules**:
- First risk headline MUST reference consequences of stated challenge
- Second risk addresses competitive implications
- Company name NOT repeated (uses "the organization", "the company")

### 4. Recommendations (3 items)
Each recommendation contains:
- **Title**: 4-8 words, imperative form (e.g., "Prioritize performance upgrades for high-volume systems")
- **Description**: Single sentence, 22-30 words

**Personalization Rules**:
- Stage-appropriate actions:
  - Observer: foundational, cost-focused steps
  - Challenger: performance, integration, scalability steps
  - Leader: governance, optimization, AI-readiness steps
- Company name appears once (in first recommendation only)
- Language tailored to persona (ITDM = technical, BDM = business outcomes)

### 5. Stage Identification Text
Template-generated text matching AMD's format:
- **Format**: "Based on the information you shared, your organization best aligns with the {stage} stage of modernization."
- Uses "your organization" (not company name) per AMD gold standard examples

### 6. Case Study Selection
Selected based on priority → industry → challenge → stage (updated logic):

| Priority | Condition | Case Study |
|----------|-----------|------------|
| 1 | Priority = "Reducing cost" | **Smurfit Westrock** (25% cost savings) |
| 2 | Industry = Healthcare/Financial/Government | **PQR** (security/compliance) |
| 3 | Challenge = skills_gap/data_governance AND industry NOT tech/retail/telecom | **PQR** (infrastructure) |
| 4 | Priority = improving_performance/preparing_ai (remaining industries) | **KT Cloud** (AI/GPU scaling) |
| 5 | Stage = Observer (default) | **Smurfit Westrock** |
| 5 | Stage = Challenger (default) | **KT Cloud** |
| 5 | Stage = Leader (default) | **PQR** |

Each case study has:
- **Name**: Full case study title
- **Description**: One sentence summary with metrics
- **Link**: URL to the full case study page (TODO: verify exact AMD URLs)

---

## Content Quality Rules (from AMD Guidelines)

1. **Headlines**: 4-8 words, no colons, imperative or benefit-driven
2. **Descriptions**: Single sentence, 22-30 words
3. **Company Name**: Exactly ONCE per section (advantages, risks, recommendations)
4. **No jargon**: No buzzwords, hype, or filler phrases like "in today's landscape"
5. **No formatting**: No em dashes, exclamation marks, or emojis

---

## Few-Shot Examples (Gold Standards)
The LLM uses these examples for consistent output quality. Updated to match AMD's gold standard examples:

| Stage | Company | Industry | Persona | Priority | Challenge |
|-------|---------|----------|---------|----------|-----------|
| Observer | AECOM | AEC | ITDM | Reducing cost | Legacy systems |
| Observer | Allbirds | Consumer Goods | BDM | Reducing cost | Resource constraints |
| Challenger | Target | Retail | BDM | Improving performance | Integration friction |
| Challenger | Caterpillar | Manufacturing | BDM | Improving performance | Skills gap |
| Leader | HCA Healthcare | Healthcare | ITDM | Preparing for AI | Data governance |
| Leader | JPMorgan Chase | Financial Services | BDM | Improving performance | Data governance |

The system automatically selects the most relevant example based on industry and priority similarity.

---

## API Endpoint
```
POST /rad/executive-review
{
  "email": "user@company.com",
  "firstName": "John",
  "lastName": "Doe",
  "company": "Acme Corp",
  "companySize": "enterprise",
  "persona": "cto",
  "industry": "technology",
  "itEnvironment": "modernizing",
  "businessPriority": "preparing_ai",
  "challenge": "integration_friction"
}
```

---

## Testing URLs
- **Beta Backend**: https://amd1-1-backend-beta.onrender.com
- **Beta Frontend**: https://amd1-1-testing.vercel.app (needs Vercel token fix)
- **Local Frontend**: http://localhost:3001 (running in devcontainer)
