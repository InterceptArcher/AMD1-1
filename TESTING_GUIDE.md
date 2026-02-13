# Testing Guide: Executive Review JSON PDF

## What's Different from Alpha?

### Current Alpha Deployment (Web Display Only)
- **Endpoint**: `POST /rad/executive-review` (JSON response)
- **Frontend**: Displays executive review as HTML on the web page
- **Output**: Shows 2-page assessment inline in the browser
- **Use Case**: Web-only viewing experience

### New Implementation (PDF with Embedded JSON)
- **Endpoint**: `POST /rad/executive-review-pdf` (PDF file)
- **Frontend**: Could download PDF for offline use
- **Output**: Downloadable PDF with embedded JSON metadata
- **Use Cases**:
  - Email delivery of PDFs
  - CRM integration (extract JSON programmatically)
  - Offline viewing and printing
  - Audit trails and compliance

**Key Difference**: The new implementation adds **PDF generation + JSON embedding** while the alpha only shows the content as HTML.

---

## How to Test

### Option 1: Quick Test with curl (Backend Must Be Running)

#### 1. Start the Backend
```bash
cd /workspaces/AMD1-1_Alpha/backend

# Install dependencies if needed
pip install pypdf weasyprint reportlab anthropic fastapi uvicorn

# Run the backend
uvicorn app.main:app --reload --port 8000
```

#### 2. Test JSON Generation (Existing Alpha Endpoint)
```bash
curl -X POST http://localhost:8000/rad/executive-review \
  -H "Content-Type: application/json" \
  -d '{
    "company": "Acme Corp",
    "companySize": "enterprise",
    "industry": "technology",
    "persona": "cto",
    "itEnvironment": "modernizing",
    "businessPriority": "improving_performance",
    "challenge": "integration_friction"
  }' | jq
```

**Expected Output**: JSON with advantages, risks, recommendations

#### 3. Test PDF Generation (NEW Endpoint)
```bash
curl -X POST http://localhost:8000/rad/executive-review-pdf \
  -H "Content-Type: application/json" \
  -d '{
    "company": "Acme Corp",
    "companySize": "enterprise",
    "industry": "technology",
    "persona": "cto",
    "itEnvironment": "modernizing",
    "businessPriority": "improving_performance",
    "challenge": "integration_friction"
  }' \
  --output acme_executive_review.pdf
```

**Expected Output**: `acme_executive_review.pdf` file downloaded

#### 4. Test JSON Extraction (NEW Endpoint)
```bash
curl -X POST http://localhost:8000/rad/extract-pdf-json \
  -F "file=@acme_executive_review.pdf" | jq
```

**Expected Output**: Extracted JSON matching the original data

---

### Option 2: Test on Alpha Deployment

The alpha deployment is at: `https://amd1-1-alpha.vercel.app` (frontend)
Backend is at: `https://amd1-1-backend.onrender.com`

#### Check if New Endpoints Are Deployed

```bash
# Test health endpoint
curl https://amd1-1-backend.onrender.com/rad/health

# Test if PDF endpoint exists
curl -X POST https://amd1-1-backend.onrender.com/rad/executive-review-pdf \
  -H "Content-Type: application/json" \
  -d '{
    "company": "Test Corp",
    "companySize": "enterprise",
    "industry": "technology",
    "persona": "cto",
    "itEnvironment": "modernizing",
    "businessPriority": "improving_performance",
    "challenge": "integration_friction"
  }' \
  --output test_review.pdf
```

**If you get a 404 error**: The new endpoints haven't been deployed yet. You need to deploy the backend changes first.

---

### Option 3: Frontend Integration Test

#### A. Add Download Button to Existing UI

Modify `/workspaces/AMD1-1_Alpha/frontend/src/components/ExecutiveReviewDisplay.tsx`:

```tsx
// Add this button after the review content
<button
  onClick={async () => {
    const response = await fetch('/api/rad/executive-review-pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        company: executiveReview.company_name,
        // ... other form data
      }),
    });

    if (response.ok) {
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${executiveReview.company_name}_executive_review.pdf`;
      a.click();
    }
  }}
  className="mt-8 px-6 py-3 bg-[#00c8aa] text-[#0a0a12] font-bold rounded-lg hover:bg-[#00e0be] transition-all"
>
  Download PDF
</button>
```

#### B. Test the Frontend

1. Start frontend dev server:
```bash
cd /workspaces/AMD1-1_Alpha/frontend
npm run dev
```

2. Open browser to `http://localhost:3000`

3. Fill out the form with:
   - Company: Acme Corp
   - Size: Enterprise
   - Industry: Technology
   - Role: CTO
   - IT Environment: Modernizing
   - Priority: Improving performance
   - Challenge: Integration friction

4. Click "Download PDF" button (after adding it)

5. Verify PDF downloads and opens correctly

---

### Option 4: Python Test Script

If you have dependencies installed:

```bash
cd /workspaces/AMD1-1_Alpha/backend

# Install dependencies
pip install pypdf weasyprint reportlab anthropic

# Run test script
python scripts/test_executive_review_pdf.py
```

**Expected Output**:
```
============================================================
AMD Executive Review PDF Test
============================================================

Step 1: Generating executive review JSON...
------------------------------------------------------------
✓ Company: Acme Corporation
✓ Stage: Challenger
✓ Advantages: 2 items
✓ Risks: 2 items
✓ Recommendations: 3 items
✓ Case Study: KT Cloud Expands AI Power...

Step 2: Generating PDF with embedded JSON metadata...
------------------------------------------------------------
✓ PDF generated: 45678 bytes
✓ PDF saved to: test_executive_review.pdf

Step 3: Extracting JSON from PDF...
------------------------------------------------------------
✓ JSON successfully extracted from PDF
✓ Company name matches
✓ Stage matches
✓ Advantages count matches

============================================================
✓ Test completed successfully!
============================================================
```

