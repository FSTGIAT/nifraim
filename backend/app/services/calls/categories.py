"""What a call was about — ONE closed list, shared by the summary prompt, the DB column,
the agent tools, the data map and the UI. Add a category here and nowhere else."""
from __future__ import annotations

CATEGORIES: dict[str, str] = {
    "transfer": "ניוד / העברה",
    "fees": "דמי ניהול",
    "pension": "פנסיה / גמל",
    "study_fund": "קרן השתלמות",
    "health_life": "ביטוח בריאות / חיים",
    "claim": "תביעה",
    "mortgage": "משכנתא",
    "new_sale": "מכירה חדשה",
    "retention": "ביטול / שימור",
    "service": "שירות / בירור",
    "other": "אחר",
    # not work at all (family, friends, errands) — hidden everywhere, audio deleted (services/calls/privacy.py)
    "personal": "אישית",
}

URGENCY = {"high": "דחוף", "normal": "רגיל", "low": "לא דחוף"}


def label(key: str | None) -> str:
    return CATEGORIES.get(key or "", CATEGORIES["other"])


def key_for(text: str | None) -> str | None:
    """'דמי ניהול' / 'fees' / 'ניוד' → its key (agent tools accept either language)."""
    t = (text or "").strip().lower()
    if not t:
        return None
    if t in CATEGORIES:
        return t
    for k, v in CATEGORIES.items():
        parts = [p.strip() for p in v.split("/") if p.strip()]
        # "דמי" ⊂ "דמי ניהול" ok; a short part ("אחר") must be the whole query, not a word inside it
        if t in v or any(t == p or (len(p) >= 4 and p in t) for p in parts):
            return k
    return None
