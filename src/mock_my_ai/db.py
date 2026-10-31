"""SQLite persistence for console users, API keys, IP allowlists, custom models."""
from __future__ import annotations

import hashlib
import ipaddress
import secrets
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

_lock = threading.Lock()
_db_path: Path | None = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def configure_db(path: Path) -> None:
    global _db_path
    _db_path = path
    path.parent.mkdir(parents=True, exist_ok=True)
    init_db()


def get_db_path() -> Path:
    if _db_path is None:
        from mock_my_ai.config import get_config

        configure_db(get_config().db_path())
    assert _db_path is not None
    return _db_path


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    path = get_db_path()
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with _lock, connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                display_name TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL DEFAULT 'default',
                key_prefix TEXT NOT NULL,
                key_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                revoked_at TEXT
            );
            CREATE TABLE IF NOT EXISTS ip_whitelist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                cidr TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, cidr)
            );
            CREATE TABLE IF NOT EXISTS custom_models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                model_id TEXT NOT NULL,
                family TEXT NOT NULL DEFAULT 'openai',
                owned_by TEXT NOT NULL DEFAULT 'custom',
                parameter_count TEXT,
                context_window INTEGER,
                features_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, model_id)
            );
            CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
            CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
            CREATE INDEX IF NOT EXISTS idx_ip_user ON ip_whitelist(user_id);
            CREATE INDEX IF NOT EXISTS idx_models_user ON custom_models(user_id);
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS request_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                method TEXT NOT NULL,
                path TEXT NOT NULL,
                status INTEGER,
                latency_ms INTEGER,
                model TEXT,
                key_prefix TEXT,
                client_ip TEXT,
                stream INTEGER NOT NULL DEFAULT 0,
                request_body TEXT,
                response_summary TEXT,
                response_body TEXT,
                user_id INTEGER,
                api_key_id INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_request_logs_created ON request_logs(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_request_logs_prefix ON request_logs(key_prefix, id DESC);
            -- idx_request_logs_user / idx_request_logs_key created in _migrate_request_logs
            -- after ALTER ADD COLUMN on existing DBs (CREATE TABLE IF NOT EXISTS is a no-op).
            """
        )
        _migrate_request_logs(conn)


# ── password / key hashing ──────────────────────────────────────────

def hash_password(password: str) -> str:
    import bcrypt

    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    import bcrypt

    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_api_key(prefix: str = "sk-mock-") -> tuple[str, str, str]:
    """Return (raw_key, display_prefix, key_hash)."""
    secret = secrets.token_hex(24)
    raw = f"{prefix}{secret}"
    display = f"{prefix}{secret[:4]}…{secret[-4:]}"
    return raw, display, hash_api_key(raw)


# ── users ───────────────────────────────────────────────────────────

def create_user(email: str, password: str, display_name: str | None = None) -> dict[str, Any]:
    email = email.strip().lower()
    if not email or "@" not in email:
        raise ValueError("invalid_email")
    if len(password) < 8:
        raise ValueError("password_too_short")
    now = _utc_now()
    pw = hash_password(password)
    with _lock, connect() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO users (email, password_hash, display_name, created_at) VALUES (?, ?, ?, ?)",
                (email, pw, display_name or email.split("@")[0], now),
            )
        except sqlite3.IntegrityError as e:
            raise ValueError("email_taken") from e
        uid = int(cur.lastrowid)
    return get_user_by_id(uid)  # type: ignore[return-value]


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT id, email, display_name, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def get_user_by_email(email: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT id, email, password_hash, display_name, created_at FROM users WHERE email = ?",
            (email.strip().lower(),),
        ).fetchone()
    return dict(row) if row else None


def authenticate_user(email: str, password: str) -> dict[str, Any] | None:
    user = get_user_by_email(email)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return {k: v for k, v in user.items() if k != "password_hash"}


# ── API keys ────────────────────────────────────────────────────────

def create_api_key(user_id: int, name: str = "default", prefix: str = "sk-mock-") -> dict[str, Any]:
    raw, display, key_hash = generate_api_key(prefix)
    now = _utc_now()
    with _lock, connect() as conn:
        cur = conn.execute(
            """INSERT INTO api_keys (user_id, name, key_prefix, key_hash, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, name.strip() or "default", display, key_hash, now),
        )
        kid = int(cur.lastrowid)
    return {
        "id": kid,
        "user_id": user_id,
        "name": name.strip() or "default",
        "key_prefix": display,
        "created_at": now,
        "revoked_at": None,
        "raw_key": raw,  # only returned once
    }


