> 本文与英文版内容相同；Agent 接入请优先阅读 [中文总览](../agents/overview.md)。

# Tools

Built-in **safe** tools (actually executed on the server):

| Name | Behavior |
|------|----------|
| `echo` | Returns the provided text |
| `list_files` | Lists entries under `tools.list_files_root` (no writes) |

## Client-declared tools (Claude Code, agents, …)

When the request includes a `tools` array, Mock My AI may emit **at most one** provider-native `tool_use` / `tool_calls` / `functionCall` per HTTP response. Across the conversation, once messages already contain `agent_tool_steps_max` (default **3**) prior `tool_use`/`tool_result` steps — or any prior tool activity when not forcing — the mock returns **text + thinking only** (`end_turn`) so Claude Code agent loops terminate.

**Preferred (in order):** `WebSearch` / `web_search` / `WebFetch` / `Fetch`, `Read`, `Glob`, `Grep`, `LS`, `Bash` / `Shell`, then built-in `echo` / `list_files`.

**Never mocked as tool_use** (invented stubs break Claude Code): `Skill`, `SlashCommand`, `Workflow`, `Artifact`, `Edit`, `Write`, `Update`, `Notebook*`, `TodoWrite`, `Agent`, `Task`, `Cron*`, `Stop`, `ExitPlanMode`, etc. If the client only sent banned tools, the mock returns **text only**.

Arguments fill **every** `required` schema field (and respect `enum`). Bash/Shell `command` is chosen from a **read-only** allowlist (`pwd`, `ls`, `cat README.md`, …) with a matching `description`. Fetch gets a real `https://…` URL. Undeclared tools are never invented.

**Server side-effects:** only `echo` / `list_files` run locally. Everything else is stub `tool_use` only.

## Search citations vs search tools

Textual Sources / 「来源」 blocks are controlled by the console **Settings → Mock search** switch (default **off**) or per-request `mock_search`. Declaring `WebSearch` prefers a normal `tool_use` with a query stub; it does not force citations on.
