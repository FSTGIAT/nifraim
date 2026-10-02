"""Nifra AI v2 — one agent, typed tools, fast answers. See docs/ARCHITECTURE.md §17.

    question ─► cache (user, question, data_version) ─► instant
             ─► router: one of the top intents ─► metric tool ─► templated answer + chart (no LLM)
             ─► agent loop: Sonnet 5.5 + tools (streamed, prompt-cached)

Privacy: no tool takes a user id. Every tool receives a ToolContext bound to the
session's user, and every cache key starts with that user's id.
"""
