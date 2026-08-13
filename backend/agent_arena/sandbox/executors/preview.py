"""Static preview servers per participant, bound to a dedicated sandbox port.

The backend spawns the sandbox with encrypted_ports=[8080, 8081] and obtains
public HTTPS tunnel URLs; the executor starts one of these servers per player
workdir so the frontend can render a live preview iframe (Sandpack feel).
"""

from __future__ import annotations

import functools
import http.server
import logging
import threading
from pathlib import Path

_PREVIEW_PORT_BASE = 8080


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args) -> None:  # keep sandbox logs clean
        return


class StaticPreviewServer:
    def __init__(self, workdir: Path, port: int):
        self.workdir = Path(workdir)
        self.port = int(port)
        self.httpd: http.server.ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self.workdir.mkdir(parents=True, exist_ok=True)
        handler = functools.partial(QuietHandler, directory=str(self.workdir))
        self.httpd = http.server.ThreadingHTTPServer(("0.0.0.0", self.port), handler)
        self.httpd.daemon_threads = True
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self._thread.start()
        logging.getLogger(__name__).info(
            "preview serving %s on :%s", self.workdir, self.port
        )

    def stop(self) -> None:
        if self.httpd is not None:
            try:
                self.httpd.shutdown()
            except Exception:
                pass
            try:
                self.httpd.server_close()
            except Exception:
                pass
            self.httpd = None


def port_for_index(index: int) -> int:
    return _PREVIEW_PORT_BASE + index


def preview_enabled() -> bool:
    import os

    return os.environ.get("ARENA_PREVIEW", "1") == "1"
