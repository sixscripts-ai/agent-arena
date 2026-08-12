from agent_arena.providers import _apply_host_row


def test_apply_host_row_override():
    base = {
        "id": "host:openai-gpt4o-mini",
        "name": "OpenAI (GPT-4o mini)",
        "base_url": "https://api.openai.com/v1",
        "masked_key": "sk-…",
        "auth_style": "bearer",
        "model_name": "gpt-4o-mini",
        "cred": "openai",
    }
    row = _apply_host_row(base, {"name": "OpenAI mini", "model_name": "gpt-4o"})
    assert row["name"] == "OpenAI mini"
    assert row["model_name"] == "gpt-4o"
    assert row["base_url"] == "https://api.openai.com/v1"
