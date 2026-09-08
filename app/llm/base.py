"""Provider-agnostic LLM contract.

Everything above this layer (agent, tools, FastAPI, chat.py) talks only in these
types, so adding Claude or OpenAI means writing one new module — nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from app.db import StoredMessage


@dataclass(frozen=True)
class ToolSpec:
    """A tool the model may call. `parameters` is plain JSON Schema."""

    name: str
    description: str
    parameters: dict


@dataclass(frozen=True)
class ToolCall:
    name: str
    args: dict


@dataclass
class Turn:
    """One provider response: either a reply for the user, or tool calls to run."""

    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    def generate(
        self,
        system: str,
        history: list[StoredMessage],
        tools: list[ToolSpec],
    ) -> Turn: ...
