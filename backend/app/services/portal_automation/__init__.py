"""Portal automation framework.

Per-company plugins drive a Playwright browser through username + password +
SMS OTP login flows on insurance portals, then download Excel reports that
flow into Nifraim's normal upload/parse pipeline.
"""

from app.services.portal_automation.base import BasePortalAutomation
from app.services.portal_automation.companies import REGISTRY

__all__ = ["BasePortalAutomation", "REGISTRY"]
