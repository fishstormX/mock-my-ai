# Contributing to Mock My AI

Thanks for helping improve Mock My AI.

## Development setup

```bash
uv sync --extra dev --extra docs
uv run python scripts/generate_corpus.py   # if needed
uv run mock-my-ai
uv run pytest -q
```

## Guidelines

- Keep replies **mock-only** — never proxy to real providers in this project.
- Prefer schema-compatible changes across OpenAI / Anthropic / Gemini routes.
- Add or extend pytest coverage for new endpoints or generation behavior.
- Do not commit `data/app.db`, `data/.session_secret`, `.venv/`, or `site/`.

## Pull requests

1. Fork and branch from `main`.
2. Keep commits focused; update README/docs when behavior changes.
3. Ensure `uv run pytest -q` passes.
