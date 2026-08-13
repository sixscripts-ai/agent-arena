"""HTTP client for sandbox → backend /internal/* callbacks."""

from __future__ import annotations

import time
from typing import Any, Protocol

import httpx


class Transport(Protocol):
    def post(self, path: str, json: dict) -> dict: ...


class HttpTransport:
    def __init__(self, base_url: str, internal_key: str, timeout: float = 600.0):
        self.base_url = base_url.rstrip("/")
        self.internal_key = internal_key
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout, follow_redirects=True)

    def post(self, path: str, json: dict) -> dict:
        url = self.base_url + path
        headers = {"X-Internal-Key": self.internal_key}
        last_err: Exception | None = None
        for attempt in range(3):
            try:
                resp = self.client.post(url, headers=headers, json=json)
                if resp.status_code >= 500:
                    raise httpx.HTTPError(f"server {resp.status_code}")
                if resp.status_code >= 400:
                    raise RuntimeError(
                        f"internal {path} failed: {resp.status_code} {resp.text[:200]}"
                    )
                try:
                    return resp.json()
                except ValueError as exc:
                    raise RuntimeError(
                        f"internal {path} returned non-JSON body "
                        f"(status {resp.status_code}, {len(resp.content)} bytes): "
                        f"{resp.text[:120]!r}"
                    ) from exc
            except (httpx.HTTPError, RuntimeError) as exc:
                last_err = exc
                if isinstance(exc, RuntimeError) and "failed: 4" in str(exc):
                    raise
                time.sleep(0.5 * (2**attempt))
        raise RuntimeError(f"internal {path} exhausted retries: {last_err}")


class FakeTransport:
    """In-memory transport for hermetic unit tests."""

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []
        self.model_replies: dict[str, Any] = {}
        self.judge_result: dict[str, Any] = {
            "scores": {},
            "justifications": {},
            "judge_model": "mock",
        }
        self.rounds: list[dict] = []
        self.battle_status: str = "running"

    def post(self, path: str, json: dict) -> dict:
        self.calls.append((path, json))
        if path == "/internal/model":
            mid = json.get("model_id", "")
            reply = self.model_replies.get(mid, f"[reply:{mid}]")
            if isinstance(reply, list):
                content = reply.pop(0) if reply else f"[reply:{mid}]"
            else:
                content = reply
            return {"content": content}
        if path == "/internal/judge":
            return self.judge_result
        if path == "/internal/round":
            self.rounds.append(json)
            return {"ok": True, "event_id": "fake", "sequence": json.get("sequence")}
        if path == "/internal/status":
            return {"status": self.battle_status}
        if path == "/internal/finalize":
            return {"ok": True, "status": json.get("status", "completed")}
        raise RuntimeError(f"unknown path {path}")


class InternalClient:
    def __init__(self, transport: Transport):
        self.t = transport

    def model(
        self,
        battle_id: str,
        model_id: str,
        messages: list[dict],
        phase: str = "",
        max_tokens: int | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "battle_id": battle_id,
            "model_id": model_id,
            "phase": phase,
            "messages": messages,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        data = self.t.post("/internal/model", payload)
        return data.get("content", "")

    def judge(
        self,
        battle_id: str,
        rubric: str,
        artifacts: list[dict],
        weights: dict | None = None,
    ) -> dict:
        return self.t.post(
            "/internal/judge",
            {
                "battle_id": battle_id,
                "rubric": rubric,
                "weights": weights,
                "artifacts": artifacts,
            },
        )

    def round(
        self,
        battle_id: str,
        phase: str,
        model_id: str,
        artifact: str,
        event_type: str = "artifact",
        sequence: int | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "battle_id": battle_id,
            "phase": phase,
            "model_id": model_id,
            "artifact": artifact,
            "event_type": event_type,
        }
        if sequence is not None:
            payload["sequence"] = sequence
        self.t.post("/internal/round", payload)

    def status(self, battle_id: str) -> str:
        data = self.t.post("/internal/status", {"battle_id": battle_id})
        return str(data.get("status") or "unknown")

    def finalize(self, battle_id: str, status: str, scores: dict | None = None) -> dict:
        return self.t.post(
            "/internal/finalize",
            {
                "battle_id": battle_id,
                "status": status,
                "scores": scores or {},
            },
        )
