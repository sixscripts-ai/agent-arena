"""Structured model results and tool-call normalization."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any

NATIVE_TOOL_NAMES = (
    "ls",
    "read",
    "write",
    "patch",
    "shell",
    "install",
    "fetch",
    "test",
    "use_skill",
    "preview",
    "skills",
)

_REPAIR_EXAMPLE = (
    'Call tools. Example: {"tool":"read","path":"TARGET.md"} '
    "or native function ls/read/write/test/use_skill."
)


@dataclass
class ModelResult:
    content: str
    tool_calls: list[dict] = field(default_factory=list)
    finish_reason: str | None = None
    provider: str | None = None
    model: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def native_tool_schemas() -> list[dict]:
    """OpenAI-compatible tool definitions matching ToolSession operations."""
    return [
        _fn("ls", "List files in the workspace.", {"path": {"type": "string", "description": "Directory path"}}, []),
        _fn("read", "Read a file.", {"path": {"type": "string"}}, ["path"]),
        _fn(
            "write",
            "Write a file. Create parent directories as needed.",
            {"path": {"type": "string"}, "content": {"type": "string"}},
            ["path", "content"],
        ),
        _fn(
            "patch",
            "Replace old_string with new_string in a file, or overwrite via content.",
            {
                "path": {"type": "string"},
                "old_string": {"type": "string"},
                "new_string": {"type": "string"},
                "content": {"type": "string"},
            },
            ["path"],
        ),
        _fn("shell", "Run a shell command.", {"cmd": {"type": "string"}}, ["cmd"]),
        _fn("install", "Install packages (pip/npm).", {"cmd": {"type": "string"}}, ["cmd"]),
        _fn("fetch", "HTTP GET a URL.", {"url": {"type": "string"}}, ["url"]),
        _fn("test", "Run tests/test_target.py or the given path.", {"path": {"type": "string"}}, []),
        _fn("use_skill", "Read a mounted skill SKILL.md.", {"name": {"type": "string"}}, ["name"]),
        _fn("preview", "Report the local preview server.", {"url": {"type": "string"}}, []),
        _fn(
            "skills",
            "Choose skills from the mounted pool.",
            {"chosen": {"type": "array", "items": {"type": "string"}}},
            ["chosen"],
        ),
    ]


def _fn(name: str, description: str, properties: dict, required: list[str]) -> dict:
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return {
        "type": "function",
        "function": {"name": name, "description": description, "parameters": schema},
    }


def parse_openai_response(data: dict) -> ModelResult:
    """Preserve content, tool_calls, finish_reason, provider, and model."""
    choice = (data.get("choices") or [{}])[0] or {}
    message = choice.get("message") or {}
    content = message.get("content")
    if content is None:
        content_str = ""
    else:
        content_str = str(content)
    raw_calls = message.get("tool_calls") or []
    tool_calls: list[dict] = []
    if isinstance(raw_calls, list):
        for tc in raw_calls:
            if not isinstance(tc, dict):
                continue
            fn = tc.get("function") or {}
            tool_calls.append(
                {
                    "id": tc.get("id") or "",
                    "type": tc.get("type") or "function",
                    "function": {
                        "name": fn.get("name") or "",
                        "arguments": fn.get("arguments")
                        if isinstance(fn.get("arguments"), str)
                        else json.dumps(fn.get("arguments") or {}),
                    },
                }
            )
    return ModelResult(
        content=content_str,
        tool_calls=tool_calls,
        finish_reason=choice.get("finish_reason"),
        provider=data.get("provider"),
        model=data.get("model"),
    )


def model_result_from_payload(data: dict | None) -> ModelResult:
    data = data or {}
    if "choices" in data:
        return parse_openai_response(data)
    calls = data.get("tool_calls") or []
    if not isinstance(calls, list):
        calls = []
    return ModelResult(
        content=str(data.get("content") or ""),
        tool_calls=calls,
        finish_reason=data.get("finish_reason"),
        provider=data.get("provider"),
        model=data.get("model"),
    )


def _args_to_call(name: str, args: dict, call_id: str = "") -> dict:
    tool = (name or "").strip()
    call: dict[str, Any] = {"tool": tool, "id": call_id}
    if tool in ("ls", "read", "rm", "tree", "test"):
        call["path"] = str(args.get("path") or ("" if tool != "ls" else "."))
        if tool == "ls" and not call["path"]:
            call["path"] = "."
    elif tool == "write":
        call["path"] = str(args.get("path") or "")
        call["content"] = str(args.get("content") or "")
    elif tool == "patch":
        call["path"] = str(args.get("path") or "")
        call["old_string"] = str(args.get("old_string") or args.get("old") or "")
        call["new_string"] = str(args.get("new_string") or args.get("new") or "")
        call["content"] = str(args.get("content") or "")
    elif tool in ("shell", "install"):
        call["cmd"] = str(args.get("cmd") or args.get("command") or "")
    elif tool == "fetch":
        call["url"] = str(args.get("url") or "")
    elif tool == "use_skill":
        call["name"] = str(args.get("name") or "")
    elif tool == "preview":
        call["url"] = str(args.get("url") or "")
    elif tool == "skills":
        chosen = args.get("chosen") or args.get("skills") or []
        if isinstance(chosen, str):
            chosen = [s.strip() for s in chosen.split(",") if s.strip()]
        call["chosen"] = list(chosen)
    else:
        call.update({k: v for k, v in args.items() if k != "tool"})
    return call


def _validate_call(call: dict) -> str | None:
    tool = call.get("tool")
    if not tool:
        return "missing tool name"
    if tool in ("read", "write", "patch") and not call.get("path"):
        return f"{tool} requires path"
    if tool == "write" and call.get("content") is None:
        return "write requires content"
    if tool == "use_skill" and not call.get("name"):
        return "use_skill requires name"
    if tool in ("shell", "install") and not call.get("cmd"):
        return f"{tool} requires cmd"
    if tool == "fetch" and not call.get("url"):
        return "fetch requires url"
    if tool == "unknown" or call.get("error"):
        return str(call.get("error") or "unknown tool")
    return None


def _parse_json_actions(content: str) -> list[dict] | None:
    text = (content or "").strip()
    if not text:
        return None
    fence = re.match(r"^```(?:json)?\s*([\s\S]*?)```$", text)
    if fence:
        text = fence.group(1).strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            start = text.find("[")
            end = text.rfind("]")
        if start < 0 or end <= start:
            return None
        try:
            obj = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    items: list
    if isinstance(obj, list):
        items = obj
    elif isinstance(obj, dict):
        if isinstance(obj.get("tools"), list):
            items = obj["tools"]
        elif any(k in obj for k in ("tool", "name", "action")):
            items = [obj]
        else:
            return None
    else:
        return None
    out: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("tool") or item.get("name") or item.get("action") or "")
        args = item.get("arguments") or item.get("args")
        if not isinstance(args, dict):
            args = {k: v for k, v in item.items() if k not in ("tool", "name", "action", "id", "type")}
        out.append(_args_to_call(name, args, str(item.get("id") or "")))
    return out or None


def _typed_arg_error(name: str, call_id: str, detail: str) -> dict:
    return {
        "tool": name or "unknown",
        "id": call_id,
        "error": "invalid_arguments",
        "detail": detail,
    }


def normalize_tool_calls(result: ModelResult) -> tuple[list[dict], str | None]:
    """Native tool_calls, then JSON content, then textual TOOL syntax."""
    errors: list[str] = []
    if result.tool_calls:
        calls: list[dict] = []
        for tc in result.tool_calls:
            fn = tc.get("function") or {}
            name = str(fn.get("name") or "")
            call_id = str(tc.get("id") or "")
            raw_args = fn.get("arguments") if fn.get("arguments") is not None else "{}"
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args or {})
            except json.JSONDecodeError:
                errors.append(f"invalid_arguments:{name}")
                calls.append(_typed_arg_error(name, call_id, "tool arguments were not valid JSON"))
                continue
            if not isinstance(args, dict):
                errors.append(f"invalid_arguments:{name}")
                calls.append(_typed_arg_error(name, call_id, "tool arguments must be a JSON object"))
                continue
            call = _args_to_call(name, args, call_id)
            err = _validate_call(call)
            if err:
                call["error"] = err
                errors.append(err)
            calls.append(call)
        return calls, ("; ".join(errors) if errors else None)
    json_calls = _parse_json_actions(result.content)
    if json_calls:
        valid = []
        for call in json_calls:
            err = _validate_call(call)
            if err:
                call["error"] = err
                errors.append(err)
            valid.append(call)
        return valid, ("; ".join(errors) if errors else None)
    from .sandbox.executors.advanced_executor import parse_tool_calls

    text_calls = parse_tool_calls(result.content or "")
    text_calls = [c for c in text_calls if c.get("tool") != "error"]
    if text_calls:
        valid = []
        for call in text_calls:
            err = _validate_call(call)
            if err:
                call["error"] = err
                errors.append(err)
            valid.append(call)
        return valid, ("; ".join(errors) if errors else None)
    err = "; ".join(errors) if errors else None
    if not (result.content or "").strip() and not result.tool_calls:
        err = err or "empty content and no tool_calls"
    elif not err:
        err = "no tool calls in content or tool_calls"
    return [], err


def classify_provider_error(exc: BaseException) -> str | None:
    msg = str(exc).lower()
    if "provider_quota_exhausted" in msg or "failed: 429" in msg or "status=429" in msg:
        return "provider_quota_exhausted"
    if "provider timeout" in msg or "failed: 504" in msg:
        return "provider_timeout"
    if "provider_auth_failed" in msg or "failed: 401" in msg or "failed: 403" in msg:
        return "provider_auth_failed"
    if "exhausted retries" in msg or "llm returned" in msg or "server 502" in msg:
        return "provider_error"
    return None


def repair_prompt() -> str:
    names = ", ".join(NATIVE_TOOL_NAMES)
    return (
        "Your last reply had no valid tool call. "
        f"You must invoke one of: {names}. "
        f"{_REPAIR_EXAMPLE} "
        "Plain prose is not execution."
    )


def excerpt(text: str, limit: int = 400) -> str:
    raw = text or ""
    return raw[:limit]


def model_capabilities(model_id: str, record: dict | None = None) -> dict[str, bool]:
    caps = {
        "supports_tools": True,
        "supports_json_mode": True,
        "supports_text_tools": True,
    }
    if model_id == "host:or-gemma-31b":
        caps["supports_tools"] = False
        caps["supports_json_mode"] = False
    if record:
        for key in caps:
            if key in record:
                caps[key] = bool(record[key])
    return caps
