"""OpenAI-compatible chat completions for user providers and host free model."""

from __future__ import annotations

import httpx
from fastapi import HTTPException

from .model_protocol import ModelResult, parse_openai_response

DEFAULT_PROVIDER_TIMEOUT = 60.0


def build_headers(auth_style: str, api_key: str) -> dict[str, str]:
    if auth_style == "modal_proxy":
        parts = [p.strip() for p in api_key.split(":")]
        if len(parts) != 2:
            raise HTTPException(
                status_code=400, detail="modal_proxy key must be 'wk-...:ws-...'"
            )
        return {"Modal-Key": parts[0], "Modal-Secret": parts[1]}
    return {"Authorization": f"Bearer {api_key}"}


def chat_completion(
    *,
    base_url: str,
    auth_style: str,
    api_key: str,
    model: str,
    messages: list[dict],
    max_tokens: int = 1024,
    temperature: float = 0.7,
    timeout: float = DEFAULT_PROVIDER_TIMEOUT,
    response_format: dict | None = None,
    tools: list[dict] | None = None,
    tool_choice: str | dict | None = None,
) -> str:
    result = chat_completion_result(
        base_url=base_url,
        auth_style=auth_style,
        api_key=api_key,
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        timeout=timeout,
        response_format=response_format,
        tools=tools,
        tool_choice=tool_choice,
    )
    return result.content


def chat_completion_result(
    *,
    base_url: str,
    auth_style: str,
    api_key: str,
    model: str,
    messages: list[dict],
    max_tokens: int = 1024,
    temperature: float = 0.7,
    timeout: float = DEFAULT_PROVIDER_TIMEOUT,
    response_format: dict | None = None,
    tools: list[dict] | None = None,
    tool_choice: str | dict | None = None,
) -> ModelResult:
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
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice if tool_choice is not None else "auto"
    try:
        resp = httpx.post(url, headers=headers, json=payload, timeout=timeout)
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="provider timeout") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail=f"LLM request failed: {exc}"
        ) from exc
    if resp.status_code == 429:
        raise HTTPException(status_code=429, detail="provider_quota_exhausted")
    if resp.status_code in (401, 403):
        raise HTTPException(status_code=resp.status_code, detail="provider_auth_failed")
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"LLM returned {resp.status_code}: {resp.text[:300]}",
        )
    try:
        data = resp.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Malformed LLM response") from exc
    try:
        result = parse_openai_response(data)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Malformed LLM response") from exc
    if result.provider is None:
        result.provider = data.get("provider")
    if result.model is None:
        result.model = data.get("model") or model
    return result
