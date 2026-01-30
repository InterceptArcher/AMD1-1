"""
PDF Service: Generates personalized ebook PDFs.
Uses HTML templates with personalization slots.
Stores PDFs in Supabase Storage, returns signed URLs.
"""

import logging
import io
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from string import Template

from app.config import settings
from app.services.ebook_content import (
    EBOOK_SECTIONS,
    CASE_STUDIES,
    get_case_study_for_industry,
    get_buying_stage_context,
    get_persona_context
)

logger = logging.getLogger(__name__)

# PDF Configuration
PDF_EXPIRY_HOURS = 24 * 7  # 7 days


class PDFService:
    """
    Generates personalized PDF ebooks.
    - Uses HTML templates with personalization
    - Stores in Supabase Storage
    - Returns signed URLs for download
    """

    def __init__(self, supabase_client=None):
        """
        Initialize PDF service.

        Args:
            supabase_client: Optional Supabase client for storage
        """
        self.supabase = supabase_client
        self.storage_bucket = "personalized-pdfs"
        logger.info("PDF service initialized")

    async def generate_pdf(
        self,
        job_id: int,
        profile: Dict[str, Any],
        intro_hook: str,
        cta: str
    ) -> Dict[str, Any]:
        """
        Generate personalized PDF for a job.

        Args:
            job_id: Job ID for tracking
            profile: Normalized profile data
            intro_hook: Personalized intro hook
            cta: Personalized CTA

        Returns:
            Dict with pdf_url, storage_path, file_size
        """
        try:
            # Generate HTML content
            html_content = self._render_template(profile, intro_hook, cta)

            # Convert to PDF
            pdf_bytes = await self._html_to_pdf(html_content)

            if not pdf_bytes:
                raise ValueError("PDF generation returned empty content")

            # Generate unique filename
            email = profile.get("email", "unknown")
            filename = self._generate_filename(email, job_id)

            # Store in Supabase Storage (if available)
            if self.supabase:
                storage_path, pdf_url = await self._store_pdf(
                    pdf_bytes, filename
                )
            else:
                # Return base64 for testing
                import base64
                storage_path = f"local/{filename}"
                pdf_url = f"data:application/pdf;base64,{base64.b64encode(pdf_bytes).decode()}"

            result = {
                "pdf_url": pdf_url,
                "storage_path": storage_path,
                "file_size_bytes": len(pdf_bytes),
                "generated_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(hours=PDF_EXPIRY_HOURS)).isoformat()
            }

            logger.info(f"Generated PDF for job {job_id}: {len(pdf_bytes)} bytes")
            return result

        except Exception as e:
            logger.error(f"PDF generation failed for job {job_id}: {e}")
            raise

    async def generate_amd_ebook(
        self,
        job_id: int,
        profile: Dict[str, Any],
        personalization: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate personalized AMD ebook with 3 personalization points.

        Args:
            job_id: Job ID for tracking
            profile: Normalized profile data
            personalization: Dict with personalized_hook, case_study_framing, personalized_cta
            user_context: User-provided context (goal, persona, industry)

        Returns:
            Dict with pdf_url, storage_path, file_size
        """
        try:
            user_context = user_context or {}

            # Get the appropriate case study based on industry
            industry = user_context.get("industry_input") or profile.get("industry", "technology")
            case_study = get_case_study_for_industry(industry)

            # Generate HTML content with AMD ebook template
            html_content = self._render_amd_ebook_template(
                profile=profile,
                personalized_hook=personalization.get("personalized_hook", ""),
                case_study=case_study,
                case_study_framing=personalization.get("case_study_framing", ""),
                personalized_cta=personalization.get("personalized_cta", ""),
                user_context=user_context
            )

            # Convert to PDF
            pdf_bytes = await self._html_to_pdf(html_content)

            if not pdf_bytes:
                raise ValueError("PDF generation returned empty content")

            # Generate unique filename
            email = profile.get("email", "unknown")
            filename = self._generate_filename(email, job_id)

            # Store in Supabase Storage (if available)
            if self.supabase:
                storage_path, pdf_url = await self._store_pdf(pdf_bytes, filename)
            else:
                import base64
                storage_path = f"local/{filename}"
                pdf_url = f"data:application/pdf;base64,{base64.b64encode(pdf_bytes).decode()}"

            result = {
                "pdf_url": pdf_url,
                "storage_path": storage_path,
                "file_size_bytes": len(pdf_bytes),
                "generated_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(hours=PDF_EXPIRY_HOURS)).isoformat(),
                "case_study_used": case_study["title"]
            }

            logger.info(f"Generated AMD ebook for job {job_id}: {len(pdf_bytes)} bytes, case study: {case_study['title']}")
            return result

        except Exception as e:
            logger.error(f"AMD ebook generation failed for job {job_id}: {e}")
            raise

    def _render_amd_ebook_template(
        self,
        profile: Dict[str, Any],
        personalized_hook: str,
        case_study: Dict[str, Any],
        case_study_framing: str,
        personalized_cta: str,
        user_context: Dict[str, Any]
    ) -> str:
        """Render AMD ebook HTML template with personalization."""
        template = Template(self._get_amd_ebook_template())

        variables = {
            "first_name": profile.get("first_name", "Reader"),
            "company_name": profile.get("company_name", "your company"),
            "title": profile.get("title", "Professional"),
            "industry": user_context.get("industry_input") or profile.get("industry", "your industry"),
            "generated_date": datetime.utcnow().strftime("%B %d, %Y"),
            # Personalized sections
            "personalized_hook": personalized_hook,
            "case_study_framing": case_study_framing,
            "personalized_cta": personalized_cta,
            # Case study content
            "case_study_title": case_study["title"],
            "case_study_company": case_study["company"],
            "case_study_industry": case_study["industry"],
            "case_study_challenge": case_study["challenge"],
            "case_study_solution": case_study["solution"],
            "case_study_quote": case_study["quote"],
            "case_study_quote_author": case_study["quote_author"],
            "case_study_result": case_study["result"],
            # Static content
            "intro_section": EBOOK_SECTIONS["intro_section"],
            "three_stages_intro": EBOOK_SECTIONS["three_stages_intro"],
            "leaders_section": EBOOK_SECTIONS["leaders_section"],
            "challengers_section": EBOOK_SECTIONS["challengers_section"],
            "observers_section": EBOOK_SECTIONS["observers_section"],
            "path_to_leadership": EBOOK_SECTIONS["path_to_leadership"],
            "modernization_models": EBOOK_SECTIONS["modernization_models"],
            "why_amd": EBOOK_SECTIONS["why_amd"],
            "assessment_questions": EBOOK_SECTIONS["assessment_questions"],
        }

        return template.safe_substitute(variables)

    def _get_amd_ebook_template(self) -> str:
        """Get the AMD ebook HTML template."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>From Observers to Enterprise AI Readiness</title>
    <style>
        @page { size: A4; margin: 1.5cm; }
        * { box-sizing: border-box; }
        body {
            font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #1a1a2e;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            font-size: 11pt;
        }
        h1 { font-size: 28pt; color: #ED1C24; margin-bottom: 10px; }
        h2 { font-size: 18pt; color: #1a1a2e; border-bottom: 2px solid #ED1C24; padding-bottom: 8px; margin-top: 30px; }
        h3 { font-size: 14pt; color: #ED1C24; margin-top: 20px; }
        .cover {
            text-align: center;
            padding: 80px 20px;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: white;
            page-break-after: always;
            border-radius: 8px;
        }
        .cover h1 { color: white; font-size: 32pt; }
        .cover .subtitle { font-size: 14pt; color: #aaa; margin-top: 20px; }
        .cover .personalized-for {
            margin-top: 40px;
            padding: 20px;
            background: rgba(237, 28, 36, 0.2);
            border-radius: 8px;
            border: 1px solid #ED1C24;
        }
        .personalized-hook {
            background: linear-gradient(135deg, #ED1C24 0%, #c41e24 100%);
            color: white;
            padding: 25px;
            border-radius: 8px;
            margin: 30px 0;
            font-size: 12pt;
        }
        .personalized-hook h3 { color: white; margin-top: 0; }
        .section { page-break-inside: avoid; margin-bottom: 25px; }
        .stats-box {
            background: #f5f5f5;
            padding: 20px;
            border-left: 4px solid #ED1C24;
            margin: 20px 0;
        }
        .stats-box .stat { font-size: 24pt; color: #ED1C24; font-weight: bold; }
        .case-study {
            background: #f8f9fa;
            padding: 25px;
            border-radius: 8px;
            margin: 30px 0;
            border: 1px solid #e0e0e0;
            page-break-inside: avoid;
        }
        .case-study-header {
            background: #1a1a2e;
            color: white;
            padding: 15px 20px;
            margin: -25px -25px 20px -25px;
            border-radius: 8px 8px 0 0;
        }
        .case-study-framing {
            background: #fff3cd;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
            border-left: 4px solid #ED1C24;
            font-style: italic;
        }
        .quote {
            font-style: italic;
            padding: 15px 20px;
            background: white;
            border-left: 4px solid #ED1C24;
            margin: 15px 0;
        }
        .quote-author { font-weight: bold; color: #666; margin-top: 10px; }
        .cta-section {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: white;
            padding: 40px;
            border-radius: 8px;
            text-align: center;
            margin-top: 40px;
            page-break-inside: avoid;
        }
        .cta-section h2 { color: white; border: none; }
        .cta-section .personalized-cta {
            font-size: 14pt;
            margin: 20px 0;
            padding: 20px;
            background: rgba(237, 28, 36, 0.3);
            border-radius: 8px;
        }
        .cta-button {
            display: inline-block;
            background: #ED1C24;
            color: white;
            padding: 15px 40px;
            border-radius: 4px;
            text-decoration: none;
            font-weight: bold;
            margin-top: 15px;
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 9pt;
            color: #666;
        }
        .amd-logo { color: #ED1C24; font-weight: bold; font-size: 16pt; }
        ul { padding-left: 20px; }
        li { margin-bottom: 8px; }
        .two-col { display: flex; gap: 20px; }
        .two-col > div { flex: 1; }
    </style>
</head>
<body>
    <!-- COVER PAGE -->
    <div class="cover">
        <div class="amd-logo">AMD</div>
        <h1>FROM OBSERVERS TO<br>ENTERPRISE AI READINESS</h1>
        <p class="subtitle">A Strategic Guide to Data Center Modernization</p>
        <div class="personalized-for">
            <p>Prepared for</p>
            <p style="font-size: 18pt; font-weight: bold;">$first_name</p>
            <p>$title at $company_name</p>
            <p style="margin-top: 15px; font-size: 10pt;">$generated_date</p>
        </div>
    </div>

    <!-- PERSONALIZED HOOK -->
    <div class="personalized-hook">
        <h3>A Message For You</h3>
        <p>$personalized_hook</p>
    </div>

    <!-- INTRO SECTION -->
    <div class="section">
        <h2>Redefining the Data Center: AI Readiness in the Age of Acceleration</h2>
        <p>$intro_section</p>
        <div class="stats-box">
            <span class="stat">97%</span>
            <p>of data center capacity was occupied as of March 2023 in top North American markets.</p>
        </div>
    </div>

    <!-- THREE STAGES -->
    <div class="section">
        <h2>Understanding the Three Stages of Data Center Modernization</h2>
        <p>$three_stages_intro</p>
    </div>

    <div class="section">
        <h3>Data Center Leaders (26%)</h3>
        <p>$leaders_section</p>
    </div>

    <div class="section">
        <h3>Data Center Challengers (32%)</h3>
        <p>$challengers_section</p>
    </div>

    <div class="section">
        <h3>Data Center Observers (42%)</h3>
        <p>$observers_section</p>
    </div>

    <!-- PATH TO LEADERSHIP -->
    <div class="section">
        <h2>The Path to Leadership: Moving Through the Stages</h2>
        <p>$path_to_leadership</p>
    </div>

    <div class="section">
        <h2>Modernization Models</h2>
        <p>$modernization_models</p>
    </div>

    <!-- PERSONALIZED CASE STUDY -->
    <div class="case-study">
        <div class="case-study-header">
            <h3 style="margin: 0; color: white;">Customer Success: $case_study_company</h3>
            <p style="margin: 5px 0 0 0; font-size: 10pt; opacity: 0.8;">$case_study_industry</p>
        </div>
        <div class="case-study-framing">
            <strong>Why this matters for $company_name:</strong><br>
            $case_study_framing
        </div>
        <p><strong>The Challenge:</strong> $case_study_challenge</p>
        <p><strong>The Solution:</strong> $case_study_solution</p>
        <div class="quote">
            "$case_study_quote"
            <div class="quote-author">— $case_study_quote_author</div>
        </div>
        <p><strong>The Result:</strong> $case_study_result</p>
    </div>

    <!-- ASSESSMENT -->
    <div class="section">
        <h2>Where Do You Stand on the Modernization Curve?</h2>
        <p>$assessment_questions</p>
    </div>

    <!-- WHY AMD -->
    <div class="section">
        <h2>Why AMD: Your Strategic Partner</h2>
        <p>$why_amd</p>
    </div>

    <!-- PERSONALIZED CTA -->
    <div class="cta-section">
        <h2>Ready to Take the Next Step?</h2>
        <div class="personalized-cta">
            $personalized_cta
        </div>
        <a href="https://www.amd.com/en/solutions/data-center.html" class="cta-button">Explore AMD AI Solutions</a>
    </div>

    <!-- FOOTER -->
    <div class="footer">
        <p>This guide was personalized for $first_name at $company_name</p>
        <p>Generated on $generated_date</p>
        <p style="margin-top: 15px;">© 2025 Advanced Micro Devices, Inc.</p>
    </div>
</body>
</html>'''

    def _get_case_study_for_profile(
        self,
        profile: Dict[str, Any],
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get appropriate case study based on profile industry."""
        industry = user_context.get("industry_input") or profile.get("industry", "technology")
        return get_case_study_for_industry(industry)

    def _render_template(
        self,
        profile: Dict[str, Any],
        intro_hook: str,
        cta: str
    ) -> str:
        """
        Render HTML template with personalization.

        Args:
            profile: Profile data
            intro_hook: Personalized intro
            cta: Personalized CTA

        Returns:
            Rendered HTML string
        """
        template = Template(self._get_ebook_template())

        # Prepare template variables
        variables = {
            "first_name": profile.get("first_name", "Reader"),
            "company_name": profile.get("company_name", "your company"),
            "title": profile.get("title", "Professional"),
            "industry": profile.get("industry", "your industry"),
            "intro_hook": intro_hook,
            "cta": cta,
            "generated_date": datetime.utcnow().strftime("%B %d, %Y"),
        }

        return template.safe_substitute(variables)

    def _get_ebook_template(self) -> str:
        """Get the HTML ebook template."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your Personalized Guide</title>
    <style>
        @page {
            size: A4;
            margin: 2cm;
        }

        body {
            font-family: 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 40px;
        }

        .cover {
            text-align: center;
            padding: 100px 0;
            page-break-after: always;
        }

        .cover h1 {
            font-size: 36px;
            color: #1a365d;
            margin-bottom: 20px;
        }

        .cover .subtitle {
            font-size: 18px;
            color: #4a5568;
            margin-bottom: 40px;
        }

        .personalized-intro {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin: 40px 0;
        }

        .personalized-intro h2 {
            margin-top: 0;
            font-size: 24px;
        }

        .personalized-intro p {
            font-size: 18px;
            margin-bottom: 0;
        }

        .chapter {
            page-break-before: always;
            padding-top: 40px;
        }

        .chapter h2 {
            color: #1a365d;
            font-size: 28px;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }

        .chapter p {
            font-size: 14px;
            margin-bottom: 16px;
        }

        .callout {
            background: #f7fafc;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin: 20px 0;
        }

        .cta-section {
            background: #1a365d;
            color: white;
            padding: 40px;
            border-radius: 10px;
            text-align: center;
            margin-top: 60px;
        }

        .cta-section h2 {
            color: white;
            margin-top: 0;
        }

        .cta-section p {
            font-size: 18px;
        }

        .cta-button {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 15px 40px;
            border-radius: 5px;
            text-decoration: none;
            font-weight: bold;
            margin-top: 20px;
        }

        .footer {
            text-align: center;
            margin-top: 60px;
            padding-top: 20px;
            border-top: 1px solid #e2e8f0;
            font-size: 12px;
            color: #718096;
        }
    </style>
</head>
<body>
    <div class="cover">
        <h1>Strategic Growth Guide</h1>
        <p class="subtitle">Personalized insights for $company_name</p>
        <p>Prepared for: $first_name</p>
        <p>$generated_date</p>
    </div>

    <div class="personalized-intro">
        <h2>A Message For You</h2>
        <p>$intro_hook</p>
    </div>

    <div class="chapter">
        <h2>Chapter 1: Understanding the Landscape</h2>
        <p>The $industry sector is evolving rapidly. Companies like $company_name are at the forefront of this transformation, and leaders in your position as $title play a crucial role in driving success.</p>

        <div class="callout">
            <strong>Key Insight:</strong> Organizations that adapt their strategies early see 40% better outcomes in competitive markets.
        </div>

        <p>In this guide, we'll explore actionable strategies tailored to your role and industry. Each section builds on proven methodologies that have helped similar organizations achieve their goals.</p>
    </div>

    <div class="chapter">
        <h2>Chapter 2: Strategic Frameworks</h2>
        <p>Effective strategy requires a structured approach. For $title roles in $industry, we recommend focusing on three key areas:</p>

        <p><strong>1. Alignment</strong> - Ensure your team's efforts connect directly to organizational objectives.</p>
        <p><strong>2. Measurement</strong> - Establish clear metrics that reflect true progress.</p>
        <p><strong>3. Iteration</strong> - Build feedback loops that enable continuous improvement.</p>

        <div class="callout">
            <strong>Pro Tip:</strong> Start with one area and expand. Trying to transform everything at once often leads to none succeeding.
        </div>
    </div>

    <div class="chapter">
        <h2>Chapter 3: Implementation Roadmap</h2>
        <p>Turning strategy into action requires careful planning. Here's a practical 90-day roadmap:</p>

        <p><strong>Days 1-30:</strong> Assessment and alignment. Understand current state and stakeholder needs.</p>
        <p><strong>Days 31-60:</strong> Pilot and learn. Test approaches with a controlled group.</p>
        <p><strong>Days 61-90:</strong> Scale and optimize. Expand what works, adjust what doesn't.</p>

        <p>Remember, $first_name, the goal isn't perfection—it's progress. Each step forward builds momentum for the next.</p>
    </div>

    <div class="cta-section">
        <h2>Ready to Take the Next Step?</h2>
        <p>$cta</p>
        <a href="#" class="cta-button">Schedule a Conversation</a>
    </div>

    <div class="footer">
        <p>This guide was personalized for $first_name at $company_name</p>
        <p>Generated on $generated_date</p>
    </div>
</body>
</html>
"""

    async def _html_to_pdf(self, html_content: str) -> bytes:
        """
        Convert HTML to PDF.

        Uses weasyprint if available, otherwise returns a placeholder.

        Args:
            html_content: HTML string to convert

        Returns:
            PDF bytes
        """
        try:
            # Try weasyprint first (preferred for production)
            from weasyprint import HTML
            pdf_bytes = HTML(string=html_content).write_pdf()
            return pdf_bytes
        except ImportError:
            logger.warning("weasyprint not available, generating placeholder PDF")

        # Fallback: Generate a simple PDF using reportlab if available
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas

            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=letter)
            c.drawString(100, 750, "Personalized Ebook")
            c.drawString(100, 700, "Full PDF generation requires weasyprint")
            c.save()
            buffer.seek(0)
            return buffer.read()
        except ImportError:
            pass

        # Ultimate fallback: Return a minimal valid PDF
        logger.warning("No PDF library available, returning minimal PDF")
        return self._minimal_pdf()

    def _minimal_pdf(self) -> bytes:
        """Generate a minimal valid PDF file."""
        # Minimal PDF structure
        pdf = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (Personalized Ebook) Tj ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000206 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
300
%%EOF"""
        return pdf

    def _generate_filename(self, email: str, job_id: int) -> str:
        """Generate unique filename for PDF."""
        # Hash email for privacy
        email_hash = hashlib.md5(email.encode()).hexdigest()[:8]
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"ebook_{email_hash}_{job_id}_{timestamp}.pdf"

    async def _store_pdf(
        self,
        pdf_bytes: bytes,
        filename: str
    ) -> tuple[str, str]:
        """
        Store PDF in Supabase Storage.

        Args:
            pdf_bytes: PDF content
            filename: Target filename

        Returns:
            Tuple of (storage_path, signed_url)
        """
        if not self.supabase:
            raise ValueError("Supabase client not configured")

        storage_path = f"{self.storage_bucket}/{filename}"

        # Handle mock mode - return mock URL without actual storage
        if getattr(self.supabase, 'mock_mode', False) or self.supabase.client is None:
            logger.info(f"[MOCK] Would store PDF at {storage_path}")
            mock_url = f"https://mock-storage.example.com/{storage_path}?token=mock-signed-url"
            return storage_path, mock_url

        try:
            # Upload to Supabase Storage
            self.supabase.client.storage.from_(self.storage_bucket).upload(
                filename,
                pdf_bytes,
                {"content-type": "application/pdf"}
            )

            # Generate signed URL
            signed_url = self.supabase.client.storage.from_(
                self.storage_bucket
            ).create_signed_url(
                filename,
                PDF_EXPIRY_HOURS * 3600  # Convert to seconds
            )

            return storage_path, signed_url.get("signedURL", "")

        except Exception as e:
            logger.error(f"Failed to store PDF: {e}")
            raise

    async def get_pdf_url(self, storage_path: str) -> Optional[str]:
        """
        Get signed URL for existing PDF.

        Args:
            storage_path: Storage path of the PDF

        Returns:
            Signed URL or None
        """
        if not self.supabase:
            return None

        # Handle mock mode
        if getattr(self.supabase, 'mock_mode', False) or self.supabase.client is None:
            return f"https://mock-storage.example.com/{storage_path}?token=mock-signed-url"

        try:
            filename = storage_path.split("/")[-1]
            signed_url = self.supabase.client.storage.from_(
                self.storage_bucket
            ).create_signed_url(
                filename,
                PDF_EXPIRY_HOURS * 3600
            )
            return signed_url.get("signedURL")
        except Exception as e:
            logger.error(f"Failed to get PDF URL: {e}")
            return None
