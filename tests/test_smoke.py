from __future__ import annotations

from tests.conftest import ANTHROPIC_KEY, GEMINI_KEY, OPENAI_KEY


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    for lang in ("en", "zh", "ja", "es", "fr"):
        assert body["corpus"][lang] >= 1000


def test_auth_reject(client):
    r = client.get("/v1/models")
    assert r.status_code == 401


def test_list_models(client):
    r = client.get("/v1/models", headers={"Authorization": f"Bearer {OPENAI_KEY}"})
    assert r.status_code == 200
    data = r.json()["data"]
    ids = {m["id"] for m in data}
    assert "gpt-4o-mini" in ids
    assert "claude-sonnet-4-5" in ids
    assert "gemini-2.5-flash" in ids
    assert "deepseek-flash" in ids
    # obsolete / specialty must be gone
    assert "gpt-3.5-turbo" not in ids
    assert "claude-3-opus-20240229" not in ids
    assert "text-embedding-3-small" not in ids


def test_chat_completions_english(client):
    r = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_KEY}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Hello, tell me about the weather"}],
            "mock_seed": 1,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "chat.completion"
    assert body["choices"][0]["message"]["content"]
    usage = body["usage"]
    assert usage["prompt_tokens"] > 0
    assert usage["completion_tokens"] > 0
    cached = usage["prompt_tokens_details"]["cached_tokens"]
    assert 0 <= cached <= usage["prompt_tokens"]
    ratio = cached / usage["prompt_tokens"]
    assert 0.15 <= ratio <= 0.85
    assert body["mock_my_ai"]["lang"] == "en"


def test_chat_completions_chinese(client):
    r = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_KEY}"},
        json={
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "你好，请介绍一下今天的天气如何"}],
            "mock_thinking": True,
            "mock_seed": 2,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["mock_my_ai"]["lang"] == "zh"
    assert body["choices"][0]["message"].get("reasoning_content")


def test_custom_qa_ping(client):
    r = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_KEY}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "please ping now"}],
            "mock_seed": 0,
        },
    )
    assert r.status_code == 200
    assert r.json()["choices"][0]["message"]["content"] == "pong"


def test_deepseek_cache_ratio(client):
    r = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_KEY}"},
        json={
            "model": "deepseek-flash",
            "messages": [
                {
                    "role": "user",
                    "content": "Please explain what token caching means in large language model APIs in a few sentences.",
                }
            ],
            "mock_seed": 7,
        },
    )
    assert r.status_code == 200
    usage = r.json()["usage"]
    ratio = usage["prompt_tokens_details"]["cached_tokens"] / usage["prompt_tokens"]
    assert 0.90 <= ratio <= 0.99


def test_completions(client):
    r = client.post(
        "/v1/completions",
        headers={"Authorization": f"Bearer {OPENAI_KEY}"},
        json={"model": "gpt-4.1-mini", "prompt": "Once upon a time", "mock_seed": 3},
    )
    assert r.status_code == 200
    assert r.json()["choices"][0]["text"]


def test_responses(client):
    r = client.post(
        "/v1/responses",
        headers={"Authorization": f"Bearer {OPENAI_KEY}"},
        json={"model": "gpt-4o-mini", "input": "What is Mock My AI?", "mock_seed": 4},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "response"
    assert body["output"]


def test_tool_rounds(client):
    r = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_KEY}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Use tools"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "echo",
                        "parameters": {
                            "type": "object",
                            "properties": {"text": {"type": "string"}},
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "list_files",
                        "parameters": {
                            "type": "object",
                            "properties": {"path": {"type": "string"}},
                        },
                    },
                },
            ],
            "mock_tool_rounds": 1,
            "mock_seed": 5,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["choices"][0]["finish_reason"] == "tool_calls"
    assert body["choices"][0]["message"]["tool_calls"]
    assert len(body["mock_my_ai"]["tool_rounds"]) == 1
    assert len(body["choices"][0]["message"]["tool_calls"]) == 1


