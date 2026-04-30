"""Abstract base for per-portal automation plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page


class BasePortalAutomation(ABC):
    """One subclass per insurance portal.

    Subclasses implement the three abstract methods. The runner orchestrates:
        login → (await OTP from otp_inbox) → submit_otp → download_reports.

    Plugins that download password-protected Excel files (e.g. Phoenix) should
    set `report_password` after `download_reports`; the runner forwards it to
    `parse_excel(..., password=report_password)` so msoffcrypto can decrypt.
    """

    portal_kind: str = ""
    company_label: str = ""  # Hebrew display name
    report_password: str | None = None

    @abstractmethod
    async def login(self, page: "Page", username: str, password: str) -> None:
        """Navigate to the portal and submit username + password.

        Should leave the page on the OTP-entry screen.
        """

    @abstractmethod
    async def submit_otp(self, page: "Page", otp: str) -> None:
        """Type the SMS OTP into the form and submit.

        Should leave the page on a logged-in state from which `download_reports`
        can navigate.
        """

    @abstractmethod
    async def download_reports(self, page: "Page", download_dir: Path) -> list[Path]:
        """Navigate to the reports section and download every relevant file.

        Returns the list of saved file paths (under `download_dir`).
        """

    # ------ Shared helpers (subclasses may override or compose) ------

    async def _wait_visible(self, page: "Page", selector: str, timeout: int = 15000) -> None:
        await page.wait_for_selector(selector, state="visible", timeout=timeout)

    async def _safe_screenshot(self, page: "Page", path: Path) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(path), full_page=True)
        except Exception:
            # Never let screenshot failure mask the original error
            pass

    async def _expect_download(self, page: "Page", trigger_coro, save_to: Path) -> Path:
        """Helper: run `trigger_coro` (which clicks the download button) inside
        `expect_download`, then save the resulting file to `save_to`."""
        async with page.expect_download() as dl_info:
            await trigger_coro
        download = await dl_info.value
        save_to.parent.mkdir(parents=True, exist_ok=True)
        await download.save_as(str(save_to))
        return save_to
