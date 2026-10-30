from __future__ import annotations

from fastapi import Header, HTTPException, Request

from mock_my_ai.config import AppConfig, get_config


def _extract_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return authorization.strip()


def client_ip_from_request(request: Request) -> str | None:
    """Prefer proxy headers set by nginx, then direct client."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        # leftmost is original client
        return xff.split(",")[0].strip()
    xri = request.headers.get("x-real-ip")
    if xri:
        return xri.strip()
    if request.client:
        return request.client.host
    return None


def is_sample_key(key: str, cfg: AppConfig) -> bool:
    return key in set(cfg.auth.sample_keys.values())


def key_looks_valid(key: str, cfg: AppConfig) -> bool:
    """Legacy format helper — sample exact, optional prefix, or any non-empty for tests."""
    if not key:
        return False
    if is_sample_key(key, cfg):
        return True
    if cfg.auth.accept_prefix_keys and any(key.startswith(p) for p in cfg.auth.accepted_prefixes):
        return True
    return False


def resolve_key(key: str, cfg: AppConfig) -> dict | None:
    """
    Resolve API key to a context dict:
      {"kind": "sample"|"db"|"prefix", "user_id": int|None, "raw": key, ...}
    """
    if not key:
        return None
    if is_sample_key(key, cfg):
        return {"kind": "sample", "user_id": None, "raw": key}

    from mock_my_ai.db import resolve_api_key

    db_key = resolve_api_key(key)
    if db_key:
        return {"kind": "db", "user_id": db_key["user_id"], "raw": key, **db_key}

    if cfg.auth.accept_prefix_keys and any(key.startswith(p) for p in cfg.auth.accepted_prefixes):
        return {"kind": "prefix", "user_id": None, "raw": key}

    return None


async def require_api_key(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
    x_goog_api_key: str | None = Header(default=None, alias="x-goog-api-key"),
) -> str | None:
    """Validate API key (sample / console DB / optional prefix) and enforce IP allowlist."""
    cfg = get_config()
    if not cfg.auth.require_api_key:
        return None

    key = x_api_key or x_goog_api_key or _extract_bearer(authorization)
    if not key:
        key = request.query_params.get("key")

    ctx = resolve_key(key or "", cfg) if key else None
    if not ctx:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "message": (
                        "Invalid API key. Use a documented sample key "
                        "(e.g. sk-mock-openai-demo-key-...), a key created in the console, "
                        "or (if enabled) any key matching accepted prefixes."
                    ),
                    "type": "invalid_request_error",
                    "code": "invalid_api_key",
                }
            },
        )

    # IP allowlist for console keys
    user_id = ctx.get("user_id")
    if user_id is not None:
        from mock_my_ai.db import ip_allowed_for_user

        client_ip = client_ip_from_request(request)
        if not ip_allowed_for_user(int(user_id), client_ip):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": {
                        "message": (
                            f"Client IP {client_ip or '(unknown)'} is not on this key owner's allowlist."
                        ),
                        "type": "invalid_request_error",
                        "code": "ip_not_allowed",
                    }
                },
            )

    # Stash for downstream if needed
    request.state.api_key_ctx = ctx
    return ctx["raw"]