def test_anthropic_messages(client):
    r = client.post(
        "/v1/messages",
        headers={"x-api-key": ANTHROPIC_KEY},
        json={
            "model": "claude-sonnet-4-5",
            "max_tokens": 128,
            "messages": [{"role": "user", "content": "Hola, ¿cómo estás?"}],
            "mock_seed": 6,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "message"
    assert body["content"]
    assert body["usage"]["input_tokens"] > 0
    assert body["mock_my_ai"]["lang"] == "es"


def test_gemini_generate(client):
    r = client.post(
        "/v1beta/models/gemini-2.5-flash:generateContent",
        headers={"x-goog-api-key": GEMINI_KEY},
        json={
            "contents": [{"role": "user", "parts": [{"text": "Bonjour, parlez-moi du temps"}]}],
            "mock_seed": 8,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["candidates"][0]["content"]["parts"]
    assert body["usageMetadata"]["promptTokenCount"] > 0
    assert body["mock_my_ai"]["lang"] == "fr"


def test_search_toggle(client):
    r = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_KEY}"},
        json={
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Search something"}],
            "mock_search": True,
            "mock_seed": 9,
        },
    )
    assert r.status_code == 200
    assert r.json()["mock_my_ai"]["search_results"]


def test_anthropic_messages_stream(client):
    r = client.post(
        "/v1/messages",
        headers={"x-api-key": ANTHROPIC_KEY},
        json={
            "model": "claude-sonnet-4-5",
            "max_tokens": 128,
            "stream": True,
            "messages": [{"role": "user", "content": "Hello stream test"}],
            "mock_seed": 11,
        },
    )
    assert r.status_code == 200
    assert "text/event-stream" in r.headers.get("content-type", "")
    body = r.text
    assert "event: message_start" in body
    assert "event: message_stop" in body
    assert "text_delta" in body
    assert "event: content_block_delta" in body


def test_anthropic_bash_tool_use_with_schema_stubs(client):
    """Bash gets tool_use with read-only command; Edit is never selected."""
    r = client.post(
        "/v1/messages",
        headers={"x-api-key": ANTHROPIC_KEY},
        json={
            "model": "claude-sonnet-4-5",
            "max_tokens": 128,
            "messages": [{"role": "user", "content": "Please run a command"}],
            "tools": [
                {
                    "name": "Bash",
                    "description": "Run a shell command",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string"},
                            "description": {"type": "string"},
                        },
                        "required": ["command", "description"],
                    },
                },
                {
                    "name": "Edit",
                    "description": "Edit a file",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string"},
                            "old_string": {"type": "string"},
                            "new_string": {"type": "string"},
                        },
                        "required": ["file_path", "old_string", "new_string"],
                    },
                },
            ],
            "mock_tool_rounds": 1,
            "mock_seed": 12,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["stop_reason"] == "tool_use"
    # thinking on by default for debug
    assert any(b.get("type") == "thinking" for b in body["content"])
    tool_blocks = [b for b in body["content"] if b["type"] == "tool_use"]
    assert tool_blocks
    names = {b["name"] for b in tool_blocks}
    assert names == {"Bash"}
    for b in tool_blocks:
        inp = b["input"]
        assert "command" in inp and "description" in inp
        cmd = str(inp["command"]).strip()
        assert cmd
        assert not any(x in cmd for x in (">", "rm ", "mv ", "touch ", "npm install"))
        assert cmd.split()[0] in {"pwd", "ls", "head", "cat", "find", "wc"}
        assert str(inp["description"]).strip()


