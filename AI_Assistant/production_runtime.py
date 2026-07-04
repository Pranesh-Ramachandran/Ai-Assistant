"""Production HTTP primitives for the JARVIS Neural Grid server."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from dataclasses import dataclass
from http.server import ThreadingHTTPServer
from typing import Any


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        return max(minimum, min(maximum, int(os.getenv(name, str(default)))))
    except ValueError:
        return default


@dataclass(frozen=True)
class ServerConfig:
    host: str
    port: int
    allowed_origins: frozenset[str]
    api_token: str
    max_body_bytes: int
    max_text_chars: int
    socket_timeout: int
    max_workers: int
    max_sse_clients: int
    log_transcripts: bool
    require_confirmation: bool

    @classmethod
    def from_env(cls) -> "ServerConfig":
        host = os.getenv("JARVIS_HOST", "localhost").strip() or "localhost"
        port = _env_int("JARVIS_PORT", 7890, 1, 65535)
        default_origins = f"http://localhost:{port},http://127.0.0.1:{port}"
        origins = frozenset(
            item.strip().rstrip("/")
            for item in os.getenv("JARVIS_ALLOWED_ORIGINS", default_origins).split(",")
            if item.strip()
        )
        return cls(
            host=host,
            port=port,
            allowed_origins=origins,
            api_token=os.getenv("JARVIS_API_TOKEN", "").strip(),
            max_body_bytes=_env_int("JARVIS_MAX_BODY_BYTES", 8 * 1024 * 1024, 1024, 32 * 1024 * 1024),
            max_text_chars=_env_int("JARVIS_MAX_TEXT_CHARS", 10_000, 256, 100_000),
            socket_timeout=_env_int("JARVIS_SOCKET_TIMEOUT", 30, 2, 300),
            max_workers=_env_int("JARVIS_MAX_WORKERS", 16, 2, 128),
            max_sse_clients=_env_int("JARVIS_MAX_SSE_CLIENTS", 4, 1, 32),
            log_transcripts=_env_bool("JARVIS_LOG_TRANSCRIPTS", False),
            require_confirmation=_env_bool("JARVIS_REQUIRE_ACTION_CONFIRMATION", True),
        )


class Metrics:
    def __init__(self) -> None:
        self.started_at = time.time()
        self._lock = threading.Lock()
        self._requests: dict[tuple[str, int], int] = {}
        self._latency_sum: dict[str, float] = {}
        self._active = 0
        self._rejected = 0

    def request_started(self) -> None:
        with self._lock:
            self._active += 1

    def request_finished(self, path: str, status: int, elapsed: float) -> None:
        with self._lock:
            self._active = max(0, self._active - 1)
            key = (path, status)
            self._requests[key] = self._requests.get(key, 0) + 1
            self._latency_sum[path] = self._latency_sum.get(path, 0.0) + elapsed

    def rejected(self) -> None:
        with self._lock:
            self._rejected += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "uptime_seconds": round(time.time() - self.started_at, 3),
                "active_requests": self._active,
                "rejected_requests": self._rejected,
                "requests": {f"{p}|{s}": n for (p, s), n in self._requests.items()},
            }

    def prometheus(self) -> str:
        with self._lock:
            lines = [
                "# TYPE jarvis_uptime_seconds gauge",
                f"jarvis_uptime_seconds {time.time() - self.started_at:.3f}",
                "# TYPE jarvis_active_requests gauge",
                f"jarvis_active_requests {self._active}",
                "# TYPE jarvis_rejected_requests_total counter",
                f"jarvis_rejected_requests_total {self._rejected}",
                "# TYPE jarvis_http_requests_total counter",
            ]
            for (path, status), count in sorted(self._requests.items()):
                safe_path = path.replace('\\', '\\\\').replace('"', '\\"')
                lines.append(
                    f'jarvis_http_requests_total{{path="{safe_path}",status="{status}"}} {count}'
                )
            return "\n".join(lines) + "\n"


class ConfirmationGuard:
    """Single-use, short-lived confirmations for state-changing operations."""

    _SENSITIVE_ACTIONS = {
        "/api/clear": {"*"},
        "/api/enroll": {"*"},
        "/api/desktop": {"command"},
        "/api/smarthome": {"control", "scene", "add_device", "remove_device"},
        "/api/calendar": {"add"},
        "/api/memory": {"set_profile", "save_place", "set_pref"},
        "/api/booking": {"checkout"},
    }

    def __init__(self, enabled: bool = True, ttl_seconds: int = 120) -> None:
        self.enabled = enabled
        self.ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._pending: dict[str, tuple[float, str]] = {}

    @staticmethod
    def _fingerprint(path: str, payload: dict[str, Any]) -> str:
        clean = {k: v for k, v in payload.items() if k != "confirmation_token"}
        raw = path + "\n" + json.dumps(clean, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def check(self, path: str, payload: dict[str, Any]) -> tuple[bool, str | None]:
        if not self.enabled:
            return True, None
        actions = self._SENSITIVE_ACTIONS.get(path)
        action = str(payload.get("action") or "command").lower()
        if not actions or ("*" not in actions and action not in actions):
            return True, None

        fingerprint = self._fingerprint(path, payload)
        supplied = str(payload.get("confirmation_token") or "")
        now = time.time()
        with self._lock:
            self._pending = {k: v for k, v in self._pending.items() if v[0] > now}
            pending = self._pending.pop(supplied, None) if supplied else None
            if pending and pending[0] > now and hmac.compare_digest(pending[1], fingerprint):
                return True, None
            token = secrets.token_urlsafe(24)
            self._pending[token] = (now + self.ttl_seconds, fingerprint)
            return False, token


class BoundedThreadingHTTPServer(ThreadingHTTPServer):
    """Threaded HTTP server with a hard cap on concurrent request threads."""

    daemon_threads = True
    block_on_close = False
    allow_reuse_address = True

    def __init__(self, server_address, handler_class, max_workers: int, metrics: Metrics):
        self._slots = threading.BoundedSemaphore(max_workers)
        self.metrics = metrics
        self.request_queue_size = max_workers
        super().__init__(server_address, handler_class)

    def process_request(self, request, client_address):
        if not self._slots.acquire(blocking=False):
            self.metrics.rejected()
            try:
                body = b'{"error":"server is at capacity"}'
                headers = (
                    b"HTTP/1.1 503 Service Unavailable\r\n"
                    b"Content-Type: application/json\r\n"
                    b"Connection: close\r\n"
                    + f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
                )
                request.sendall(headers + body)
            finally:
                self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._slots.release()


def validate_payload(value: Any, max_text_chars: int, *, key: str = "", depth: int = 0) -> None:
    if depth > 12:
        raise ValueError("JSON nesting is too deep")
    if isinstance(value, dict):
        if len(value) > 100:
            raise ValueError("too many JSON fields")
        for child_key, child in value.items():
            if not isinstance(child_key, str) or len(child_key) > 100:
                raise ValueError("invalid JSON field name")
            validate_payload(child, max_text_chars, key=child_key, depth=depth + 1)
    elif isinstance(value, list):
        if len(value) > 1000:
            raise ValueError("JSON list is too large")
        for child in value:
            validate_payload(child, max_text_chars, key=key, depth=depth + 1)
    elif isinstance(value, str):
        limit = 12 * 1024 * 1024 if key in {"image_b64", "imageData"} else max_text_chars
        if len(value) > limit:
            raise ValueError(f"field '{key or 'value'}' is too long")


def redacted_text(text: str, include_content: bool) -> str:
    text = str(text or "")
    if include_content:
        return text[:2000]
    digest = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:12]
    return f"<redacted length={len(text)} sha256={digest}>"
