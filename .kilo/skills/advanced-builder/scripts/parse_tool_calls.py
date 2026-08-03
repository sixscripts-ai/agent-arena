from __future__ import annotations
import re
from typing import Any

def _extract_path(arg_str: str) -> str:
    if not arg_str:
        return ""
    m = re.search(r'path\s*=\s*"([^"]+)"', arg_str)
    if m:
        return m.group(1).strip()
    m = re.search(r"path\s*=\s*'([^']+)'", arg_str)
    if m:
        return m.group(1).strip()
    m = re.search(r"path\s*=\s*([^\s]+)", arg_str)
    if m:
        return m.group(1).strip()
    arg_str = arg_str.strip()
    if arg_str and "=" not in arg_str:
        return arg_str
    return ""

def parse_tool_calls(text: str) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        if stripped == "DONE" or stripped.upper() == "DONE":
            break
        if stripped.upper().startswith("TOOL "):
            remainder = stripped[5:].strip()
            if not remainder:
                calls.append({"tool": "unknown", "raw": line, "error": "ERROR: empty tool"})
                i += 1
                continue
            parts = remainder.split(None, 1)
            tool_name = parts[0].lower()
            arg_str = parts[1] if len(parts) > 1 else ""
            if tool_name in ("write", "run"):
                path = _extract_path(arg_str)
                body_lines: list[str] = []
                i += 1
                found_end = False
                while i < len(lines):
                    l = lines[i]
                    if l.strip() == "END_TOOL":
                        found_end = True
                        break
                    body_lines.append(l)
                    i += 1
                if not found_end:
                    calls.append({"tool": tool_name, "path": path, "content": "\n".join(body_lines), "error": "ERROR: missing END_TOOL"})
                    break
                content = "\n".join(body_lines)
                calls.append({"tool": tool_name, "path": path, "content": content} if tool_name == "write" else {"tool": "run", "path": path, "content": content})
                i += 1
                continue
            elif tool_name in ("read", "ls", "test", "clean"):
                path = _extract_path(arg_str)
                if tool_name == "ls" and not path:
                    path = arg_str.strip() or "."
                    if "=" in path:
                        path = _extract_path(path)
                    if not path:
                        path = "."
                calls.append({"tool": tool_name, "path": path})
                i += 1
                continue
            else:
                calls.append({"tool": tool_name, "raw": remainder, "error": f"ERROR: unknown tool {tool_name}"})
                i += 1
                continue
        else:
            i += 1
    return calls
