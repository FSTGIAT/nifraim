"""Tool registry: one decorator, one frozen sorted tool list, one dispatcher.

Tools are plain async functions `fn(ctx: ToolContext, **args) -> str | dict`.
Schemas never contain a user id — `ctx.user` is the session user. The list is
sorted and frozen so the prompt-cache prefix (tools → system) is byte-stable.
The same registry can be exposed as an MCP server later (one source of tools).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)
FORBIDDEN_ARGS = {"user_id", "user", "owner_id", "agent_id"}


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    schema: dict
    category: str
    fn: Callable[..., Awaitable]
    status_he: str          # shown to the agent while it runs ("בודק חובות פתוחים…")
    action: bool = False    # proposes something the agent must approve


_TOOLS: dict[str, Tool] = {}


def tool(name: str, description: str, properties: dict | None = None, required: list[str] | None = None,
         *, category: str, status_he: str, action: bool = False):
    props = properties or {}
    assert not (set(props) & FORBIDDEN_ARGS), f"tool {name} must not take a user id"
    schema = {"type": "object", "properties": props, "required": required or [], "additionalProperties": False}

    def deco(fn):
        _TOOLS[name] = Tool(name, description, schema, category, fn, status_he, action)
        return fn
    return deco


def get(name: str) -> Tool | None:
    _load()
    return _TOOLS.get(name)


def all_tools() -> list[Tool]:
    _load()
    return sorted(_TOOLS.values(), key=lambda t: t.name)


def anthropic_tools(*, actions: bool = True) -> list[dict]:
    out = []
    for t in all_tools():
        if t.action and not actions:
            continue
        d = {"name": t.name, "description": t.description, "input_schema": t.schema}
        # the API caps strict tools at 20: strict where a malformed input would DO something
        # (actions) or break the UI (render_chart); read tools are validated by dispatch()
        if t.action or t.category == "viz":
            d["strict"] = True
        out.append(d)
    return out


async def dispatch(ctx, name: str, args: dict) -> str:
    t = get(name)
    if not t:
        return f"אין כלי בשם {name}."
    if t.action and not getattr(ctx, "allow_actions", True):
        return ("הסוכן שאל שאלה ולא ביקש לפעול — אל תכין פעולה. ענה על השאלה, ואם פעולה תעזור — "
                "הצע אותה במשפט אחד ('אפשר שאכין…').")
    args = {k: v for k, v in (args or {}).items() if k not in FORBIDDEN_ARGS and k in t.schema["properties"]}
    try:
        out = await t.fn(ctx, **args)
    except Exception as e:  # noqa: BLE001 — a tool error is a tool_result, not a crash
        logger.warning("agent tool %s failed: %r", name, e)
        try:
            await ctx.db.rollback()
            await ctx.db.refresh(ctx.user)      # rollback expired it; later tools read ctx.user.id
        except Exception:  # noqa: BLE001
            pass
        return f"הכלי {name} נכשל ({type(e).__name__}). נסה כלי אחר או ענה עם מה שיש."
    if isinstance(out, str):
        return out
    return json.dumps(out, ensure_ascii=False, default=str)


_loaded = False


def _load():
    global _loaded
    if _loaded:
        return
    _loaded = True
    from app.services.agent import tools_data, tools_maslaka, tools_market, tools_actions, tools_memory, tools_viz, tools_calls  # noqa: F401
