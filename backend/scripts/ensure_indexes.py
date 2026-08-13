"""Ensure Appwrite indexes exist for Agent Arena collections."""
import time
from agent_arena import db

# Define indexes needed: collection -> list of (key, type, attributes)
INDEXES = {
    "battles": [
        ("user_id_idx", "key", ["user_id"]),
        ("status_idx", "key", ["status"]),
        ("saved_idx", "key", ["saved"]),
        ("format_id_idx", "key", ["format_id"]),
        ("user_status_idx", "key", ["user_id", "status"]),
        ("user_saved_idx", "key", ["user_id", "saved"]),
    ],
    "providers": [
        ("user_id_idx", "key", ["user_id"]),
        ("user_name_idx", "key", ["user_id", "name"]),
    ],
    "rounds": [
        ("battle_id_idx", "key", ["battle_id"]),
    ],
    "scores": [
        ("battle_id_idx", "key", ["battle_id"]),
        ("battle_model_idx", "key", ["battle_id", "model_id"]),
    ],
    "battle_events": [
        ("battle_id_idx", "key", ["battle_id"]),
        ("battle_created_idx", "key", ["battle_id", "created_at"]),
    ],
    "leaderboard": [
        ("format_id_idx", "key", ["format_id"]),
        ("model_id_idx", "key", ["model_id"]),
    ],
    "formats": [
        ("name_idx", "key", ["name"]),
    ],
}

def ensure():
    databases = db.get_databases()
    db_id = db.get_database_id()
    for coll, idxs in INDEXES.items():
        existing = set()
        try:
            res = databases.list_indexes(db_id, coll)
            existing = {i.key for i in res.indexes}
        except Exception as e:
            print(f"{coll}: list failed {e}")
            continue
        for key, typ, attrs in idxs:
            if key in existing:
                continue
            try:
                print(f"Creating {coll}.{key} on {attrs}...")
                databases.create_index(db_id, coll, key, typ, attrs)
                # Appwrite creates indexes async, wait a bit
                time.sleep(1)
            except Exception as e:
                # may already exist or attribute not available yet
                print(f"  failed {coll}.{key}: {e}")

if __name__ == "__main__":
    ensure()
    print("done")
