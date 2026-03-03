"""Tests for log sanitization — strips PII from log messages."""
from app.utils.log_sanitizer import sanitize_log


class TestLogSanitizer:

    def test_strips_email(self):
        msg = "Processing request for john.doe@acme.com"
        result = sanitize_log(msg)
        assert "john.doe@acme.com" not in result
        assert "[EMAIL]" in result

    def test_strips_multiple_emails(self):
        msg = "Sent from admin@test.com to user@corp.org"
        result = sanitize_log(msg)
        assert "admin@test.com" not in result
        assert "user@corp.org" not in result

    def test_preserves_non_pii(self):
        msg = "Enrichment complete: 3 sources, latency 4500ms"
        result = sanitize_log(msg)
        assert result == msg

    def test_strips_name_field_patterns(self):
        msg = "first_name='John', last_name='Smith'"
        result = sanitize_log(msg)
        assert "John" not in result
        assert "Smith" not in result

    def test_strips_name_json_patterns(self):
        msg = '{"first_name": "Jane", "last_name": "Doe", "industry": "tech"}'
        result = sanitize_log(msg)
        assert "Jane" not in result
        assert "Doe" not in result
        assert "tech" in result

    def test_handles_empty_string(self):
        assert sanitize_log("") == ""

    def test_handles_none(self):
        assert sanitize_log(None) == ""
