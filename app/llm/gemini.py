"""Google Gemini provider (google-genai SDK) with manual tool calling."""

from __future__ import annotations

import json

from google import genai
from google.genai import types

from app.db import StoredMessage
from app.llm.base import ToolCall, ToolSpec, Turn

_TYPE_MAP = {
    "object": "OBJECT",
    "array": "ARRAY",
    "string": "STRING",
    "integer": "INTEGER",
    "number": "NUMBER",
    "boolean": "BOOLEAN",
}


def _to_gemini_schema(schema: dict) -> dict:
    """JSON Schema -> the uppercase-typed dialect the Gemini SDK expects."""
    out: dict = {}
    for key, value in schema.items():
        if key == "type" and isinstance(value, str):
            out["type"] = _TYPE_MAP.get(value, value.upper())
        elif key == "properties":
            out["properties"] = {k: _to_gemini_schema(v) for k, v in value.items()}
        elif key == "items":
            out["items"] = _to_gemini_schema(value)
        else:
            out[key] = value
    return out


def _to_contents(history: list[StoredMessage]) -> list[types.Content]:
    contents: list[types.Content] = []
    for msg in history:
        if msg.role == "user":
            contents.append(types.Content(role="user", parts=[types.Part(text=msg.content)]))
        elif msg.role == "assistant":
            contents.append(types.Content(role="model", parts=[types.Part(text=msg.content)]))
        elif msg.role == "tool_call":
            contents.append(
                types.Content(
                    role="model",
                    parts=[
                        types.Part.from_function_call(
                            name=msg.tool_name or "", args=json.loads(msg.content)
                        )
                    ],
                )
            )
        elif msg.role == "tool_result":
            contents.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_function_response(
                            name=msg.tool_name or "", response=json.loads(msg.content)
                        )
                    ],
                )
            )
    return contents


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        self.model = model
        self._client = genai.Client(api_key=api_key)

    def generate(self, system: str, history: list[StoredMessage], tools: list[ToolSpec]) -> Turn:
        declarations = [
            types.FunctionDeclaration(
                name=t.name,
                description=t.description,
                parameters=_to_gemini_schema(t.parameters),
            )
            for t in tools
        ]
        response = self._client.models.generate_content(
            model=self.model,
            contents=_to_contents(history),
            config=types.GenerateContentConfig(
                system_instruction=system,
                tools=[types.Tool(function_declarations=declarations)],
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                temperature=0.4,
            ),
        )

        candidates = response.candidates or []
        parts = (
            candidates[0].content.parts if candidates and candidates[0].content else None
        ) or []
        calls = [
            ToolCall(part.function_call.name or "", dict(part.function_call.args or {}))
            for part in parts
            if part.function_call
        ]
        text = "".join(part.text for part in parts if part.text).strip()
        return Turn(text=text or None, tool_calls=calls)
