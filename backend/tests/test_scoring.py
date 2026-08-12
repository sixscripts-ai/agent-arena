"""Unit tests for scoring helpers (no Appwrite required)."""

from agent_arena.scoring import parse_scores_payload


def test_parse_scores_payload_json_string():
    raw = '{"scores": {"host:a": 48.0, "host:b": 8}, "judge_model": "kimi"}'
    assert parse_scores_payload(raw) == {"host:a": 48.0, "host:b": 8.0}


def test_parse_scores_payload_dict():
    assert parse_scores_payload({"scores": {"m1": 10}}) == {"m1": 10.0}


def test_parse_scores_payload_invalid():
    assert parse_scores_payload(None) is None
    assert parse_scores_payload("") is None
    assert parse_scores_payload("not-json") is None
    assert parse_scores_payload({"scores": {}}) is None
    assert parse_scores_payload({"nope": 1}) is None


def test_apply_battle_status_transitions():
    from agent_arena.internal_router import _apply_battle_status

    class Doc:
        def __init__(self, status):
            self.data = {"status": status, "$id": "b1"}

    updates: list[dict] = []

    class DB:
        def update_document(self, database_id, collection, doc_id, data):
            updates.append(data)

    db = DB()
    assert _apply_battle_status(db, "db", "b1", Doc("queued"), "running") == "running"
    assert updates[-1] == {"status": "running"}
    assert _apply_battle_status(db, "db", "b1", Doc("running"), "completed") == "completed"
    assert (
        _apply_battle_status(db, "db", "b1", Doc("completed"), "failed") is None
    ), "must not regress completed→failed"
    assert _apply_battle_status(db, "db", "b1", Doc("completed"), "completed") == "completed"
