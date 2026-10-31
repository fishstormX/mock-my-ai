"""Middleware: log mock generation API calls to SQLite for the console."""
from __future__ import annotations

import json
import re
import time
from typing import Any, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

_GEN_PATHS = {
    "/v1/chat/completions",
    "/v1/completions",
    "/v1/responses",
    "/v1/messages",
    "/anthropic/v1/messages",
}
_GENERATE_CONTENT_RE = re.compile(r":generateContent$")


def should_log_request(method: str, path: str) -> bool:
    if method.upper() != "POST":
        return False
    if path in _GEN_PATHS:
        return True
    if _GENERATE_CONTENT_RE.search(path) and (
        path.startswith("/v1beta/") or path.startswith("/gemini/")
    ):
        return True
    return False


def _raw_key_from_headers(request: Request) -> str | None:
    raw = (
        request.headers.get("x-api-key")
        or request.headers.get("x-goog-api-key")
        or ""
    )
    if not raw:
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            raw = auth[7:].strip()
        elif auth:
            raw = auth.strip()
    if not raw:
        raw = request.query_params.get("key") or ""
    return raw or None


def _key_prefix(raw: str | None) -> str | None:
    if not raw:
        return None
    if len(raw) <= 12:
        return raw[:4] + "…"
    return raw[:10] + "…" + raw[-4:]


def _resolve_log_key(request: Request) -> dict[str, Any]:
    """Return key_prefix / user_id / api_key_id for request logging (never raw secret)."""
    raw = _raw_key_from_headers(request)
    prefix = _key_prefix(raw)
    out: dict[str, Any] = {
        "key_prefix": prefix,
        "user_id": None,
        "api_key_id": None,
    }
    if not raw:
        return out
    try:
        from mock_my_ai.auth import resolve_key
        from mock_my_ai.config import get_config

        ctx = resolve_key(raw, get_config())
    except Exception:
        ctx = None
    if not ctx:
        return out
    if ctx.get("kind") == "db":
        out["user_id"] = ctx.get("user_id")
        out["api_key_id"] = ctx.get("key_id")
        # Prefer console display prefix when available
        if ctx.get("key_prefix"):
            out["key_prefix"] = ctx["key_prefix"]
    return out


def _client_ip(request: Request) -> str | None:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    xri = request.headers.get("x-real-ip")
    if xri:
        return xri.strip()
    if request.client:
        return request.client.host
    return None


def _summarize_response(body: bytes, stream: bool) -> str:
    if stream:
        return json.dumps({"stream": True}, ensure_ascii=False)
    if not body:
        return ""
    try:
        data = json.loads(body.decode("utf-8", errors="replace"))
    except Exception:
        text = body.decode("utf-8", errors="replace")
        return text[:500]

    summary: dict[str, Any] = {}
    if isinstance(data, dict):
        # Anthropic
        if data.get("type") == "message":
            summary["stop_reason"] = data.get("stop_reason")
            types = [b.get("type") for b in (data.get("content") or []) if isinstance(b, dict)]
            summary["content_types"] = types
            summary["tool_use"] = "tool_use" in types
            for b in data.get("content") or []:
                if isinstance(b, dict) and b.get("type") == "text":
                    summary["text_preview"] = str(b.get("text") or "")[:200]
                    break
        # OpenAI chat
        elif data.get("object") == "chat.completion":
            choice = (data.get("choices") or [{}])[0]
            summary["finish_reason"] = choice.get("finish_reason")
            msg = choice.get("message") or {}
            summary["tool_use"] = bool(msg.get("tool_calls"))
            if msg.get("content"):
                summary["text_preview"] = str(msg["content"])[:200]
        # OpenAI responses
        elif data.get("object") == "response":
            summary["status"] = data.get("status")
            outs = data.get("output") or []
            summary["tool_use"] = any(
                isinstance(o, dict) and o.get("type") == "function_call" for o in outs
            )
        # Gemini
        elif "candidates" in data:
            parts = (
                ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
            )
            summary["tool_use"] = any(
                isinstance(p, dict) and "functionCall" in p for p in parts
            )
            for p in parts:
                if isinstance(p, dict) and p.get("text"):
                    summary["text_preview"] = str(p["text"])[:200]
                    break

        meta = data.get("mock_my_ai") or {}
        if isinstance(meta, dict):
            summary["lang"] = meta.get("lang")
            summary["search"] = bool(meta.get("search_results"))
            if meta.get("tool_rounds"):
                summary["tool_rounds"] = len(meta["tool_rounds"])
            if not summary.get("text_preview") and meta.get("text"):
                summary["text_preview"] = str(meta["text"])[:200]

    return json.dumps(summary, ensure_ascii=False)


