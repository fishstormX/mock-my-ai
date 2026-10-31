# Mock My AI

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Live demo](https://img.shields.io/badge/demo-aimock.fishmaple.cn-0ea5e9)](https://aimock.fishmaple.cn)

Open-source **mock AI API server** for local agents, SDKs, and CI.  
Point OpenAI / Anthropic / Gemini-compatible clients at Mock My AI and get **schema-correct fake replies** — no upstream inference, no API bills.

**Live demo:** [https://aimock.fishmaple.cn](https://aimock.fishmaple.cn) · **GitHub:** [fishstormX/mock-my-ai](https://github.com/fishstormX/mock-my-ai)

---

## Why

- Integration-test coding agents (Codex, Claude Code, Hermes, custom harnesses) without burning tokens  
- Develop against Chat Completions, Responses, Messages, and Gemini shapes with real SSE streams  
- Demo consoles and model pickers with a credible catalog (auto-refreshed from [models.dev](https://models.dev/))

Responses are **corpus text**, not model output. Treat every reply as mock data.

---

## Features

| Area | What you get |
|------|----------------|
| **API families** | OpenAI Chat Completions + Completions + Responses; Anthropic Messages; Gemini `generateContent` / model list |
| **Streaming** | SSE for chat completions and Responses (`stream: true`) |
| **Language-aware corpus** | en / zh / ja / es / fr — **1100+ segments each**; zh-Hans & zh-Hant → `zh` |
| **Tokens** | tiktoken-style counts + realistic `cached_tokens` (DeepSeek IDs: 90–99% cache) |
| **Thinking** | Optional reasoning / thinking blocks (on by default; overridable per request) |
| **Search mock** | Optional citations; WebSearch results internalized (no Fetch follow-up) |
| **Agent tool loop** | 0–3 `tool_use` per HTTP call; hard stop across turns (`agent_tool_steps_max`); read-only Shell/Bash; bans Skill / Edit / Write / Fetch / Agent / … |
| **Auth** | Sample keys + console-issued keys; optional IP/CIDR allowlist |
| **Console** | Sign up, API keys, custom models, request log, settings (ZH/EN) |
| **Catalog** | models.dev refresh → `data/models_catalog_cache.json` (24h TTL) + bundled offline snapshot |
| **Docs** | Bilingual (EN/ZH) agent integration guides + FastAPI OpenAPI at `/api/docs` |

---

## Quick start

### uv (recommended)

```bash
git clone https://github.com/fishstormX/mock-my-ai.git
cd mock-my-ai
uv sync --extra dev --extra docs
uv run python scripts/generate_corpus.py   # if corpus not present
uv run mock-my-ai
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) — OpenAPI at `/api/docs`, MkDocs at `/docs/`.

### venv + pip

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,docs]"
python scripts/generate_corpus.py
mock-my-ai
```

### Docker Compose

```bash
docker compose up --build
# → http://127.0.0.1:8000
```

---

## Sample API keys

| Family | Key |
|--------|-----|
| OpenAI-style | `sk-mock-openai-demo-key-0123456789abcdef` |
| Anthropic-style | `sk-ant-mock-anthropic-demo-key-0123456789` |
| Gemini-style | `AIzaMockGeminiDemoKey0123456789abcdef` |

By default only these sample keys **and** keys created in the web console are accepted.  
Set `MOCK_MY_AI_ACCEPT_PREFIX_KEYS=true` (or `auth.accept_prefix_keys` in YAML) to accept any key with prefixes `sk-mock-` / `sk-ant-mock-` / `AIzaMock`.

---

## Point a client at it

| Client | Base URL (local) | Notes |
|--------|------------------|--------|
| OpenAI SDK / Codex `wire_api=chat` | `http://127.0.0.1:8000/v1` | Bearer sample or console key |
| Codex `wire_api=responses` | same `/v1` | Uses `/v1/responses` + SSE |
| Anthropic SDK | `http://127.0.0.1:8000` | `x-api-key` + `/v1/messages` |
| Gemini | `http://127.0.0.1:8000` | `x-goog-api-key` + `/v1beta/models/...:generateContent` |

Production demo base: `https://aimock.fishmaple.cn/v1` (OpenAI-style).

---

## Curl examples

**Chat Completions (Chinese → Chinese corpus):**

```bash
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-mock-openai-demo-key-0123456789abcdef" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "你好，请介绍一下今天的天气"}],
    "mock_thinking": true
  }' | python -m json.tool
```

**Streaming chat:**

```bash
curl -N http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-mock-openai-demo-key-0123456789abcdef" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","stream":true,"messages":[{"role":"user","content":"ping"}]}'
```

**Anthropic Messages:**

```bash
curl -s http://127.0.0.1:8000/v1/messages \
  -H "x-api-key: sk-ant-mock-anthropic-demo-key-0123456789" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5",
    "max_tokens": 256,
    "messages": [{"role": "user", "content": "Hello there"}]
  }' | python -m json.tool
```

**Gemini generateContent:**

```bash
curl -s "http://127.0.0.1:8000/v1beta/models/gemini-2.5-flash:generateContent" \
  -H "x-goog-api-key: AIzaMockGeminiDemoKey0123456789abcdef" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"role":"user","parts":[{"text":"Bonjour, comment ça va?"}]}]}' \
  | python -m json.tool
```

**Custom Q&A (`ping` → `pong`):**

```bash
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-mock-openai-demo-key-0123456789abcdef" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"ping"}]}'
```

**Tool loop (client-declared tools):**

```bash
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-mock-openai-demo-key-0123456789abcdef" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "List files please"}],
    "tools": [
      {"type": "function", "function": {"name": "echo", "parameters": {"type": "object", "properties": {"text": {"type": "string"}}}}},
      {"type": "function", "function": {"name": "list_files", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}}}}
    ],
    "mock_tool_rounds": 2
  }' | python -m json.tool
```

---

## Configuration

Primary file: [`config/default.yaml`](config/default.yaml).

| Section | Controls |
|---------|----------|
| `auth` | Sample keys, prefix acceptance |
| `generation` | Tool loop 0–3, agent budget, cache ratios, thinking / search defaults |
| `tools` | Built-in `echo` / `list_files` roots |
| `models` | models.dev URL, cache path, TTL, YAML custom models |
| `corpus` | Segment path + `custom_qa.json` |
| `console` | SQLite path, optional `public_base_url` |

### Environment variables

| Variable | Purpose |
|----------|---------|
| `MOCK_MY_AI_HOST` / `MOCK_MY_AI_PORT` | Bind address (default `0.0.0.0:8000`) |
| `MOCK_MY_AI_PUBLIC_BASE_URL` | Canonical URL in the UI (e.g. `https://aimock.fishmaple.cn`) |
| `MOCK_MY_AI_SESSION_SECRET` | Cookie signing secret (else auto file under `data/.session_secret`) |
| `MOCK_MY_AI_ACCEPT_PREFIX_KEYS` | `true` → accept any matching prefix key |

See [`.env.example`](.env.example).

---

## Web console

Visit `/` (ZH/EN marketing), then **Sign up**:

- Create / revoke API keys (secret shown once)
- Optional IP / CIDR allowlist (empty = allow all)
- Custom models (params + context window)
- Public model browser at `/models`
- Request log (per-key isolation; 6h / max 20 per key; expandable full JSON)

SQLite defaults to `data/app.db` (gitignored).

---

## Model catalog

Built-in OpenAI / Anthropic / Gemini lists are pulled from [models.dev](https://models.dev/) (`https://models.dev/api.json`), cached at `data/models_catalog_cache.json` (TTL default **24h**), and refreshed on startup when stale. Deprecated, embedding, image-only, and TTS IDs are filtered out. Offline / blocked networks fall back to the bundled snapshot in `models_catalog_bundled.py`.

---

## Project layout

```
config/default.yaml          # auth, generation, tools, catalog, corpus
data/corpus/<lang>/          # JSONL segments (en zh ja es fr)
data/corpus/custom_qa.json   # exact / pattern Q&A overrides
data/models_catalog_cache.json
src/mock_my_ai/              # FastAPI app, routes, generation, console
docs/en docs/zh              # MkDocs agent integration (EN/ZH)
scripts/generate_corpus.py
tests/                       # pytest (50+ smoke / behavior tests)
Dockerfile / docker-compose.yml
```

---

## Docs & tests

```bash
uv run mkdocs build -d site    # served at /docs/ when the app runs
uv run mkdocs serve            # live docs only
uv run pytest -q
```

---

## Security notes

- **No real model calls.** All completions are mock.
- Built-in tools are **read-only** (`echo`, directory listing). Dangerous agent tools (write/edit/fetch/shell mutate) are not selected by the mock loop.
- Do not commit `data/app.db` or `data/.session_secret`.
- Demo keys are public samples — rotate console keys on shared deployments.

---

## License

MIT — see [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

Maintained by [fishstormX](https://github.com/fishstormX) · demo [aimock.fishmaple.cn](https://aimock.fishmaple.cn)
