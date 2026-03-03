"""Strip PII from log messages before output."""
import re


# Email pattern
_EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

# Name field patterns: first_name='...', "last_name": "..."
_NAME_FIELD_RE = re.compile(
    r"""['"]?(?:first_name|last_name|firstName|lastName)['"]?"""
    r"""(?:\s*[=:]\s*['"]?)([^'",}\s]+)""",
    re.IGNORECASE
)


def sanitize_log(msg) -> str:
    """Remove PII (emails, name values) from a log message."""
    if not msg:
        return ""

    msg = str(msg)
    result = _EMAIL_RE.sub("[EMAIL]", msg)
    result = _NAME_FIELD_RE.sub(
        lambda m: m.group(0).replace(m.group(1), "[REDACTED]"),
        result,
    )
    return result
