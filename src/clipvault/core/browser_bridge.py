"""Opt-in, authenticated loopback bridge for the browser draft extension."""

import hmac
import json
import os
import re
import secrets
import threading
import uuid
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from PySide6.QtCore import QObject, Signal

from clipvault.core.privacy import validate_capture

PORT = 47963
MAX_BODY = 500_000
_EXTENSION_ORIGIN = re.compile(r"^chrome-extension://[a-p]{32}$")


def pairing_token(directory: Path) -> str:
    path = directory / "browser-sync.key"
    if path.exists():
        token = path.read_text(encoding="ascii").strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{40,64}", token):
            raise ValueError("Invalid browser pairing token")
        return token
    token = secrets.token_urlsafe(32)
    directory.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return pairing_token(directory)
    with os.fdopen(descriptor, "w", encoding="ascii") as handle:
        handle.write(token)
        handle.flush()
        os.fsync(handle.fileno())
    return token


def validate_draft(payload):
    if not isinstance(payload, dict) or set(payload) != {
        "id",
        "origin",
        "path",
        "text",
        "created_at",
        "updated_at",
        "revision",
    }:
        raise ValueError("Invalid draft")
    draft_id = str(uuid.UUID(payload["id"]))
    origin = payload["origin"]
    path = payload["path"]
    revision = payload["revision"]
    if not isinstance(origin, str) or len(origin) > 512:
        raise ValueError("Invalid origin")
    parts = urlsplit(origin)
    if (
        parts.scheme not in {"https", "http"}
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or parts.path not in {"", "/"}
        or parts.query
        or parts.fragment
    ):
        raise ValueError("Invalid origin")
    if not isinstance(path, str) or not path.startswith("/") or len(path) > 512:
        raise ValueError("Invalid path")
    if "?" in path or "#" in path or "\x00" in path:
        raise ValueError("Invalid path")
    if type(revision) is not int or not 0 < revision < 2**31:
        raise ValueError("Invalid revision")
    if not validate_capture(payload["text"], filter_sensitive=False).allowed:
        raise ValueError("Invalid text")
    created = datetime.fromisoformat(payload["created_at"].replace("Z", "+00:00"))
    updated = datetime.fromisoformat(payload["updated_at"].replace("Z", "+00:00"))
    if created.tzinfo is None or updated.tzinfo is None or created > updated:
        raise ValueError("Invalid timestamp")
    return {
        "id": draft_id,
        "origin": origin.rstrip("/"),
        "path": path,
        "text": payload["text"],
        "created_at": created.astimezone(UTC).isoformat(timespec="microseconds"),
        "updated_at": updated.astimezone(UTC).isoformat(timespec="microseconds"),
        "revision": revision,
    }


class BrowserBridge(QObject):
    received = Signal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.server = None
        self.thread = None

    def start(self, token: str, port: int = PORT):
        if self.server is not None:
            return
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def _origin_allowed(self):
                origin = self.headers.get("Origin")
                return not origin or bool(_EXTENSION_ORIGIN.fullmatch(origin))

            def _send(self, status, payload):
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                origin = self.headers.get("Origin")
                if origin and _EXTENSION_ORIGIN.fullmatch(origin):
                    self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except OSError:
                    pass

            def _authorized(self):
                value = self.headers.get("Authorization", "")
                return self._origin_allowed() and hmac.compare_digest(value, "Bearer " + token)

            def do_OPTIONS(self):
                if not self._origin_allowed() or not self.headers.get("Origin"):
                    self._send(403, {"ok": False})
                    return
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", self.headers["Origin"])
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
                self.send_header("Content-Length", "0")
                self.end_headers()

            def do_GET(self):
                if self.path != "/v1/status" or not self._authorized():
                    self._send(403, {"ok": False})
                    return
                self._send(200, {"ok": True})

            def do_POST(self):
                if self.path != "/v1/drafts" or not self._authorized():
                    self._send(403, {"ok": False})
                    return
                try:
                    size = int(self.headers.get("Content-Length", "0"))
                    if (
                        not 0 < size <= MAX_BODY
                        or self.headers.get_content_type() != "application/json"
                    ):
                        raise ValueError("Invalid request")
                    self.connection.settimeout(3)
                    body = self.rfile.read(size)
                    if len(body) != size:
                        raise ValueError("Incomplete request")
                    draft = validate_draft(json.loads(body.decode("utf-8")))
                except (ValueError, TypeError, KeyError, AttributeError, OSError, UnicodeError):
                    self._send(400, {"ok": False})
                    return
                acknowledgement = {"event": threading.Event(), "ok": False}
                bridge.received.emit(draft, acknowledgement)
                if not acknowledgement["event"].wait(5) or not acknowledgement["ok"]:
                    self._send(503, {"ok": False})
                    return
                self._send(200, {"ok": True})

        self.server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(timeout=2)
            self.server = None
            self.thread = None
