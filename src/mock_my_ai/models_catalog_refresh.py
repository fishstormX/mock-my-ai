"""Fetch / cache / map model catalogs from models.dev."""

from __future__ import annotations

import json
import logging
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_SOURCE = "https://models.dev/api.json"
DEFAULT_CACHE_REL = "data/models_catalog_cache.json"
DEFAULT_TTL_HOURS = 24
FETCH_TIMEOUT_S = 30

# Hard denylist (obsolete even if models.dev still lists them as active).
OBSOLETE_DENYLIST = frozenset(
    {
        "gpt-3.5-turbo",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
        "gemini-pro",
        "gemini-1.5-flash-8b",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "chatgpt-4o-latest",  # alias churn; prefer gpt-4o
    }
)

# Drop non-chat / specialty ids by pattern.
_DROP_ID_RE = re.compile(
    r"(embedding|tts|realtime|lyria|imagen|dall-?e|deep-research|"
    r"-image(?:-|$)|canvas|whisper|transcribe|moderation|"
    r"-live(?:-|$)|omni-flash)",
    re.I,
)

# Prefer keeping these when present and not deprecated (after filter).
POPULAR_BY_PROVIDER: dict[str, list[str]] = {
    "openai": [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4.1",
        "gpt-4.1-mini",
        "o3",
        "o4-mini",
        "gpt-5",
        "gpt-5-mini",
        "gpt-5.4",
        "gpt-5.6",
    ],
    "anthropic": [
        "claude-sonnet-4-5",
        "claude-haiku-4-5",
        "claude-opus-4-5",
        "claude-sonnet-4-6",
        "claude-opus-4-6",
        "claude-sonnet-5",
        "claude-haiku-5-5",
    ],
    "google": [
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-pro-latest",
        "gemini-flash-latest",
        "gemini-3.5-flash",
    ],
    "deepseek": [
        "deepseek-flash",
        "deepseek-v4-pro",
        "deepseek-chat",
        "deepseek-reasoner",
    ],
}

CAPS = {"openai": 40, "anthropic": 20, "gemini": 20}

_lock = threading.RLock()
_refresh_lock = threading.Lock()
_state: dict[str, Any] = {
    "openai": None,
    "anthropic": None,
    "gemini": None,
    "meta": None,
    "loaded": False,
}
_bg_thread: threading.Thread | None = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _cfg_catalog() -> dict[str, Any]:
    try:
        from mock_my_ai.config import get_config

        m = get_config().models
        return {
            "source": getattr(m, "catalog_source", None) or DEFAULT_SOURCE,
            "cache_path": getattr(m, "catalog_cache_path", None) or DEFAULT_CACHE_REL,
            "ttl_hours": float(getattr(m, "catalog_ttl_hours", None) or DEFAULT_TTL_HOURS),
            "auto_refresh": bool(getattr(m, "catalog_auto_refresh", True)),
        }
    except Exception:
        return {
            "source": DEFAULT_SOURCE,
            "cache_path": DEFAULT_CACHE_REL,
            "ttl_hours": float(DEFAULT_TTL_HOURS),
            "auto_refresh": True,
        }


def cache_path() -> Path:
    cfg = _cfg_catalog()
    p = Path(cfg["cache_path"])
    return p if p.is_absolute() else _project_root() / p


def map_model_entry(model_id: str, meta: dict[str, Any], owned_by: str) -> dict[str, Any]:
    """Map one models.dev entry to our public catalog shape."""
    mods = meta.get("modalities") or {}
    inp = mods.get("input") or []
    limit = meta.get("limit") or {}
    ctx = limit.get("context") if limit.get("context") is not None else limit.get("input")
    try:
        context_window = int(ctx) if ctx is not None else 128000
    except (TypeError, ValueError):
        context_window = 128000
    multimodal = bool(meta.get("attachment")) or ("image" in inp)
    return {
        "id": model_id,
        "owned_by": owned_by,
        "parameter_count": "unknown",
        "context_window": context_window,
        "features": {
            "multimodal_input": multimodal,
            "thinking": bool(meta.get("reasoning")),
            "search": bool(meta.get("tool_call")),
        },
        "release_date": meta.get("release_date") or "",
        "name": meta.get("name"),
    }


