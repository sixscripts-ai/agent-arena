import httpx
from appwrite.exception import AppwriteException
from appwrite.query import Query
from fastapi import APIRouter, Depends, HTTPException

from . import crypto, db
from .auth import get_current_user, is_admin_user, require_admin
from .config import settings
from .schema import ensure_schema
from .schemas import HostCatalogPatch, ProviderCreate, ProviderHealth, ProviderOut

router = APIRouter(prefix="/providers", tags=["providers"])

DEFAULT_MODAL_KIMI_BASE = "https://inference.us-west.modal.direct/v1"
MANUS_BASE = "https://api.manus.ai"
HOST_DEFAULT_ID = "host:manus-1.6-lite"


def _modal_kimi_base() -> str:
    return (settings().get("JUDGE_MODAL_BASE") or DEFAULT_MODAL_KIMI_BASE).rstrip("/")


def _modal_kimi_model() -> str:
    return (
        settings().get("JUDGE_MODAL_MODEL")
        or "sixscripts--ep-kimi-k3-server.us-west.modal.direct"
    )


# Multi-backend host catalog. Each entry declares how to resolve credentials.
# Public list only includes entries whose credentials are present.
HOST_PROVIDERS: list[dict] = [
    {
        "id": "host:modal-kimi",
        "name": "Modal (Kimi-K3)",
        "base_url": DEFAULT_MODAL_KIMI_BASE,
        "masked_key": "modal-key…",
        "auth_style": "modal_proxy",
        "model_name": "sixscripts--ep-kimi-k3-server.us-west.modal.direct",
        "cred": "modal_judge",
    },
    {
        "id": "host:manus-1.6",
        "name": "Manus 1.6",
        "base_url": MANUS_BASE,
        "masked_key": "manus-…",
        "auth_style": "manus",
        "model_name": "manus-1.6",
        "cred": "manus",
    },
    {
        "id": HOST_DEFAULT_ID,
        "name": "Manus 1.6 Lite",
        "base_url": MANUS_BASE,
        "masked_key": "manus-…",
        "auth_style": "manus",
        "model_name": "manus-1.6-lite",
        "cred": "manus",
    },
    {
        "id": "host:manus-1.6-max",
        "name": "Manus 1.6 Max",
        "base_url": MANUS_BASE,
        "masked_key": "manus-…",
        "auth_style": "manus",
        "model_name": "manus-1.6-max",
        "cred": "manus",
    },
    {
        "id": "host:merge-gateway",
        "name": "Merge Gateway",
        "base_url": "https://api-gateway.merge.dev/v1/openai",
        "masked_key": "mg__…",
        "auth_style": "bearer",
        "model_name": "openai/gpt-4o-mini",
        "cred": "merge",
    },
    {
        "id": "host:tokenrouter",
        "name": "TokenRouter",
        "base_url": "https://api.tokenrouter.com/v1",
        "masked_key": "sk-…",
        "auth_style": "bearer",
        "model_name": "moonshotai/kimi-k3-free",
        "cred": "tokenrouter",
    },
    {
        "id": "host:xai-grok",
        "name": "xAI (Grok)",
        "base_url": "https://api.x.ai/v1",
        "masked_key": "xai-…",
        "auth_style": "bearer",
        "model_name": "grok-4-1-fast-non-reasoning",
        "cred": "xai",
    },
    {
        "id": "host:openai-gpt4o-mini",
        "name": "OpenAI (GPT-4o mini)",
        "base_url": "https://api.openai.com/v1",
        "masked_key": "sk-…",
        "auth_style": "bearer",
        "model_name": "gpt-4o-mini",
        "cred": "openai",
    },
]

HOST_FREE = next(p for p in HOST_PROVIDERS if p["id"] == HOST_DEFAULT_ID)
HOST_BY_ID = {p["id"]: p for p in HOST_PROVIDERS}
_PUBLIC_KEYS = ("id", "name", "base_url", "masked_key", "auth_style", "model_name")


def is_host_model(model_id: str) -> bool:
    return model_id in HOST_BY_ID


def _cred_material(cred: str) -> str | None:
    """Return api_key material for a host cred type, or None if unavailable."""
    s = settings()
    if cred == "manus":
        return s.get("HOST_MANUS_KEY") or None
    if cred == "modal_judge":
        proxy = s.get("JUDGE_MODAL_PROXY_TOKEN") or ""
        if proxy and (("." in proxy and "wk-" in proxy) or ":" in proxy):
            return proxy
        key = s.get("JUDGE_MODAL_KEY") or ""
        secret = s.get("JUDGE_MODAL_SECRET") or ""
        if key and secret:
            return f"{key}:{secret}"
        return None
    if cred == "merge":
        return s.get("HOST_MERGE_KEY") or None
    if cred == "tokenrouter":
        return s.get("HOST_TOKENROUTER_KEY") or None
    if cred == "xai":
        return s.get("HOST_XAI_KEY") or None
    if cred == "openai":
        return s.get("HOST_OPENAI_KEY") or None
    return None


