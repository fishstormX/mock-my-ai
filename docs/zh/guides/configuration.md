> 本文与英文版内容相同；Agent 接入请优先阅读 [中文总览](../agents/overview.md)。

# Configuration

Default file: `config/default.yaml`.

Override path with env `MOCK_MY_AI_CONFIG=/path/to.yaml`.

## Server

| Key | Default | Notes |
|-----|---------|-------|
| `server.host` | `0.0.0.0` | Also `MOCK_MY_AI_HOST` |
| `server.port` | `8000` | Also `MOCK_MY_AI_PORT` |
| `server.docs_enabled` | `true` | OpenAPI UI at `/api/docs` |

## Auth

Light **format** checks only — never validated against a real provider.

- Accepted prefixes: `sk-mock-`, `sk-ant-mock-`, `AIzaMock`
- Disable with `auth.require_api_key: false` or env `MOCK_MY_AI_REQUIRE_API_KEY=false`

## Generation

| Key | Meaning |
|-----|---------|
| `tool_loop_min` / `tool_loop_max` | In-response tool_use rounds per HTTP call (default **1 / 1**) |
| `agent_tool_steps_max` | Across-conversation tool budget (default **3**, clamp 1–5). Past this, no more `tool_use`. |
| `cache_ratio_*` | Prompt `cached_tokens` ratio (20–80%) |
| `deepseek_cache_ratio_*` | For model IDs containing `deepseek` (90–99%) |
| `thinking_enabled_default` | Default reasoning / thinking blocks (**true** for debug-friendly mocks) |
| `search_enabled_default` | Default mock search citations (「来源」); **false** by default. Console **Settings** toggle overrides per instance. Per-request `mock_search` always wins. |

Per-request overrides (all families where applicable):

- `mock_thinking` (bool)
- `mock_search` (bool)
- `mock_tool_rounds` (int 0–10)
- `mock_seed` (int) for reproducible picks

## Tools

```yaml
tools:
  enabled: [echo, list_files]
  list_files_root: "./"
  list_files_max: 50
```

## Custom models

```yaml
models:
  custom:
    - id: "my-org/custom-mock-1"
      owned_by: "custom"
      family: "openai"
      features:
        thinking: true
        search: false
        multimodal_input: true
```


## Console settings

- **Mock search citations** — Settings tab switch (default off). When enabled, search-capable models append Sources / 来源 fake results unless the request sets `mock_search`.
- **Request logs** — Console tab listing recent generation API calls (path, status, latency, truncated body). Health/static/marketing traffic is skipped.
