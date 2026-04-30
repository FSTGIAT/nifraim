"""Per-company portal automation plugins.

To add a new portal, create a module under this directory with a subclass of
`BasePortalAutomation` and register it in the REGISTRY dict below.
"""

from app.services.portal_automation.base import BasePortalAutomation
from app.services.portal_automation.companies.phoenix import PhoenixPortal
from app.services.portal_automation.companies.migdal import MigdalPortal
from app.services.portal_automation.companies.clal import ClalPortal
from app.services.portal_automation.companies.menora import MenoraPortal
from app.services.portal_automation.companies.altshuler import AltshulerPortal
from app.services.portal_automation.companies.hachshara import HachsharaPortal
from app.services.portal_automation.companies.excellence import ExcellencePortal
from app.services.portal_automation.companies.mor import MorPortal
from app.services.portal_automation.companies.ayalon import AyalonPortal
from app.services.portal_automation.companies.clal_health import ClalHealthPortal


REGISTRY: dict[str, type[BasePortalAutomation]] = {
    "phoenix": PhoenixPortal,
    "migdal": MigdalPortal,
    "clal": ClalPortal,
    "menora": MenoraPortal,
    "altshuler": AltshulerPortal,
    "hachshara": HachsharaPortal,
    "excellence": ExcellencePortal,
    "mor": MorPortal,
    "ayalon": AyalonPortal,
    "clal_health": ClalHealthPortal,
}


# UI display labels (Hebrew). Frontend can fetch this list to populate dropdowns.
PORTAL_LABELS: dict[str, str] = {
    "phoenix": "הפניקס",
    "migdal": "מגדל",
    "clal": "כלל חיים",
    "menora": "מנורה",
    "altshuler": "אלטשולר",
    "hachshara": "הכשרה",
    "excellence": "אקסלנס",
    "mor": "מור",
    "ayalon": "איילון",
    "clal_health": "כלל בריאות",
}
