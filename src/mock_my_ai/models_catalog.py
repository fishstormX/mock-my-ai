from __future__ import annotations

from typing import Any

from mock_my_ai.config import get_config
from mock_my_ai.models_catalog_bundled import (
    BUNDLED_ANTHROPIC_MODELS,
    BUNDLED_GEMINI_MODELS,
    BUNDLED_OPENAI_MODELS,
)
from mock_my_ai.models_catalog_refresh import get_catalog_meta, get_runtime_catalogs

# Offline / import-time snapshot (also used if refresh never runs).
OPENAI_MODELS: list[dict[str, Any]] = list(BUNDLED_OPENAI_MODELS)
ANTHROPIC_MODELS: list[dict[str, Any]] = list(BUNDLED_ANTHROPIC_MODELS)
GEMINI_MODELS: list[dict[str, Any]] = list(BUNDLED_GEMINI_MODELS)


def _runtime_openai() -> list[dict[str, Any]]:
    cats = get_runtime_catalogs()
    return list(cats.get("openai") or OPENAI_MODELS)


def _runtime_anthropic() -> list[dict[str, Any]]:
    cats = get_runtime_catalogs()
    return list(cats.get("anthropic") or ANTHROPIC_MODELS)


def _runtime_gemini() -> list[dict[str, Any]]:
    cats = get_runtime_catalogs()
    return list(cats.get("gemini") or GEMINI_MODELS)


def _yaml_custom_models(family: str | None = None) -> list[dict[str, Any]]:
    cfg = get_config()
    out = []
    for m in cfg.models.custom:
        if family and m.family != family:
            continue
        out.append(
            {
                "id": m.id,
                "owned_by": m.owned_by,
                "parameter_count": m.parameter_count,
                "context_window": m.context_window,
                "features": m.features,
                "family": m.family,
                "source": "yaml",
            }
        )
    return out


def _db_custom_models(family: str | None = None) -> list[dict[str, Any]]:
    try:
        from mock_my_ai.db import list_custom_models

        rows = list_custom_models(user_id=None)
    except Exception:
        return []
    out = []
    for r in rows:
        if family and r.get("family") != family:
            continue
        out.append(
            {
                "id": r["model_id"],
                "owned_by": r.get("owned_by") or "custom",
                "parameter_count": r.get("parameter_count"),
                "context_window": r.get("context_window"),
                "features": r.get("features") or {},
                "family": r.get("family") or "openai",
                "source": "db",
                "db_id": r.get("id"),
                "user_id": r.get("user_id"),
            }
        )
    return out


def _custom_models(family: str | None = None) -> list[dict[str, Any]]:
    return _yaml_custom_models(family) + _db_custom_models(family)


def _dedupe(models: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    uniq: list[dict[str, Any]] = []
    for m in models:
        if m["id"] in seen:
            continue
        seen.add(m["id"])
        uniq.append(m)
    return uniq


def builtin_models_flat() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in _runtime_openai():
        fam = "deepseek" if m.get("owned_by") == "deepseek" else "openai"
        out.append({**m, "family": fam, "source": "builtin"})
    for m in _runtime_anthropic():
        out.append({**m, "family": "anthropic", "source": "builtin"})
    for m in _runtime_gemini():
        out.append({**m, "family": "gemini", "source": "builtin"})
    return out


def all_openai_compat_models() -> list[dict[str, Any]]:
    models = list(_runtime_openai()) + _custom_models("openai") + _custom_models("deepseek")
    for m in _runtime_anthropic() + _runtime_gemini():
        models.append({**m})
    models += _custom_models("anthropic") + _custom_models("gemini")
    return _dedupe(models)


def anthropic_models() -> list[dict[str, Any]]:
    return list(_runtime_anthropic()) + _custom_models("anthropic")


def gemini_models() -> list[dict[str, Any]]:
    return list(_runtime_gemini()) + _custom_models("gemini")


def catalog_source_info() -> dict[str, Any]:
    """Metadata for console / public models page."""
    return get_catalog_meta()


def get_model_features(model_id: str) -> dict[str, Any]:
    for m in all_openai_compat_models():
        if m["id"] == model_id:
            return dict(m.get("features") or {})
    return {"multimodal_input": True, "thinking": False, "search": False}


def to_openai_list_item(m: dict[str, Any], created: int = 1700000000) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": m["id"],
        "object": "model",
        "created": created,
        "owned_by": m.get("owned_by", "mock-my-ai"),
    }
    # Extra mock-my-ai metadata (harmless for OpenAI clients)
    if m.get("parameter_count") is not None:
        item["parameter_count"] = m["parameter_count"]
    if m.get("context_window") is not None:
        item["context_window"] = m["context_window"]
    return item
