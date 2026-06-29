from __future__ import annotations

import hmac
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from .runtime import FactorRuntime, RuntimeConflictError

MAX_REQUEST_BYTES = 5 * 1024 * 1024


class FactorHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        runtime: FactorRuntime,
        *,
        admin_token: str,
        ingest_token: str,
    ) -> None:
        if not admin_token or not ingest_token:
            raise ValueError("admin_token and ingest_token are required")
        super().__init__(address, FactorRequestHandler)
        self.runtime = runtime
        self.admin_token = admin_token
        self.ingest_token = ingest_token


class FactorRequestHandler(BaseHTTPRequestHandler):
    server: FactorHTTPServer
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/health":
            self._send(HTTPStatus.OK, self.server.runtime.health())
        elif path == "/v1/factors":
            self._send(HTTPStatus.OK, self.server.runtime.factor_manifest())
        elif path == "/v1/snapshot":
            self._send(HTTPStatus.OK, self.server.runtime.snapshot())
        else:
            self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            if path == "/v1/market/bars":
                self._require_token("X-Ingest-Token", self.server.ingest_token)
                payload = self._read_json()
                bars = (
                    payload if isinstance(payload, list) else payload.get("bars") if isinstance(payload, dict) else None
                )
                if bars is None and isinstance(payload, dict):
                    bars = [payload]
                if not isinstance(bars, list):
                    raise ValueError("Request must be a market bar or an object containing a bars list")
                self._send(HTTPStatus.OK, self.server.runtime.ingest(bars))
            elif path == "/v1/admin/reload":
                self._require_token("X-Admin-Token", self.server.admin_token)
                payload = self._read_json()
                generation = _required_generation(payload)
                self._send(HTTPStatus.OK, self.server.runtime.reload(expected_generation=generation))
            else:
                self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
        except PermissionError as exc:
            self.close_connection = True
            self._send(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized", "detail": str(exc)})
        except RuntimeConflictError as exc:
            self._send(HTTPStatus.CONFLICT, {"error": "generation_conflict", "detail": str(exc)})
        except (json.JSONDecodeError, ValueError) as exc:
            self._send(HTTPStatus.BAD_REQUEST, {"error": "invalid_request", "detail": str(exc)})

    def do_PUT(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            if path != "/v1/admin/factors":
                if path != "/v1/admin/config":
                    self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                    return
            self._require_token("X-Admin-Token", self.server.admin_token)
            payload = self._read_json()
            factors = payload.get("factors") if isinstance(payload, dict) else None
            if not isinstance(factors, list):
                raise ValueError("factors must be a list")
            generation = _required_generation(payload)
            if path == "/v1/admin/config":
                strategies = payload.get("strategies")
                if not isinstance(strategies, list):
                    raise ValueError("strategies must be a list")
                result = self.server.runtime.replace_config(
                    factors,
                    strategies,
                    expected_generation=generation,
                )
            else:
                result = self.server.runtime.replace_factors(factors, expected_generation=generation)
            self._send(HTTPStatus.OK, result)
        except PermissionError as exc:
            self.close_connection = True
            self._send(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized", "detail": str(exc)})
        except RuntimeConflictError as exc:
            self._send(HTTPStatus.CONFLICT, {"error": "generation_conflict", "detail": str(exc)})
        except (json.JSONDecodeError, ValueError) as exc:
            self._send(HTTPStatus.BAD_REQUEST, {"error": "invalid_request", "detail": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}", flush=True)

    def _require_token(self, header: str, expected: str) -> None:
        supplied = self.headers.get(header, "")
        if not hmac.compare_digest(supplied, expected):
            raise PermissionError(f"A valid {header} header is required")

    def _read_json(self) -> Any:
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            raise ValueError("Content-Length is required")
        length = int(raw_length)
        if length < 0 or length > MAX_REQUEST_BYTES:
            raise ValueError(f"Request body must not exceed {MAX_REQUEST_BYTES} bytes")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _send(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=True, allow_nan=False).encode("utf-8")
        self.send_response(int(status))
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if self.close_connection:
            self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)


def _required_generation(payload: Any) -> int:
    if not isinstance(payload, dict) or "expected_generation" not in payload:
        raise ValueError("expected_generation is required")
    generation = int(payload["expected_generation"])
    if generation < 0:
        raise ValueError("expected_generation must not be negative")
    return generation