def test_anthropic_explicit_safe_tool_rounds(client):
    r = client.post(
        "/v1/messages",
        headers={"x-api-key": ANTHROPIC_KEY},
        json={
            "model": "claude-sonnet-4-5",
            "max_tokens": 128,
            "messages": [{"role": "user", "content": "Use echo tool"}],
            "tools": [
                {
                    "name": "echo",
                    "description": "Echo text",
                    "input_schema": {
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                        "required": ["text"],
                    },
                }
            ],
            "mock_tool_rounds": 1,
            "mock_seed": 13,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["stop_reason"] == "tool_use"
    tool_blocks = [b for b in body["content"] if b["type"] == "tool_use"]
    assert tool_blocks
    assert tool_blocks[0]["name"] == "echo"
    assert "text" in tool_blocks[0]["input"]


def test_lang_follows_last_user_not_english_system(client):
    """Claude Code sends a huge English system; user Chinese must still get zh corpus."""
    r = client.post(
        "/v1/messages",
        headers={"x-api-key": ANTHROPIC_KEY},
        json={
            "model": "claude-sonnet-4-5",
            "max_tokens": 256,
            "system": (
                "You are Claude Code, Anthropic's official CLI for Claude. "
                "You help with software engineering tasks using tools. "
                "Be concise and follow the user's instructions carefully. " * 30
            ),
            "messages": [{"role": "user", "content": "你好，请看一下落库"}],
            "mock_seed": 42,
            "mock_search": False,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["mock_my_ai"]["lang"] == "zh"
    text = body["mock_my_ai"]["text"]
    # Chinese corpus / replies contain CJK
    assert any("\u4e00" <= ch <= "\u9fff" for ch in text)


def test_search_default_off_for_search_capable_model(client):
    """search_enabled_default is false; no 来源 unless console switch or mock_search."""
    r = client.post(
        "/v1/messages",
        headers={"x-api-key": ANTHROPIC_KEY},
        json={
            "model": "claude-sonnet-4-5",
            "max_tokens": 256,
            "messages": [{"role": "user", "content": "你好，帮我查一下"}],
            "mock_seed": 43,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["mock_my_ai"]["search_results"] is None
    text_out = body["mock_my_ai"]["text"]
    assert "来源" not in text_out and "Sources:" not in text_out


def test_search_disabled_explicitly(client):
    r = client.post(
        "/v1/messages",
        headers={"x-api-key": ANTHROPIC_KEY},
        json={
            "model": "claude-sonnet-4-5",
            "max_tokens": 128,
            "messages": [{"role": "user", "content": "Hello no search please"}],
            "mock_search": False,
            "mock_seed": 44,
        },
    )
    assert r.status_code == 200
    assert r.json()["mock_my_ai"]["search_results"] is None


def test_web_search_tool_emits_tool_calls_not_citations(client):
    """Search-named tools get tool_use with internalized results; no text Sources:."""
    r = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_KEY}"},
        json={
            "model": "gpt-4.1-mini",  # any chat model; mock_search off via default
            "messages": [{"role": "user", "content": "Look this up about pandas"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "web_search",
                        "parameters": {
                            "type": "object",
                            "properties": {"query": {"type": "string"}},
                            "required": ["query"],
                        },
                    },
                }
            ],
            "mock_tool_rounds": 1,
            "mock_seed": 45,
            "mock_thinking": False,
        },
    )
    assert r.status_code == 200
    body = r.json()
    msg = body["choices"][0]["message"]
    assert msg.get("tool_calls")
    assert msg["tool_calls"][0]["function"]["name"] == "web_search"
    import json as _json

    args = _json.loads(msg["tool_calls"][0]["function"]["arguments"])
    assert "query" in args and str(args["query"]).strip()
    # Results internalized on companion result + search_results (no Fetch needed)
    call = body["mock_my_ai"]["tool_rounds"][0]["calls"][0]
    payload = call["result"]
    if isinstance(payload, str):
        payload = _json.loads(payload)
    assert payload.get("results")
    assert body["mock_my_ai"]["search_results"]
    # Assistant text must not look like citation dump while tool_use is pending
    text_out = msg.get("content") or ""
    assert "Sources:" not in text_out and "来源" not in text_out


def test_anthropic_tools_zero_rounds_stays_text(client):
    """Explicit mock_tool_rounds=0 must not emit tool_use even when Bash is listed."""
    r = client.post(
        "/v1/messages",
        headers={"x-api-key": ANTHROPIC_KEY},
        json={
            "model": "claude-sonnet-4-5",
            "max_tokens": 128,
            "messages": [{"role": "user", "content": "Please help edit a file"}],
            "tools": [
                {
                    "name": "Bash",
                    "description": "Run a shell command",
                    "input_schema": {
                        "type": "object",
                        "properties": {"command": {"type": "string"}},
                        "required": ["command"],
                    },
                }
            ],
            "mock_tool_rounds": 0,
            "mock_seed": 12,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["stop_reason"] == "end_turn"
    types = {b["type"] for b in body["content"]}
    assert "tool_use" not in types
    assert "text" in types


def test_anthropic_bash_tool_use_streams(client):
    r = client.post(
        "/v1/messages",
        headers={"x-api-key": ANTHROPIC_KEY},
        json={
            "model": "claude-sonnet-4-5",
            "max_tokens": 128,
            "stream": True,
            "messages": [{"role": "user", "content": "run pwd"}],
            "tools": [
                {
                    "name": "Bash",
                    "description": "Run shell",
                    "input_schema": {
                        "type": "object",
                        "properties": {"command": {"type": "string"}},
                        "required": ["command"],
                    },
                }
            ],
            "mock_tool_rounds": 1,
            "mock_seed": 99,
        },
    )
    assert r.status_code == 200
    assert "text/event-stream" in r.headers.get("content-type", "")
    body = r.text
    assert "event: message_start" in body
    assert "tool_use" in body
    assert "input_json_delta" in body
    assert "event: message_stop" in body


def test_never_calls_skill_when_read_present(client):
    r = client.post(
        "/v1/messages",
        headers={"x-api-key": ANTHROPIC_KEY},
        json={
            "model": "claude-sonnet-4-5",
            "max_tokens": 128,
            "messages": [{"role": "user", "content": "read the readme"}],
            "tools": [
                {
                    "name": "Skill",
                    "description": "Run a skill",
                    "input_schema": {
                        "type": "object",
                        "properties": {"skill": {"type": "string"}},
                        "required": ["skill"],
                    },
                },
                {
                    "name": "Read",
                    "description": "Read a file",
                    "input_schema": {
                        "type": "object",
                        "properties": {"file_path": {"type": "string"}},
                        "required": ["file_path"],
                    },
                },
                {
                    "name": "Agent",
                    "description": "Spawn agent",
                    "input_schema": {
                        "type": "object",
                        "properties": {"description": {"type": "string"}},
                        "required": ["description"],
                    },
                },
            ],
            "mock_tool_rounds": 1,
            "mock_seed": 3,
        },
    )
    assert r.status_code == 200
    body = r.json()
    tool_blocks = [b for b in body["content"] if b["type"] == "tool_use"]
    assert tool_blocks
    names = {b["name"] for b in tool_blocks}
    assert names == {"Read"}
    assert len(tool_blocks) == 1
    assert tool_blocks[0]["input"].get("file_path")


def test_only_banned_tools_yields_text_no_tool_use(client):
    r = client.post(
        "/v1/messages",
        headers={"x-api-key": ANTHROPIC_KEY},
        json={
            "model": "claude-sonnet-4-5",
            "max_tokens": 128,
            "messages": [{"role": "user", "content": "do a skill"}],
            "tools": [
                {
                    "name": "Skill",
                    "input_schema": {
                        "type": "object",
                        "properties": {"skill": {"type": "string"}},
                        "required": ["skill"],
                    },
                },
                {
                    "name": "Workflow",
                    "input_schema": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "required": ["name"],
                    },
                },
            ],
            "mock_tool_rounds": 2,
            "mock_seed": 8,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["stop_reason"] == "end_turn"
    assert "tool_use" not in {b["type"] for b in body["content"]}
    assert body["mock_my_ai"]["tool_rounds"] == []


def test_shell_readonly_fetch_banned(client):
    r = client.post(
        "/v1/messages",
        headers={"x-api-key": ANTHROPIC_KEY},
        json={
            "model": "claude-sonnet-4-5",
            "max_tokens": 128,
            "messages": [{"role": "user", "content": "list dir and fetch docs"}],
            "tools": [
                {
                    "name": "Shell",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string"},
                            "description": {"type": "string"},
                        },
                        "required": ["command", "description"],
                    },
                },
                {
                    "name": "Fetch",
                    "input_schema": {
                        "type": "object",
                        "properties": {"url": {"type": "string"}},
                        "required": ["url"],
                    },
                },
                {
                    "name": "Update",
                    "input_schema": {
                        "type": "object",
                        "properties": {"file_path": {"type": "string"}},
                        "required": ["file_path"],
                    },
                },
            ],
            "mock_tool_rounds": 1,
            "mock_seed": 21,
        },
    )
    assert r.status_code == 200
    body = r.json()
    tool_blocks = [b for b in body["content"] if b["type"] == "tool_use"]
    assert tool_blocks
    names = {b["name"] for b in tool_blocks}
    assert "Update" not in names
    assert names == {"Shell"}
    for b in tool_blocks:
        assert b["input"]["command"].split()[0] in {"pwd", "ls", "head", "cat", "find", "wc"}
        assert b["input"]["description"]


def test_tool_rounds_clamped_to_three_per_response(client):
    """mock_tool_rounds>3 is clamped; response exposes up to 3 tool_calls."""
    r = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_KEY}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "tools"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "echo",
                        "parameters": {
                            "type": "object",
                            "properties": {"text": {"type": "string"}},
                            "required": ["text"],
                        },
                    },
                }
            ],
            "mock_tool_rounds": 99,
            "mock_seed": 1,
            "mock_thinking": False,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["mock_my_ai"]["tool_rounds"]) == 1
    assert len(body["mock_my_ai"]["tool_rounds"][0]["calls"]) == 3
    assert len(body["choices"][0]["message"]["tool_calls"]) == 3


