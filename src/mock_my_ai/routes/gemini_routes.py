from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from mock_my_ai.auth import require_api_key
from mock_my_ai.generation import generate_mock, usage_gemini
from mock_my_ai.models_catalog import gemini_models

router = APIRouter(tags=["Gemini Compatible"])


class GeminiGenerateRequest(BaseModel):
    contents: list[dict[str, Any]] = Field(default_factory=list)
    systemInstruction: dict[str, Any] | None = None
    tools: list[dict[str, Any]] | None = None
    generationConfig: dict[str, Any] | None = None
    # Mock extensions
    mock_thinking: bool | None = None
    mock_search: bool | None = None
    mock_tool_rounds: int | None = None
    mock_seed: int | None = None


def _contents_to_messages(contents: list[dict[str, Any]], system: dict | None) -> list[dict[str, Any]]:
    msgs: list[dict[str, Any]] = []
    if system:
        parts = system.get("parts") or []
        text = " ".join(str(p.get("text", "")) for p in parts if isinstance(p, dict))
        if text:
            msgs.append({"role": "system", "content": text})
    for c in contents:
        role = c.get("role", "user")
        if role == "model":
            role = "assistant"
        parts = c.get("parts") or []
        texts = []
        for p in parts:
            if isinstance(p, dict) and "text" in p:
                texts.append(str(p["text"]))
            # Accept multimodal parts (image etc.) without processing
        msgs.append({"role": role, "content": "\n".join(texts)})
    return msgs


def _extract_gemini_tools(tools: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    out = []
    for t in tools or []:
        decls = t.get("functionDeclarations") or t.get("function_declarations") or []
        for d in decls:
            out.append(
                {
                    "name": d.get("name"),
                    "description": d.get("description", ""),
                    "parameters": d.get("parameters") or d.get("parametersJsonSchema") or {},
                }
            )
        if "name" in t:
            out.append(
                {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("parameters") or t.get("input_schema") or {},
                }
            )
    return out


@router.get("/v1beta/models")
@router.get("/gemini/v1beta/models")
async def list_gemini_models(
    _: str | None = Depends(require_api_key),
    pageSize: int = Query(default=100),
) -> dict[str, Any]:
    models = []
    for m in gemini_models()[:pageSize]:
        models.append(
            {
                "name": f"models/{m['id']}",
                "displayName": m["id"],
                "description": "Mock My AI catalog entry",
                "supportedGenerationMethods": ["generateContent", "countTokens"],
            }
        )
    return {"models": models}


@router.post("/v1beta/models/{model}:generateContent")
@router.post("/gemini/v1beta/models/{model}:generateContent")
async def generate_content(
    model: str,
    body: GeminiGenerateRequest,
    _: str | None = Depends(require_api_key),
) -> dict[str, Any]:
    model_id = model.removeprefix("models/")
    messages = _contents_to_messages(body.contents, body.systemInstruction)
    tools = _extract_gemini_tools(body.tools)

    # Gemini "thinking" via generationConfig extension or mock flag
    thinking = body.mock_thinking
    gen = body.generationConfig or {}
    if thinking is None and gen.get("thinkingConfig"):
        thinking = True

    result = generate_mock(
        model=model_id,
        messages=messages,
        tools=tools or None,
        enable_thinking=thinking,
        enable_search=body.mock_search,
        force_tool_rounds=body.mock_tool_rounds,
        seed=body.mock_seed,
    )

    parts: list[dict[str, Any]] = []
    if result.thinking:
        parts.append({"text": f"[thinking]\n{result.thinking}\n[/thinking]\n"})

    finish = "STOP"
    if result.tool_rounds:
        for c in result.tool_rounds[0]["calls"]:
            parts.append(
                {
                    "functionCall": {
                        "name": c["name"],
                        "args": c["arguments"],
                    }
                }
            )
        finish = "STOP"
    else:
        parts.append({"text": result.text})

    return {
        "candidates": [
            {
                "content": {"role": "model", "parts": parts},
                "finishReason": finish,
                "index": 0,
            }
        ],
        "usageMetadata": usage_gemini(result),
        "modelVersion": model_id,
        "mock_my_ai": {
            "lang": result.lang,
            "text": result.text,
            "tool_rounds": [
                {
                    "round": tr["round"],
                    "calls": [
                        {
                            "id": c["id"],
                            "name": c["name"],
                            "arguments": c["arguments"],
                            "result": c["result"],
                        }
                        for c in tr["calls"]
                    ],
                }
                for tr in result.tool_rounds
            ],
            "search_results": result.search_results,
        },
    }


@router.post("/v1beta/models/{model}:countTokens")
@router.post("/gemini/v1beta/models/{model}:countTokens")
async def count_tokens_endpoint(
    model: str,
    body: GeminiGenerateRequest,
    _: str | None = Depends(require_api_key),
) -> dict[str, Any]:
    from mock_my_ai.language import extract_text_from_messages
    from mock_my_ai.tokens import count_tokens

    messages = _contents_to_messages(body.contents, body.systemInstruction)
    text = extract_text_from_messages(messages)
    n = count_tokens(text)
    return {"totalTokens": n}
