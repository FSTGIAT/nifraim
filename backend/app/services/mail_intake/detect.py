"""Which provider hosts an agent's mailbox — answered by DNS, never by asking.

Agents use custom domains (`moshe@eitam-finance.com`), so the mail *client* they
name tells you nothing. Asking "Gmail or Outlook?" actively misleads: an agent who
reads mail in the Outlook desktop app may sit on a Microsoft 365 tenant, on Google
Workspace, or on a cPanel host — and the three have incompatible auth stories:

    microsoft  Exchange Online basic auth is PERMANENTLY disabled and app
               passwords are blocked with it. OAuth (Graph) is the only door.
    google     PERSONAL @gmail.com only. App passwords still work there (with
               2-Step Verification), and IMAP has been on by default since
               Jan 2025. The OAuth alternative, gmail.readonly, is a Google
               *restricted* scope needing an annually-revalidated CASA assessment.
    other      No usable OAuth or password — forward the mail to us instead.

Google WORKSPACE (a custom domain whose MX is Google) deliberately maps to
`other`, NOT `google`: since 2025 Workspace refuses IMAP with a username/password
or an app password and demands OAuth, which for Gmail means the CASA-gated
restricted scope. Routing it to `google` would hand the agent an app-password
field that can never succeed. Personal Gmail is identified by the DOMAIN, not the
MX, because both share `aspmx.l.google.com`.

So we resolve the domain's MX record and route on the answer. `dnspython` is not a
dependency (and `dig` isn't in the container), so this uses DNS-over-HTTPS through
`httpx`, which is already vendored.

Detection is a hint, not a verdict: split-delivery domains and security gateways
(Proofpoint, Mimecast) sit in front of the real host and will mislead it. Callers
must let the user override, and `other` is the safe default because the forwarding
path works everywhere.
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

MICROSOFT = "microsoft"
GOOGLE = "google"
OTHER = "other"

VALID_HOSTS = (MICROSOFT, GOOGLE, OTHER)

_DOH_URL = "https://cloudflare-dns.com/dns-query"
_DOH_TIMEOUT_S = 5.0

# Matched against the lowercased MX target. Order matters only for readability —
# no domain legitimately matches both.
_MX_SIGNATURES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (MICROSOFT, ("mail.protection.outlook.com", "outlook.com", "hotmail.com")),
    (GOOGLE, ("aspmx.l.google.com", "googlemail.com", "google.com")),
)

# The only domains where an app password over IMAP still works. Everything else
# on Google's MX is Workspace, which requires OAuth we can't afford (see above).
_PERSONAL_GMAIL_DOMAINS = ("gmail.com", "googlemail.com")

# Security gateways answer MX for the domain and relay to the real mailbox behind
# them, so the MX tells us nothing about who hosts it. Common in Israeli firms
# with an M365 tenant. They resolve to `other` like any unknown host — which is
# correct, since forwarding works regardless — but we log them so a support
# question ("why didn't it offer me the Microsoft button?") has an answer.
_GATEWAY_SIGNATURES = (
    "mimecast.com", "pphosted.com", "ppe-hosted.com", "barracudanetworks.com",
    "messagelabs.com", "trendmicro.com", "cyren.com", "securence.com",
)


def domain_of(email: str) -> str | None:
    email = (email or "").strip().lower()
    if "@" not in email:
        return None
    domain = email.rsplit("@", 1)[1].strip()
    return domain or None


async def detect_mail_host(email: str) -> str:
    """Resolve `email`'s domain MX and classify it. Never raises.

    Any failure — malformed address, NXDOMAIN, no MX, DoH timeout — returns
    `other`, whose forwarding path works regardless of who hosts the mailbox.
    """
    domain = domain_of(email)
    if not domain:
        return OTHER

    try:
        targets = await _resolve_mx(domain)
    except Exception as e:  # DoH is best-effort; never block the user on it
        logger.warning("mail_intake: MX lookup failed for %s: %s", domain, e)
        return OTHER

    if not targets:
        logger.info("mail_intake: %s has no MX records", domain)
        return OTHER

    for host, suffixes in _MX_SIGNATURES:
        for target in targets:
            if any(target == s or target.endswith("." + s) for s in suffixes):
                if host == GOOGLE and domain not in _PERSONAL_GMAIL_DOMAINS:
                    # Workspace: app passwords are refused, so the IMAP path
                    # would fail forever. Forwarding works today.
                    logger.info("mail_intake: %s is Google Workspace -> forwarding path", domain)
                    return OTHER
                return host

    if any(any(t == g or t.endswith("." + g) for g in _GATEWAY_SIGNATURES) for t in targets):
        logger.info(
            "mail_intake: %s sits behind a mail security gateway (%s) — the real host "
            "is invisible to MX; using the forwarding path",
            domain, targets[0],
        )
        return OTHER

    logger.info("mail_intake: %s MX %s matched no known provider", domain, targets[:2])
    return OTHER


async def _resolve_mx(domain: str) -> list[str]:
    """Return MX targets, lowercased, trailing dot stripped, in preference order."""
    async with httpx.AsyncClient(timeout=_DOH_TIMEOUT_S) as client:
        resp = await client.get(
            _DOH_URL,
            params={"name": domain, "type": "MX"},
            headers={"accept": "application/dns-json"},
        )
        resp.raise_for_status()
        payload = resp.json()

    answers = payload.get("Answer") or []
    parsed: list[tuple[int, str]] = []
    for a in answers:
        # An MX rdata is "<preference> <exchange>", e.g. "0 foo.mail.protection.outlook.com."
        data = (a.get("data") or "").strip()
        parts = data.split(None, 1)
        if len(parts) != 2:
            continue
        try:
            pref = int(parts[0])
        except ValueError:
            continue
        parsed.append((pref, parts[1].rstrip(".").lower()))

    return [target for _, target in sorted(parsed)]
