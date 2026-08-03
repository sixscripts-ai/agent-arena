"""Host-owned Kimi-K3 judge with retry, guarded JSON parse, and redaction."""

from __future__ import annotations

import json
import re
import time
from typing import Any

from fastapi import HTTPException

from . import llm_client
from .config import settings
from .redact import sanitize_artifact

DEFAULT_JUDGE_MODEL = "moonshotai/Kimi-K3"
DEFAULT_JUDGE_BASE = (
    "https://aschenbrenerashton--ep-kimi-k3-server.us-west.modal.direct/v1"
)
SCORE_MIN, SCORE_MAX = 0.0, 100.0
MAX_ATTEMPTS = 3


def _system_prompt(rubric: str, weights: dict[str, float] | None) -> str:
    weights_txt = json.dumps(weights or {})
    return f"""You are a rigorous, impartial AI battle judge.

## Rubric
{rubric}

## Scoring weights (JSON)
{weights_txt}

## Rules
- Score EACH model_id independently on a 0-100 scale.
- Do NOT favour models by prompt position or name length.
- Think step-by-step, then output ONLY a JSON object (no markdown fences):
{{
  "scores": {{"<model_id>": <float 0-100>, ...}},
  "reasoning": "<3-5 sentences>"
}}
"""


def _parse_json_object(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _clamp(score: float) -> float:
    return float(max(SCORE_MIN, min(SCORE_MAX, score)))


def _host_judge_spec() -> tuple[str, str, str, str]:
    s = settings()
    # New Bearer proxy token takes precedence: wk-xxx.ws-yyy (dot)
    proxy_token = s.get("JUDGE_MODAL_PROXY_TOKEN") or ""
    if proxy_token:
        proxy_token = proxy_token.strip()
        if "." in proxy_token and "wk-" in proxy_token and "ws-" in proxy_token:
            return DEFAULT_JUDGE_BASE, "modal_proxy", proxy_token, DEFAULT_JUDGE_MODEL
        if ":" in proxy_token:
            parts = [p.strip() for p in proxy_token.split(":")]
            if len(parts) == 2 and parts[0] and parts[1]:
                return (
                    DEFAULT_JUDGE_BASE,
                    "modal_proxy",
                    proxy_token,
                    DEFAULT_JUDGE_MODEL,
                )
        # incomplete wk- only → fall through to fallback, not old ak/as
        if proxy_token.startswith("wk-"):
            pass  # incomplete, try fallback below
        else:
            # old ak/as colon pair still valid for some setups
            if ":" in proxy_token:
                return (
                    DEFAULT_JUDGE_BASE,
                    "modal_proxy",
                    proxy_token,
                    DEFAULT_JUDGE_MODEL,
                )
    # Fallback chain if Modal proxy not configured / incomplete:
    # 1) TokenRouter Kimi-K3-Free (user says only this works) -> 2) Groq -> 3) DeepSeek -> 4) OpenRouter Free
    tr_key = s.get("HOST_TOKENROUTER_KEY") or ""
    if tr_key:
        return (
            "https://api.tokenrouter.com/v1",
            "bearer",
            tr_key,
            "moonshotai/kimi-k3-free",
        )
    groq_key = s.get("HOST_GROQ_KEY") or ""
    if groq_key:
        return (
            "https://api.groq.com/openai/v1",
            "bearer",
            groq_key,
            "llama-3.3-70b-versatile",
        )
    deep_key = s.get("HOST_DEEPSEEK_KEY") or ""
    if deep_key:
        return (
            "https://api.deepseek.com/v1",
            "bearer",
            deep_key,
            "deepseek-v4-flash",
        )
    or_key = s.get("HOST_OPENROUTER_KEY") or ""
    if or_key:
        # use a free model that supports json_object reasonably well
        return (
            "https://openrouter.ai/api/v1",
            "bearer",
            or_key,
            "nvidia/nemotron-3-nano-30b-a3b:free",
        )
    key = s.get("JUDGE_MODAL_KEY") or ""
    secret = s.get("JUDGE_MODAL_SECRET") or ""
    if not key or not secret:
        raise HTTPException(
            status_code=500,
            detail="Judge credentials not configured (no proxy token and no HOST_OPENROUTER_KEY fallback)",
        )
    combined = f"{key}:{secret}"
    return DEFAULT_JUDGE_BASE, "modal_proxy", combined, DEFAULT_JUDGE_MODEL


def judge_battle(
    *,
    model_ids: list[str],
    artifacts: list[dict],
    rubric: str,
    weights: dict[str, float] | None = None,
    judge_model: str | None = None,
    call_spec: tuple[str, str, str, str] | None = None,
) -> dict[str, Any]:
    """Return {scores: {model_id: float}, justifications: {model_id: str}, judge_model: str}."""
    base_url, auth_style, api_key, model = call_spec or _host_judge_spec()
    if judge_model:
        model = judge_model

    user_payload = {
        "model_ids": model_ids,
        "artifacts": artifacts,
    }
    messages = [
        {"role": "system", "content": _system_prompt(rubric, weights)},
        {"role": "user", "content": json.dumps(user_payload)},
    ]

    last_err: Exception | None = None
    raw = ""
    for attempt in range(MAX_ATTEMPTS):
        try:
            raw = llm_client.chat_completion(
                base_url=base_url,
                auth_style=auth_style,
                api_key=api_key,
                model=model,
                messages=messages,
                max_tokens=8192,
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            parsed = _parse_json_object(raw)
            raw_scores = parsed.get("scores") or {}
            reasoning = sanitize_artifact(str(parsed.get("reasoning", "")))
            scores: dict[str, float] = {}
            justifications: dict[str, str] = {}
            for mid in model_ids:
                if mid not in raw_scores:
                    raise ValueError(f"missing score for {mid}")
                scores[mid] = _clamp(float(raw_scores[mid]))
                justifications[mid] = reasoning
            return {
                "scores": scores,
                "justifications": justifications,
                "judge_model": model,
            }
        except Exception as exc:  # noqa: BLE001 — retry then fail battle
            last_err = exc
            time.sleep(0.5 * (2**attempt))
    raise HTTPException(
        status_code=502, detail=f"Judge failed after retries: {last_err}"
    )
