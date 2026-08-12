"""OpenAI-compatible chat completions for user providers and host models."""

from __future__ import annotations

import time

import httpx
from fastapi import HTTPException

MANUS_BASE = "https://api.manus.ai"
MANUS_PROFILES = frozenset({"manus-1.6", "manus-1.6-lite", "manus-1.6-max"})


def build_headers(auth_style: str, api_key: str) -> dict[str, str]:
    if auth_style == "manus":
        return {"x-manus-api-key": api_key.strip(), "Content-Type": "application/json"}
    if auth_style == "modal_proxy":
        # New Modal proxy format: Bearer wk-...ws-... (dot)
        # Old format: Modal-Key/Secret via colon wk-...:ws-...
        api_key = api_key.strip()
        if ":" in api_key:
            parts = [p.strip() for p in api_key.split(":")]
            if len(parts) == 2 and parts[0] and parts[1]:
                return {"Modal-Key": parts[0], "Modal-Secret": parts[1]}
        if "." in api_key and "wk-" in api_key and "ws-" in api_key:
            return {"Authorization": f"Bearer {api_key}"}
        if api_key.startswith("wk-") and "." not in api_key and ":" not in api_key:
            raise HTTPException(
                status_code=400,
                detail=(
                    "modal_proxy token incomplete: you provided only wk- part. "
                    "Modal proxy now requires 'Bearer wk-....ws-...' dot format. "
                    "Generate a new proxy token in Modal dashboard → Settings → Proxy Auth Tokens, "
                    "copy the full 'wk-....ws-...' string."
                ),
            )
        raise HTTPException(
            status_code=400,
            detail="modal_proxy key must be 'wk-...:ws-...' (colon) or 'wk-...ws-...' (dot Bearer)",
        )
    return {"Authorization": f"Bearer {api_key}"}


def _messages_to_prompt(messages: list[dict]) -> str:
    parts: list[str] = []
    for m in messages:
        role = str(m.get("role") or "user").upper()
        content = m.get("content") or ""
        if isinstance(content, list):
            chunks = []
            for c in content:
                if isinstance(c, dict) and c.get("type") == "text":
                    chunks.append(str(c.get("text") or ""))
                else:
                    chunks.append(str(c))
            content = "\n".join(chunks)
        parts.append(f"{role}:\n{content}")
    parts.append(
        "ASSISTANT:\nReply with the final answer only. Do not ask follow-up questions."
    )
    return "\n\n".join(parts)


def _manus_extract_assistant(messages: list) -> str:
    texts: list[str] = []
    for ev in messages or []:
        if not isinstance(ev, dict):
            continue
        if ev.get("type") != "assistant_message":
            continue
        am = ev.get("assistant_message") or {}
        content = am.get("content") if isinstance(am, dict) else None
        if content:
            texts.append(str(content))
    return "\n\n".join(texts).strip()


def _manus_latest_status(messages: list) -> str | None:
    for ev in messages or []:
        if not isinstance(ev, dict):
            continue
        if ev.get("type") != "status_update":
            continue
        su = ev.get("status_update") or {}
        if isinstance(su, dict) and su.get("agent_status"):
            return str(su["agent_status"])
    return None


def manus_task_completion(
    *,
    api_key: str,
    model: str,
    messages: list[dict],
    timeout: float = 600.0,
) -> str:
    """Create a Manus v2 task and poll until stopped; return assistant text."""
    profile = model if model in MANUS_PROFILES else "manus-1.6"
    headers = build_headers("manus", api_key)
    prompt = _messages_to_prompt(messages)
    create_url = f"{MANUS_BASE}/v2/task.create"
    payload = {
        "message": {"content": prompt},
        "agent_profile": profile,
        "interactive_mode": False,
        "hide_in_task_list": True,
    }
    try:
        created = httpx.post(create_url, headers=headers, json=payload, timeout=60.0)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail=f"Manus create failed: {exc}"
        ) from exc
    if created.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"Manus create {created.status_code}: {created.text[:300]}",
        )
    data = created.json() if created.content else {}
    task_id = data.get("task_id")
    if not task_id:
        raise HTTPException(status_code=502, detail="Manus create missing task_id")

    deadline = time.time() + max(30.0, timeout)
    list_url = f"{MANUS_BASE}/v2/task.listMessages"
    last_err = ""
    while time.time() < deadline:
        try:
            resp = httpx.get(
                list_url,
                headers=headers,
                params={
                    "task_id": task_id,
                    "order": "desc",
                    "limit": 50,
                    "verbose": "false",
                },
                timeout=60.0,
            )
        except httpx.HTTPError as exc:
            last_err = str(exc)
            time.sleep(2.0)
            continue
        if resp.status_code >= 400:
            last_err = f"{resp.status_code}: {resp.text[:200]}"
            time.sleep(2.0)
            continue
        body = resp.json() if resp.content else {}
        events = body.get("messages") or body.get("data") or []
        if not isinstance(events, list):
            events = []
        status = _manus_latest_status(events)
        if status == "error":
            raise HTTPException(
                status_code=502, detail=f"Manus task error for {task_id}"
            )
        if status in ("stopped", "waiting"):
            text = _manus_extract_assistant(events)
            if text:
                return text
            if status == "waiting":
                raise HTTPException(
                    status_code=502,
                    detail=f"Manus task waiting for input ({task_id})",
                )
            # stopped but empty — try ascending once
            try:
                resp2 = httpx.get(
                    list_url,
                    headers=headers,
                    params={
                        "task_id": task_id,
                        "order": "asc",
                        "limit": 100,
                        "verbose": "false",
                    },
                    timeout=60.0,
                )
                body2 = resp2.json() if resp2.content else {}
                events2 = body2.get("messages") or body2.get("data") or []
                text2 = _manus_extract_assistant(
                    events2 if isinstance(events2, list) else []
                )
                if text2:
                    return text2
            except httpx.HTTPError:
                pass
            raise HTTPException(
                status_code=502,
                detail=f"Manus task stopped with empty assistant output ({task_id})",
            )
        time.sleep(3.0)

    raise HTTPException(
        status_code=502,
        detail=f"Manus task timed out ({task_id}){': ' + last_err if last_err else ''}",
    )


def chat_completion(
    *,
    base_url: str,
    auth_style: str,
    api_key: str,
    model: str,
    messages: list[dict],
    max_tokens: int = 1024,
    temperature: float = 0.7,
    timeout: float = 120.0,
    response_format: dict | None = None,
) -> str:
    if auth_style == "manus":
        return manus_task_completion(
            api_key=api_key,
            model=model,
            messages=messages,
            timeout=max(timeout, 600.0),
        )

    headers = build_headers(auth_style, api_key)
    url = base_url.rstrip("/") + "/chat/completions"
    payload: dict = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if response_format is not None:
        payload["response_format"] = response_format
    try:
        resp = httpx.post(url, headers=headers, json=payload, timeout=timeout)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail=f"LLM request failed: {exc}"
        ) from exc
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"LLM returned {resp.status_code}: {resp.text[:300]}",
        )
    data = resp.json()
    try:
        message = data["choices"][0]["message"]
        content = message.get("content") or ""
        if not content:
            content = message.get("reasoning_content") or ""
        return content or ""
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="Malformed LLM response") from exc
