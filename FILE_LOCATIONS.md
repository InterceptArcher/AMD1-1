# 📍 File Locations in Codespace

Here's exactly where each file was created or modified in `/workspaces/AMD1-1_Alpha/`:

## 🆕 NEW FILES CREATED

### Frontend Components
```
/workspaces/AMD1-1_Alpha/app/components/LoadingState.tsx
/workspaces/AMD1-1_Alpha/app/components/PersonalizedResults.tsx
/workspaces/AMD1-1_Alpha/app/layout.tsx
```

### Backend API
```
/workspaces/AMD1-1_Alpha/app/api/personalize/route.ts
```

### Library Code
```
/workspaces/AMD1-1_Alpha/lib/schemas.ts
/workspaces/AMD1-1_Alpha/lib/anthropic/client.ts
/workspaces/AMD1-1_Alpha/lib/anthropic/mock-client.ts
/workspaces/AMD1-1_Alpha/lib/supabase/client.ts
/workspaces/AMD1-1_Alpha/lib/supabase/queries.ts
/workspaces/AMD1-1_Alpha/lib/utils/email.ts
/workspaces/AMD1-1_Alpha/lib/utils/enrichment.ts
/workspaces/AMD1-1_Alpha/lib/enrichment/rad-client.ts
/workspaces/AMD1-1_Alpha/lib/personalization/template-engine.ts
/workspaces/AMD1-1_Alpha/lib/personalization/llm-adapter.ts
```

### Database & Migrations
```
/workspaces/AMD1-1_Alpha/supabase/migrations/001_create_personalization_tables.sql
/workspaces/AMD1-1_Alpha/supabase/migrations/002_add_enrichment_fields.sql
/workspaces/AMD1-1_Alpha/supabase/migrations/003_add_ai_priority_field.sql
/workspaces/AMD1-1_Alpha/supabase/README.md
```

### Deployment Scripts
```
/workspaces/AMD1-1_Alpha/scripts/deploy-backend-supabase.sh
/workspaces/AMD1-1_Alpha/scripts/deploy-frontend-vercel.sh
```

### Tests
```
/workspaces/AMD1-1_Alpha/tests/landing-page.spec.ts
/workspaces/AMD1-1_Alpha/tests/email-form.spec.ts
/workspaces/AMD1-1_Alpha/tests/api-personalize.spec.ts
```

### Configuration & Documentation
```
/workspaces/AMD1-1_Alpha/.env.example
/workspaces/AMD1-1_Alpha/next.config.mjs
/workspaces/AMD1-1_Alpha/vercel.json
/workspaces/AMD1-1_Alpha/IMPLEMENTATION_SUMMARY.md
/workspaces/AMD1-1_Alpha/IMPLEMENTATION_COMPLETE.md
/workspaces/AMD1-1_Alpha/INTEGRATION_PLAN.md
/workspaces/AMD1-1_Alpha/FULL_EXPLANATION.md
/workspaces/AMD1-1_Alpha/REAL_COMPANY_TESTING.md
/workspaces/AMD1-1_Alpha/MOCK_VS_REAL_COMPARISON.md
```

## ✏️ MODIFIED FILES

### Updated Existing Files
```
/workspaces/AMD1-1_Alpha/app/page.tsx              (Full workflow integration)
/workspaces/AMD1-1_Alpha/app/components/EmailForm.tsx   (API integration)
/workspaces/AMD1-1_Alpha/package.json              (Added dependencies)
/workspaces/AMD1-1_Alpha/tsconfig.json             (Next.js configuration)
/workspaces/AMD1-1_Alpha/setup/stack.json          (Added Supabase)
/workspaces/AMD1-1_Alpha/README.md                 (Full documentation)
/workspaces/AMD1-1_Alpha/.gitignore                (Next.js additions)
/workspaces/AMD1-1_Alpha/playwright.config.ts      (Fixed typo from playright)
```

## 📦 Dependencies Added

```json
{
  "@anthropic-ai/sdk": "^0.30.0",
  "@supabase/supabase-js": "^2.45.0",
  "zod": "^3.23.0"
}
```

## 🗂️ Directory Structure Created

```
lib/
├── anthropic/
├── supabase/
└── utils/

app/
├── api/
│   └── personalize/
└── components/

supabase/
└── migrations/
```

## 🎯 Quick Access Guide

### To modify the guided form (NEW):
```
→ app/components/EmailForm.tsx (Dropdown options and validation)
→ lib/schemas.ts (Form field validation)
→ app/page.tsx (Form submission handler)
```

### To modify the personalization logic:
```
→ lib/anthropic/client.ts (Claude prompts and API calls)
→ lib/personalization/llm-adapter.ts (Template adaptation)
→ lib/personalization/template-engine.ts (Template library and selection)
→ lib/enrichment/rad-client.ts (RAD API integration)
→ lib/utils/email.ts (Type definitions for persona and buyer stage)
```

### To modify the UI:
```
→ app/page.tsx (Main workflow)
→ app/components/EmailForm.tsx (Form)
→ app/components/LoadingState.tsx (Loading UI)
→ app/components/PersonalizedResults.tsx (Results display)
```

### To modify the API:
```
→ app/api/personalize/route.ts (Main API logic)
→ lib/schemas.ts (Validation schemas)
→ lib/supabase/queries.ts (Database operations)
```

### To modify database schema:
```
→ supabase/migrations/001_create_personalization_tables.sql (Base tables)
→ supabase/migrations/002_add_enrichment_fields.sql (RAD enrichment fields)
→ supabase/migrations/003_add_ai_priority_field.sql (AI priority field)
```

### To test:
```
→ tests/landing-page.spec.ts
→ tests/email-form.spec.ts
→ tests/api-personalize.spec.ts
```

### To deploy:
```
→ scripts/deploy-frontend-vercel.sh
→ scripts/deploy-backend-supabase.sh
```

---

**All files are located in the IDE's file explorer** and can be searched using Ctrl+P (Cmd+P on Mac).
