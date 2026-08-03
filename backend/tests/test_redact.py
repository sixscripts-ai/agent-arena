from agent_arena.redact import REDACT_PATTERNS, sanitize_artifact


def test_four_spec_patterns_present():
    assert len(REDACT_PATTERNS) == 4
    assert "sk-[A-Za-z0-9_-]{16,}" in REDACT_PATTERNS
    assert "wk-[A-Za-z0-9]{20,}" in REDACT_PATTERNS
    assert "ws-[A-Za-z0-9]{20,}" in REDACT_PATTERNS
    assert "standard_[A-Za-z0-9]{60,}" in REDACT_PATTERNS


def test_redacts_all_pattern_kinds():
    text = (
        "key=sk-abcdefghijklmnopqrstuvwxyz "
        "id=wk-abcdefghijklmnopqrstuvwxyz "
        "sec=ws-abcdefghijklmnopqrstuvwxyz "
        "appwrite=standard_" + "A" * 60
    )
    out = sanitize_artifact(text)
    assert "[REDACTED]" in out
    assert "sk-abcdefghijklmnopqrstuvwxyz" not in out
    assert "wk-abcdefghijklmnopqrstuvwxyz" not in out
    assert "ws-abcdefghijklmnopqrstuvwxyz" not in out
    assert "standard_" + "A" * 60 not in out


def test_does_not_mangle_short_secretlike_text():
    text = "api sk-abc short"
    assert sanitize_artifact(text) == "api sk-abc short"


def test_truncates_oversized_artifact():
    text = "x" * 200_000
    out = sanitize_artifact(text)
    assert len(out.encode()) <= 100_000


def test_truncates_multibyte_without_crashing():
    text = "\u4e2d" * 200_000
    out = sanitize_artifact(text)
    assert len(out.encode()) <= 100_000


def test_redacts_secret_straddling_truncation_boundary():
    padding = "x" * (100_000 - 10)
    text = padding + "sk-abcdefghijklmnopqrstuvwxyz"
    out = sanitize_artifact(text)
    assert len(out.encode()) <= 100_000
    # Redaction happens BEFORE truncation, so the secret is fully replaced and no
    # partial "sk-..." prefix can leak past the byte cap (regression for a real
    # leak where truncate-then-redact left "sk-abcdefg" visible).
    assert "sk-abcdefghijklmnopqrstuvwxyz" not in out
    assert "sk-" not in out
