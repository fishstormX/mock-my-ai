# Mock My AI — Phase 1 Spec

## Goal
Open-source project + official website that mocks popular AI provider APIs. Clients can point SDKs/tools at this server with realistic keys, model lists, and response shapes, while content is fake corpus (not real model inference).

## Product name
Mock My AI (repo suggestion: `mock-my-ai`)

## Phase 1 scope
- Text models that advertise multimodal input capability (accept image/audio/file parts in request schema; mock still returns text).
- Compatible request/response formats for the three major families:
  - OpenAI-style: Chat Completions (`/v1/chat/completions`), Completions, Responses API (`/v1/responses`) where practical
  - Anthropic-style: Messages API
  - Google Gemini-style: `generateContent` / OpenAI-compat where documented
- Full-looking model catalogs for each provider family (copy public model IDs/names from docs; allow custom model registration via config/API).
- Config & docs that mirror official AI console/docs style: base URL, API keys, model list, feature flags.
- Feature toggles (per request and/or model config):
  - Built-in search (mock search tool / grounding-style fields)
  - Thinking / reasoning (mock reasoning tokens or thinking blocks)
- Tool calling: support agent loops of 0–10 rounds; ship a small set of safe, read-only CLI-like tools (echo, list files / `ls`-style). Tools must be configurable; no write/delete/network-dangerous ops by default.

## Mock generation logic
1. Detect input language with an open-source Python package (e.g. `langdetect` or `lingua-py`). Treat zh-Hans and zh-Hant as Chinese.
2. Pick corpus for that language; fallback to English for unsupported languages.
3. At least 5 primary languages with ≥1000 corpus segments each (non-political, non-sensitive). Segment lengths vary (short→long). Generate or collect offline; do not include sensitive topics.
4. Each response: random selection logic; support custom Q&A corpus overrides (exact or pattern match → fixed reply).
5. Token accounting must look real:
   - Prompt/completion/total tokens consistent with output length (use a real tokenizer approximation, e.g. tiktoken or similar).
   - `cached_tokens` (or provider-equivalent) ratio: default random 20%–80% of prompt tokens; for DeepSeek-series model IDs use 90%–99%.
6. Tool loops: randomly (or config-driven) 0–10 iterations with tool_calls → tool results → final message; stay schema-correct for each API family.

## API keys & auth
- Accept keys that look like official ones (prefix patterns); validate format lightly; document example keys. No real upstream calls.

## Website / docs
- Landing page explaining the project + quickstart
- Comprehensive configuration docs (base URLs per format, env vars, model list, feature flags, custom models, custom corpus, tools)
- Deployable as the project “official site” (static docs + API; suggest docs site + FastAPI backend)

## Tech preferences (agent may refine)
- Backend: Python 3.11+, FastAPI, uvicorn
- Language detect: open-source py package
- Corpus: JSON/JSONL under `data/corpus/<lang>/`
- Config: YAML/TOML + env
- Docs: MkDocs or VitePress (or FastAPI-served markdown) — pick one and ship
- License: Apache-2.0 or MIT (prefer MIT unless reason otherwise)
- Tests: pytest for schema compatibility smoke tests per endpoint family
- Docker Compose for local run; README with curl examples for OpenAI/Anthropic/Gemini clients

## Out of scope for Phase 1
- Real model inference or proxying to real providers
- Dangerous tools (shell write, rm, arbitrary network)
- Full billing/usage dashboards
- Non-text generation (image/video out)

## Success criteria
- `docker compose up` (or `uv run`) serves mock APIs + docs
- OpenAI / Anthropic / Gemini style clients can list models and chat with mock replies
- Language-aware corpus, realistic token/cache fields, thinking & search toggles, tool loops 0–10
- Custom models + custom Q&A corpus documented and working
- Clean open-source README, CONTRIBUTING, LICENSE, and website docs
