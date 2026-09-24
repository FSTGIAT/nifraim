"""AI mail agent: reads mail from senders the agent chose, summarises it, and
drafts replies the agent approves before anything is sent.

    intake.py   poll watched senders → MailItem rows (encrypted bodies)
    triage.py   Claude Haiku → category / summary / entities / needs_reply
    draft.py    Claude Sonnet → a reply grounded in the agent's Nifraim data
    context.py  the grounding (customer products, commission-file boundaries)
    llm.py      one Anthropic call with a strict JSON tool schema + fallback
    usage.py    per-user daily cap + the ai_usage ledger
"""
