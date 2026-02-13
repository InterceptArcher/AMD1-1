# Executive Review JSON PDF Implementation

## Overview

The Executive Review PDF system generates structured 2-page AMD Data Center Modernization assessments with embedded JSON metadata. This allows for both human-readable PDFs and programmatic data extraction.

## Architecture

### Components

1. **Executive Review Service** (`executive_review_service.py`)
   - Generates structured JSON content using Claude LLM
   - Uses few-shot prompting with stage-specific examples
   - Maps company inputs to AMD taxonomy (Observer/Challenger/Leader)

2. **PDF Service** (`pdf_service.py`)
   - Renders JSON data into branded AMD PDF
   - Embeds JSON as PDF metadata using pypdf
   - Provides extraction utility to read embedded data

3. **API Endpoints** (`enrichment.py`)
   - `/rad/executive-review` - Generate JSON only
   - `/rad/executive-review-pdf` - Generate and download PDF
   - `/rad/extract-pdf-json` - Extract JSON from uploaded PDF

## JSON Structure

```json
{
  "company_name": "Acme Corporation",
  "stage": "Challenger",
  "stage_sidebar": "58% of Challengers are currently undertaking modernization initiatives.",
  "advantages": [
    {
      "headline": "Performance gains from upgrading core systems",
      "description": "Modernizing high-volume workloads improves responsiveness across operations."
    },
    {
      "headline": "Faster throughput by reducing integration friction",
      "description": "Improving data flow between systems enables more consistent performance."
    }
  ],
  "risks": [
    {
      "headline": "Persistent slowdowns from legacy system connections",
      "description": "If integration issues remain unresolved, performance bottlenecks will continue."
    },
    {
      "headline": "Competitors advance with more unified platforms",
      "description": "Delays in improving system performance allow faster competitors to gain advantage."
    }
  ],
  "recommendations": [
    {
      "title": "Prioritize performance upgrades for high-volume systems",
      "description": "Focus modernization on transactional workloads to improve speed and reduce friction."
    },
    {
      "title": "Strengthen integration across core platforms",
      "description": "Improve data consistency and flow between systems to eliminate performance delays."
    },
    {
      "title": "Adopt scalable infrastructure to support unified operations",
      "description": "Move toward flexible compute environments to handle growing performance demands."
    }
  ],
  "case_study": "KT Cloud Expands AI Power with AMD Instinct Accelerators",
  "case_study_description": "KT Cloud built a scalable AI cloud service using AMD Instinct MI250 accelerators..."
}
```

## API Usage

### 1. Generate JSON Content

```bash
curl -X POST https://your-api.com/rad/executive-review \
  -H "Content-Type: application/json" \
  -d '{
    "company": "Acme Corporation",
    "companySize": "enterprise",
    "industry": "technology",
    "persona": "cto",
    "itEnvironment": "modernizing",
    "businessPriority": "improving_performance",
    "challenge": "integration_friction"
  }'
```

**Response:**
```json
{
  "success": true,
  "company_name": "Acme Corporation",
  "inputs": {
    "industry": "Technology",
    "segment": "Enterprise",
    "persona": "ITDM",
    "stage": "Challenger",
    "priority": "Improving workload performance",
    "challenge": "Integration friction"
  },
  "executive_review": {
    "company_name": "Acme Corporation",
    "stage": "Challenger",
    "advantages": [...],
    "risks": [...],
    "recommendations": [...],
    "case_study": "...",
    "case_study_description": "..."
  }
}
```

### 2. Generate PDF with Embedded JSON

```bash
curl -X POST https://your-api.com/rad/executive-review-pdf \
  -H "Content-Type: application/json" \
  -d '{
    "company": "Acme Corporation",
    "companySize": "enterprise",
    "industry": "technology",
    "persona": "cto",
    "itEnvironment": "modernizing",
    "businessPriority": "improving_performance",
    "challenge": "integration_friction"
  }' \
  --output acme_executive_review.pdf
```

**Optional: Skip JSON embedding**
```bash
curl -X POST https://your-api.com/rad/executive-review-pdf?embed_json=false \
  ...
```

### 3. Extract JSON from PDF

```bash
curl -X POST https://your-api.com/rad/extract-pdf-json \
  -F "file=@acme_executive_review.pdf"
```

**Response:**
```json
{
  "success": true,
  "filename": "acme_executive_review.pdf",
  "data": {
    "company_name": "Acme Corporation",
    "stage": "Challenger",
    "advantages": [...],
    "risks": [...],
    "recommendations": [...]
  },
  "metadata": {
    "company": "Acme Corporation",
    "stage": "Challenger",
    "extracted_at": "2026-02-10T12:34:56.789Z"
  }
}
```

## Use Cases

### 1. CRM Integration

Extract JSON from PDFs and sync to Salesforce:

