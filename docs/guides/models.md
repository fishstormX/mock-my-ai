# Models

Built-in catalogs for OpenAI, Anthropic, Gemini, and DeepSeek are refreshed from the open [models.dev](https://models.dev/) API (`https://models.dev/api.json`).

- Cache: `data/models_catalog_cache.json` (TTL `models.catalog_ttl_hours`, default 24h)
- Startup loads cache (or bundled snapshot) and refreshes in the background when stale
- Deprecated, embedding, image-only, TTS, and other non-chat IDs are filtered out
- Offline installs use the bundled snapshot in `models_catalog_bundled.py`

Endpoints:

- OpenAI list: `GET /v1/models`
- Anthropic list: `GET /anthropic/v1/models`
- Gemini list: `GET /v1beta/models`

Multimodal **input** parts (images, etc.) are accepted in request schemas; outputs remain text mocks.

Add more via `config/default.yaml` → `models.custom`, or the console Models tab.
