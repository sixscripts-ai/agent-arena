import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_REPO_ROOT / ".env")

_REQUIRED = [
    "APPWRITE_ENDPOINT",
    "APPWRITE_PROJECT_ID",
    "APPWRITE_API_KEY",
    "APPWRITE_DATABASE_ID",
]


@lru_cache
def settings() -> dict:
    missing = [k for k in _REQUIRED if not os.environ.get(k)]
    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")
    return {
        "APPWRITE_ENDPOINT": os.environ["APPWRITE_ENDPOINT"],
        "APPWRITE_PROJECT_ID": os.environ["APPWRITE_PROJECT_ID"],
        "APPWRITE_API_KEY": os.environ["APPWRITE_API_KEY"],
        "APPWRITE_DATABASE_ID": os.environ["APPWRITE_DATABASE_ID"],
        "FERNET_KEY": os.environ.get("FERNET_KEY", ""),
        "HOST_OPENROUTER_KEY": os.environ.get("HOST_OPENROUTER_KEY", ""),
        "INTERNAL_API_KEY": os.environ.get("INTERNAL_API_KEY", ""),
        "JUDGE_MODAL_KEY": os.environ.get("JUDGE_MODAL_KEY", ""),
        "JUDGE_MODAL_SECRET": os.environ.get("JUDGE_MODAL_SECRET", ""),
    }
