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
from app.services.portal_automation.companies.yelin import YelinPortal
from app.services.portal_automation.companies.meitav import MeitavPortal


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
    "yelin": YelinPortal,
    "meitav": MeitavPortal,
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
    "altshuler": "אלטשולר — עמלות (נפרעים)",
    "hachshara": "הכשרה",
    "excellence": "אקסלנס",
    "mor": "מור",
    "ayalon": "איילון",
    "clal_health": "כלל בריאות",
    "harel": "הראל",
    "harel_commissions": "הראל — ריכוז תשלומי עמלות",
    "harel_savings": "הראל — מוצרי צבירה (פרודוקציה)",
    "yelin": "ילין לפידות — עמלות (נפרעים)",
    "meitav": "מיטב דש — דוח עמלות לסוכן (נפרעים)",
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
    "altshuler":            ("אלטשולר", "נפרעים", "https://agents.as-invest.co.il/Login"),
    "hachshara":            ("הכשרה", "נפרעים", "https://agents-login.hcsra.co.il/my.policy"),
    "excellence":           ("אקסלנס", "פרודוקציה", ""),
    "mor":                  ("מור", "נפרעים", "https://join.more.co.il/agentsportal/agents/login"),
    "yelin":                ("ילין לפידות", "נפרעים", "https://online.yl-invest.co.il/agents/"),
    "meitav":               ("מיטב דש", "נפרעים", "https://customers.meitav.co.il/v2/login/LoginAgent"),
    "ayalon":               ("איילון", "פרודוקציה", ""),
}

# ──────────────────────────────────────────────────────────────────────────
# What the LOGIN FORM actually asks for, per portal
# ──────────────────────────────────────────────────────────────────────────
# The DB has exactly two credential columns (username + encrypted_password), but
# Mor's login form has THREE fields: מס' רשיון + ת"ז + טלפון. `mor.py::_split`
# therefore reads them back out of a PACKED username="<license>|<id>" plus
# password="<phone>".
#
# That packing was invisible to the UI: the "הוסף פורטל" modal only ever rendered a
# generic שם משתמש + סיסמה, so a user adding מור had no way to supply the phone —
# and since Mor SMS-OTPs that number, the run could never even start.
#
# So Mor DECLARES its fields here and the modal renders them. `target` says which DB
# column the value lands in; multiple fields on the same target are joined with "|"
# in list order — exactly the convention `_split` already parses. Every other portal
# has no entry and falls back to the plain username + password pair, so this map
# holds only the exception.
#
#   secret=True  → stored encrypted, never echoed back to the UI; blank on edit
#                  means "leave unchanged".
#
# INVARIANT: the field order here must match `mor.py::_split`. Change one, change
# the other.
PORTAL_LOGIN_FIELDS: dict[str, list[dict]] = {
    "mor": [
        {"key": "license", "label": "מספר רשיון", "placeholder": "מספר רשיון הסוכן",
         "type": "text", "target": "username", "secret": False, "required": True},
        {"key": "identity", "label": "תעודת זהות", "placeholder": "9 ספרות",
         "type": "text", "target": "username", "secret": False, "required": True},
        {"key": "phone", "label": "טלפון נייד", "placeholder": "הטלפון שאליו מגיע קוד ה-SMS",
         "type": "tel", "target": "password", "secret": True, "required": True,
         "hint": "מור שולחת את קוד האימות ב-SMS למספר הזה"},
    ],
}

# The pair every other portal uses.
DEFAULT_LOGIN_FIELDS: list[dict] = [
    {"key": "username", "label": "שם משתמש", "placeholder": "שם המשתמש בפורטל",
     "type": "text", "target": "username", "secret": False, "required": True},
    {"key": "password", "label": "סיסמה", "placeholder": "",
     "type": "password", "target": "password", "secret": True, "required": True},
]


def login_fields_for(portal_kind: str) -> list[dict]:
    """The login-form spec the UI should render for this portal."""
    return PORTAL_LOGIN_FIELDS.get(portal_kind, DEFAULT_LOGIN_FIELDS)