def test_tool_rounds_zero_yields_text_only(client):
    """mock_tool_rounds=0 → text+thinking only (no tool_use)."""
    r = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_KEY}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "hello"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "echo",
                        "parameters": {
                            "type": "object",
                            "properties": {"text": {"type": "string"}},
                            "required": ["text"],
                        },
                    },
                }
            ],
            "mock_tool_rounds": 0,
            "mock_seed": 2,
            "mock_thinking": True,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["mock_my_ai"]["tool_rounds"] == []
    assert body["choices"][0]["message"].get("tool_calls") is None
    assert body["choices"][0]["finish_reason"] == "stop"


def test_tool_loop_config_allows_zero_to_three(client):
    """Default config range is 0–3; forced values in range are honored."""
    from mock_my_ai.config import get_config
    cfg = get_config()
    assert cfg.generation.tool_loop_min == 0
    assert cfg.generation.tool_loop_max == 3
    for n in (1, 2, 3):
        r = client.post(
            "/v1/messages",
            headers={"x-api-key": ANTHROPIC_KEY},
            json={
                "model": "claude-sonnet-4-5",
                "max_tokens": 128,
                "messages": [{"role": "user", "content": f"tools {n}"}],
                "tools": [
                    {
                        "name": "echo",
                        "input_schema": {
                            "type": "object",
                            "properties": {"text": {"type": "string"}},
                            "required": ["text"],
                        },
                    }
                ],
                "mock_tool_rounds": n,
                "mock_seed": 10 + n,
                "mock_thinking": False,
            },
        )
        assert r.status_code == 200
        body = r.json()
        tool_blocks = [b for b in body["content"] if b["type"] == "tool_use"]
        assert len(tool_blocks) == n



