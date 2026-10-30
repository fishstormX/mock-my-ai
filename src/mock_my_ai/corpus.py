from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from mock_my_ai.config import AppConfig, get_config


@dataclass
class Segment:
    id: str
    lang: str
    text: str
    length: str = "medium"


@dataclass
class CustomQA:
    pattern: str
    match: str  # regex | contains | exact
    reply: str
    langs: list[str]


class CorpusStore:
    def __init__(self, cfg: AppConfig | None = None):
        self.cfg = cfg or get_config()
        self._by_lang: dict[str, list[Segment]] = {}
        self._qa: list[CustomQA] = []
        self._load()

    def _load(self) -> None:
        root = self.cfg.corpus_dir()
        for lang in self.cfg.corpus.primary_languages:
            path = root / lang / "segments.jsonl"
            segs: list[Segment] = []
            if path.exists():
                with path.open(encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        obj = json.loads(line)
                        segs.append(
                            Segment(
                                id=obj.get("id", ""),
                                lang=obj.get("lang", lang),
                                text=obj["text"],
                                length=obj.get("length", "medium"),
                            )
                        )
            self._by_lang[lang] = segs

        qa_path = self.cfg.custom_qa_file()
        if qa_path.exists():
            data = json.loads(qa_path.read_text(encoding="utf-8"))
            for item in data:
                self._qa.append(
                    CustomQA(
                        pattern=item["pattern"],
                        match=item.get("match", "contains"),
                        reply=item["reply"],
                        langs=item.get("langs", ["*"]),
                    )
                )

    def count(self, lang: str) -> int:
        return len(self._by_lang.get(lang, []))

    def match_custom_qa(self, text: str, lang: str) -> str | None:
        for rule in self._qa:
            if "*" not in rule.langs and lang not in rule.langs:
                continue
            if rule.match == "exact":
                if text.strip() == rule.pattern:
                    return rule.reply
            elif rule.match == "regex":
                if re.search(rule.pattern, text, flags=re.IGNORECASE | re.DOTALL):
                    return rule.reply
            else:  # contains
                if rule.pattern.lower() in text.lower():
                    return rule.reply
        return None

    def pick(self, lang: str, rng: random.Random | None = None) -> str:
        rng = rng or random.Random()
        fallback = self.cfg.corpus.fallback_language
        segs = self._by_lang.get(lang) or self._by_lang.get(fallback) or []
        if not segs:
            return {
                "en": "This is a mock response from Mock My AI.",
                "zh": "这是来自 Mock My AI 的模拟回复。",
                "ja": "これは Mock My AI のモック応答です。",
                "es": "Esta es una respuesta simulada de Mock My AI.",
                "fr": "Ceci est une réponse simulée de Mock My AI.",
            }.get(lang, "This is a mock response from Mock My AI.")

        n = rng.randint(1, max(1, self.cfg.generation.max_output_segments))
        chosen = [rng.choice(segs).text for _ in range(n)]
        joiner = "" if lang in ("zh", "ja") else " "
        # For ja still prefer space between sentences sometimes
        if lang == "ja":
            joiner = ""
        return joiner.join(chosen)


@lru_cache
def get_corpus() -> CorpusStore:
    return CorpusStore()
