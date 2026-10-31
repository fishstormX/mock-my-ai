# Quickstart

## Run with uv

```bash
git clone https://github.com/fishstormX/mock-my-ai.git
cd mock-my-ai
uv sync --extra docs
uv run python scripts/generate_corpus.py   # if corpus missing
uv run mock-my-ai
# → http://127.0.0.1:8000
```

## Docker Compose

```bash
docker compose up --build
```

## Smoke curl

```bash
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-mock-openai-demo-key-0123456789abcdef" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"ping"}]}'
```

Expect custom Q&A reply containing `pong`.

Next: [Agent overview](agents/overview.md)