def list_api_keys(user_id: int, include_revoked: bool = False) -> list[dict[str, Any]]:
    with connect() as conn:
        if include_revoked:
            rows = conn.execute(
                "SELECT id, user_id, name, key_prefix, created_at, revoked_at FROM api_keys WHERE user_id = ? ORDER BY id DESC",
                (user_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT id, user_id, name, key_prefix, created_at, revoked_at FROM api_keys
                   WHERE user_id = ? AND revoked_at IS NULL ORDER BY id DESC""",
                (user_id,),
            ).fetchall()
    return [dict(r) for r in rows]


def revoke_api_key(user_id: int, key_id: int) -> bool:
    now = _utc_now()
    with _lock, connect() as conn:
        cur = conn.execute(
            "UPDATE api_keys SET revoked_at = ? WHERE id = ? AND user_id = ? AND revoked_at IS NULL",
            (now, key_id, user_id),
        )
        return cur.rowcount > 0


def resolve_api_key(raw_key: str) -> dict[str, Any] | None:
    """Return key+user info if active DB key matches."""
    if not raw_key:
        return None
    h = hash_api_key(raw_key)
    with connect() as conn:
        row = conn.execute(
            """SELECT k.id AS key_id, k.user_id, k.name, k.key_prefix, k.revoked_at,
                      u.email, u.display_name
               FROM api_keys k JOIN users u ON u.id = k.user_id
               WHERE k.key_hash = ?""",
            (h,),
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    if d.get("revoked_at"):
        return None
    return d


# ── IP whitelist ────────────────────────────────────────────────────

def list_ip_whitelist(user_id: int) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, user_id, cidr, created_at FROM ip_whitelist WHERE user_id = ? ORDER BY id",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def add_ip_whitelist(user_id: int, cidr: str) -> dict[str, Any]:
    cidr = cidr.strip()
    # Validate
    try:
        if "/" in cidr:
            ipaddress.ip_network(cidr, strict=False)
        else:
            ipaddress.ip_address(cidr)
    except ValueError as e:
        raise ValueError("invalid_cidr") from e
    now = _utc_now()
    with _lock, connect() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO ip_whitelist (user_id, cidr, created_at) VALUES (?, ?, ?)",
                (user_id, cidr, now),
            )
        except sqlite3.IntegrityError as e:
            raise ValueError("duplicate_cidr") from e
        wid = int(cur.lastrowid)
    return {"id": wid, "user_id": user_id, "cidr": cidr, "created_at": now}


def remove_ip_whitelist(user_id: int, entry_id: int) -> bool:
    with _lock, connect() as conn:
        cur = conn.execute(
            "DELETE FROM ip_whitelist WHERE id = ? AND user_id = ?",
            (entry_id, user_id),
        )
        return cur.rowcount > 0


def ip_allowed_for_user(user_id: int, client_ip: str | None) -> bool:
    entries = list_ip_whitelist(user_id)
    if not entries:
        return True  # empty = allow all
    if not client_ip:
        return False
    try:
        addr = ipaddress.ip_address(client_ip.split("%")[0].strip())
    except ValueError:
        return False
    for e in entries:
        cidr = e["cidr"]
        try:
            if "/" in cidr:
                if addr in ipaddress.ip_network(cidr, strict=False):
                    return True
            else:
                if addr == ipaddress.ip_address(cidr):
                    return True
        except ValueError:
            continue
    return False


# ── custom models ───────────────────────────────────────────────────

def list_custom_models(user_id: int | None = None) -> list[dict[str, Any]]:
    import json

    with connect() as conn:
        if user_id is None:
            rows = conn.execute(
                """SELECT id, user_id, model_id, family, owned_by, parameter_count,
                          context_window, features_json, created_at, updated_at
                   FROM custom_models ORDER BY id DESC"""
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT id, user_id, model_id, family, owned_by, parameter_count,
                          context_window, features_json, created_at, updated_at
                   FROM custom_models WHERE user_id = ? ORDER BY id DESC""",
                (user_id,),
            ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["features"] = json.loads(d.pop("features_json") or "{}")
        except Exception:
            d["features"] = {}
            d.pop("features_json", None)
        out.append(d)
    return out


def upsert_custom_model(
    user_id: int,
    model_id: str,
    *,
    family: str = "openai",
    owned_by: str = "custom",
    parameter_count: str | None = None,
    context_window: int | None = None,
    features: dict[str, Any] | None = None,
    row_id: int | None = None,
) -> dict[str, Any]:
    import json

    model_id = model_id.strip()
    if not model_id:
        raise ValueError("model_id_required")
    family = family.strip() or "openai"
    if family not in ("openai", "anthropic", "gemini", "deepseek"):
        raise ValueError("invalid_family")
    now = _utc_now()
    feats = json.dumps(features or {})
    with _lock, connect() as conn:
        if row_id is not None:
            cur = conn.execute(
                """UPDATE custom_models SET model_id=?, family=?, owned_by=?, parameter_count=?,
                   context_window=?, features_json=?, updated_at=?
                   WHERE id=? AND user_id=?""",
                (
                    model_id,
                    family,
                    owned_by or "custom",
                    parameter_count,
                    context_window,
                    feats,
                    now,
                    row_id,
                    user_id,
                ),
            )
            if cur.rowcount == 0:
                raise ValueError("not_found")
            rid = row_id
        else:
            try:
                cur = conn.execute(
                    """INSERT INTO custom_models
                       (user_id, model_id, family, owned_by, parameter_count, context_window,
                        features_json, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        user_id,
                        model_id,
                        family,
                        owned_by or "custom",
                        parameter_count,
                        context_window,
                        feats,
                        now,
                        now,
                    ),
                )
            except sqlite3.IntegrityError as e:
                raise ValueError("model_id_taken") from e
            rid = int(cur.lastrowid)
    models = list_custom_models(user_id)
    for m in models:
        if m["id"] == rid:
            return m
    raise RuntimeError("upsert_failed")


def delete_custom_model(user_id: int, row_id: int) -> bool:
    with _lock, connect() as conn:
        cur = conn.execute(
            "DELETE FROM custom_models WHERE id = ? AND user_id = ?",
            (row_id, user_id),
        )
        return cur.rowcount > 0

# ── app settings ────────────────────────────────────────────────────

def get_app_setting(key: str, default: str | None = None) -> str | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = ?",
            (key,),
        ).fetchone()
    if not row:
        return default
    return str(row["value"])


def set_app_setting(key: str, value: str) -> None:
    now = _utc_now()
    with _lock, connect() as conn:
        conn.execute(
            """INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
            (key, value, now),
        )


def get_search_enabled() -> bool:
    """Console switch for mock search citations; falls back to YAML default."""
    from mock_my_ai.config import get_config

    raw = get_app_setting("search_enabled")
    if raw is None:
        return bool(get_config().generation.search_enabled_default)
    return raw.strip().lower() in ("1", "true", "yes", "on")


def set_search_enabled(enabled: bool) -> None:
    set_app_setting("search_enabled", "1" if enabled else "0")


# ── request logs ────────────────────────────────────────────────────

_REQUEST_LOG_MAX_AGE_HOURS = 6
_REQUEST_LOG_MAX_PER_KEY = 20
_REQUEST_BODY_MAX = 100_000
_RESPONSE_BODY_MAX = 100_000
_RESPONSE_SUMMARY_MAX = 4000

_LOG_SELECT = """id, created_at, method, path, status, latency_ms, model,
                 key_prefix, client_ip, stream, request_body, response_summary,
                 response_body, user_id, api_key_id"""


def _migrate_request_logs(conn: sqlite3.Connection) -> None:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(request_logs)").fetchall()}
    alters = []
    if "response_body" not in cols:
        alters.append("ALTER TABLE request_logs ADD COLUMN response_body TEXT")
    if "user_id" not in cols:
        alters.append("ALTER TABLE request_logs ADD COLUMN user_id INTEGER")
    if "api_key_id" not in cols:
        alters.append("ALTER TABLE request_logs ADD COLUMN api_key_id INTEGER")
    for sql in alters:
        conn.execute(sql)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_request_logs_user ON request_logs(user_id, id DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_request_logs_key ON request_logs(api_key_id, id DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_request_logs_prefix ON request_logs(key_prefix, id DESC)"
    )


def _truncate(s: str | None, n: int) -> str | None:
    if s is None:
        return None
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"


def _prune_request_logs(
    conn: sqlite3.Connection,
    *,
    api_key_id: int | None,
    key_prefix: str | None,
) -> None:
    from datetime import timedelta

    cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=_REQUEST_LOG_MAX_AGE_HOURS)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute("DELETE FROM request_logs WHERE created_at < ?", (cutoff,))

    # Per-key cap: prefer api_key_id; fall back to key_prefix for sample/prefix keys
    if api_key_id is not None:
        conn.execute(
            """DELETE FROM request_logs WHERE api_key_id = ? AND id NOT IN (
                 SELECT id FROM request_logs WHERE api_key_id = ?
                 ORDER BY id DESC LIMIT ?
               )""",
            (api_key_id, api_key_id, _REQUEST_LOG_MAX_PER_KEY),
        )
    elif key_prefix:
        conn.execute(
            """DELETE FROM request_logs
               WHERE api_key_id IS NULL AND key_prefix = ? AND id NOT IN (
                 SELECT id FROM request_logs
                 WHERE api_key_id IS NULL AND key_prefix = ?
                 ORDER BY id DESC LIMIT ?
               )""",
            (key_prefix, key_prefix, _REQUEST_LOG_MAX_PER_KEY),
        )


def insert_request_log(
    *,
    method: str,
    path: str,
    status: int | None,
    latency_ms: int | None,
    model: str | None = None,
    key_prefix: str | None = None,
    client_ip: str | None = None,
    stream: bool = False,
    request_body: str | None = None,
    response_summary: str | None = None,
    response_body: str | None = None,
    user_id: int | None = None,
    api_key_id: int | None = None,
) -> int:
    now = _utc_now()
    with _lock, connect() as conn:
        cur = conn.execute(
            """INSERT INTO request_logs
               (created_at, method, path, status, latency_ms, model, key_prefix,
                client_ip, stream, request_body, response_summary, response_body,
                user_id, api_key_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                now,
                method,
                path,
                status,
                latency_ms,
                model,
                key_prefix,
                client_ip,
                1 if stream else 0,
                _truncate(request_body, _REQUEST_BODY_MAX),
                _truncate(response_summary, _RESPONSE_SUMMARY_MAX),
                _truncate(response_body, _RESPONSE_BODY_MAX),
                user_id,
                api_key_id,
            ),
        )
        rid = int(cur.lastrowid)
        _prune_request_logs(conn, api_key_id=api_key_id, key_prefix=key_prefix)
    return rid


def list_request_logs(
    limit: int = 100,
    *,
    user_id: int | None = None,
) -> list[dict[str, Any]]:
    """List logs newest-first. When user_id is set, only that user's key traffic."""
    limit = max(1, min(500, int(limit)))
    with connect() as conn:
        if user_id is None:
            rows = conn.execute(
                f"SELECT {_LOG_SELECT} FROM request_logs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                f"""SELECT {_LOG_SELECT} FROM request_logs
                    WHERE user_id = ?
                    ORDER BY id DESC LIMIT ?""",
                (int(user_id), limit),
            ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["stream"] = bool(d.get("stream"))
        out.append(d)
    return out


def get_request_log(log_id: int, *, user_id: int | None = None) -> dict[str, Any] | None:
    with connect() as conn:
        if user_id is None:
            row = conn.execute(
                f"SELECT {_LOG_SELECT} FROM request_logs WHERE id = ?",
                (log_id,),
            ).fetchone()
        else:
            row = conn.execute(
                f"SELECT {_LOG_SELECT} FROM request_logs WHERE id = ? AND user_id = ?",
                (log_id, int(user_id)),
            ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["stream"] = bool(d.get("stream"))
    return d


def clear_request_logs(*, user_id: int | None = None) -> int:
    """Clear logs. When user_id is set, only that user's rows are removed."""
    with _lock, connect() as conn:
        if user_id is None:
            cur = conn.execute("DELETE FROM request_logs")
        else:
            cur = conn.execute("DELETE FROM request_logs WHERE user_id = ?", (int(user_id),))
        return cur.rowcount

