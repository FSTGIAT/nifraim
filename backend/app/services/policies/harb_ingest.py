"""One served הר הביטוח request → insurance_policies + policy_documents (Markdown).

Called by the portal runner for kind `harbituach` INSTEAD of the generic ingest (this is never
production/נפרעים). Runs on the agent's local worker, so it does NOT embed — the cloud's
policies_index_sweep indexes the new documents within ~2 minutes. The AI version bump happens
after commit (versioning listener; HarbRequest/InsurancePolicy/PolicyDocument are watched).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from app.models.harb_request import HarbRequest
from app.services.policies.harb_parser import parse_harb_xlsx
from app.services.policies.store import replace_harb_snapshot

logger = logging.getLogger(__name__)


async def ingest(db, req: HarbRequest, xlsx: Path | None, details_json: Path | None = None) -> int:
    """Parse + store; marks the request done. Returns the coverage count. Commits."""
    if xlsx is None or not xlsx.exists():
        raise ValueError("לא התקבל קובץ אקסל מהר הביטוח")
    parsed = parse_harb_xlsx(xlsx.read_bytes())
    details = []
    if details_json and details_json.exists():
        try:
            details = json.loads(details_json.read_text("utf-8")) or []
        except ValueError:
            logger.warning("harb: unreadable details file %s", details_json)
    n = await replace_harb_snapshot(db, req, parsed, details)
    req.status = "done"
    req.policies_count = n
    req.error = None
    req.completed_at = datetime.utcnow()
    await db.commit()
    logger.info("harb: request %s customer %s → %d coverages, %d detail pages",
                req.id, req.customer_id_number, n, len(details))
    return n
