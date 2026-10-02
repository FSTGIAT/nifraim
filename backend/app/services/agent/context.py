"""ToolContext — the ONLY way a tool reaches data. Bound to one user."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


@dataclass
class ToolContext:
    db: AsyncSession
    user: User
    data_version: int = 0
    prefetched: str = ""                               # tool output fetched before the model (prefetch.py)
    allow_actions: bool = True                         # False = a question: action tools refuse
    _map: Any = None                                   # data_map.MapContext, loaded once per turn
    results: dict[str, dict] = field(default_factory=dict)   # result_id -> chartable rows (render_chart refs)
    vizs: list[dict] = field(default_factory=list)            # charts to emit
    proposals: list[dict] = field(default_factory=list)       # actions awaiting the agent's click

    async def map(self):
        """The data map context (merged comparison + rates + cases + mail) — the same
        source the dashboards' office-agent pages use. Cached per data_version."""
        if self._map is None:
            from app.services import data_map
            from app.services.agent import cache
            key = ("map",)
            hit = cache.get(self.user.id, self.data_version, key)
            if hit is None:
                hit = await data_map.load(self.db, self.user)
                cache.put(self.user.id, self.data_version, key, hit, ttl=1800)
            self._map = hit
        return self._map

    def keep(self, rows: list[dict], *, label: str, value: str, unit: str = "₪", title: str = "") -> str:
        """Store chartable rows; returns a result_id the model passes to render_chart."""
        rid = "r" + uuid.uuid4().hex[:6]
        self.results[rid] = {"rows": rows, "label": label, "value": value, "unit": unit, "title": title}
        return rid
