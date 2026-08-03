import httpx
from appwrite.exception import AppwriteException
from appwrite.query import Query
from fastapi import APIRouter, Depends, HTTPException

from . import crypto, db
from .auth import get_current_user
from .config import settings
from .schemas import ProviderCreate, ProviderHealth, ProviderOut

router = APIRouter(prefix="/providers", tags=["providers"])

HOST_FREE_ID = "host:openrouter-free"
HOST_FREE = {
    "id": HOST_FREE_ID,
    "name": "OpenRouter Free (Nemotron)",
    "base_url": "https://openrouter.ai/api/v1",
    "masked_key": "sk-or-...free",
    "auth_style": "bearer",
    "model_name": "nvidia/nemotron-3-ultra-550b-a55b:free",
}


def _fernet_key() -> bytes:
    key = settings()["FERNET_KEY"]
    if not key:
        raise HTTPException(status_code=500, detail="Server encryption key not configured")
    return key.encode()


def _find_existing(databases, database_id, user_id, name):
    res = databases.list_documents(
        database_id, "providers",
        queries=[Query.equal("user_id", user_id), Query.equal("name", name), Query.limit(1)],
    )
    docs = res.documents
    return docs[0] if docs else None


@router.post("", response_model=ProviderOut)
def create_provider(body: ProviderCreate, user_id: str = Depends(get_current_user)):
    encrypted = crypto.encrypt_key(body.api_key, _fernet_key())
    masked = crypto.mask_key(body.api_key)
    databases = db.get_databases()
    database_id = db.get_database_id()
    payload = {
        "user_id": user_id,
        "name": body.name,
        "base_url": body.base_url,
        "encrypted_key": encrypted,
        "masked_key": masked,
        "auth_style": body.auth_style,
        "model_name": body.model_name,
    }
    try:
        existing = _find_existing(databases, database_id, user_id, body.name)
        if existing:
            doc = databases.update_document(database_id, "providers", existing.id, payload)
        else:
            doc = databases.create_document(database_id, "providers", "unique()", payload)
    except AppwriteException as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ProviderOut(id=doc.id, name=body.name, base_url=body.base_url,
                        masked_key=masked, auth_style=body.auth_style, model_name=body.model_name)


@router.get("")
def list_providers(user_id: str = Depends(get_current_user)):
    databases = db.get_databases()
    res = databases.list_documents(
        db.get_database_id(), "providers",
        queries=[Query.equal("user_id", user_id), Query.limit(100)],
    )
    items = [
        ProviderOut(id=d.id, name=d.data["name"], base_url=d.data["base_url"],
                    masked_key=d.data["masked_key"], auth_style=d.data["auth_style"],
                    model_name=d.data.get("model_name", "")).model_dump()
        for d in res.documents
    ]
    items.insert(0, dict(HOST_FREE))
    return items


def get_model_call_spec(model_id: str, user_id: str) -> tuple[str, str, str, str]:
    """Return (base_url, auth_style, api_key, model_name) for a battle model_id."""
    if model_id == HOST_FREE_ID:
        key = settings().get("HOST_OPENROUTER_KEY") or ""
        if not key:
            raise HTTPException(status_code=500, detail="HOST_OPENROUTER_KEY not configured")
        return (
            HOST_FREE["base_url"],
            HOST_FREE["auth_style"],
            key,
            HOST_FREE["model_name"],
        )
    databases = db.get_databases()
    database_id = db.get_database_id()
    try:
        doc = databases.get_document(database_id, "providers", model_id)
    except AppwriteException as exc:
        raise HTTPException(status_code=404, detail="Unknown model_id") from exc
    if doc.data.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not your provider")
    api_key = crypto.decrypt_key(doc.data["encrypted_key"], _fernet_key())
    return (
        doc.data["base_url"],
        doc.data["auth_style"],
        api_key,
        doc.data.get("model_name") or "",
    )


@router.post("/health")
def provider_health(body: ProviderHealth, _user_id: str = Depends(get_current_user)):
    headers = {}
    if body.auth_style == "modal_proxy":
        parts = [p.strip() for p in body.api_key.split(":")]
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="modal_proxy key must be 'wk-...:ws-...'")
        headers = {"Modal-Key": parts[0], "Modal-Secret": parts[1]}
    else:
        headers["Authorization"] = f"Bearer {body.api_key}"
    url = body.base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": body.model or "moonshotai/Kimi-K3",
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 5,
    }
    try:
        resp = httpx.post(url, headers=headers, json=payload, timeout=30)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Request failed: {exc}") from exc
    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Provider returned {resp.status_code}: {resp.text[:200]}")
    return {"ok": True, "status_code": resp.status_code}