def should_keep_model(model_id: str, meta: dict[str, Any], provider: str) -> bool:
    """Filter rules: drop deprecated, non-chat, specialty, denylist."""
    if meta.get("status") == "deprecated":
        return False
    if model_id in OBSOLETE_DENYLIST:
        return False
    if _DROP_ID_RE.search(model_id):
        return False
    mods = meta.get("modalities")
    if mods is not None:
        out = mods.get("output")
        if out is not None and "text" not in out:
            return False
        if out is not None and set(out) <= {"audio"}:
            return False
    if provider == "google" and not model_id.startswith("gemini-"):
        return False
    # Drop ancient Claude 3.x family ids if somehow still listed
    if re.match(r"^claude-3([.-]|$)", model_id):
        return False
    if re.match(r"^gpt-3\.5", model_id):
        return False
    return True


def _select_provider(
    models: dict[str, Any],
    provider: str,
    owned_by: str,
    cap: int,
    popular: list[str],
) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    for mid, meta in (models or {}).items():
        if not isinstance(meta, dict):
            continue
        if should_keep_model(mid, meta, provider):
            kept.append(map_model_entry(mid, meta, owned_by))
    kept.sort(key=lambda x: x.get("release_date") or "", reverse=True)
    by_id = {m["id"]: m for m in kept}
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for pid in popular:
        if pid in by_id and pid not in seen:
            selected.append(by_id[pid])
            seen.add(pid)
    for m in kept:
        if m["id"] in seen:
            continue
        selected.append(m)
        seen.add(m["id"])
        if len(selected) >= cap:
            break
    # Strip helper fields not needed in public API (keep release_date internal ok)
    out = []
    for m in selected:
        item = {
            "id": m["id"],
            "owned_by": m["owned_by"],
            "parameter_count": m["parameter_count"],
            "context_window": m["context_window"],
            "features": dict(m["features"]),
        }
        out.append(item)
    return out


