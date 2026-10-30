from __future__ import annotations

from mock_my_ai.language import detect_language, normalize_lang
from mock_my_ai.tokens import cached_tokens_for_prompt, count_tokens, is_deepseek_model


def test_normalize_zh_variants():
    assert normalize_lang("zh-cn") == "zh"
    assert normalize_lang("zh-tw") == "zh"
    assert normalize_lang("zh_CN") == "zh"


def test_detect_chinese_and_japanese():
    assert detect_language("今天天气不错，适合出去走走看看风景。") == "zh"
    assert detect_language("今日は良い天気ですね。散歩に行きましょう。") == "ja"
    assert detect_language("Hello world, how are you today?") == "en"


def test_count_tokens_positive():
    assert count_tokens("hello world") > 0
    assert count_tokens("你好世界") > 0


def test_deepseek_cache():
    assert is_deepseek_model("deepseek-flash")
    import random

    rng = random.Random(0)
    cached = cached_tokens_for_prompt(1000, "deepseek-v3", rng)
    assert 900 <= cached <= 990


def test_extract_user_text_prefers_last_user():
    from mock_my_ai.language import extract_user_text_for_lang, detect_language

    messages = [
        {
            "role": "system",
            "content": (
                "You are Claude Code, Anthropic's official CLI for Claude. "
                "You are an interactive agent that helps users with software engineering. "
                "Follow the instructions carefully and use tools when needed. "
                "Always respond in a helpful manner. " * 20
            ),
        },
        {"role": "user", "content": "你好，看一下落库情况"},
    ]
    sample = extract_user_text_for_lang(messages)
    assert "你好" in sample
    assert "Claude Code" not in sample
    assert detect_language(sample) == "zh"


def test_extract_user_text_skips_system_fallback_to_non_system():
    from mock_my_ai.language import extract_user_text_for_lang

    messages = [
        {"role": "system", "content": "Huge English system prompt only."},
        {"role": "assistant", "content": "Previous reply in English only here."},
    ]
    # No user turn → non-system (assistant), not system
    sample = extract_user_text_for_lang(messages)
    assert "Previous reply" in sample
    assert "Huge English system" not in sample
