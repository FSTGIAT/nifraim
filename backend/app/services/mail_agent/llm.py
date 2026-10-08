"""One Anthropic call that must answer through a JSON tool — no free text to
parse, no marker scraping. Model fallback in order; a retired or overloaded
model moves to the next instead of failing the job."""
from __future__ import annotations

import copy
import json
import logging

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-5"


class LlmUnavailable(RuntimeError):
    pass


# These models refuse a FORCED tool_choice ("tool"/"any") with a 400 — measured in prod 2026-10-07:
# every call summary hit the 400 on claude-sonnet-5-5 and silently fell back to claude-sonnet-5.
# For them the same JSON comes back through structured outputs (output_config.format) instead.
NO_FORCED_TOOL = ("claude-sonnet-5-5", "claude-opus-5-5", "claude-fable-5-1", "claude-mythos-5-1")
_UNSUPPORTED = ("maxItems", "minItems", "minLength", "maxLength", "minimum", "maximum", "pattern", "format", "default")


def output_schema(schema: dict) -> dict:
    """The tool's input_schema made acceptable to structured outputs: objects closed
    (additionalProperties false), keywords it doesn't support dropped. The prompt still asks
    for the limits; the schema just stops enforcing them."""
    def walk(node):
        if isinstance(node, dict):
            for k in _UNSUPPORTED:
                node.pop(k, None)
            if node.get("type") == "object" or "properties" in node:
                node["additionalProperties"] = False
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
        return node
    return walk(copy.deepcopy(schema))


async def call_tool(
    *, models: list[str], system: str, user: str, tool: dict, max_tokens: int = 1500,
) -> tuple[dict, str, object]:
    """Returns (tool_input, model_used, usage)."""
    if not settings.ANTHROPIC_API_KEY:
        raise LlmUnavailable("ANTHROPIC_API_KEY not set")
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY, max_retries=1, timeout=90)
    last: Exception | None = None
    for model in models:
        structured = model.startswith(NO_FORCED_TOOL)
        try:
            if structured:
                resp = await client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                    output_config={"format": {"type": "json_schema", "schema": output_schema(tool["input_schema"])}},
                )
            else:
                resp = await client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                    tools=[tool],
                    tool_choice={"type": "tool", "name": tool["name"]},
                )
        except anthropic.AuthenticationError:
            raise
        except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
            # the message, not just the class — "BadRequestError" alone hid a model-API limit for days
            logger.warning("mail_agent.llm: %s failed (%s: %s), trying next", model, type(e).__name__, str(e)[:200])
            last = e
            continue
        if structured:
            if resp.stop_reason not in ("refusal", "max_tokens"):
                text = next((b.text for b in resp.content if b.type == "text"), "")
                try:
                    return json.loads(text), model, resp.usage
                except ValueError:
                    pass
            last = RuntimeError(f"{model} returned no valid JSON (stop={resp.stop_reason})")
            continue
        for block in resp.content:
            if block.type == "tool_use" and block.name == tool["name"]:
                return dict(block.input), model, resp.usage
        last = RuntimeError(f"{model} returned no {tool['name']} call")
    raise LlmUnavailable(str(last))
