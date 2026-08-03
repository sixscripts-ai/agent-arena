from appwrite.services.account import Account
from fastapi import Header, HTTPException

from .db import get_client


def get_current_user(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        client = get_client()
        client.set_jwt(token)
        account = Account(client).get()
        return account["$id"] if isinstance(account, dict) else account.id
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired session") from exc

