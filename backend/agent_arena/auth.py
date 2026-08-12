from appwrite.client import Client
from appwrite.services.account import Account
from fastapi import Depends, Header, HTTPException

from .config import settings


def get_current_user(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        # JWT auth must not share a client that has the server API key set —
        # Appwrite prefers the key and Account.get() then fails as a guest.
        s = settings()
        client = (
            Client()
            .set_endpoint(s["APPWRITE_ENDPOINT"])
            .set_project(s["APPWRITE_PROJECT_ID"])
            .set_jwt(token)
        )
        account = Account(client).get()
        return account["$id"] if isinstance(account, dict) else account.id
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired session") from exc


def admin_user_ids() -> set[str]:
    raw = settings().get("ARENA_ADMIN_USER_IDS") or ""
    return {part.strip() for part in raw.split(",") if part.strip()}


def is_admin_user(user_id: str) -> bool:
    return user_id in admin_user_ids()


def require_admin(user_id: str = Depends(get_current_user)) -> str:
    if not is_admin_user(user_id):
        raise HTTPException(status_code=403, detail="Admin only")
    return user_id
