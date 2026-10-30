from __future__ import annotations

import json
from pathlib import Path

from mock_my_ai.models_catalog_refresh import map_model_entry, map_models_dev, should_keep_model

FIXTURE = Path(__file__).parent / "fixtures" / "models_dev_sample.json"


def _raw() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_drop_deprecated_embedding_image_and_denylist():
    raw = _raw()
    openai = raw["openai"]["models"]
    assert should_keep_model("gpt-4o", openai["gpt-4o"], "openai")
    assert not should_keep_model("gpt-3.5-turbo", openai["gpt-3.5-turbo"], "openai")
    assert not should_keep_model(
        "text-embedding-3-small", openai["text-embedding-3-small"], "openai"
    )
    assert not should_keep_model("gpt-image-1", openai["gpt-image-1"], "openai")

    anthropic = raw["anthropic"]["models"]
    assert should_keep_model("claude-sonnet-4-5", anthropic["claude-sonnet-4-5"], "anthropic")
    assert not should_keep_model(
        "claude-3-opus-20240229", anthropic["claude-3-opus-20240229"], "anthropic"
    )

    google = raw["google"]["models"]
    assert should_keep_model("gemini-2.5-flash", google["gemini-2.5-flash"], "google")
    assert not should_keep_model("gemini-pro", google["gemini-pro"], "google")
    assert not should_keep_model("gemma-4-31b-it", google["gemma-4-31b-it"], "google")

    deepseek = raw["deepseek"]["models"]
    assert should_keep_model("deepseek-flash", deepseek["deepseek-flash"], "deepseek")
    assert not should_keep_model("deepseek-v4-flash", deepseek["deepseek-v4-flash"], "deepseek")


def test_feature_mapping():
    raw = _raw()
    m = map_model_entry("o3", raw["openai"]["models"]["o3"], "openai")
    assert m["id"] == "o3"
    assert m["owned_by"] == "openai"
    assert m["context_window"] == 200000
    assert m["features"]["thinking"] is True
    assert m["features"]["search"] is True
    assert m["features"]["multimodal_input"] is True


def test_map_models_dev_keeps_chat_only():
    cats = map_models_dev(_raw())
    openai_ids = {m["id"] for m in cats["openai"]}
    assert "gpt-4o" in openai_ids
    assert "o3" in openai_ids
    assert "deepseek-flash" in openai_ids
    assert "gpt-3.5-turbo" not in openai_ids
    assert "text-embedding-3-small" not in openai_ids
    assert "gpt-image-1" not in openai_ids
    assert "deepseek-v4-flash" not in openai_ids

    anth_ids = {m["id"] for m in cats["anthropic"]}
    assert "claude-sonnet-4-5" in anth_ids
    assert "claude-3-opus-20240229" not in anth_ids

    gem_ids = {m["id"] for m in cats["gemini"]}
    assert "gemini-2.5-flash" in gem_ids
    assert "gemini-pro" not in gem_ids
    assert "gemma-4-31b-it" not in gem_ids
