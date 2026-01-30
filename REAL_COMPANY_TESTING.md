# Testing With Real Companies

## 🏢 AMD Guided Experience Testing Guide

### ✅ WORKS FOR ALL COMPANIES (Real Logic)

The application now uses a **guided form experience** where users explicitly provide key information through dropdown menus. This works for **ANY company**!

---

## 📝 New Guided Form Structure

### Required Fields (All via Dropdowns/Input):

#### 1. Company (Text Input)
```
User enters company name directly
→ "AMD", "Microsoft", "Google", "Any Company Name"
✅ No lookup needed - uses user input
```

#### 2. Role (Dropdown Selection)
```
User selects from:
- Business Leader / Executive
- IT / Technical
- Finance
- Operations
- Security

→ Directly sets persona (no inference needed)
✅ Works for ANY company
```

#### 3. Modernization Stage (Dropdown Selection)
```
User selects from:
- Exploring & Learning (Early Stage) → awareness
- Evaluating & Comparing (Mid Stage) → evaluation
- Ready to Implement (Late Stage) → decision

→ Directly sets buyer stage (no CTA inference needed)
✅ Works for ANY company
```

#### 4. AI Priority (Dropdown Selection)
```
User selects from:
- Infrastructure Modernization
- AI/ML Workloads
- Cloud Migration
- Data Center Optimization
- Performance & Scalability
- Cost Optimization

→ Captured for content personalization
✅ Works for ANY company
```

#### 5. Work Email (Required)
```
✅ john@anyrandomcompany.com      → Valid
✅ security@startup123.io          → Valid
✅ ops@mycompany.co.uk             → Valid
❌ notanemail                      → Invalid
❌ missing@domain                  → Invalid

→ Used for domain extraction and enrichment
```

#### 6. Name (Optional)
```
User can optionally provide name for light personalization
```

---

## 🎯 How It Works Now

### Old Way (Inference):
```
Email: security@stripe.com + CTA: compare
→ System infers: "Security persona", "Evaluation stage"
→ System looks up: Company from database
```

### New Way (User-Driven):
```
User fills guided form:
  Company: "Stripe"
  Role: "Security"
  Modernization Stage: "Evaluating & Comparing"
  AI Priority: "AI/ML Workloads"
  Email: security@stripe.com
  Name: (optional)

→ No inference needed - user tells us directly!
→ Company name comes from user input
→ Still enriches from email domain for additional context
```

---

## 🧪 Test Scenarios

### Test Case 1: Large Enterprise (Microsoft)
```bash
Form Input:
  Company: "Microsoft"
  Role: "IT / Technical"
  Modernization Stage: "Evaluating & Comparing (Mid Stage)"
  AI Priority: "AI/ML Workloads"
  Email: john@microsoft.com
  Name: "John Smith" (optional)

Expected Output:
  ✅ Persona: "IT"
  ✅ Buyer Stage: "evaluation"
  ✅ Company: "Microsoft" (from form)
  ✅ AI Priority: "AI/ML Workloads"
  ✅ Domain: "microsoft.com"
  ✅ Enrichment: Additional data from RAD API
```

### Test Case 2: Startup (Any Company)
```bash
Form Input:
  Company: "RandomStartup Inc"
  Role: "Business Leader / Executive"
  Modernization Stage: "Exploring & Learning (Early Stage)"
  AI Priority: "Cloud Migration"
  Email: founder@randomstartup.io
  Name: "Jane Doe" (optional)

Expected Output:
  ✅ Persona: "Business Leader"
  ✅ Buyer Stage: "awareness"
  ✅ Company: "RandomStartup Inc" (from form)
  ✅ AI Priority: "Cloud Migration"
  ✅ Domain: "randomstartup.io"
  ✅ Enrichment: RAD API attempts lookup
```

### Test Case 3: Mid-Market (AMD Focus)
```bash
Form Input:
  Company: "TechCorp Solutions"
  Role: "Operations"
  Modernization Stage: "Ready to Implement (Late Stage)"
  AI Priority: "Infrastructure Modernization"
  Email: ops@techcorp.com
  Name: (leave blank)

Expected Output:
  ✅ Persona: "Operations"
  ✅ Buyer Stage: "decision"
  ✅ Company: "TechCorp Solutions" (from form)
  ✅ AI Priority: "Infrastructure Modernization"
  ✅ Domain: "techcorp.com"
  ✅ Name: Not provided (optional field)
```

### Test Case 4: Finance Focus
```bash
Form Input:
  Company: "Global Bank"
  Role: "Finance"
  Modernization Stage: "Evaluating & Comparing (Mid Stage)"
  AI Priority: "Cost Optimization"
  Email: cfo@globalbank.com
  Name: "Michael Chen" (optional)

Expected Output:
  ✅ Persona: "Finance"
  ✅ Buyer Stage: "evaluation"
  ✅ Company: "Global Bank" (from form)
  ✅ AI Priority: "Cost Optimization"
  ✅ Domain: "globalbank.com"
```

### Test Case 5: Security Focus
```bash
Form Input:
  Company: "HealthTech Inc"
  Role: "Security"
  Modernization Stage: "Exploring & Learning (Early Stage)"
  AI Priority: "Data Center Optimization"
  Email: ciso@healthtech.com
  Name: (leave blank)

Expected Output:
  ✅ Persona: "Security"
  ✅ Buyer Stage: "awareness"
  ✅ Company: "HealthTech Inc" (from form)
  ✅ AI Priority: "Data Center Optimization"
  ✅ Domain: "healthtech.com"
```

---

## 📊 What Gets Enriched

Even though users provide company name directly, the system still enriches data from the email domain:

