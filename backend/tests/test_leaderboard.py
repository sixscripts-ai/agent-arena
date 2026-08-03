from agent_arena import db
from agent_arena import leaderboard
from agent_arena.elo import INITIAL_RATING
from tests.conftest import make_user_id, requires_appwrite


@requires_appwrite
def test_apply_result_updates_elo():
    databases = db.get_databases()
    database_id = db.get_database_id()
    fmt = f"fmt-{make_user_id()[:16]}"
    a, b = f"model-a-{make_user_id()[:10]}", f"model-b-{make_user_id()[:10]}"
    leaderboard.apply_result(databases, database_id, fmt, [a, b], {a: 80.0, b: 20.0})

    rankings = leaderboard.get_rankings(databases, database_id, fmt)
    ra = next(r for r in rankings if r["model_id"] == a)
    rb = next(r for r in rankings if r["model_id"] == b)
    assert ra["elo"] > INITIAL_RATING
    assert rb["elo"] < INITIAL_RATING
    assert ra["games_played"] == 1
    assert ra["rank"] < rb["rank"]

    # second application is idempotent in structure (updates, not duplicates)
    leaderboard.apply_result(databases, database_id, fmt, [a, b], {a: 20.0, b: 80.0})
    rankings = leaderboard.get_rankings(databases, database_id, fmt)
    ra2 = next(r for r in rankings if r["model_id"] == a)
    assert ra2["games_played"] == 2


@requires_appwrite
def test_overall_scope_tracks_separately():
    databases = db.get_databases()
    database_id = db.get_database_id()
    a, b = f"model-x-{make_user_id()[:10]}", f"model-y-{make_user_id()[:10]}"
    leaderboard.apply_result(databases, database_id, "overall", [a, b], {a: 90.0, b: 10.0})
    rankings = leaderboard.get_rankings(databases, database_id, "overall")
    assert any(r["model_id"] == a for r in rankings)