def _host_configured(p: dict) -> bool:
    return bool(_cred_material(p.get("cred", "")))


def _load_host_overrides() -> dict[str, dict]:
    """Map host_id -> override fields from Appwrite host_catalog (best-effort)."""
    try:
        databases = db.get_databases()
        database_id = db.get_database_id()
        res = databases.list_documents(
            database_id, "host_catalog", queries=[Query.limit(100)]
        )
    except Exception:
        return {}
    out: dict[str, dict] = {}
    for doc in res.documents:
        data = doc.data if hasattr(doc, "data") else {}
        out[doc.id] = {
            "name": data.get("name"),
            "base_url": data.get("base_url"),
            "model_name": data.get("model_name"),
            "enabled": data.get("enabled"),
        }
    return out


def _apply_host_row(p: dict, override: dict | None = None) -> dict:
    row = {k: p[k] for k in _PUBLIC_KEYS}
    if p.get("cred") == "modal_judge":
        row["base_url"] = _modal_kimi_base()
        row["model_name"] = _modal_kimi_model()
    if override:
        if override.get("name"):
            row["name"] = override["name"]
        if override.get("base_url"):
            row["base_url"] = override["base_url"]
        if override.get("model_name"):
            row["model_name"] = override["model_name"]
    return row


def configured_host_providers() -> list[dict]:
    overrides = _load_host_overrides()
    out = []
    for p in HOST_PROVIDERS:
        ov = overrides.get(p["id"])
        if ov is not None and ov.get("enabled") is False:
            continue
        if not _host_configured(p):
            continue
        out.append(_apply_host_row(p, ov))
    return out


def _fernet_key() -> bytes:
    key = settings()["FERNET_KEY"]
    if not key:
        raise HTTPException(
            status_code=500, detail="Server encryption key not configured"
        )
    return key.encode()


