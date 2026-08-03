import re

REDACT_PATTERNS = [
    r"sk-[A-Za-z0-9_-]{16,}",
    r"wk-[A-Za-z0-9]{20,}",
    r"ws-[A-Za-z0-9]{20,}",
    r"standard_[A-Za-z0-9]{60,}",
]

ARTIFACT_MAX_BYTES = 100_000


def redact(text: str) -> str:
    for pattern in REDACT_PATTERNS:
        text = re.sub(pattern, "[REDACTED]", text)
    return text


def sanitize_artifact(text: str, max_bytes: int = ARTIFACT_MAX_BYTES) -> str:
    redacted = redact(text)
    return redacted.encode("utf-8", errors="ignore")[:max_bytes].decode("utf-8", errors="ignore")