def test_fetch_never_selected(client):
    """Fetch / WebFetch are banned; WebSearch is preferred and internalized."""
    r = client.post(
        "/v1/messages",
        headers={"x-api-key": ANTHROPIC_KEY},
        json={
            "model": "claude-sonnet-4-5",
            "max_tokens": 256,
            "messages": [{"role": "user", "content": "search for mock-my-ai docs"}],
            "tools": [
                {
                    "name": "Fetch",
                    "input_schema": {
                        "type": "object",
                        "properties": {"url": {"type": "string"}},
                        "required": ["url"],
                    },
                },
                {
                    "name": "WebFetch",
                    "input_schema": {
                        "type": "object",
                        "properties": {"url": {"type": "string"}},
                        "required": ["url"],
                    },
                },
                {
                    "name": "WebSearch",
                    "input_schema": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                    },
                },
            ],
            "mock_tool_rounds": 1,
            "mock_seed": 7,
            "mock_thinking": False,
        },
    )
    assert r.status_code == 200
    body = r.json()
    tool_blocks = [b for b in body["content"] if b["type"] == "tool_use"]
    assert len(tool_blocks) == 1
    assert tool_blocks[0]["name"] == "WebSearch"
    assert "query" in tool_blocks[0]["input"]
    # Internalized search payload on companion result + mock_my_ai.search_results
    rounds = body["mock_my_ai"]["tool_rounds"]
    assert rounds
    call = rounds[0]["calls"][0]
    assert call["name"] == "WebSearch"
    payload = call["result"]
    if isinstance(payload, str):
        import json as _json
        payload = _json.loads(payload)
    assert payload.get("results")
    assert payload.get("note", "").lower().find("fetch") >= 0
    assert body["mock_my_ai"]["search_results"]
    assert len(body["mock_my_ai"]["search_results"]) >= 2


