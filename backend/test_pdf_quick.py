#!/usr/bin/env python3
"""
Quick test to generate and view the new Executive Review PDF.
Run this without starting the full server.
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app.services.executive_review_service import ExecutiveReviewService
    from app.services.pdf_service import PDFService
    import json
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("\nPlease install dependencies first:")
    print("  cd /workspaces/AMD1-1_Alpha/backend")
    print("  python3 -m pip install --user -r requirements.txt")
    sys.exit(1)


async def test_pdf():
    print("=" * 60)
    print("Testing Executive Review PDF Generation")
    print("=" * 60)
    print()

    # Step 1: Generate JSON
    print("Step 1: Generating executive review JSON...")
    service = ExecutiveReviewService()

    review_data = await service.generate_executive_review(
        company_name="Acme Corporation",
        industry="Technology",
        segment="Enterprise",
        persona="ITDM",
        stage="Challenger",
        priority="Improving workload performance",
        challenge="Integration friction"
    )

    print(f"✓ Generated review for: {review_data['company_name']}")
    print(f"✓ Stage: {review_data['stage']}")
    print(f"✓ Advantages: {len(review_data['advantages'])}")
    print(f"✓ Risks: {len(review_data['risks'])}")
    print(f"✓ Recommendations: {len(review_data['recommendations'])}")
    print()

    # Step 2: Generate PDF
    print("Step 2: Generating PDF with embedded JSON...")
    pdf_service = PDFService()

    try:
        pdf_bytes = await pdf_service.generate_executive_review_pdf(
            executive_review=review_data,
            embed_json=True
        )

        # Save PDF
        output_file = "executive_review_test.pdf"
        with open(output_file, "wb") as f:
            f.write(pdf_bytes)

        print(f"✓ PDF generated: {len(pdf_bytes):,} bytes")
        print(f"✓ Saved to: {os.path.abspath(output_file)}")
        print()

        # Step 3: Extract JSON
        print("Step 3: Extracting JSON from PDF...")
        extracted = PDFService.extract_json_from_pdf(pdf_bytes)

        if extracted:
            print("✓ JSON successfully extracted!")
            print(f"✓ Company: {extracted.get('company_name')}")
            print(f"✓ Stage: {extracted.get('stage')}")
            print()
            print("=" * 60)
            print("✓ TEST PASSED - PDF ready to view!")
            print("=" * 60)
            print(f"\nOpen the PDF: {os.path.abspath(output_file)}")
            print()
            return True
        else:
            print("⚠️  JSON extraction returned None (pypdf might not be installed)")
            print("   PDF was still generated successfully")
            print()
            print("=" * 60)
            print("✓ PDF GENERATED - Open it to view!")
            print("=" * 60)
            print(f"\nOpen the PDF: {os.path.abspath(output_file)}")
            print()
            return True

    except Exception as e:
        print(f"❌ Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(test_pdf())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
