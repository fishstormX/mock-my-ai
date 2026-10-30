from __future__ import annotations

import math
import random
from functools import lru_cache

from mock_my_ai.config import get_config

try:
    import tiktoken

    _ENC = tiktoken.get_encoding("cl100k_base")
except Exception:  # pragma: no cover
    _ENC = None


def count_tokens(text: str) -> int:
    if not text:
        return 0
    if _ENC is not None:
        try:
            return len(_ENC.encode(text))
        except Exception:
            pass
    # Fallback: rough char-based estimate
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff" or "\u3040" <= ch <= "\u30ff")
    if cjk > len(text) // 3:
        return max(1, len(text))
    return max(1, len(text) // 4)


def is_deepseek_model(model: str) -> bool:
    m = (model or "").lower()
    return "deepseek" in m


def cached_tokens_for_prompt(prompt_tokens: int, model: str, rng: random.Random | None = None) -> int:
    """Pick a realistic cached_tokens count within configured ratio bands.

    For very short prompts, integer rounding may make the exact band
    impossible; we then pick the closest feasible integer, preferring the
    lower bound for DeepSeek (high-cache) models.
    """
    rng = rng or random.Random()
    cfg = get_config().generation
    if prompt_tokens <= 0:
        return 0
    if is_deepseek_model(model):
        lo, hi = cfg.deepseek_cache_ratio_min, cfg.deepseek_cache_ratio_max
        prefer_high = True
    else:
        lo, hi = cfg.cache_ratio_min, cfg.cache_ratio_max
        prefer_high = False

    ratio = rng.uniform(lo, hi)
    cached = int(round(prompt_tokens * ratio))
    min_cached = math.ceil(prompt_tokens * lo - 1e-12)
    max_cached = math.floor(prompt_tokens * hi + 1e-12)
    min_cached = max(0, min(prompt_tokens, min_cached))
    max_cached = max(0, min(prompt_tokens, max_cached))

    if min_cached > max_cached:
        # Band empty at this token length — pick closest feasible value
        if prefer_high:
            return min(prompt_tokens, max(min_cached, max_cached))
        return max(0, min(prompt_tokens, round(prompt_tokens * ((lo + hi) / 2))))

    return max(min_cached, min(max_cached, cached))


@lru_cache(maxsize=1)
def _warmup() -> None:
    count_tokens("warmup")


_warmup()
