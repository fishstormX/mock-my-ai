from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from mock_my_ai.config import AppConfig, get_config

SAFE_TOOLS = {
    "echo": {
        "name": "echo",
        "description": "Echo back the provided text. Read-only, no side effects.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to echo"},
            },
            "required": ["text"],
        },
    },
    "list_files": {
        "name": "list_files",
        "description": "List files in a directory under the configured root (read-only).",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path under the list_files root",
                    "default": ".",
                },
            },
            "required": [],
        },
    },
}


def enabled_tool_defs(cfg: AppConfig | None = None) -> list[dict[str, Any]]:
    cfg = cfg or get_config()
    out = []
    for name in cfg.tools.enabled:
        if name in SAFE_TOOLS:
            out.append(SAFE_TOOLS[name])
    return out


def openai_tools_schema(cfg: AppConfig | None = None) -> list[dict[str, Any]]:
    return [
        {"type": "function", "function": t}
        for t in enabled_tool_defs(cfg)
    ]


def anthropic_tools_schema(cfg: AppConfig | None = None) -> list[dict[str, Any]]:
    return [
        {
            "name": t["name"],
            "description": t["description"],
            "input_schema": t["parameters"],
        }
        for t in enabled_tool_defs(cfg)
    ]


def run_tool(name: str, arguments: dict[str, Any] | str, cfg: AppConfig | None = None) -> str:
    cfg = cfg or get_config()
    if name not in cfg.tools.enabled or name not in SAFE_TOOLS:
        return json.dumps({"error": f"tool '{name}' is not enabled"})

    if isinstance(arguments, str):
        try:
            args = json.loads(arguments) if arguments else {}
        except json.JSONDecodeError:
            args = {"text": arguments}
    else:
        args = arguments or {}

    if name == "echo":
        return str(args.get("text", ""))

    if name == "list_files":
        root = cfg.list_files_root().resolve()
        rel = args.get("path") or "."
        # Prevent path escape
        target = (root / rel).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            return json.dumps({"error": "path escapes list_files_root"})
        if not target.exists():
            return json.dumps({"error": "path not found", "path": rel})
        if target.is_file():
            return json.dumps({"type": "file", "name": target.name, "size": target.stat().st_size})
        entries = []
        try:
            for i, p in enumerate(sorted(target.iterdir(), key=lambda x: x.name)):
                if i >= cfg.tools.list_files_max:
                    break
                entries.append(
                    {
                        "name": p.name,
                        "type": "dir" if p.is_dir() else "file",
                        "size": (p.stat().st_size if p.is_file() else None),
                    }
                )
        except OSError as e:
            return json.dumps({"error": str(e)})
        return json.dumps({"path": rel, "entries": entries}, ensure_ascii=False)

    return json.dumps({"error": "unknown tool"})


def parse_tool_calls_from_request(tools: list | None) -> list[dict[str, Any]]:
    """Normalize request-provided tool definitions (OpenAI style)."""
    out = []
    for t in tools or []:
        if not isinstance(t, dict):
            continue
        if t.get("type") == "function" and isinstance(t.get("function"), dict):
            fn = t["function"]
            out.append({"name": fn.get("name"), "description": fn.get("description", "")})
        elif "name" in t:
            out.append({"name": t["name"], "description": t.get("description", "")})
    return out
