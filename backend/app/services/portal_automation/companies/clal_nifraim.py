"""Clal (כלל) commission / נפרעים download — agent paid-commission reports.

Sibling of `clal.py` (which downloads PRODUCTION files from the InfoBay / PayLink
drawers). This plugin grabs the **עמלות / נפרעים** reports instead, from Clal's
Angular `../commissions` page — exactly the way Harel splits
`harel`/`harel_savings` (production) from `harel_commissions` (נפרעים), and Menora
splits `menora` from `menora_nifraim`.

Login + SMS-OTP are identical to production (F5 BIG-IP APM entry-link → creds →
OTP), so `login` / `submit_otp` are inherited from `ClalPortal` unchanged. Only
`download_reports` differs.

Flow (operator-provided 2026-06-18):
    1..2  same as production: entry-link → username + password → SMS OTP →
          lands on the Angular SPA (…/ClalAgentClient/#/).
    3. Click `<a href="../commissions" target="_blank">לפירוט עמלות</a>` — this
       opens a NEW TAB with a ui-grid of commission types.
    4. The grid groups rows under the "סוג עמלה" column. Each row is a type
       (פנסיה / חיים / בריאות / גמל). Clicking a type opens a drill page titled
       e.g. "עמלות שוטפות חיים יוני 2026" (month varies — never hardcoded).
    5. On the drill page, click the `<tab-heading>פוליסה</tab-heading>` tab.
    6. Click `<a ng-click="downloadExcel(...)">יצא לאקסל</a>` and save the file.

The downloaded חיים/בריאות Excels carry Clal commission signatures
(`clal_life_nifraim` / `clal_health_nifraim`), so `detect_format()` routes them
as `commission` → auto-compare vs. production. No parser changes needed for
those. פנסיה/גמל exports may have different columns with no signature yet — we
still download them; the diagnostics dumps reveal their real columns so a parser
signature can be added afterward.

As with production, failures (and successes) drop
`data/portal_screenshots/<run_id>_*.{png,html,txt}` so selectors can be refined
from real evidence.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import TYPE_CHECKING

from app.services.portal_automation.companies.clal import ClalPortal

if TYPE_CHECKING:
    from playwright.async_api import Page


# Only these commission types are wanted (operator: download exactly
# פנסיה / חיים / גמל / בריאות). Summary/aggregate rows (סך זכאות, סך העברה לבנק)
# and other categories (היקף, פרסים ומבצעים, מקדמות, מע"מ, אחר) are skipped.
# A type with no data this period renders ng-hide (no drill link) and drops out
# naturally — e.g. פנסיה when the agent has no pension commissions that month.
WANTED_TYPES = {"פנסיה", "חיים", "גמל", "בריאות"}


def _sanitize_label(text: str) -> str:
    """Collapse whitespace + strip filesystem-hostile chars for a filename."""
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    cleaned = re.sub(r"[\\/:*?\"<>|]", "", cleaned)
    return cleaned[:40] or "type"


class ClalNifraimPortal(ClalPortal):
    """Clal commission (נפרעים) download. Inherits login + submit_otp."""

    portal_kind = "clal_nifraim"
    company_label = "כלל — עמלות (נפרעים)"
    # Folded into the consolidated `clal` plugin (PayLink production + this
    # commissions report in one APM login). Still runnable as a manual single run.
    include_in_batch = False
    # Explicitly EMPTY: this class subclasses the parent portal, and would
    # otherwise inherit its `folds` and point at ITSELF.
    folds = ()

    async def download_reports(
        self,
        page: "Page",
        download_dir: Path,
        *,
        username: str | None = None,
    ) -> list[Path]:
        # Clal commission exports are not password-protected.
        self.report_password = None

        from app.services.portal_automation.runner import (
            SCREENSHOT_ROOT,
            logger as _logger,
        )

        run_id = download_dir.name
        download_dir.mkdir(parents=True, exist_ok=True)

        # `page` is reassigned across tab swaps, so the checkpoint helper reads
        # the enclosing-scope name each call rather than closing over one handle.
        async def _checkpoint(stem: str) -> Path:
            p = SCREENSHOT_ROOT / f"{run_id}_{stem}.png"
            await self._safe_screenshot(page, p)
            await self._dump_page_state(page, p)
            return p

        # ── XHR fallback: downloadExcel() is an Angular action that may stream
        # the blob via XHR rather than firing a native browser download. Capture
        # any Excel/attachment response so we still get the bytes. ──
        xhr_capture: dict = {"bytes": None, "url": None, "filename": None}

        async def _on_response(resp):
            try:
                ct = (resp.headers.get("content-type") or "").lower()
                cd = (resp.headers.get("content-disposition") or "").lower()
                url = resp.url.lower()
                is_excel = (
                    "spreadsheetml" in ct
                    or "vnd.ms-excel" in ct
                    or "octet-stream" in ct
                    or "attachment" in cd
                    or ".xlsx" in url
                    or (".xls" in url and "/css" not in url)
                    or ".xlsx" in cd
                    or ".xls" in cd
                )
                if is_excel and xhr_capture["bytes"] is None:
                    body = await resp.body()
                    if body and len(body) > 1024:
                        xhr_capture["bytes"] = body
                        xhr_capture["url"] = resp.url
                        m = re.search(
                            r"filename\*?=(?:UTF-8'')?\"?([^\";\r\n]+)",
                            resp.headers.get("content-disposition") or "",
                            re.IGNORECASE,
                        )
                        if m:
                            xhr_capture["filename"] = m.group(1).strip()
            except Exception:
                pass

        listener_page = page
        page.on("response", _on_response)

        def _swap_listener(new_page: "Page") -> None:
            """Move the XHR listener onto a newly-focused tab."""
            nonlocal listener_page
            if new_page is listener_page:
                return
            try:
                listener_page.remove_listener("response", _on_response)
            except Exception:
                pass
            listener_page = new_page
            new_page.on("response", _on_response)

        try:
            await _checkpoint("post_otp")

            # ── Step A: open the commissions tab via "לפירוט עמלות" ──
            # Do NOT force-navigate (F5 APM session). The link carries
            # href="../commissions" target="_blank" → opens a new tab.
            #
            # ONLY anchor-scoped selectors. The old `*:has-text('לפירוט עמלות')`
            # fallback matched a rotating PROMO tile on the SPA home and opened a
            # marketing PDF (clalbit.co.il/…/memberclub_digital_a4-3.pdf) instead
            # of the commissions grid → "לא נמצאו סוגי עמלה" (live 2026-07-24).
            # A real commissions entry is always an <a> with a commissions href
            # or that exact link text, never an arbitrary element.
            commissions_link = [
                "a[href*='commissions']",
                "a:has-text('לפירוט עמלות')",
            ]

            async def _open_commissions() -> bool:
                """Click the "לפירוט עמלות" anchor. Prefer a visible click, but
                fall back to an in-page dispatch: the anchor is confirmed present
                (href="../commissions", live 2026-07-30) yet Angular Material can
                keep it in a non-active panel, so Playwright's visibility gate
                skips it and the run wrongly reports "לא נמצא הקישור". A direct
                .click() on the `<a target="_blank">` still opens the new tab that
                expect_page catches. Scoped to a commissions href / that exact
                text so it can't hit the promo tile."""
                if await self._click_first_visible(page, commissions_link, timeout=6000):
                    return True
                return bool(await page.evaluate(
                    """() => {
                        const a = [...document.querySelectorAll('a')].find(e =>
                            /commissions/i.test(e.getAttribute('href') || '')
                            || (e.textContent || '').includes('לפירוט עמלות'));
                        if (a) { a.click(); return true; }
                        return false;
                    }"""
                ))

            grid_page: "Page" = page
            clicked = False
            try:
                async with page.context.expect_page(timeout=12000) as popup_info:
                    clicked = await _open_commissions()
                grid_page = await popup_info.value
                await grid_page.wait_for_load_state("domcontentloaded", timeout=20000)
                _logger.info("Clal נפרעים: commissions opened in popup → %s", grid_page.url)
            except Exception:
                # No popup — it may have navigated in the same tab, or the first
                # attempt found nothing; retry the dispatch once.
                if not clicked:
                    clicked = await _open_commissions()
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass

            if not clicked:
                await _checkpoint("A_commissions_no_match")
                raise RuntimeError(
                    f"לא נמצא הקישור 'לפירוט עמלות' ב-{page.url}. "
                    f"בדוק/י {run_id}_A_commissions_no_match.txt"
                )

            _swap_listener(grid_page)
            page = grid_page
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass
            await page.wait_for_timeout(1500)
            await _checkpoint("commissions_grid")

            # ── Step B: enumerate the commission-type rows generically ──
            # The grid groups rows under the "סוג עמלה" header. Clicking the
            # header first stabilizes ordering (best-effort, harmless if absent).
            await self._click_first_visible(
                page,
                [
                    "span.ui-grid-header-cell-label:has-text('סוג עמלה')",
                    "*:has-text('סוג עמלה')",
                ],
                timeout=4000,
            )
            await page.wait_for_timeout(800)

            # Each type row renders TWO elements with the same label:
            #   <a ng-show="row.entity.Link" ng-click="…loadSelectedSystem(…)">LABEL</a>
            #   <span ng-show="!row.entity.Link">LABEL</span>
            # The <a> is the CLICKABLE drill link, visible only when the row has
            # a Link (i.e. has data this period); otherwise it carries `ng-hide`
            # and the plain <span> shows instead. So the downloadable types are
            # exactly the VISIBLE anchors (`:not(.ng-hide)`). Rows without a Link
            # this period (e.g. פנסיה with no data, summary totals like
            # סך העברה לבנק) are correctly skipped. We re-locate each row by exact
            # link text per iteration, since the SPA re-renders the grid.
            type_labels: list[str] = await page.evaluate(
                """
                () => {
                    const seen = [];
                    document.querySelectorAll('a[ng-click*="loadSelectedSystem"]').forEach((a) => {
                        if (a.classList.contains('ng-hide')) return;  // no drill link this period
                        const t = (a.innerText || a.textContent || '').trim();
                        if (t && !seen.includes(t)) seen.push(t);
                    });
                    return seen;
                }
                """
            ) or []

            wanted = [t for t in type_labels if t in WANTED_TYPES]
            (SCREENSHOT_ROOT / f"{run_id}_commission_rows.txt").write_text(
                "URL: " + page.url
                + "\n\nALL CLICKABLE TYPES:\n" + "\n".join(type_labels)
                + "\n\nWANTED (downloading):\n" + "\n".join(wanted),
                encoding="utf-8",
            )
            _logger.info(
                "Clal נפרעים: %d clickable types %s → downloading %s",
                len(type_labels), type_labels, wanted,
            )
            type_labels = wanted

            if not type_labels:
                await _checkpoint("B_no_types")
                raise RuntimeError(
                    f"לא נמצאו סוגי עמלה בטבלה ב-{page.url}. "
                    f"בדוק/י {run_id}_B_no_types.txt ו-{run_id}_commission_rows.txt"
                )

            grid_url = page.url
            saved: list[Path] = []

            # ── Step C: per type — drill → פוליסה tab → יצא לאקסל ──
            for ti, label in enumerate(type_labels):
                safe = _sanitize_label(label)

                # C.1 — click the type's drill link. loadSelectedSystem is an
                # Angular scope action → usually a same-tab route change, but
                # handle a new tab too. The anchors carry an ng-click but NO
                # href, so they're absent from the accessibility tree
                # (get_by_role('link') misses them) — locate the visible anchor
                # by its ng-click + label text instead. Re-locate each pass since
                # the SPA re-renders the grid.
                pages_before = set(page.context.pages)
                try:
                    await page.locator(
                        "a[ng-click*='loadSelectedSystem']:not(.ng-hide)",
                        has_text=label,
                    ).first.click(timeout=8000)
                except Exception as e:
                    # A skipped type used to vanish into a worker-local warning: the
                    # run went green while contributing only the types that happened
                    # to work. Live: EVERY one of kiko's six Clal runs downloaded חיים
                    # and nothing else — בריאות (24 real per-client rows) never landed,
                    # and no one could see why. Report it.
                    _logger.warning("Clal נפרעים: could not click type '%s': %s", label, e)
                    self.partial_errors.append(f"כלל {label}: לא נפתח ({str(e)[:60]})")
                    continue
                await page.wait_for_timeout(2500)
                new_pages = [p for p in page.context.pages if p not in pages_before]
                drill = new_pages[-1] if new_pages else page
                if drill is not page:
                    try:
                        await drill.wait_for_load_state("domcontentloaded", timeout=20000)
                    except Exception:
                        pass
                    _swap_listener(drill)
                    page = drill
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass
                await page.wait_for_timeout(1500)
                await _checkpoint(f"drill_{safe}")

                # C.2 — click the "פוליסה" tab on the drill page, then wait for
                # the tab body (and its export button) to render.
                # MUST be an EXACT text match: "פוליסה" is a substring of the
                # sibling tab "סוכנים בפוליסה" (which sorts BEFORE it), so a
                # :has-text() (substring) click lands on the wrong tab and
                # exports agent-level aggregates with no client id. :text-is()
                # matches the trimmed full text exactly.
                await self._click_first_visible(
                    page,
                    [
                        "tab-heading:text-is('פוליסה')",
                        ".tab-head:text-is('פוליסה')",
                        "li[heading='פוליסה']",
                        "a:text-is('פוליסה')",
                    ],
                    timeout=8000,
                )
                try:
                    await page.wait_for_load_state("networkidle", timeout=8000)
                except Exception:
                    pass
                await page.wait_for_timeout(2000)

                # Inventory every export-ish trigger in the active tab so we can
                # see (per type) what download mechanism is present.
                try:
                    inv = await page.evaluate(
                        """
                        () => {
                            const out = [];
                            document.querySelectorAll(
                                "a[ng-click*='downloadExcel'], [ng-click*='downloadExcel'], .export-btn"
                            ).forEach((el) => {
                                const r = el.getBoundingClientRect();
                                out.push({
                                    tag: el.tagName,
                                    cls: el.className,
                                    ngclick: el.getAttribute('ng-click') || '',
                                    text: (el.innerText || el.textContent || '').trim().slice(0, 40),
                                    visible: !!(r.width && r.height) && !el.classList.contains('ng-hide'),
                                });
                            });
                            return out;
                        }
                        """
                    ) or []
                    (SCREENSHOT_ROOT / f"{run_id}_export_inv_{safe}.txt").write_text(
                        "\n".join(str(x) for x in inv), encoding="utf-8"
                    )
                    _logger.info("Clal נפרעים: '%s' export candidates: %d (%s)",
                                 label, len(inv), [x for x in inv if x["visible"]][:3])
                except Exception:
                    pass

                # C.3 — 3-layer download of "יצא לאקסל". The single-section export
                # <a> is hidden when the tab has multiple sections, so also accept
                # per-section downloadExcel triggers and the non-PDF export-btn.
                # A drill with sub-tabs (e.g. חיים: מוצר/סוכנים/מעסיקים/פוליסה/
                # כיסוי) renders ONE יצא לאקסל anchor PER tab — only the active
                # tab's is visible; the rest are display:none but still match a
                # plain `a[ng-click*=downloadExcel]`. Pin `:visible` so we click
                # the active (פוליסה) tab's export, not a hidden sibling.
                xhr_capture.update({"bytes": None, "url": None, "filename": None})
                excel_selectors = [
                    "a[ng-click*='downloadExcel']:not(.ng-hide):visible",
                    "[ng-click*='downloadExcel']:not(.ng-hide):visible",
                    "a:has(img[alt*='אקסל']):visible",
                    "a:has-text('יצא לאקסל'):visible",
                    "a.export-btn:not(.export-pdf-btn):visible",
                    ".export-btn:not(.export-pdf-btn):visible",
                ]

                # Capture the report period from the title (e.g. "עמלות שוטפות
                # חיים יוני 2026") and put it in the filename. The exported file
                # itself carries NO period, so detect_period_month would fall
                # back to policy start-dates and mis-attribute the month (חיים
                # resolved to Jan, בריאות to 2023). A Hebrew month+year in the
                # filename is the most reliable signal.
                period_label = None
                try:
                    period_label = await page.evaluate(
                        r"""
                        () => {
                            const re = /(ינואר|פברואר|מרץ|אפריל|מאי|יוני|יולי|אוגוסט|ספטמבר|אוקטובר|נובמבר|דצמבר)\s+(20\d\d)/;
                            for (const el of document.querySelectorAll('span,h1,h2,h3,h4,div')) {
                                const t = (el.innerText || el.textContent || '').trim();
                                if (t.startsWith('עמלות שוטפות')) {
                                    const m = t.match(re);
                                    if (m) return m[1] + ' ' + m[2];
                                }
                            }
                            return null;
                        }
                        """
                    )
                except Exception:
                    period_label = None
                name_stem = "כלל עמלות " + safe + (f" {period_label}" if period_label else "")

                fallback_name = f"{name_stem}.xlsx"
                got: Path | None = None
                try:
                    async with page.expect_download(timeout=90000) as dl_info:
                        if not await self._click_first_visible(
                            page, excel_selectors, timeout=8000
                        ):
                            raise RuntimeError("no-excel-export-clicked")
                    download = await dl_info.value
                    suggested = (download.suggested_filename or "").strip()
                    ext = Path(suggested).suffix or ".xlsx"
                    got = download_dir / f"{name_stem}{ext}"
                    await download.save_as(str(got))
                except Exception as native_err:
                    for _ in range(30):  # ~15s
                        if xhr_capture["bytes"]:
                            break
                        await asyncio.sleep(0.5)
                    if xhr_capture["bytes"]:
                        got = download_dir / fallback_name
                        got.write_bytes(xhr_capture["bytes"])
                    else:
                        _logger.warning(
                            "Clal נפרעים: export failed for '%s' (%s)", label, native_err
                        )
                        await _checkpoint(f"export_fail_{safe}")

                if got:
                    saved.append(got)
                    _logger.info(
                        "Clal נפרעים: saved %s (%d bytes)", got.name, got.stat().st_size
                    )
                else:
                    # The type opened but produced no export — just as invisible as a
                    # failed click, and just as costly (a whole report missing from
                    # the merged נפרעים while the run reports success).
                    self.partial_errors.append(f"כלל {label}: נפתח אך לא ירד קובץ")

                # C.4 — return to the grid for the next type.
                if ti < len(type_labels) - 1:
                    if page is not grid_page and page is not listener_page:
                        # drill opened its own tab — close it, back to grid.
                        try:
                            await page.close()
                        except Exception:
                            pass
                    if page is not grid_page:
                        _swap_listener(grid_page)
                        page = grid_page
                    # Same-tab drill: navigate back to the grid view.
                    if page.url != grid_url:
                        try:
                            await page.go_back(timeout=8000)
                            await page.wait_for_load_state("domcontentloaded", timeout=10000)
                        except Exception:
                            pass
                    try:
                        await page.wait_for_selector(
                            "a[ng-click*='loadSelectedSystem']:not(.ng-hide)", timeout=8000
                        )
                    except Exception:
                        pass
                    await page.wait_for_timeout(800)

            if not saved:
                await _checkpoint("C_no_downloads")
                raise RuntimeError(
                    f"זוהו {len(type_labels)} סוגי עמלה אך לא ירדו קבצים. "
                    f"בדוק/י {run_id}_commission_rows.txt ו-{run_id}_C_no_downloads.txt"
                )

            # Say — on EVERY run, success or not — which types the portal offered and
            # which actually produced a file. The screenshots that carry this live on
            # the agent's own PC and cannot be read remotely, so the reconciliation has
            # to reach the server. This one line is what would have shown, six runs
            # ago, that Clal was only ever bringing back חיים.
            from app.services.portal_automation.runner import _worker_note
            _worker_note(
                f"clal_nifraim: offered={type_labels} → downloaded={[p.name for p in saved]}"
            )

            return saved
        finally:
            try:
                listener_page.remove_listener("response", _on_response)
            except Exception:
                pass
