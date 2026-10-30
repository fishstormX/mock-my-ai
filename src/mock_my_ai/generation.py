from __future__ import annotations

import json
import random
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from mock_my_ai.config import get_config
from mock_my_ai.corpus import get_corpus
from mock_my_ai.language import (
    detect_language,
    extract_text_from_messages,
    extract_user_text_for_lang,
)
from mock_my_ai.models_catalog import get_model_features
from mock_my_ai.tokens import cached_tokens_for_prompt, count_tokens
from mock_my_ai.tools import SAFE_TOOLS, run_tool


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:24]}"


@dataclass
class MockResult:
    text: str
    lang: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cached_tokens: int
    thinking: str | None = None
    search_results: list[dict[str, Any]] | None = None
    tool_rounds: list[dict[str, Any]] = field(default_factory=list)
    finish_reason: str = "stop"

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


def _tool_defs(tools: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Normalize OpenAI / Anthropic / Gemini-ish tool defs to {name, schema, description}."""
    out: list[dict[str, Any]] = []
    for t in tools or []:
        if not isinstance(t, dict):
            continue
        if t.get("type") == "function" and isinstance(t.get("function"), dict):
            fn = t["function"]
            name = fn.get("name")
            schema = fn.get("parameters") or fn.get("input_schema") or {}
            desc = fn.get("description") or ""
        else:
            name = t.get("name")
            schema = t.get("input_schema") or t.get("parameters") or {}
            desc = t.get("description") or ""
        if not name:
            continue
        if not isinstance(schema, dict):
            schema = {}
        out.append({"name": str(name), "schema": schema, "description": str(desc)})
    return out


def _tool_names(tools: list[dict[str, Any]] | None) -> list[str]:
    return [d["name"] for d in _tool_defs(tools)]


def _want_thinking(model: str, request_flag: bool | None) -> bool:
    cfg = get_config().generation
    features = get_model_features(model)
    if request_flag is not None:
        return bool(request_flag)
    if features.get("thinking"):
        return True
    return cfg.thinking_enabled_default


def _effective_search_enabled() -> bool:
    """Console SQLite setting overrides YAML ``search_enabled_default`` when set."""
    try:
        from mock_my_ai.db import get_search_enabled

        return get_search_enabled()
    except Exception:
        return get_config().generation.search_enabled_default


_SEARCH_TOOL_RE = re.compile(r"(?i)web_?search|^search$|google")
_FETCH_TOOL_RE = re.compile(r"(?i)web_?fetch|^fetch$")

_SYSTEM_REMINDER_RE = re.compile(
    r"<system-reminder\b[^>]*>.*?</system-reminder>",
    re.IGNORECASE | re.DOTALL,
)
_SYSTEM_REMINDER_OPEN_RE = re.compile(
    r"<system-reminder\b[^>]*>.*",
    re.IGNORECASE | re.DOTALL,
)
_ENV_HEADER_RE = re.compile(r"(?is)#\s*Environment\b.*?(?=\n#\s|\Z)")


def _sanitize_user_probe(text: str) -> str:
    """Strip Claude Code injected blocks; keep a short clean user utterance.

    Prefer a brief Chinese/English line (e.g. 「你好」) over ``<system-reminder>`` /
    ``# Environment`` dumps that otherwise pollute WebSearch queries and titles.
    """
    if not text:
        return ""
    s = _SYSTEM_REMINDER_RE.sub(" ", text)
    s = _SYSTEM_REMINDER_OPEN_RE.sub(" ", s)
    s = _ENV_HEADER_RE.sub(" ", s)
    s = re.sub(
        r"(?im)^(?:Primary working directory|You have been invoked)\b.*$",
        " ",
        s,
    )
    s = re.sub(r"</?system-reminder\b[^>]*>", " ", s, flags=re.I)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{2,}", "\n", s).strip()
    if not s:
        return ""
    # Prefer a short CJK utterance when present (typical Claude Code + Chinese user)
    cjk_runs = re.findall(r"[\u4e00-\u9fff]{1,40}", s)
    if cjk_runs:
        # Prefer the first short run (user greeting) over later noise
        return cjk_runs[0].strip()
    # First non-empty line, truncated
    for line in s.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#") or line.startswith("<"):
            continue
        return line[:80]
    return s[:80]


def _has_search_named_tool(tools: list[dict[str, Any]] | None) -> bool:
    return any(_SEARCH_TOOL_RE.search(n) for n in _tool_names(tools))


def _want_search(
    model: str,
    request_flag: bool | None,
    tools: list[dict[str, Any]] | None = None,
) -> bool:
    """Decide whether to attach mock search citations (「来源」).

    - ``mock_search: false`` always disables
    - ``mock_search: true`` always enables
    - else: instance search switch (console / ``search_enabled_default``) AND
      model ``features.search``

    Prefer emitting WebSearch tool_use when that tool is declared; citations stay
    off by default unless the console switch / mock_search enables them.
    """
    if request_flag is False:
        return False
    if request_flag is True:
        return True
    if not _effective_search_enabled():
        return False
    features = get_model_features(model)
    return bool(features.get("search"))


def _mock_thinking(lang: str, rng: random.Random) -> str:
    cfg = get_config().generation
    n = rng.randint(cfg.thinking_token_min, cfg.thinking_token_max)
    snippets = {
        "zh": [
            "先理解用户问题的核心意图。",
            "检查是否需要调用工具。",
            "组织一个清晰、简洁的回答结构。",
            "确认语气与语言一致。",
            "避免引入无关话题。",
            "优先使用只读工具收集上下文。",
        ],
        "en": [
            "Identify the user's main intent.",
            "Decide whether tools are needed.",
            "Outline a clear, concise answer.",
            "Keep language consistent with the query.",
            "Avoid unrelated topics.",
            "Prefer read-only tools to gather context.",
        ],
        "ja": [
            "ユーザーの意図を整理する。",
            "ツールが必要か判断する。",
            "簡潔な回答の流れを作る。",
            "言語を質問に合わせる。",
            "無関係な話題は避ける。",
        ],
        "es": [
            "Identificar la intención principal.",
            "Decidir si hacen falta herramientas.",
            "Esbozar una respuesta clara.",
            "Mantener el idioma de la consulta.",
            "Evitar temas no relacionados.",
        ],
        "fr": [
            "Identifier l'intention principale.",
            "Décider si des outils sont nécessaires.",
            "Structurer une réponse claire.",
            "Garder la langue de la requête.",
            "Éviter les sujets hors sujet.",
        ],
    }
    pool = snippets.get(lang, snippets["en"])
    parts = [rng.choice(pool) for _ in range(max(2, n // 25))]
    text = (" " if lang not in ("zh", "ja") else "").join(parts)
    while count_tokens(text) < n:
        extra = rng.choice(pool)
        text = text + ((" " + extra) if lang not in ("zh", "ja") else extra)
    return text


def _mock_search(query: str, lang: str, rng: random.Random) -> list[dict[str, Any]]:
    """Varied mock search hits — clearly fake, multi-lang titles/snippets."""
    q = _sanitize_user_probe(query) or (query or "general").strip()[:80] or "general"
    # Guard: never leak system-reminder fragments into titles
    if "system-reminder" in q.lower() or "# environment" in q.lower():
        q = "general"
    q = q[:80]
    titles = {
        "en": [
            f"What is {q}? A practical overview",
            f"{q} — FAQ and common pitfalls",
            f"Deep dive: {q} for engineers",
            f"Cheatsheet: working with {q}",
            f"Community notes on {q}",
        ],
        "zh": [
            f"关于{q}的简明概述",
            f"{q}：常见问题与实践",
            f"深入理解 {q}",
            f"{q} 速查表",
            f"社区讨论：{q}",
        ],
        "ja": [
            f"{q}の概要",
            f"{q}のFAQ",
            f"実践：{q}",
            f"{q}チートシート",
            f"コミュニティメモ：{q}",
        ],
        "es": [
            f"Resumen de {q}",
            f"FAQ sobre {q}",
            f"Guía práctica: {q}",
            f"Notas comunitarias: {q}",
        ],
        "fr": [
            f"Aperçu de {q}",
            f"FAQ : {q}",
            f"Guide pratique — {q}",
            f"Notes communautaires : {q}",
        ],
    }
    snippets = {
        "en": [
            f"Mock result summarizing key ideas about {q}. Not a real web page.",
            f"This fictional article walks through {q} with examples and caveats.",
            f"Random mock snippet #{rng.randint(100, 999)} related to {q}.",
            f"Background context for {q}; generated for API testing only.",
        ],
        "zh": [
            f"与「{q}」相关的模拟搜索摘要，非真实网页。",
            f"虚构文章介绍 {q} 的要点与注意事项。",
            f"随机模拟片段 #{rng.randint(100, 999)}，仅用于联调。",
            f"关于 {q} 的背景说明（Mock）。",
        ],
        "ja": [
            f"{q}に関するモック検索スニペットです。",
            f"テスト用の架空記事：{q}。",
            f"ランダム mock #{rng.randint(100, 999)} — {q}。",
        ],
        "es": [
            f"Fragmento mock sobre {q}. No es una página real.",
            f"Artículo ficticio de prueba acerca de {q}.",
        ],
        "fr": [
            f"Extrait mock sur {q}. Pas une vraie page.",
            f"Article fictif de test concernant {q}.",
        ],
    }
    domains = [
        "example.com",
        "docs.example.org",
        "wiki.mock.local",
        "blog.mock.dev",
        "kb.example.net",
    ]
    tpool = titles.get(lang, titles["en"])
    spool = snippets.get(lang, snippets["en"])
    results: list[dict[str, Any]] = []
    n = rng.randint(2, 4)
    used: set[str] = set()
    for i in range(n):
        title = rng.choice(tpool)
        tries = 0
        while title in used and tries < 5:
            title = rng.choice(tpool)
            tries += 1
        used.add(title)
        domain = rng.choice(domains)
        slug = abs(hash(f"{title}:{i}:{rng.random()}")) % 100000
        results.append(
            {
                "title": title,
                "url": f"https://{domain}/mock/{slug}",
                "snippet": rng.choice(spool),
            }
        )
    return results


def _format_search_citation(search_results: list[dict[str, Any]], lang: str) -> str:
    header = {
        "en": "\n\nSources:",
        "zh": "\n\n来源：",
        "ja": "\n\n出典:",
        "es": "\n\nFuentes:",
        "fr": "\n\nSources :",
    }.get(lang, "\n\nSources:")
    lines = [header]
    for r in search_results:
        lines.append(f"- [{r['title']}]({r['url']}): {r['snippet']}")
    return "\n".join(lines)


# Tools that blow up Claude Code when stubbed with invented ids/names.
_BANNED_TOOL_RE = re.compile(
    r"(?i)^(Skill|SlashCommand|Workflow|Artifact|Edit|Write|Update|NotebookEdit|"
    r"Notebook|TodoWrite|Agent|Task|ExitPlanMode|EnterPlanMode|Stop|Cron\w*|"
    r"ExitPlan|PlanMode|Fetch|WebFetch|Web_Fetch)$"
)

# Preference order for tools we are willing to mock-call (read / search oriented).
_PREFERRED_TOOL_ORDER = [
    "websearch",
    "web_search",
    "read",
    "glob",
    "grep",
    "ls",
    "bash",
    "shell",
    "echo",
    "list_files",
]

_READONLY_SHELL = [
    ("pwd", "Print the current working directory"),
    ("ls", "List files in the current directory"),
    ("ls -la", "List all files with details in the current directory"),
    ("ls -la .", "List detailed contents of the current directory"),
    ("head -n 20 README.md", "Show the first 20 lines of README.md"),
    ("cat README.md", "Read the contents of README.md"),
    ("find . -maxdepth 1 -type f", "List files in the current directory only"),
    ("wc -l README.md", "Count lines in README.md"),
]

_WRITEISH_SHELL_RE = re.compile(
    r"(?i)(\brm\b|\bmv\b|\bcp\b|\btouch\b|\bchmod\b|\bchown\b|\bmkdir\b|\brmdir\b|"
    r"\btee\b|\bnpm\s+install\b|\bpip\s+install\b|\bapt\b|\byum\b|\bdnf\b|"
    r"\bgit\s+(commit|push|reset|checkout)\b|>|>>|<<|\bdd\b|\bmkfs\b)"
)


def _is_banned_tool(name: str) -> bool:
    if _BANNED_TOOL_RE.match(name or ""):
        return True
    # Never mock-call Fetch / WebFetch — search results are internalized in WebSearch.
    if _FETCH_TOOL_RE.search(name or ""):
        return True
    return False


def _prefer_key(name: str) -> tuple[int, str]:
    lname = (name or "").lower()
    try:
        return (_PREFERRED_TOOL_ORDER.index(lname), lname)
    except ValueError:
        if _SEARCH_TOOL_RE.search(name):
            return (0, lname)
        return (len(_PREFERRED_TOOL_ORDER) + 10, lname)


def _filter_callable_tools(defs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep only tools safe to mock-call for Claude Code; prefer read/search."""
    allowed = [d for d in defs if not _is_banned_tool(d["name"])]
    preferred = [
        d
        for d in allowed
        if d["name"].lower() in set(_PREFERRED_TOOL_ORDER)
        or _SEARCH_TOOL_RE.search(d["name"])
    ]
    pool = preferred if preferred else allowed
    return sorted(pool, key=lambda d: _prefer_key(d["name"]))


def _guess_file_from_text(user_text: str) -> str:
    if not user_text:
        return "README.md"
    m = re.search(
        r"(?i)\b([\w./-]+\.(?:md|py|ts|tsx|js|jsx|json|ya?ml|toml|txt|go|rs|java|c|cpp|h))\b",
        user_text,
    )
    if m:
        p = m.group(1)
        if not p.startswith("/") and ".." not in p:
            return p
    return "README.md"


def _pick_readonly_shell(rng: random.Random) -> tuple[str, str]:
    return rng.choice(_READONLY_SHELL)


def _stub_value_for_prop(
    *,
    name: str,
    key: str,
    prop: dict[str, Any],
    user_text: str,
    round_idx: int,
    rng: random.Random,
    ctx: dict[str, Any],
) -> Any:
    """Plausible stub for one schema property — never invent undeclared keys."""
    if isinstance(prop.get("enum"), list) and prop["enum"]:
        return rng.choice(prop["enum"])
    if "const" in prop:
        return prop["const"]

    ptype = prop.get("type", "string")
    lname = (name or "").lower()
    lkey = key.lower()

    if lkey in ("command", "cmd") or (lname in ("bash", "shell") and lkey in ("command", "cmd")):
        cmd, _desc = ctx.setdefault("_shell", _pick_readonly_shell(rng))
        return cmd
    if lkey == "description" and lname in ("bash", "shell"):
        _cmd, desc = ctx.setdefault("_shell", _pick_readonly_shell(rng))
        return desc
    if lkey in ("query", "q", "search_query", "search"):
        q = _sanitize_user_probe(user_text) or "mock query"
        return q[:120]
    if lkey in ("url", "uri", "href", "link") or (
        _FETCH_TOOL_RE.search(name or "") and lkey in ("url", "uri", "href", "link")
    ):
        return rng.choice(
            [
                "https://example.com/",
                "https://example.com/docs",
                "https://example.org/mock",
                "https://httpbin.org/get",
            ]
        )
    if lkey in ("file_path", "filepath", "filename", "file"):
        return _guess_file_from_text(user_text)
    if lkey == "path":
        if lname == "read":
            return _guess_file_from_text(user_text)
        if lname in ("ls", "glob", "list_files"):
            return "."
        return _guess_file_from_text(user_text)
    if lkey in ("pattern", "glob", "glob_pattern"):
        return "*.md" if "grep" not in lname else "README"
    if lkey == "regex":
        return "README"
    if lkey in ("include", "includes"):
        return "*.md"
    if lkey in ("text", "message", "content", "prompt", "input") and lname in (
        "echo",
        "list_files",
    ):
        return f"mock-{name}-round-{round_idx}"
    if lkey in ("offset", "limit", "max_results", "num_results", "count", "head_limit"):
        return 0 if lkey == "offset" else 20
    if lkey in ("case_insensitive", "multiline"):
        return lkey == "case_insensitive"

    if "default" in prop:
        return prop["default"]

    if ptype == "integer":
        return 1
    if ptype == "number":
        return 1.0
    if ptype == "boolean":
        return False
    if ptype == "array":
        return []
    if ptype == "object":
        return {}
    if isinstance(ptype, list):
        if "string" in ptype:
            return ""
        if "integer" in ptype:
            return 1
        if "boolean" in ptype:
            return False
        if "null" in ptype:
            return None
    if lkey in ("description", "desc", "summary", "reason", "rationale"):
        return f"Inspect project context (round {round_idx})"
    return f"value-{key}"


def _stub_args_from_schema(
    name: str,
    schema: dict[str, Any],
    *,
    user_text: str,
    round_idx: int,
    rng: random.Random,
) -> dict[str, Any]:
    props = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    required = schema.get("required")
    ctx: dict[str, Any] = {}

    if isinstance(required, list) and required:
        # Fill EVERY required property (Claude Code validates strictly).
        keys = [str(k) for k in required]
    elif props:
        preferred = [
            k
            for k in (
                "command",
                "description",
                "query",
                "url",
                "text",
                "path",
                "file_path",
                "pattern",
                "glob_pattern",
                "message",
                "content",
            )
            if k in props
        ]
        keys = preferred if preferred else list(props.keys())[:3]
    else:
        lname = name.lower()
        if lname in ("bash", "shell"):
            cmd, desc = _pick_readonly_shell(rng)
            return {"command": cmd, "description": desc}
        if _SEARCH_TOOL_RE.search(name):
            q = (user_text or "mock query").strip() or "mock query"
            return {"query": q[:120]}
        if _FETCH_TOOL_RE.search(name):
            return {"url": "https://example.com/"}
        if lname == "read":
            return {"file_path": _guess_file_from_text(user_text)}
        if lname == "glob":
            return {"pattern": "*.md"}
        if lname == "grep":
            return {"pattern": "README"}
        if lname == "ls":
            return {"path": "."}
        if lname == "echo":
            return {"text": f"mock-echo-round-{round_idx}"}
        if lname == "list_files":
            return {"path": "."}
        return {}

    if name.lower() in ("bash", "shell"):
        ctx["_shell"] = _pick_readonly_shell(rng)

    args: dict[str, Any] = {}
    for key in keys:
        prop = props.get(key) if isinstance(props.get(key), dict) else {}
        args[key] = _stub_value_for_prop(
            name=name,
            key=key,
            prop=prop or {},
            user_text=user_text,
            round_idx=round_idx,
            rng=rng,
            ctx=ctx,
        )

    # Hard guarantee: shell commands stay read-only even if schema/enum tried otherwise
    if name.lower() in ("bash", "shell") and "command" in args:
        cmd = str(args["command"])
        if _WRITEISH_SHELL_RE.search(cmd) or not cmd.strip():
            c, d = _pick_readonly_shell(rng)
            args["command"] = c
            if "description" in args:
                args["description"] = d
    return args


def _is_search_tool(name: str) -> bool:
    return bool(_SEARCH_TOOL_RE.search(name or ""))

def _prior_used_search_tool(messages: list[dict[str, Any]] | None) -> bool:
    """True if conversation already contains a WebSearch-style tool_use."""
    if not messages:
        return False
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        tcalls = msg.get("tool_calls")
        if isinstance(tcalls, list):
            for tc in tcalls:
                if not isinstance(tc, dict):
                    continue
                fn = tc.get("function") if isinstance(tc.get("function"), dict) else {}
                name = str(fn.get("name") or tc.get("name") or "")
                if _is_search_tool(name):
                    return True
        content = msg.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    if _is_search_tool(str(block.get("name") or "")):
                        return True
        if msg.get("type") == "function_call" and _is_search_tool(str(msg.get("name") or "")):
            return True
    return False


def _choose_tool_calls(
    tool_defs: list[dict[str, Any]],
    round_idx: int,
    rng: random.Random,
    *,
    user_text: str = "",
    lang: str = "en",
    count: int = 1,
) -> list[dict[str, Any]]:
    """Produce ``count`` tool_use payloads for callable (non-banned) client tools.

    WebSearch results are fabricated in-process and stored on the call ``result``
    so the client does not need a follow-up Fetch.
    """
    tool_defs = _filter_callable_tools(tool_defs)
    if not tool_defs or count <= 0:
        return []
    # Prefer WebSearch when present so search is internalized in one step.
    search_defs = [d for d in tool_defs if _is_search_tool(d["name"])]
    pool = search_defs if search_defs else tool_defs
    top = pool[: max(1, min(4, len(pool)))]
    chosen: list[dict[str, Any]] = []
    for i in range(count):
        # First pick prefers search pool; later picks draw from full callable set
        # for variety when multiple tools are requested in one response.
        src = top if (i == 0 or not tool_defs) else tool_defs
        chosen.append(rng.choice(src))
    cfg = get_config()
    enabled = set(cfg.tools.enabled)
    calls: list[dict[str, Any]] = []
    for td in chosen:
        name = td["name"]
        schema = td.get("schema") or {}
        if name == "echo" and not (schema.get("properties") or schema.get("required")):
            args = {"text": f"mock-echo-round-{round_idx}"}
        elif name == "list_files" and not (schema.get("properties") or schema.get("required")):
            args = {"path": "."}
        else:
            args = _stub_args_from_schema(
                name, schema, user_text=user_text, round_idx=round_idx, rng=rng
            )
            if name == "echo" and "text" not in args:
                args["text"] = f"mock-echo-round-{round_idx}"
            if name == "list_files" and "path" not in args:
                args.setdefault("path", ".")

        search_hits: list[dict[str, Any]] | None = None
        if name in SAFE_TOOLS and name in enabled:
            result = run_tool(name, args)
        elif _is_search_tool(name):
            q = str(
                args.get("query")
                or args.get("q")
                or args.get("search_query")
                or user_text
                or "general"
            ).strip() or "general"
            search_hits = _mock_search(q, lang, rng)
            result = json.dumps(
                {
                    "mock": True,
                    "executed": True,
                    "name": name,
                    "query": q,
                    "results": search_hits,
                    "note": "Search results internalized; no Fetch required",
                },
                ensure_ascii=False,
            )
        else:
            result = json.dumps(
                {
                    "mock": True,
                    "executed": False,
                    "name": name,
                    "note": "tool_use emitted with stub args; not executed on server",
                },
                ensure_ascii=False,
            )

        call_id = new_id("call")
        call: dict[str, Any] = {
            "id": call_id,
            "type": "function",
            "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)},
            "name": name,
            "arguments": args,
            "result": result,
        }
        if search_hits is not None:
            call["search_results"] = search_hits
        calls.append(call)
    return calls



def _count_prior_tool_steps(messages: list[dict[str, Any]] | None) -> int:
    """Count prior tool activity in the conversation (tool_use and/or tool_result).

    Uses max(tool_use_count, tool_result_count) so OpenAI-style tool role messages
    and Anthropic content blocks both advance the agent-loop budget.
    """
    if not messages:
        return 0
    uses = 0
    results = 0
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        # OpenAI assistant tool_calls
        tcalls = msg.get("tool_calls")
        if isinstance(tcalls, list):
            uses += len(tcalls)
        role = str(msg.get("role") or "")
        if role == "tool":
            results += 1
        content = msg.get("content")
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "tool_use":
                    uses += 1
                elif btype == "tool_result":
                    results += 1
        # Some clients nest function_call style
        if msg.get("type") == "function_call":
            uses += 1
        if msg.get("type") == "function_call_output":
            results += 1
    return max(uses, results)


def generate_mock(
    *,
    model: str,
    messages: list[dict[str, Any]] | None = None,
    prompt: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    enable_thinking: bool | None = None,
    enable_search: bool | None = None,
    force_tool_rounds: int | None = None,
    seed: int | None = None,
) -> MockResult:
    cfg = get_config()
    rng = random.Random(seed if seed is not None else time.time_ns())

    if messages:
        full_text = extract_text_from_messages(messages)
        lang_text_raw = extract_user_text_for_lang(messages)
    else:
        full_text = prompt or ""
        lang_text_raw = full_text

    # Clean Claude Code <system-reminder> / Environment dumps before lang + search.
    lang_text = _sanitize_user_probe(lang_text_raw) or _sanitize_user_probe(full_text)
    probe_for_lang = lang_text or _sanitize_user_probe(full_text) or "hello"

    # Language must follow the last user turn — not the system prompt.
    lang = detect_language(probe_for_lang, fallback=cfg.corpus.fallback_language)
    corpus = get_corpus()

    qa_probe = lang_text or probe_for_lang
    custom = corpus.match_custom_qa(qa_probe, lang)
    if custom:
        text = custom
    else:
        text = corpus.pick(lang, rng=rng)

    # Debug-friendly: thinking on by default (config); also force when tools present
    thinking_flag = enable_thinking
    if thinking_flag is None and tools:
        thinking_flag = True
    thinking = None
    if _want_thinking(model, thinking_flag):
        thinking = _mock_thinking(lang, rng)

    search_results = None
    want_search = _want_search(model, enable_search, tools)
    if want_search:
        search_query = lang_text or "general"
        search_results = _mock_search(search_query, lang, rng)
        if not custom:
            text = text + _format_search_citation(search_results, lang)

    # Tool loops — only callable (non-banned) client tools. Prefer WebSearch /
    # Read / Glob / Grep / LS / Bash|Shell. Never Skill/Edit/Write/Fetch/Agent/…
    #
    # Agent-loop budget: once messages already contain enough prior tool_use /
    # tool_result steps, stop emitting tool_use so Claude Code ends the loop.
    prior_steps = _count_prior_tool_steps(messages)
    budget = max(1, min(5, int(cfg.generation.agent_tool_steps_max)))
    agent_budget_exhausted = prior_steps >= budget

    defs = _filter_callable_tools(_tool_defs(tools))
    if agent_budget_exhausted:
        defs = []
    elif not defs:
        # Explicit mock_tool_rounds>0 with no callable client tools → demo safe tools
        # (but NOT when the client only sent banned tools — text-only instead)
        client_sent_tools = bool(_tool_defs(tools))
        if (
            force_tool_rounds is not None
            and force_tool_rounds > 0
            and not client_sent_tools
        ):
            defs = [
                {
                    "name": n,
                    "schema": SAFE_TOOLS[n]["parameters"],
                    "description": SAFE_TOOLS[n]["description"],
                }
                for n in cfg.tools.enabled
                if n in SAFE_TOOLS
            ]
        else:
            defs = []

    tool_rounds: list[dict[str, Any]] = []
    if defs:
        # Per HTTP response: random 0–3 tool_use calls (config tool_loop_min/max).
        # Packed into one round so OpenAI/Anthropic expose all calls to the client.
        # Hard stop across turns: agent_tool_steps_max only (no early soft-stop).
        _cap = 3
        if force_tool_rounds is not None:
            n_calls = max(0, min(_cap, force_tool_rounds))
        else:
            lo = max(0, min(_cap, cfg.generation.tool_loop_min))
            hi = max(lo, min(_cap, cfg.generation.tool_loop_max))
            n_calls = rng.randint(lo, hi) if hi >= lo else 0
        if n_calls > 0:
            calls = _choose_tool_calls(
                defs,
                0,
                rng,
                user_text=lang_text or "hello",
                lang=lang,
                count=n_calls,
            )
            if calls:
                tool_rounds.append({"round": 0, "calls": calls[:n_calls]})

    # Lift WebSearch hits into metadata only. Never append 「来源」/Sources to
    # assistant text unless want_search (console switch / mock_search) is on —
    # internalization lives in tool call result JSON + search_results metadata.
    for tr in tool_rounds:
        for c in tr.get("calls") or []:
            hits = c.get("search_results")
            if hits:
                search_results = hits
                break
        else:
            continue
        break

    prompt_tokens = count_tokens(full_text) + (count_tokens(thinking or "") // 4)
    completion_body = text
    if thinking:
        completion_body = thinking + "\n" + text
    completion_tokens = count_tokens(completion_body)
    for tr in tool_rounds:
        completion_tokens += count_tokens(json.dumps(tr)) // 4

    cached = cached_tokens_for_prompt(prompt_tokens, model, rng)

    return MockResult(
        text=text,
        lang=lang,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cached_tokens=cached,
        thinking=thinking,
        search_results=search_results,
        tool_rounds=tool_rounds,
        finish_reason="tool_calls" if tool_rounds and not custom else "stop",
    )


def usage_openai(result: MockResult) -> dict[str, Any]:
    return {
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
        "total_tokens": result.total_tokens,
        "prompt_tokens_details": {
            "cached_tokens": result.cached_tokens,
        },
        "completion_tokens_details": {
            "reasoning_tokens": count_tokens(result.thinking) if result.thinking else 0,
        },
    }


def usage_anthropic(result: MockResult) -> dict[str, Any]:
    return {
        "input_tokens": result.prompt_tokens,
        "output_tokens": result.completion_tokens,
        "cache_read_input_tokens": result.cached_tokens,
    }


def usage_gemini(result: MockResult) -> dict[str, Any]:
    return {
        "promptTokenCount": result.prompt_tokens,
        "candidatesTokenCount": result.completion_tokens,
        "totalTokenCount": result.total_tokens,
        "cachedContentTokenCount": result.cached_tokens,
    }