def _extract_model(req_json: Any) -> str | None:
    if not isinstance(req_json, dict):
        return None
    m = req_json.get("model")
    return str(m) if m else None


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if not should_log_request(request.method, path):
            return await call_next(request)

        t0 = time.perf_counter()
        raw_body = await request.body()
        req_json: Any = None
        req_text = ""
        if raw_body:
            try:
                req_json = json.loads(raw_body.decode("utf-8"))
                req_text = json.dumps(req_json, ensure_ascii=False)
            except Exception:
                req_text = raw_body.decode("utf-8", errors="replace")[:4000]

        stream_flag = bool(isinstance(req_json, dict) and req_json.get("stream"))
        model = _extract_model(req_json)
        # Gemini model is often in the path
        if not model and ":generateContent" in path:
            # /v1beta/models/{model}:generateContent
            m = re.search(r"/models/([^/:]+):generateContent", path)
            if m:
                model = m.group(1)

        key_meta = _resolve_log_key(request)
        client_ip = _client_ip(request)

        response = await call_next(request)
        latency_ms = int((time.perf_counter() - t0) * 1000)

        # Collect body for non-streaming JSON; leave streaming alone
        media = response.headers.get("content-type", "")
        is_sse = "text/event-stream" in media or stream_flag

        if is_sse:
            summary = _summarize_response(b"", stream=True)
            stream_body = json.dumps({"stream": True, "note": "SSE body not buffered"}, ensure_ascii=False)
            self._persist(
                method=request.method,
                path=path,
                status=response.status_code,
                latency_ms=latency_ms,
                model=model,
                key_prefix=key_meta["key_prefix"],
                client_ip=client_ip,
                stream=True,
                request_body=req_text,
                response_summary=summary,
                response_body=stream_body,
                user_id=key_meta["user_id"],
                api_key_id=key_meta["api_key_id"],
            )
            return response

        # Buffer response body
        body_parts: list[bytes] = []
        async for chunk in response.body_iterator:
            if isinstance(chunk, str):
                chunk = chunk.encode("utf-8")
            body_parts.append(chunk)
        resp_body = b"".join(body_parts)
        summary = _summarize_response(resp_body, stream=False)
        resp_text = ""
        if resp_body:
            try:
                resp_text = json.dumps(
                    json.loads(resp_body.decode("utf-8", errors="replace")),
                    ensure_ascii=False,
                )
            except Exception:
                resp_text = resp_body.decode("utf-8", errors="replace")
        self._persist(
            method=request.method,
            path=path,
            status=response.status_code,
            latency_ms=latency_ms,
            model=model,
            key_prefix=key_meta["key_prefix"],
            client_ip=client_ip,
            stream=False,
            request_body=req_text,
            response_summary=summary,
            response_body=resp_text,
            user_id=key_meta["user_id"],
            api_key_id=key_meta["api_key_id"],
        )

        headers = dict(response.headers)
        headers.pop("content-length", None)
        return Response(
            content=resp_body,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
            background=response.background,
        )

    @staticmethod
    def _persist(**kwargs: Any) -> None:
        try:
            from mock_my_ai.db import insert_request_log

            insert_request_log(**kwargs)
        except Exception:
            # Logging must never break the API
            pass