def test_after_websearch_no_citations_when_search_off(client):
    """Search off: ending text must not contain 来源/Sources even after WebSearch."""
    tools = [
        {
            "name": "WebSearch",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
        {
            "name": "Fetch",
            "input_schema": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
    ]
    # Force 0 tools this turn → text end; search still off
    r = client.post(
        "/v1/messages",
        headers={"x-api-key": ANTHROPIC_KEY},
        json={
            "model": "claude-sonnet-4-5",
            "max_tokens": 256,
            "messages": [
                {"role": "user", "content": "search the web for mock-my-ai"},
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_ws1",
                            "name": "WebSearch",
                            "input": {"query": "mock-my-ai"},
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "toolu_ws1",
                            "content": "ok",
                        }
                    ],
                },
            ],
            "tools": tools,
            "mock_tool_rounds": 0,
            "mock_search": False,
            "mock_seed": 3,
            "mock_thinking": False,
        },
    )
    assert r.status_code == 200
    body = r.json()
    tool_blocks = [b for b in body["content"] if b["type"] == "tool_use"]
    assert tool_blocks == []
    text = "".join(b.get("text", "") for b in body["content"] if b["type"] == "text")
    assert "来源" not in text and "Sources:" not in text


def test_agent_loop_second_turn_can_still_tool_use(client):
    """Under agent_tool_steps_max, a second turn may still emit tool_use (0–3)."""
    tools = [
        {
            "name": "WebSearch",
            "description": "Search the web",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
        {
            "name": "Fetch",
            "description": "Fetch a URL",
            "input_schema": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
    ]
    r = client.post(
        "/v1/messages",
        headers={"x-api-key": ANTHROPIC_KEY},
        json={
            "model": "claude-sonnet-4-5",
            "max_tokens": 128,
            "messages": [{"role": "user", "content": "search something"}],
            "tools": tools,
            "mock_tool_rounds": 1,
            "mock_seed": 1,
            "mock_thinking": False,
        },
    )
    assert r.status_code == 200
    first = r.json()
    assert first["stop_reason"] == "tool_use"
    tool_blocks = [b for b in first["content"] if b["type"] == "tool_use"]
    assert len(tool_blocks) == 1
    prior_use = tool_blocks[0]

    # Second turn with one prior tool step — still under budget → can tool_use
    r = client.post(
        "/v1/messages",
        headers={"x-api-key": ANTHROPIC_KEY},
        json={
            "model": "claude-sonnet-4-5",
            "max_tokens": 256,
            "messages": [
                {"role": "user", "content": "search something"},
                {
                    "role": "assistant",
                    "content": [
                        {"type": "thinking", "thinking": "searching"},
                        prior_use,
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": prior_use["id"],
                            "content": "mock search done",
                        }
                    ],
                },
            ],
            "tools": tools,
            "mock_tool_rounds": 1,
            "mock_seed": 2,
            "mock_thinking": False,
            "mock_search": False,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["stop_reason"] == "tool_use"
    second_tools = [b for b in body["content"] if b["type"] == "tool_use"]
    assert len(second_tools) == 1
    assert second_tools[0]["name"] != "Fetch"
    text = "".join(b.get("text", "") for b in body["content"] if b["type"] == "text")
    assert "来源" not in text and "Sources:" not in text


def test_agent_budget_hard_stop_at_three(client):
    """After agent_tool_steps_max prior tool_results, never tool_use again."""
    tools = [
        {
            "name": "Bash",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["command", "description"],
            },
        }
    ]
    history = [{"role": "user", "content": "start"}]
    # Simulate 3 completed tool cycles already in the transcript
    for i in range(3):
        tid = f"call-prior-{i}"
        history.append(
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": tid,
                        "name": "Bash",
                        "input": {"command": "pwd", "description": "Print cwd"},
                    }
                ],
            }
        )
        history.append(
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": tid, "content": f"result-{i}"}
                ],
            }
        )
    r = client.post(
        "/v1/messages",
        headers={"x-api-key": ANTHROPIC_KEY},
        json={
            "model": "claude-sonnet-4-5",
            "max_tokens": 128,
            "messages": history,
            "tools": tools,
            "mock_tool_rounds": 1,  # even explicit force cannot exceed hard budget
            "mock_seed": 9,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["stop_reason"] == "end_turn"
    assert "tool_use" not in {b["type"] for b in body["content"]}

def test_websearch_query_strips_system_reminder(client):
    """Polluted Claude Code user content must not leak into WebSearch query/titles."""
    polluted = (
        "你好\n\n<system-reminder>\n# Environment\n"
        "You have been invoked in the following environment:\n"
        "- Primary working directory: /Users/demo\n"
        "</system-reminder>"
    )
    r = client.post(
        "/v1/messages",
        headers={"x-api-key": ANTHROPIC_KEY},
        json={
            "model": "claude-sonnet-4-5",
            "max_tokens": 256,
            "messages": [{"role": "user", "content": polluted}],
            "tools": [
                {
                    "name": "WebSearch",
                    "input_schema": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                    },
                }
            ],
            "mock_tool_rounds": 1,
            "mock_seed": 11,
            "mock_thinking": False,
            "mock_search": False,
        },
    )
    assert r.status_code == 200
    body = r.json()
    tool_blocks = [b for b in body["content"] if b["type"] == "tool_use"]
    assert len(tool_blocks) == 1
    assert tool_blocks[0]["name"] == "WebSearch"
    q = tool_blocks[0]["input"]["query"]
    assert "system-reminder" not in q.lower()
    assert "Environment" not in q
    assert "你好" in q or q == "你好"
    # Titles in internalized results must not contain system-reminder
    call = body["mock_my_ai"]["tool_rounds"][0]["calls"][0]
    import json as _json
    payload = call["result"]
    if isinstance(payload, str):
        payload = _json.loads(payload)
    for hit in payload.get("results") or []:
        blob = (hit.get("title") or "") + (hit.get("snippet") or "")
        assert "system-reminder" not in blob.lower()
    text = "".join(b.get("text", "") for b in body["content"] if b["type"] == "text")
    assert "来源" not in text and "Sources:" not in text



def test_chat_completions_stream(client):
    r = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_KEY}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Hello stream please"}],
            "stream": True,
            "mock_seed": 50,
            "mock_search": False,
            "mock_thinking": False,
        },
    )
    assert r.status_code == 200
    assert "text/event-stream" in r.headers.get("content-type", "")
    body = r.text
    assert "chat.completion.chunk" in body
    assert "data: [DONE]" in body
    assert '"delta"' in body
    # No noisy 来源 when search off
    assert "来源" not in body and "Sources:" not in body


def test_responses_stream(client):
    r = client.post(
        "/v1/responses",
        headers={"Authorization": f"Bearer {OPENAI_KEY}"},
        json={
            "model": "gpt-4o-mini",
            "input": "Say hello for Codex SSE",
            "stream": True,
            "mock_seed": 51,
            "mock_search": False,
            "mock_thinking": False,
        },
    )
    assert r.status_code == 200
    assert "text/event-stream" in r.headers.get("content-type", "")
    body = r.text
    assert "event: response.created" in body
    assert "event: response.output_text.delta" in body
    assert "event: response.completed" in body
    assert "response.output_item.added" in body
    assert "response.output_item.done" in body
    assert "来源" not in body and "Sources:" not in body


def test_responses_stream_non_stream_unchanged(client):
    """stream=false / omitted still returns application/json response object."""
    r = client.post(
        "/v1/responses",
        headers={"Authorization": f"Bearer {OPENAI_KEY}"},
        json={"model": "gpt-4o-mini", "input": "non-stream", "mock_seed": 52},
    )
    assert r.status_code == 200
    assert "application/json" in r.headers.get("content-type", "")
    body = r.json()
    assert body["object"] == "response"
    assert body["status"] == "completed"
    assert body["output"]
