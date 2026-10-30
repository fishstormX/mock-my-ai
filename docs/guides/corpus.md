# Corpus & languages

Segments live under `data/corpus/<lang>/segments.jsonl`.

Primary languages (≥1000 segments each):

| Code | Language |
|------|----------|
| `en` | English |
| `zh` | Chinese (zh-Hans + zh-Hant treated as Chinese) |
| `ja` | Japanese |
| `es` | Spanish |
| `fr` | French |

Other detected languages fall back to English.

Regenerate:

```bash
uv run python scripts/generate_corpus.py
```

## Custom Q&A

Edit `data/corpus/custom_qa.json`:

```json
[
  {
    "pattern": "(?i)\\bping\\b",
    "match": "regex",
    "reply": "pong",
    "langs": ["*"]
  }
]
```

`match`: `regex` | `contains` | `exact`.
