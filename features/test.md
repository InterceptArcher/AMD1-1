You are a senior full-stack engineer. Build an ALPHA “LinkedIn Post-Click Personalization” web app.

GOAL (Alpha):
- A user clicks a LinkedIn ad → lands on a page → enters email + consent → app infers company domain + simple persona + buyer stage (from CTA) → calls Claude to generate SAFE personalized content → renders content.
- Must be demoable end-to-end with minimal setup.

TECH STACK (required):
- Frontend: Next.js (App Router) for Vercel deployment
- Backend/DB: Supabase (Postgres + Auth optional)
- Long-running/external calls: implement as Next.js API route for alpha (but structure code so it can be moved to Railway later)
- LLM: Claude API (Anthropic)

LEGAL / SAFETY RULES (must enforce in code + prompt):
- No competitor names
- No negative claims about identifiable companies/products (no defamation)
- No copyrighted text/quotes
- No invented facts or stats
- Compare approaches, not vendors
- Output must be structured JSON; render only those sections

DELIVERABLES:
1) A working Next.js project structure with:
   - /app/page.tsx landing page (reads `cta` from query string, e.g. /?cta=compare)
   - Email + consent checkbox form
   - Loading state
   - Results section that renders returned JSON into UI
2) Backend API route:
   - POST /api/personalize
   - Input: { email, cta }
   - Extract domain from email
   - Infer persona using simple rules (e.g., prefixes ops@, rev@, security@, it@, finance@ else “Business Leader”)
   - Infer buyer_stage from cta mapping:
     - compare -> Evaluation
     - learn -> Awareness
     - demo -> Decision
     - default -> Evaluation
   - Enrichment: alpha can be mocked with a small hardcoded lookup table by domain → {company_name, industry, company_size}. If domain unknown, use {“Unknown”, “General”, “Mid-market”}.
   - Call Claude with a STRICT system prompt and a JSON schema requirement. Low temperature.
   - Validate Claude output against JSON schema in code (Zod). If invalid, retry once with “fix JSON only” instruction.
   - Store job + result in Supabase tables:
     - personalization_jobs(id, created_at, email, domain, cta, persona, buyer_stage, company_name, industry, company_size, status)
     - personalization_outputs(job_id, created_at, output_json)
   - Return the parsed JSON output to frontend.

3) Supabase setup instructions:
   - SQL to create tables
   - Env vars needed:
     - NEXT_PUBLIC_SUPABASE_URL
     - NEXT_PUBLIC_SUPABASE_ANON_KEY
     - SUPABASE_SE_
