from __future__ import annotations

from functools import lru_cache
from typing import Any

from langdetect import DetectorFactory, LangDetectException, detect

# Deterministic-ish detection for tests
DetectorFactory.seed = 0

# Map langdetect codes → our corpus buckets
_LANG_MAP = {
    "en": "en",
    "zh-cn": "zh",
    "zh-tw": "zh",
    "zh": "zh",
    "ja": "ja",
    "es": "es",
    "fr": "fr",
}


def normalize_lang(code: str) -> str:
    c = (code or "").lower().replace("_", "-")
    if c.startswith("zh"):
        return "zh"
    return _LANG_MAP.get(c, c)


@lru_cache(maxsize=2048)
def detect_language(text: str, fallback: str = "en") -> str:
    """Detect language; zh-Hans/zh-Hant → zh; unknown → fallback (English)."""
    sample = (text or "").strip()
    if not sample:
        return fallback
    # Heuristic: heavy CJK
    cjk = sum(1 for ch in sample if "\u4e00" <= ch <= "\u9fff")
    if cjk >= max(3, len(sample) // 5):
        # Distinguish Japanese if kana present
        if any("\u3040" <= ch <= "\u30ff" for ch in sample):
            return "ja"
        return "zh"
    try:
        code = detect(sample[:2000])
        mapped = normalize_lang(code)
        if mapped in {"en", "zh", "ja", "es", "fr"}:
            return mapped
        return fallback
    except LangDetectException:
        return fallback


def _message_role(m: Any) -> str:
    if isinstance(m, dict):
        return str(m.get("role") or "")
    return str(getattr(m, "role", "") or "")


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for part in content:
            if isinstance(part, dict):
                if part.get("type") in ("text", "input_text"):
                    chunks.append(str(part.get("text", "")))
                elif "text" in part:
                    chunks.append(str(part["text"]))
            elif isinstance(part, str):
                chunks.append(part)
        return "\n".join(chunks)
    return ""


def extract_text_from_messages(messages: list) -> str:
    """Flatten chat-style messages into a single string (all roles)."""
    chunks: list[str] = []
    for m in messages or []:
        if isinstance(m, dict):
            content = m.get("content", "")
        else:
            content = getattr(m, "content", "")
        text = _content_to_text(content)
        if text:
            chunks.append(text)
    return "\n".join(chunks)


def extract_user_text_for_lang(messages: list) -> str:
    """Text used for language detection: prefer the last user turn.

    Claude Code / agent clients send huge English ``system`` prompts. Using the
    full flatten makes ``detect_language`` return ``en`` even when the user
    wrote Chinese. Prefer the last ``role=user`` message; if none, fall back to
    non-system messages only (never let system dominate).
    """
    user_texts: list[str] = []
    non_system: list[str] = []
    for m in messages or []:
        role = _message_role(m).lower()
        if isinstance(m, dict):
            content = m.get("content", "")
        else:
            content = getattr(m, "content", "")
        text = _content_to_text(content).strip()
        if not text:
            continue
        if role == "user":
            user_texts.append(text)
        elif role != "system":
            non_system.append(text)
    if user_texts:
        return user_texts[-1]
    if non_system:
        return "\n".join(non_system)
    return ""
