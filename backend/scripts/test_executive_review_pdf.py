#!/usr/bin/env python3
"""
Test script for Executive Review JSON PDF generation and extraction.

This script demonstrates:
1. Generating JSON-structured executive review content
2. Creating a PDF with embedded JSON metadata
3. Extracting the JSON from the PDF

Usage:
    python backend/scripts/test_executive_review_pdf.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.executive_review_service import ExecutiveReviewService
from app.services.pdf_service import PDFService


async def test_executive_review_pdf():
    """Test the full executive review PDF workflow."""

    print("=" * 60)
    print("AMD Executive Review PDF Test")
    print("=" * 60)
    print()

    # Step 1: Generate executive review JSON
    print("Step 1: Generating executive review JSON...")
    print("-" * 60)

    service = ExecutiveReviewService()
    executive_review = await service.generate_executive_review(
        company_name="Acme Corporation",
        industry="Technology",
        segment="Enterprise",
        persona="ITDM",
        stage="Challenger",
        priority="Improving workload performance",
        challenge="Integration friction"
    )

    print(f"✓ Company: {executive_review['company_name']}")
    print(f"✓ Stage: {executive_review['stage']}")
    print(f"✓ Advantages: {len(executive_review['advantages'])} items")
    print(f"✓ Risks: {len(executive_review['risks'])} items")
    print(f"✓ Recommendations: {len(executive_review['recommendations'])} items")
    print(f"✓ Case Study: {executive_review['case_study']}")
    print()

    print("JSON Structure:")
    print("-" * 60)
    print(json.dumps(executive_review, indent=2))
    print()

    # Step 2: Generate PDF with embedded JSON
    print("Step 2: Generating PDF with embedded JSON metadata...")
    print("-" * 60)

    pdf_service = PDFService()
    pdf_bytes = await pdf_service.generate_executive_review_pdf(
        executive_review=executive_review,
        embed_json=True
    )

    print(f"✓ PDF generated: {len(pdf_bytes)} bytes")

    # Save to file
    output_file = Path("test_executive_review.pdf")
    output_file.write_bytes(pdf_bytes)
    print(f"✓ PDF saved to: {output_file.absolute()}")
    print()

    # Step 3: Extract JSON from PDF
    print("Step 3: Extracting JSON from PDF...")
    print("-" * 60)

    extracted_data = PDFService.extract_json_from_pdf(pdf_bytes)

    if extracted_data:
        print("✓ JSON successfully extracted from PDF")
        print()
        print("Extracted Data:")
        print("-" * 60)
        print(json.dumps(extracted_data, indent=2))
        print()

        # Verify data integrity
        print("Data Integrity Check:")
        print("-" * 60)
        if extracted_data.get("company_name") == executive_review.get("company_name"):
            print("✓ Company name matches")
        else:
            print("✗ Company name mismatch")

        if extracted_data.get("stage") == executive_review.get("stage"):
            print("✓ Stage matches")
        else:
            print("✗ Stage mismatch")

        if len(extracted_data.get("advantages", [])) == len(executive_review.get("advantages", [])):
            print("✓ Advantages count matches")
        else:
            print("✗ Advantages count mismatch")

        print()
        print("=" * 60)
        print("✓ Test completed successfully!")
        print("=" * 60)
    else:
        print("✗ Failed to extract JSON from PDF")
        print()
        print("=" * 60)
        print("✗ Test failed")
        print("=" * 60)
        return False

    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_executive_review_pdf())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
