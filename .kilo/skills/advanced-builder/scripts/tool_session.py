from __future__ import annotations
import os
import re
import signal
import subprocess
from pathlib import Path

class ToolSession:
    def __init__(self, workdir: Path, root: Path | None = None, tool_timeout: int = 15):
        self.workdir = Path(workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.root = Path(root) if root else self.workdir.parent
        self.tool_timeout = int(tool_timeout)
        self.steps = 0
        self._max_output = 50 * 1024

    def _resolve(self, rel: str) -> Path:
        if not rel or rel == ".":
            return self.workdir
        p = Path(rel)
        if ".." in p.parts:
            raise ValueError(f"ERROR: path escape '..' rejected: {rel}")
        if p.is_absolute():
            target = p.resolve()
            try:
                target.relative_to(self.workdir.resolve())
                return target
            except Exception:
                raise ValueError(f"ERROR: absolute path escapes workdir: {rel}")
        target = (self.workdir / p).resolve()
        try:
            target.relative_to(self.workdir.resolve())
        except Exception:
            raise ValueError(f"ERROR: path escapes workdir: {rel}")
        return target

    def write(self, path: str, content: str) -> str:
        try:
            t = self._resolve(path)
            t.parent.mkdir(parents=True, exist_ok=True)
            t.write_text(content, encoding="utf-8")
            self.steps += 1
            return f"WROTE {path} {len(content)} bytes"
        except Exception as exc:
            return f"ERROR: {exc}"

    def read(self, path: str) -> str:
        try:
            t = self._resolve(path)
            if not t.exists():
                return f"ERROR: not found {path}"
            if t.is_dir():
                return f"ERROR: {path} is a directory, use ls"
            data = t.read_text(encoding="utf-8", errors="ignore")
            if len(data.encode("utf-8")) > self._max_output:
                data = data[: self._max_output] + "\n[TRUNCATED]"
            self.steps += 1
            return data
        except Exception as exc:
            return f"ERROR: {exc}"

    def ls(self, path: str = ".") -> str:
        try:
            t = self._resolve(path)
            if not t.exists():
                return f"ERROR: not found {path}"
            if t.is_file():
                return f"FILE {t.name} {t.stat().st_size}b"
            items = []
            for child in t.iterdir():
                typ = "DIR" if child.is_dir() else "FILE"
                try:
                    sz = child.stat().st_size
                except Exception:
                    sz = 0
                items.append(f"{typ} {child.name} {sz}b")
            self.steps += 1
            return "\n".join(items) if items else "(empty)"
        except Exception as exc:
            return f"ERROR: {exc}"

    def clean(self, path: str) -> str:
        try:
            t = self._resolve(path)
            if not t.exists():
                return f"ERROR: not found {path}"
            if t.is_dir():
                return f"ERROR: {path} is a dir, not cleaned"
            t.unlink()
            self.steps += 1
            return f"CLEANED {path}"
        except Exception as exc:
            return f"ERROR: {exc}"

    def run(self, path: str | None = None, inline: str | None = None) -> str:
        try:
            env = os.environ.copy()
            env["ARENA_ROOT"] = str(self.root)
            env["ARENA_WORKDIR"] = str(self.workdir)
            if path:
                try:
                    run_path = self._resolve(path)
                except Exception as exc:
                    return f"ERROR: {exc}"
                if inline and inline.strip():
                    try:
                        run_path.parent.mkdir(parents=True, exist_ok=True)
                        run_path.write_text(inline, encoding="utf-8")
                    except Exception as exc:
                        return f"ERROR: write failed {exc}"
                if not run_path.exists():
                    return f"ERROR: file not found {path}"
            else:
                if not inline or not inline.strip():
                    return "ERROR: run requires path or inline code"
                run_path = self.workdir / "_inline_run.py"
                run_path.write_text(inline, encoding="utf-8")
            proc = subprocess.Popen(
                ["python3", str(run_path)],
                cwd=str(self.workdir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                start_new_session=True,
            )
            try:
                stdout, stderr = proc.communicate(timeout=self.tool_timeout)
                rc = proc.returncode
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except Exception:
                    pass
                try:
                    proc.wait(timeout=2)
                except Exception:
                    pass
                try:
                    stdout, stderr = proc.communicate(timeout=1)
                except Exception:
                    stdout, stderr = "", ""
                self.steps += 1
                combined = (stdout or "") + "\n" + (stderr or "")
                if len(combined.encode("utf-8")) > self._max_output:
                    combined = combined[: self._max_output] + "\n[TRUNCATED]"
                return f"TIMEOUT after {self.tool_timeout}s running {run_path.name}\n{combined}\nrc={proc.returncode if proc.returncode is not None else -1}"
            combined = (stdout or "") + ("\n" + (stderr or "") if stderr else "")
            if len(combined.encode("utf-8")) > self._max_output:
                combined = combined[: self._max_output] + "\n[TRUNCATED]"
            self.steps += 1
            return f"{combined}\nrc={rc}"
        except Exception as exc:
            return f"ERROR: {exc}"

    def test(self, path: str) -> str:
        try:
            t = self._resolve(path)
            if not t.exists():
                return f"ERROR: not found {path}"
            out = self.run(path=str(t))
            has_pass = "TEST_PASS" in out
            has_fail = "TEST_FAIL" in out
            m = re.search(r"rc=(-?\d+)", out)
            rc = int(m.group(1)) if m else -1
            if has_pass and not has_fail:
                status = "PASS"
            elif has_fail:
                status = "FAIL"
            else:
                if rc == 0:
                    status = "PASS"
                elif rc != -1:
                    status = "FAIL"
                else:
                    status = "UNKNOWN"
            return f"{out}\nTEST_STATUS={status}"
        except Exception as exc:
            return f"ERROR: {exc}"
