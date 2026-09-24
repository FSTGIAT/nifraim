"""One Anthropic call that must answer through a JSON tool — no free text to
parse, no marker scraping. Model fallback in order; a retired or overloaded
model moves to the next instead of failing the job."""
from __future__ import annotations

import logging

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-5"


class LlmUnavailable(RuntimeError):
    pass


async def call_tool(
    *, models: list[str], system: str, user: str, tool: dict, max_tokens: int = 1500,
) -> tuple[dict, str, object]:
    """Returns (tool_input, model_used, usage)."""
    if not settings.ANTHROPIC_API_KEY:
        raise LlmUnavailable("ANTHROPIC_API_KEY not set")
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY, max_retries=1, timeout=90)
    last: Exception | None = None
    for model in models:
        try:
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
            logger.warning("mail_agent.llm: %s failed (%s), trying next", model, type(e).__name__)
            last = e
            continue
        for block in resp.content:
            if block.type == "tool_use" and block.name == tool["name"]:
                return dict(block.input), model, resp.usage
        last = RuntimeError(f"{model} returned no {tool['name']} call")
    raise LlmUnavailable(str(last))