def map_models_dev(raw: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Map full models.dev api.json → openai / anthropic / gemini catalogs."""
    openai_models = _select_provider(
        (raw.get("openai") or {}).get("models") or {},
        "openai",
        "openai",
        CAPS["openai"] - 8,  # leave room for deepseek
        POPULAR_BY_PROVIDER["openai"],
    )
    deepseek_models = _select_provider(
        (raw.get("deepseek") or {}).get("models") or {},
        "deepseek",
        "deepseek",
        8,
        POPULAR_BY_PROVIDER["deepseek"],
    )
    openai_all = (openai_models + deepseek_models)[: CAPS["openai"]]
    anthropic = _select_provider(
        (raw.get("anthropic") or {}).get("models") or {},
        "anthropic",
        "anthropic",
        CAPS["anthropic"],
        POPULAR_BY_PROVIDER["anthropic"],
    )
    gemini = _select_provider(
        (raw.get("google") or {}).get("models") or {},
        "google",
        "google",
        CAPS["gemini"],
        POPULAR_BY_PROVIDER["google"],
    )
    return {"openai": openai_all, "anthropic": anthropic, "gemini": gemini}


def build_cache_payload(raw: dict[str, Any], source: str) -> dict[str, Any]:
    catalogs = map_models_dev(raw)
    provider_counts = {
        "openai_src": len((raw.get("openai") or {}).get("models") or {}),
        "anthropic_src": len((raw.get("anthropic") or {}).get("models") or {}),
        "google_src": len((raw.get("google") or {}).get("models") or {}),
        "deepseek_src": len((raw.get("deepseek") or {}).get("models") or {}),
        "openai": len(catalogs["openai"]),
        "anthropic": len(catalogs["anthropic"]),
        "gemini": len(catalogs["gemini"]),
    }
    return {
        "fetched_at": _utcnow().isoformat(),
        "source": source,
        "provider_counts": provider_counts,
        "catalogs": catalogs,
    }


def fetch_models_dev(url: str | None = None, timeout: float = FETCH_TIMEOUT_S) -> dict[str, Any]:
    import httpx

    source = url or _cfg_catalog()["source"]
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        r = client.get(source)
        r.raise_for_status()
        data = r.json()
    if not isinstance(data, dict) or "openai" not in data:
        raise ValueError("models.dev response missing expected providers")
    return data


def load_cache_file(path: Path | None = None) -> dict[str, Any] | None:
    p = path or cache_path()
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Failed to read catalog cache %s: %s", p, e)
        return None
    if not isinstance(data, dict) or "catalogs" not in data:
        return None
    return data


def save_cache_file(payload: dict[str, Any], path: Path | None = None) -> Path:
    p = path or cache_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(p)
    return p


def _cache_is_fresh(payload: dict[str, Any], ttl_hours: float) -> bool:
    fetched = _parse_iso(payload.get("fetched_at"))
    if not fetched:
        return False
    age_h = (_utcnow() - fetched.astimezone(timezone.utc)).total_seconds() / 3600.0
    return age_h < ttl_hours


def _apply_payload(payload: dict[str, Any]) -> None:
    cats = payload.get("catalogs") or {}
    with _lock:
        _state["openai"] = list(cats.get("openai") or [])
        _state["anthropic"] = list(cats.get("anthropic") or [])
        _state["gemini"] = list(cats.get("gemini") or [])
        _state["meta"] = {
            "fetched_at": payload.get("fetched_at"),
            "source": payload.get("source"),
            "provider_counts": payload.get("provider_counts") or {},
        }
        _state["loaded"] = True


def _bundled_payload() -> dict[str, Any]:
    from mock_my_ai.models_catalog_bundled import BUNDLED_CACHE

    return dict(BUNDLED_CACHE)


def refresh_now(blocking: bool = True) -> dict[str, Any] | None:
    """Fetch models.dev, write cache, apply. Returns payload or None on failure."""
    cfg = _cfg_catalog()
    try:
        raw = fetch_models_dev(cfg["source"])
        payload = build_cache_payload(raw, cfg["source"])
        save_cache_file(payload)
        _apply_payload(payload)
        logger.info(
            "Model catalog refreshed from %s (%s)",
            cfg["source"],
            payload.get("provider_counts"),
        )
        return payload
    except Exception as e:
        logger.warning("Model catalog refresh failed: %s", e)
        return None


def _background_refresh() -> None:
    global _bg_thread
    try:
        refresh_now()
    finally:
        with _refresh_lock:
            _bg_thread = None


def _start_background_refresh() -> None:
    global _bg_thread
    with _refresh_lock:
        if _bg_thread is not None and _bg_thread.is_alive():
            return
        _bg_thread = threading.Thread(target=_background_refresh, name="models-catalog-refresh", daemon=True)
        _bg_thread.start()


def ensure_catalog(*, force_refresh: bool = False, allow_network: bool = True) -> dict[str, Any]:
    """
    Ensure in-memory catalogs are populated.

    Order: fresh cache → stale cache (+ background refresh) → network refresh → bundled.
    """
    cfg = _cfg_catalog()
    with _lock:
        if _state["loaded"] and not force_refresh:
            return {
                "openai": list(_state["openai"] or []),
                "anthropic": list(_state["anthropic"] or []),
                "gemini": list(_state["gemini"] or []),
                "meta": dict(_state["meta"] or {}),
            }

    cache = load_cache_file()
    if cache and (force_refresh is False) and _cache_is_fresh(cache, cfg["ttl_hours"]):
        _apply_payload(cache)
    elif cache:
        _apply_payload(cache)
        if allow_network and cfg["auto_refresh"]:
            _start_background_refresh()
    elif allow_network and cfg["auto_refresh"]:
        payload = refresh_now()
        if payload is None:
            _apply_payload(_bundled_payload())
    else:
        _apply_payload(_bundled_payload())

    with _lock:
        if not _state["loaded"]:
            _apply_payload(_bundled_payload())
        return {
            "openai": list(_state["openai"] or []),
            "anthropic": list(_state["anthropic"] or []),
            "gemini": list(_state["gemini"] or []),
            "meta": dict(_state["meta"] or {}),
        }


def get_runtime_catalogs() -> dict[str, list[dict[str, Any]]]:
    data = ensure_catalog(allow_network=True)
    return {
        "openai": data["openai"],
        "anthropic": data["anthropic"],
        "gemini": data["gemini"],
    }


def get_catalog_meta() -> dict[str, Any]:
    data = ensure_catalog(allow_network=False)
    return dict(data.get("meta") or {})


def reset_runtime_state_for_tests() -> None:
    """Clear in-memory state (unit tests only)."""
    with _lock:
        _state["openai"] = None
        _state["anthropic"] = None
        _state["gemini"] = None
        _state["meta"] = None
        _state["loaded"] = False
