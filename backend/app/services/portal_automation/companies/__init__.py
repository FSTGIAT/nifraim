"""Per-company portal automation plugins.

To add a new portal, create a module under this directory with a subclass of
`BasePortalAutomation` and register it in the REGISTRY dict below.
"""

from app.services.portal_automation.base import BasePortalAutomation
from app.services.portal_automation.companies.phoenix import PhoenixPortal
from app.services.portal_automation.companies.phoenix_nifraim import PhoenixNifraimPortal
from app.services.portal_automation.companies.phoenix_nifraim_gemel import PhoenixNifraimGemelPortal
from app.services.portal_automation.companies.phoenix_sfe import PhoenixSfePortal
from app.services.portal_automation.companies.migdal import MigdalPortal
from app.services.portal_automation.companies.migdal_apm import MigdalApmPortal
from app.services.portal_automation.companies.clal import ClalPortal
from app.services.portal_automation.companies.clal_nifraim import ClalNifraimPortal
from app.services.portal_automation.companies.menora import MenoraPortal
from app.services.portal_automation.companies.menora_nifraim import MenoraNifraimPortal
from app.services.portal_automation.companies.altshuler import AltshulerPortal
from app.services.portal_automation.companies.hachshara import HachsharaPortal
from app.services.portal_automation.companies.excellence import ExcellencePortal
from app.services.portal_automation.companies.mor import MorPortal
from app.services.portal_automation.companies.ayalon import AyalonPortal
from app.services.portal_automation.companies.clal_health import ClalHealthPortal
from app.services.portal_automation.companies.harel import HarelPortal
from app.services.portal_automation.companies.harel_commissions import HarelCommissionsPortal
from app.services.portal_automation.companies.harel_savings import HarelSavingsPortal


REGISTRY: dict[str, type[BasePortalAutomation]] = {
    "phoenix": PhoenixPortal,
    "phoenix_nifraim": PhoenixNifraimPortal,
    "phoenix_nifraim_gemel": PhoenixNifraimGemelPortal,
    "phoenix_sfe": PhoenixSfePortal,
    "migdal": MigdalPortal,
    "migdal_apm": MigdalApmPortal,
    "clal": ClalPortal,
    "clal_nifraim": ClalNifraimPortal,
    "menora": MenoraPortal,
    "menora_nifraim": MenoraNifraimPortal,
    "altshuler": AltshulerPortal,
    "hachshara": HachsharaPortal,
    "excellence": ExcellencePortal,
    "mor": MorPortal,
    "ayalon": AyalonPortal,
    "clal_health": ClalHealthPortal,
    "harel": HarelPortal,
    "harel_commissions": HarelCommissionsPortal,
    "harel_savings": HarelSavingsPortal,
}


# UI display labels (Hebrew). Frontend can fetch this list to populate dropdowns.
# Note: `migdal` and `migdal_apm` are two distinct portals with separate
# credentials — Safes (the file vault, mostly ייצור) vs. אזור סוכנים (where
# the נפרעים report lives). Labels disambiguate so the dropdown isn't ambiguous.
PORTAL_LABELS: dict[str, str] = {
    "phoenix": "הפניקס",
    "phoenix_nifraim": "הפניקס — נפרעים חא\"ט ובריאות (פרודוקציה)",
    "phoenix_nifraim_gemel": "הפניקס — נפרעים גמל (פרודוקציה)",
    "phoenix_sfe": "הפניקס — כספת (SFE)",
    "migdal": "מגדל — כספת (ייצור)",
    "migdal_apm": "מגדל — אזור סוכנים (עמלות)",
    "clal": "כלל — פיילינק (פרודוקציה)",
    "clal_nifraim": "כלל — עמלות (נפרעים)",
    "menora": "מנורה",
    "menora_nifraim": "מנורה — נפרעים",
    "altshuler": "אלטשולר",
    "hachshara": "הכשרה",
    "excellence": "אקסלנס",
    "mor": "מור",
    "ayalon": "איילון",
    "clal_health": "כלל בריאות",
    "harel": "הראל",
    "harel_commissions": "הראל — ריכוז תשלומי עמלות",
    "harel_savings": "הראל — מוצרי צבירה (פרודוקציה)",
    "phoenix_terminal": "הפניקס — טרמינל (פרודוקציה)",
}

# Portals that are NOT Playwright plugins (so NOT in REGISTRY) — driven by the
# LOCAL WORKER via a native Windows orchestrator (backend/scripts/windows/
# phoenix_terminal_run.py). They are creatable, selectable, and batch-eligible,
# but run_automation/_run_inner cannot execute them; local_worker and
# batch_runner dispatch them specially. Value = the orchestrator script entry.
WORKER_ONLY_PORTALS: dict[str, str] = {
    "phoenix_terminal": "scripts/windows/phoenix_terminal_run.py",
}

# Clean picker metadata: (company, category, login_url) per portal_kind. Drives a
# simple "<company> <category>" option + the URL in the "add portal" UI. PORTAL_LABELS
# stays the verbose label used elsewhere (batch pills etc.).
PORTAL_META: dict[str, tuple[str, str, str]] = {
    "menora":               ("מנורה", "פרודוקציה", "https://menoranet.menora.co.il/"),
    "menora_nifraim":       ("מנורה", "נפרעים", "https://menoranet.menora.co.il/"),
    "migdal":               ("מגדל", "פרודוקציה", "https://mfte.migdal.co.il/"),
    "migdal_apm":           ("מגדל", "נפרעים", "https://apmaccess.migdal.co.il/my.policy"),
    "harel_savings":        ("הראל", "פרודוקציה", "https://agents.harel-group.co.il/my.policy"),
    "harel_commissions":    ("הראל", "נפרעים", "https://agents.harel-group.co.il/my.policy"),
    "harel":                ("הראל", "פרודוקציה (כספת)", "https://www.harelsafe.co.il/Login.aspx"),
    "phoenix_terminal":     ("הפניקס", "פרודוקציה", "https://agent.fnx.co.il/my.policy"),
    "phoenix_nifraim":      ("הפניקס", "נפרעים חיים+בריאות", "https://agent.fnx.co.il/my.policy"),
    "phoenix_nifraim_gemel":("הפניקס", "נפרעים גמל", "https://agent.fnx.co.il/my.policy"),
    "phoenix_sfe":          ("הפניקס", "פרודוקציה (כספת SFE)", "https://sfe.fnx.co.il/SFE/"),
    "phoenix":              ("הפניקס", "טרמינל (ישן)", "https://agent.fnx.co.il/my.policy"),
    "clal":                 ("כלל", "פרודוקציה", "https://www.clalbit.co.il/"),
    "clal_nifraim":         ("כלל", "נפרעים", "https://www.clalbit.co.il/"),
    "clal_health":          ("כלל בריאות", "נפרעים", ""),
    "altshuler":            ("אלטשולר", "פרודוקציה", ""),
    "hachshara":            ("הכשרה", "פרודוקציה", ""),
    "excellence":           ("אקסלנס", "פרודוקציה", ""),
    "mor":                  ("מור", "נפרעים", "https://join.more.co.il/agentsportal/agents/login"),
    "ayalon":               ("איילון", "פרודוקציה", ""),
}
