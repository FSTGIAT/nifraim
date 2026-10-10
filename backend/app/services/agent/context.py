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
    named_customer: str | None = None                   # a customer's full name found in the question
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

    async def book_state(self) -> dict:
        """What of the agent's OWN data exists yet: production, נפרעים, מסלקה. A new agent has none — the
        fast lane answered "כל מה שצפוי שולם" on an empty account (2026-10-10). Market data is public and
        needs none of this."""
        if getattr(self, "_book", None) is None:
            from sqlalchemy import func, select
            from app.models.maslaka_agent_link import MaslakaAgentLink
            from app.models.pension_holding import PensionHolding
            from app.models.upload import FileUpload
            uid = self.user.id
            prod = (await self.db.execute(select(func.count()).select_from(FileUpload).where(
                FileUpload.user_id == uid, FileUpload.is_production.is_(True)))).scalar_one()
            other = (await self.db.execute(select(func.count()).select_from(FileUpload).where(
                FileUpload.user_id == uid, FileUpload.is_production.is_not(True)))).scalar_one()
            mas = (await self.db.execute(select(func.count(func.distinct(PensionHolding.customer_id_number))).where(
                PensionHolding.user_id == uid))).scalar_one()
            link = (await self.db.execute(select(MaslakaAgentLink.status).where(MaslakaAgentLink.user_id == uid))).scalars().first()
            self._book = {"production": prod > 0, "commission": other > 0, "maslaka_customers": mas,
                          "association": link or "not_started"}
        return self._book

    def keep(self, rows: list[dict], *, label: str, value: str, unit: str = "₪", title: str = "",
             chart: str | None = None, table: dict | None = None) -> str:
        """Store chartable rows; returns a result_id the model passes to render_chart.
        `chart` = the natural type (donut for a distribution) — the automatic chart uses it."""
        rid = "r" + uuid.uuid4().hex[:6]
        self.results[rid] = {"rows": rows, "label": label, "value": value, "unit": unit, "title": title, "chart": chart,
                             "table": table}   # {"columns": [...], "rows": [[...]]} — render_chart(type=table)
        return rid