```python
import requests

# Generate PDF
response = requests.post(
    "https://api.amd.com/rad/executive-review-pdf",
    json={"company": "Acme Corp", ...}
)
pdf_bytes = response.content

# Extract JSON
files = {"file": ("review.pdf", pdf_bytes, "application/pdf")}
extracted = requests.post(
    "https://api.amd.com/rad/extract-pdf-json",
    files=files
).json()

# Sync to Salesforce
salesforce_client.create_record(
    "ExecutiveReview__c",
    {
        "Company__c": extracted["data"]["company_name"],
        "Stage__c": extracted["data"]["stage"],
        "Advantages__c": json.dumps(extracted["data"]["advantages"]),
        ...
    }
)
```

### 2. Content A/B Testing

Compare content variations programmatically:

```python
# Generate variants
variant_a = generate_review(priority="reducing_cost")
variant_b = generate_review(priority="improving_performance")

# Extract and compare
data_a = extract_json_from_pdf(variant_a)
data_b = extract_json_from_pdf(variant_b)

print(f"Variant A advantages: {data_a['advantages']}")
print(f"Variant B advantages: {data_b['advantages']}")
```

### 3. Audit Trail

Track what content was delivered to each account:

```python
# Store PDF in S3
s3_client.put_object(
    Bucket="delivered-pdfs",
    Key=f"{account_id}/review_{timestamp}.pdf",
    Body=pdf_bytes
)

# Log JSON to database
db.execute("""
    INSERT INTO content_audit_log
    (account_id, stage, advantages, risks, recommendations, delivered_at)
    VALUES (?, ?, ?, ?, ?, ?)
""", account_id, stage, json.dumps(advantages), ...)
```

## PDF Metadata Fields

The following metadata is embedded in every PDF:

| Field | Type | Description |
|-------|------|-------------|
| `/ExecutiveReviewData` | JSON string | Complete executive review data |
| `/GeneratedBy` | String | "AMD Data Center Modernization Engine" |
| `/GeneratedAt` | ISO datetime | PDF generation timestamp |
| `/ContentType` | String | "ExecutiveReview" |
| `/Company` | String | Company name |
| `/Stage` | String | Modernization stage (Observer/Challenger/Leader) |

## Technical Details

### PDF Metadata Embedding

Uses pypdf to write custom metadata fields:

```python
import pypdf
import json

reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
writer = pypdf.PdfWriter()

for page in reader.pages:
    writer.add_page(page)

metadata = {
    "/ExecutiveReviewData": json.dumps(executive_review_data),
    "/GeneratedBy": "AMD Data Center Modernization Engine",
    "/GeneratedAt": datetime.utcnow().isoformat(),
    ...
}

writer.add_metadata(metadata)

output = io.BytesIO()
writer.write(output)
output.seek(0)
return output.read()
```

### JSON Extraction

Reads custom metadata from PDF:

```python
import pypdf
import json

reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
json_str = reader.metadata.get("/ExecutiveReviewData")
data = json.loads(json_str)
return data
```

## Testing

Run the test script to verify the implementation:

```bash
cd backend
python scripts/test_executive_review_pdf.py
```

This will:
1. Generate executive review JSON
2. Create PDF with embedded metadata
3. Extract and verify the JSON

## Implementation Checklist

- [x] Executive review service with few-shot prompting
- [x] JSON-to-PDF rendering with AMD branding
- [x] PDF metadata embedding (pypdf)
- [x] JSON extraction utility
- [x] API endpoints for generation and extraction
- [x] Documentation and examples
- [ ] Frontend UI for executive review form
- [ ] Email delivery integration
- [ ] Supabase storage for generated PDFs
- [ ] Analytics tracking

## Rationale

### Why Embed JSON in PDF Metadata?

1. **Single Source of Truth**: PDF contains both human-readable content and machine-readable data
2. **CRM Integration**: Easily extract structured data for Salesforce/HubSpot sync
3. **Audit Trail**: Track exactly what content was delivered to each account
4. **A/B Testing**: Programmatically compare content variations
5. **Content Analysis**: Analyze personalization patterns across accounts

### Why JSON-First Architecture?

1. **Structured Content**: LLM generates consistent JSON structure
2. **Template Flexibility**: Same JSON can render to PDF, HTML, email, etc.
3. **Validation**: Schema validation ensures content quality
4. **API-First**: JSON responses work for web, mobile, integrations
5. **Future-Proof**: Easy to add new output formats (PowerPoint, interactive web)

## Next Steps

1. **Frontend Integration**: Add executive review form to Next.js app
2. **Email Delivery**: Send PDFs via SendGrid/Resend with JSON backup
3. **Analytics**: Track which recommendations drive conversions
4. **Multi-Language**: Generate reviews in multiple languages
5. **Interactive Mode**: Let users refine recommendations in real-time