---

## Verification Checklist

### ✅ JSON Generation Works
- [ ] `/rad/executive-review` returns structured JSON
- [ ] JSON contains advantages, risks, recommendations
- [ ] Case study is selected correctly

### ✅ PDF Generation Works
- [ ] `/rad/executive-review-pdf` returns PDF file
- [ ] PDF has AMD branding (cyan #00c8aa, correct fonts)
- [ ] PDF contains all content from JSON
- [ ] File size is reasonable (~40-100KB)

### ✅ JSON Embedding Works
- [ ] PDF metadata contains `/ExecutiveReviewData` field
- [ ] Metadata includes generation timestamp
- [ ] Metadata includes company name and stage

### ✅ JSON Extraction Works
- [ ] `/rad/extract-pdf-json` accepts uploaded PDF
- [ ] Extracted JSON matches original data
- [ ] All fields are present and correct

---

## Common Issues & Solutions

### Issue: `ModuleNotFoundError: No module named 'pypdf'`
**Solution**: Install dependencies
```bash
pip install pypdf weasyprint reportlab
```

### Issue: `weasyprint not available, using reportlab fallback`
**Solution**: This is expected. Install weasyprint for better quality:
```bash
pip install weasyprint
# On Ubuntu/Debian:
sudo apt-get install python3-cffi python3-brotli libpango-1.0-0 libpangoft2-1.0-0
```

### Issue: `404 Not Found` on alpha deployment
**Solution**: Backend changes haven't been deployed yet. Deploy using:
```bash
cd /workspaces/AMD1-1_Alpha
./scripts/deploy-backend-supabase.sh
```

### Issue: PDF renders but JSON extraction fails
**Solution**: pypdf might not be installed on production. Check logs:
```bash
# Check Render logs
# Ensure pypdf is in requirements.txt
```

### Issue: CORS error when testing from frontend
**Solution**: Make sure backend allows CORS for your frontend domain:
```python
# In backend/app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://amd1-1-alpha.vercel.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Next Steps After Testing

Once testing is complete:

1. **Deploy Backend**
   ```bash
   cd /workspaces/AMD1-1_Alpha
   git add .
   git commit -m "Add executive review JSON PDF generation with metadata embedding"
   git push origin beta
   # Deploy to Render
   ```

2. **Add Frontend UI**
   - Add "Download PDF" button to ExecutiveReviewDisplay component
   - Show loading state while PDF generates
   - Handle download errors gracefully

3. **Enable Email Delivery**
   - Integrate with SendGrid/Resend
   - Attach generated PDF to email
   - Include PDF extraction instructions

4. **Monitor Performance**
   - Track PDF generation time
   - Monitor file sizes
   - Log extraction success rate

5. **Add Analytics**
   - Track which companies download PDFs
   - Monitor which stages/industries most common
   - A/B test content variations

---

## Comparison: Alpha vs New Implementation

| Feature | Alpha (Current) | New Implementation |
|---------|----------------|-------------------|
| **Output Format** | HTML (web only) | PDF (downloadable) |
| **Endpoint** | `/rad/executive-review` | `/rad/executive-review-pdf` |
| **JSON Metadata** | ❌ No | ✅ Yes (embedded) |
| **Offline Use** | ❌ No | ✅ Yes |
| **Email Delivery** | ❌ No | ✅ Yes |
| **CRM Integration** | ⚠️ Manual | ✅ Programmatic |
| **Audit Trail** | ❌ No | ✅ Yes (metadata) |
| **Print Quality** | ⚠️ Browser-dependent | ✅ High quality |

---

## Testing Scenarios

### Scenario 1: Web Display (Alpha)
1. User fills form
2. Frontend calls `/rad/executive-review`
3. JSON returned
4. Frontend renders HTML
5. User views in browser

### Scenario 2: PDF Download (New)
1. User fills form
2. Frontend calls `/rad/executive-review-pdf`
3. PDF generated with embedded JSON
4. Browser downloads PDF
5. User can open, print, email PDF

### Scenario 3: CRM Integration (New)
1. User downloads PDF
2. Sales rep uploads to Salesforce
3. Apex code calls `/rad/extract-pdf-json`
4. JSON extracted and saved to custom object
5. Automated follow-up triggered based on stage

---

## Questions to Ask

1. **Do you want BOTH web display AND PDF download?**
   - Keep existing `/rad/executive-review` for web
   - Add new `/rad/executive-review-pdf` for download

2. **Should PDF be generated automatically or on-demand?**
   - Auto: Generate during form submission
   - On-demand: Add "Download PDF" button

3. **Do you need email delivery?**
   - If yes, integrate with SendGrid/Resend
   - If no, just provide download link

4. **Do you need CRM integration?**
   - If yes, document extraction API for sales team
   - If no, PDF metadata still useful for audit trails

---

## Summary

The **new implementation** adds PDF generation with embedded JSON to the existing web-based executive review system. This enables:

✅ Offline viewing and sharing
✅ Email delivery
✅ CRM integration via JSON extraction
✅ Audit trails and compliance
✅ Print-ready output

The **alpha deployment** continues to work for web-only viewing, and both can coexist (JSON for web, PDF for download).
