"""
Nightly compliance check: verify no PII write paths exist in production code.
This test is run by the Archer security agent.
"""
import os
import re
import pytest

# Production source directories
BACKEND_SRC = os.path.join(os.path.dirname(__file__), "..", "app")

# PII write functions that should NOT appear in production code
PII_WRITE_PATTERNS = [
    r"\.store_raw_data\(",
    r"\.upsert_finalize_data\(",
    r"\.write_finalize_data\(",
    r"\.create_staging_record\(",
    r"\.update_staging_record\(",
    r"\.create_personalization_job\(",
    r"\.store_personalization_output\(",
    r"\.create_pdf_delivery\(",
    r"\.update_pdf_delivery\(",
]

# Files to scan (exclude tests, migrations, and the client definition itself)
EXCLUDE_PATTERNS = ["test_", "conftest", "migration", "__pycache__"]


def _get_source_files():
    """Get all .py files in backend/app/."""
    files = []
    for root, dirs, filenames in os.walk(BACKEND_SRC):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in filenames:
            if f.endswith(".py") and not any(ex in f for ex in EXCLUDE_PATTERNS):
                files.append(os.path.join(root, f))
    return files


class TestPiiCompliance:
    """Verify no PII write calls exist in production code."""

    @pytest.mark.parametrize("pattern", PII_WRITE_PATTERNS)
    def test_no_pii_write_calls_in_routes(self, pattern):
        """Scan route handlers for PII write calls."""
        routes_dir = os.path.join(BACKEND_SRC, "routes")
        violations = []
        for filepath in _get_source_files():
            if not filepath.startswith(routes_dir):
                continue
            with open(filepath, "r") as f:
                for i, line in enumerate(f, 1):
                    if re.search(pattern, line) and not line.strip().startswith("#"):
                        violations.append(f"{filepath}:{i}: {line.strip()}")
        assert violations == [], f"PII write call found: {pattern}\n" + "\n".join(violations)

    @pytest.mark.parametrize("pattern", PII_WRITE_PATTERNS)
    def test_no_pii_write_calls_in_services(self, pattern):
        """Scan services for PII write calls (excluding supabase_client.py definitions)."""
        services_dir = os.path.join(BACKEND_SRC, "services")
        violations = []
        for filepath in _get_source_files():
            if not filepath.startswith(services_dir):
                continue
            if "supabase_client" in filepath:
                continue
            with open(filepath, "r") as f:
                for i, line in enumerate(f, 1):
                    if re.search(pattern, line) and not line.strip().startswith("#"):
                        violations.append(f"{filepath}:{i}: {line.strip()}")
        assert violations == [], f"PII write call found: {pattern}\n" + "\n".join(violations)

    def test_no_email_in_log_statements(self):
        """Verify log statements don't interpolate email directly."""
        violations = []
        email_log_re = re.compile(r'logger\.\w+\(.*\{email\}')
        for filepath in _get_source_files():
            if "supabase_client" in filepath:
                continue
            with open(filepath, "r") as f:
                for i, line in enumerate(f, 1):
                    if email_log_re.search(line) and "sanitize_log" not in line:
                        violations.append(f"{filepath}:{i}: {line.strip()}")
        assert violations == [], "Unsanitized email in log:\n" + "\n".join(violations)
