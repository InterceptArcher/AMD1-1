"""
Compare enrichment output between main (old) and beta (new) backends.
Uses /rad/executive-review which returns full enrichment data.
Usage: python3 scripts/compare_enrichment.py email@company.com
"""

import sys
import json
import httpx
import asyncio
from datetime import datetime

MAIN_URL = "https://amd1-1-backend.onrender.com"
BETA_URL = "https://amd1-1-backend-beta.onrender.com"

TIMEOUT = 120.0  # Render cold starts can be slow


async def fetch(base_url: str, email: str, label: str) -> dict:
    """Hit /rad/executive-review and return the full JSON response."""
    print(f"[{label}] Enriching {email}...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{base_url}/rad/executive-review",
            json={"email": email, "force_refresh": True},
        )
        if resp.status_code != 200:
            print(f"[{label}] ERROR {resp.status_code}: {resp.text[:300]}")
            return {}
        data = resp.json()
        print(f"[{label}] OK — company={data.get('company_name')}")
        return data


def compare(main: dict, beta: dict):
    """Print a structured comparison of key enrichment differences."""
    print("\n" + "=" * 70)
    print("ENRICHMENT COMPARISON: MAIN vs BETA")
    print("=" * 70)

    def row(label, m_val, b_val):
        changed = " <<<" if str(m_val) != str(b_val) else ""
        m_str = str(m_val)[:40] if m_val else "(none)"
        b_str = str(b_val)[:40] if b_val else "(none)"
        print(f"  {label:<22} {m_str:<42} {b_str:<42}{changed}")

    m_enrich = main.get("enrichment", {})
    b_enrich = beta.get("enrichment", {})
    m_inputs = main.get("inputs", {})
    b_inputs = beta.get("inputs", {})
    m_inferred = main.get("inferred_context", {})
    b_inferred = beta.get("inferred_context", {})

    # --- Company & Identity ---
    print(f"\n{'--- COMPANY & IDENTITY ---':^100}")
    print(f"  {'Field':<22} {'MAIN':<42} {'BETA':<42}")
    print(f"  {'-'*22} {'-'*42} {'-'*42}")
    row("Company Name", main.get("company_name"), beta.get("company_name"))
    row("Industry (input)", m_inputs.get("industry"), b_inputs.get("industry"))
    row("Industry (raw)", m_enrich.get("industry"), b_enrich.get("industry"))
    row("Title", m_enrich.get("title"), b_enrich.get("title"))
    row("Employee Count", m_enrich.get("employee_count"), b_enrich.get("employee_count"))
    row("Founded Year", m_enrich.get("founded_year"), b_enrich.get("founded_year"))
    row("Quality Score", m_enrich.get("data_quality_score"), b_enrich.get("data_quality_score"))

    # --- Context Inference ---
    print(f"\n{'--- CONTEXT INFERENCE ---':^100}")
    print(f"  {'Field':<22} {'MAIN':<42} {'BETA':<42}")
    print(f"  {'-'*22} {'-'*42} {'-'*42}")
    row("Segment", m_inputs.get("segment"), b_inputs.get("segment"))
    row("Persona", m_inputs.get("persona"), b_inputs.get("persona"))
    row("Stage", m_inputs.get("stage"), b_inputs.get("stage"))
    row("Priority", m_inputs.get("priority"), b_inputs.get("priority"))
    row("Challenge", m_inputs.get("challenge"), b_inputs.get("challenge"))
    row("IT Environment", m_inferred.get("it_environment"), b_inferred.get("it_environment"))
    row("Urgency", m_inferred.get("urgency_level"), b_inferred.get("urgency_level"))
    row("Confidence", m_inferred.get("confidence_score"), b_inferred.get("confidence_score"))

    # --- News (biggest expected diff) ---
    m_themes = m_enrich.get("news_themes", [])
    b_themes = b_enrich.get("news_themes", [])
    m_news = m_enrich.get("recent_news", []) or []
    b_news = b_enrich.get("recent_news", []) or []
    diff_marker = " <<<" if m_themes != b_themes else ""

    print(f"\n{'--- NEWS (biggest diff expected) ---':^100}")
    print(f"  MAIN themes: {m_themes}")
    print(f"  BETA themes: {b_themes}{diff_marker}")
    print(f"\n  MAIN headlines ({len(m_news)}):")
    for a in m_news[:3]:
        title = a.get("title", "") if isinstance(a, dict) else str(a)
        print(f"    - {title[:90]}")
    print(f"  BETA headlines ({len(b_news)}):")
    for a in b_news[:3]:
        title = a.get("title", "") if isinstance(a, dict) else str(a)
        print(f"    - {title[:90]}")

    # --- NEW: News Analysis (beta only) ---
    b_na = beta.get("news_analysis", {})
    print(f"\n{'--- NEWS ANALYSIS (beta only) ---':^100}")
    if b_na:
        print(f"  Sentiment:    {b_na.get('sentiment', '?')}")
        print(f"  AI Readiness: {b_na.get('ai_readiness', '?')}")
        print(f"  Crisis:       {b_na.get('crisis', '?')}")
    else:
        print("  (not present — old code path)")

    # --- NEW: Tech Signals (beta only) ---
    b_tech = b_inferred.get("tech_signals")
    print(f"\n{'--- TECH SIGNALS (beta only) ---':^100}")
    if b_tech:
        print(f"  Maturity:     {b_tech.get('maturity')}")
        for cat in ["cloud", "ai_ml", "data", "security", "traditional"]:
            vals = b_tech.get(cat, [])
            if vals:
                print(f"  {cat:<14} {vals}")
    else:
        print("  (not present — no company tags or old code)")

    # --- Executive Review Content ---
    m_review = main.get("executive_review", {})
    b_review = beta.get("executive_review", {})

    print(f"\n{'--- EXECUTIVE REVIEW ---':^100}")
    m_advs = m_review.get("advantages", [])
    b_advs = b_review.get("advantages", [])
    print(f"  Advantages (MAIN): {len(m_advs)} items")
    for a in m_advs[:2]:
        print(f"    [{a.get('headline', '')}] {a.get('description', '')[:80]}")
    print(f"  Advantages (BETA): {len(b_advs)} items")
    for a in b_advs[:2]:
        print(f"    [{a.get('headline', '')}] {a.get('description', '')[:80]}")

    print("\n" + "=" * 70)


async def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/compare_enrichment.py email@company.com")
        print("\nExamples:")
        print("  python3 scripts/compare_enrichment.py user@jpmorgan.com")
        print("  python3 scripts/compare_enrichment.py user@salesforce.com")
        print("  python3 scripts/compare_enrichment.py user@ge.com")
        sys.exit(1)

    email = sys.argv[1]
    print(f"Comparing enrichment for: {email}")
    print(f"  MAIN: {MAIN_URL}")
    print(f"  BETA: {BETA_URL}")

    main_data, beta_data = await asyncio.gather(
        fetch(MAIN_URL, email, "MAIN"),
        fetch(BETA_URL, email, "BETA"),
    )

    if main_data and beta_data:
        compare(main_data, beta_data)

    # Save full JSON for deeper inspection
    slug = email.split("@")[0].replace(".", "_")
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    for label, data in [("main", main_data), ("beta", beta_data)]:
        path = f"/tmp/enrich_{label}_{slug}_{ts}.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"\n  {label.upper()} JSON: {path}")

    print(f"\n  Diff: diff /tmp/enrich_main_{slug}_{ts}.json /tmp/enrich_beta_{slug}_{ts}.json")


if __name__ == "__main__":
    asyncio.run(main())