### From User Input (Dropdown/Text):
- Company name
- Role/Persona
- Modernization stage
- AI priority

### From Email Domain (RAD Enrichment):
- Industry classification
- Company size
- Employee count
- Headquarters location
- Technology stack
- Recent news
- Buying intent signals
- Confidence score

### Combined Result:
```json
{
  "company_name": "Microsoft" (from user input),
  "persona": "IT" (from user selection),
  "buyer_stage": "evaluation" (from user selection),
  "ai_priority": "AI/ML Workloads" (from user selection),
  "industry": "Technology" (from RAD enrichment),
  "company_size": "enterprise" (from RAD enrichment),
  "employee_count": "221,000" (from RAD enrichment),
  "technology": ["Azure", "Office 365", ...] (from RAD enrichment)
}
```

---

## 🚀 Testing the Application

### Via Web UI:
```
1. Navigate to: http://localhost:3000
2. Fill out the guided form:
   - Company: Your test company
   - Role: Select from dropdown
   - Modernization Stage: Select from dropdown
   - AI Priority: Select from dropdown
   - Email: Enter valid work email
   - Name: (optional)
3. Check consent checkbox
4. Click "Get Personalized Content"
5. Wait for loading (20-40s)
6. Review personalized results
```

### Via API:
```bash
curl -X POST http://localhost:3000/api/personalize \
  -H "Content-Type: application/json" \
  -d '{
    "company": "AMD",
    "role": "IT",
    "modernization_stage": "evaluation",
    "ai_priority": "AI/ML Workloads",
    "email": "john@amd.com",
    "name": "John Smith",
    "cta": "compare"
  }'
```

Expected response:
```json
{
  "success": true,
  "jobId": 12345,
  "data": {
    "headline": "AI/ML Infrastructure for AMD Technical Teams",
    "subheadline": "...",
    "value_prop_1": "...",
    "value_prop_2": "...",
    "value_prop_3": "...",
    "cta_text": "Compare AI/ML Solutions"
  },
  "enrichment": {
    "company_name": "AMD",
    "industry": "Technology",
    "company_size": "enterprise",
    "confidence_score": 0.92
  },
  "metadata": {
    "persona": "IT",
    "buyer_stage": "evaluation",
    "company": "AMD",
    "ai_priority": "AI/ML Workloads",
    "total_latency_ms": 24000
  }
}
```

---

## 🎯 Advantages of Guided Experience

### ✅ No Inference Errors:
- Users explicitly select their role (no guessing from email)
- Users explicitly select their stage (no guessing from CTA)
- Users provide company name directly

### ✅ Works for ANY Company:
- No database of known companies needed
- No enrichment API failures blocking submission
- User provides the critical information upfront

### ✅ Better Data Quality:
- AI Priority is captured (valuable signal)
- Modernization stage is explicit
- Company name is accurate (from source)

### ✅ Improved UX:
- Clear, guided experience (4-6 questions)
- Progressive disclosure
- User feels in control

---

## 🧪 Quick Test Script

Test multiple scenarios:
```bash
# Test Case 1: IT Role, Evaluation Stage
curl -X POST http://localhost:3000/api/personalize \
  -H "Content-Type: application/json" \
  -d '{
    "company": "Microsoft",
    "role": "IT",
    "modernization_stage": "evaluation",
    "ai_priority": "AI/ML Workloads",
    "email": "tech@microsoft.com",
    "cta": "compare"
  }'

# Test Case 2: Business Leader, Decision Stage
curl -X POST http://localhost:3000/api/personalize \
  -H "Content-Type: application/json" \
  -d '{
    "company": "Startup Inc",
    "role": "Business Leader",
    "modernization_stage": "decision",
    "ai_priority": "Cloud Migration",
    "email": "ceo@startup.com",
    "cta": "demo"
  }'

# Test Case 3: Security, Awareness Stage
curl -X POST http://localhost:3000/api/personalize \
  -H "Content-Type: application/json" \
  -d '{
    "company": "FinTech Corp",
    "role": "Security",
    "modernization_stage": "awareness",
    "ai_priority": "Infrastructure Modernization",
    "email": "ciso@fintech.com",
    "cta": "learn"
  }'
```

---

## 💡 Recommendation for Demos

### Best Demo Flow:
1. **Show the guided form** - highlight the dropdown selections
2. **Explain the value** - "Users tell us exactly what they need"
3. **Fill out for a known company** - e.g., "AMD", "Microsoft"
4. **Show the personalized results** - point out company, role, AI priority badges
5. **Explain enrichment** - "We still enrich from email domain for additional context"

### Key Talking Points:
- ✅ **User-driven personalization** - no guessing or inference
- ✅ **Works for any company** - no database limitations
- ✅ **Captures AI priorities** - valuable signal for AMD campaigns
- ✅ **Rich enrichment** - combines user input with API data
- ✅ **Fast and reliable** - no blocking on enrichment failures

---

## 🎯 Bottom Line

### What Changed:
- ❌ **Removed**: Email-based persona inference
- ❌ **Removed**: CTA-based buyer stage inference
- ✅ **Added**: Explicit role selection (dropdown)
- ✅ **Added**: Explicit modernization stage selection (dropdown)
- ✅ **Added**: Explicit company name input (text)
- ✅ **Added**: AI priority capture (dropdown)

### What Still Works:
- ✅ Email validation
- ✅ Domain extraction
- ✅ RAD enrichment (from email domain)
- ✅ Template selection
- ✅ Claude AI adaptation
- ✅ Full personalization flow

### For Production:
- 🚀 All user input is captured and validated
- 🚀 RAD enrichment adds additional context
- 🚀 AI Priority enables campaign analytics
- 🚀 Works for ANY company (no database limitations)