def _find_existing(databases, database_id, user_id, name):
    res = databases.list_documents(
        database_id,
        "providers",
        queries=[
            Query.equal("user_id", user_id),
            Query.equal("name", name),
            Query.limit(1),
        ],
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
            doc = databases.update_document(
                database_id, "providers", existing.id, payload
            )
        else:
            doc = databases.create_document(
                database_id, "providers", "unique()", payload
            )
    except AppwriteException as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ProviderOut(
        id=doc.id,
        name=body.name,
        base_url=body.base_url,
        masked_key=masked,
        auth_style=body.auth_style,
        model_name=body.model_name,
    )


@router.get("")
def list_providers(user_id: str = Depends(get_current_user)):
    databases = db.get_databases()
    database_id = db.get_database_id()
    hosts = configured_host_providers()
    try:
        res = databases.list_documents(
            database_id,
            "providers",
            queries=[Query.equal("user_id", user_id), Query.limit(100)],
        )
    except AppwriteException as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    yours = [
        ProviderOut(
            id=d.id,
            name=d.data["name"],
            base_url=d.data["base_url"],
            masked_key=d.data["masked_key"],
            auth_style=d.data["auth_style"],
            model_name=d.data["model_name"],
        ).model_dump()
        for d in res.documents
    ]
    return hosts + yours


@router.get("/capabilities")
def provider_capabilities(user_id: str = Depends(get_current_user)):
    return {"is_admin": is_admin_user(user_id)}


@router.get("/host-catalog")
def list_host_catalog(_admin: str = Depends(require_admin)):
    overrides = _load_host_overrides()
    rows = []
    for p in HOST_PROVIDERS:
        ov = overrides.get(p["id"]) or {}
        row = _apply_host_row(p, ov if ov else None)
        rows.append(
            {
                **row,
                "cred": p.get("cred"),
                "enabled": False if ov.get("enabled") is False else True,
                "configured": _host_configured(p),
            }
        )
    return rows


@router.patch("/host-catalog/{host_id}")
def patch_host_catalog(
    host_id: str,
    body: HostCatalogPatch,
    _admin: str = Depends(require_admin),
):
    if host_id not in HOST_BY_ID:
        raise HTTPException(status_code=404, detail="Unknown host id")
    try:
        ensure_schema()
    except Exception:
        pass
    databases = db.get_databases()
    database_id = db.get_database_id()
    payload = {k: v for k, v in body.model_dump().items() if v is not None}
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update")
    try:
        databases.get_document(database_id, "host_catalog", host_id)
        databases.update_document(database_id, "host_catalog", host_id, payload)
    except AppwriteException:
        # create with defaults for missing optional fields
        create_payload = {
            "name": payload.get("name") or HOST_BY_ID[host_id]["name"],
            "base_url": payload.get("base_url") or HOST_BY_ID[host_id]["base_url"],
            "model_name": payload.get("model_name") or HOST_BY_ID[host_id]["model_name"],
            "enabled": payload.get("enabled", True),
        }
        try:
            databases.create_document(
                database_id, "host_catalog", host_id, create_payload
            )
        except AppwriteException as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    ov = _load_host_overrides().get(host_id) or {}
    row = _apply_host_row(HOST_BY_ID[host_id], ov)
    return {
        **row,
        "cred": HOST_BY_ID[host_id].get("cred"),
        "enabled": False if ov.get("enabled") is False else True,
        "configured": _host_configured(HOST_BY_ID[host_id]),
    }


def get_model_call_spec(model_id: str, user_id: str) -> tuple[str, str, str, str]:
    """Return (base_url, auth_style, api_key, model_name) for a battle model_id."""
    host = HOST_BY_ID.get(model_id)
    if host:
        ov = _load_host_overrides().get(model_id)
        if ov is not None and ov.get("enabled") is False:
            raise HTTPException(status_code=404, detail=f"Host model disabled: {model_id}")
        key = _cred_material(host.get("cred", ""))
        if not key:
            raise HTTPException(
                status_code=500,
                detail=f"Host credentials not configured for {model_id}",
            )
        row = _apply_host_row(host, ov)
        return (
            row["base_url"],
            host["auth_style"],
            key,
            row["model_name"],
        )
    databases = db.get_databases()
    database_id = db.get_database_id()
    try:
        doc = databases.get_document(database_id, "providers", model_id)
    except AppwriteException as exc:
        raise HTTPException(status_code=404, detail="Provider not found") from exc
    if doc.data.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Provider not owned")
    api_key = crypto.decrypt_key(doc.data["encrypted_key"], _fernet_key())
    return (
        doc.data["base_url"],
        doc.data["auth_style"],
        api_key,
        doc.data["model_name"],
    )


@router.post("/health")
def provider_health(body: ProviderHealth, _user_id: str = Depends(get_current_user)):
    from . import llm_client

    if body.auth_style == "manus":
        try:
            text = llm_client.manus_task_completion(
                api_key=body.api_key,
                model=body.model or body.model_name or "manus-1.6-lite",
                messages=[{"role": "user", "content": "Reply with exactly: pong"}],
                timeout=120.0,
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Request failed: {exc}") from exc
        return {"ok": bool(text), "status_code": 200, "preview": (text or "")[:80]}

    headers = {}
    if body.auth_style == "modal_proxy":
        api_key = body.api_key.strip()
        if ":" in api_key:
            parts = [p.strip() for p in api_key.split(":")]
            if len(parts) == 2 and parts[0] and parts[1]:
                headers = {"Modal-Key": parts[0], "Modal-Secret": parts[1]}
            else:
                raise HTTPException(
                    status_code=400,
                    detail="modal_proxy key must be 'wk-...:ws-...' (colon) or 'wk-....ws-...' (dot)",
                )
        elif "." in api_key and "wk-" in api_key and "ws-" in api_key:
            headers = {"Authorization": f"Bearer {api_key}"}
        elif api_key.startswith("wk-") and "." not in api_key:
            raise HTTPException(
                status_code=400,
                detail=(
                    "modal_proxy token incomplete: you provided only wk- part. "
                    "Modal proxy now requires 'Bearer wk-....ws-...' dot format. "
                    "Generate a new proxy token in Modal dashboard → Settings → Proxy Auth Tokens."
                ),
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="modal_proxy key must be 'wk-...:ws-...' (colon) or 'wk-....ws-...' (dot Bearer)",
            )
    else:
        headers["Authorization"] = f"Bearer {body.api_key}"
    url = body.base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": body.model or body.model_name or _modal_kimi_model(),
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 5,
    }
    try:
        resp = httpx.post(url, headers=headers, json=payload, timeout=30)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Request failed: {exc}") from exc
    if resp.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=f"Provider returned {resp.status_code}: {resp.text[:200]}",
        )
    return {"ok": True, "status_code": resp.status_code}
