"""Helper for un-implemented portal plugins.

Each per-company module subclasses `_StubPortal`, sets `portal_kind` and
`company_label`, and is registered in companies/__init__.py. When the user
attempts to run such a credential, the runner sees NotImplementedError and
records a clear `last_error` on the credential. To implement: replace the
import with a concrete subclass following phoenix.py as the template.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from app.services.portal_automation.base import BasePortalAutomation

if TYPE_CHECKING:
    from playwright.async_api import Page


class _StubPortal(BasePortalAutomation):
    portal_kind = ""
    company_label = ""

    async def login(self, page: "Page", username: str, password: str) -> None:
        raise NotImplementedError(
            f"Portal automation for '{self.portal_kind}' ({self.company_label}) is not yet implemented. "
            "Add selectors in app/services/portal_automation/companies/."
        )

    async def submit_otp(self, page: "Page", otp: str) -> None:
        raise NotImplementedError

    async def download_reports(self, page: "Page", download_dir: Path) -> list[Path]:
        raise NotImplementedError
