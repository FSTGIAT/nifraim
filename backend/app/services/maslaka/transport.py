"""Vault transport — abstract interface + two implementations.

`LocalVaultTransport` (default, no credentials needed): three local folders
under `MASLAKA_LOCAL_{OUTBOX,INBOX,ARCHIVE}`. Drop XML files in/out by hand
or via tests. This is what makes the whole pipeline runnable today without
a real clearinghouse account.

`SftpVaultTransport`: paramiko-backed real-vault path. All paramiko calls
are sync/blocking — we wrap them in `asyncio.to_thread()` per the existing
precedent (`backend/app/services/twilio_provisioning.py:103,129` and
`backend/app/services/document_extraction.py:332`) so the FastAPI event
loop stays responsive.

Switching dev → prod is **env-only**: flip `MASLAKA_TRANSPORT=local` →
`sftp` and fill the `MASLAKA_SFTP_*` settings. Zero code changes.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from app.config import settings

if TYPE_CHECKING:
    import paramiko  # imported lazily inside SftpVaultTransport to keep paramiko optional

logger = logging.getLogger(__name__)


@dataclass
class VaultFile:
    """Lightweight handle to a file in the vault.

    `name` is the filename (e.g. "feedback_v009_abc123.xml"); `bytes_size`
    lets the poll loop log throughput without re-stat'ing.
    """
    name: str
    bytes_size: int


class VaultTransport(ABC):
    """Common interface — orchestration code only depends on this."""

    @abstractmethod
    async def send(self, filename: str, payload: bytes) -> None:
        """Drop `payload` into the outbox under `filename`."""

    @abstractmethod
    async def list_inbox(self) -> list[VaultFile]:
        """List files currently in the inbox. Empty list if none."""

    @abstractmethod
    async def fetch(self, filename: str) -> bytes:
        """Read the named inbox file. Raises FileNotFoundError if missing."""

    @abstractmethod
    async def archive(self, filename: str) -> None:
        """Move the named inbox file into the archive folder (so we don't
        re-ingest it on the next poll)."""

    @abstractmethod
    async def healthcheck(self) -> bool:
        """Best-effort connectivity check. Used by manual /poll smoke tests."""


# ─── Local-filesystem mock ──────────────────────────────────────────────────
class LocalVaultTransport(VaultTransport):
    """Three local folders as the vault. Default for dev / iteration 1.

    Pure-Python `pathlib` + `shutil`. Wraps all blocking I/O in
    `asyncio.to_thread()` so a slow disk can't block the event loop.
    """

    def __init__(
        self,
        outbox: str | Path,
        inbox: str | Path,
        archive: str | Path,
    ) -> None:
        # Suffix `_dir` to avoid shadowing the `archive()` method name on
        # `self.archive` — Python attribute lookup would otherwise return
        # the Path instance and fail with "not callable" at runtime.
        self.outbox_dir = Path(outbox)
        self.inbox_dir = Path(inbox)
        self.archive_dir = Path(archive)
        # A relative path resolves against the process CWD, so a worker started
        # from a different directory silently gets a *different, empty* vault and
        # looks healthy while exchanging nothing. Fine in dev; on the Gateway the
        # Transporter owns fixed absolute folders, so say so out loud.
        for p in (self.outbox_dir, self.inbox_dir, self.archive_dir):
            if not p.is_absolute():
                logger.warning(
                    "maslaka.transport.local: %s is relative — it resolves against the "
                    "current working directory (%s). Set MASLAKA_LOCAL_* to absolute paths.",
                    p, Path.cwd(),
                )
        # mkdir on construction — keeps the first call from blowing up on
        # a fresh checkout without a setup step.
        for p in (self.outbox_dir, self.inbox_dir, self.archive_dir):
            p.mkdir(parents=True, exist_ok=True)

    async def send(self, filename: str, payload: bytes) -> None:
        path = self.outbox_dir / filename
        tmp = path.with_suffix(path.suffix + ".tmp")

        def _write() -> None:
            # Write-then-rename: the מסלקה Transporter syncs this folder on its
            # own schedule and would happily ship a half-written XML. Rename is
            # atomic within a filesystem, so the Transporter only ever observes
            # a complete file. Same reason SftpVaultTransport.send does this.
            tmp.write_bytes(payload)
            tmp.replace(path)

        await asyncio.to_thread(_write)
        logger.info("maslaka.transport.local: wrote %d bytes → %s", len(payload), path)

    async def list_inbox(self) -> list[VaultFile]:
        def _list() -> list[VaultFile]:
            out: list[VaultFile] = []
            for p in sorted(self.inbox_dir.iterdir()):
                if not p.is_file():
                    continue
                # Skip dotfiles + in-progress uploads (.tmp suffix is a
                # common pattern when files are being written).
                if p.name.startswith(".") or p.suffix == ".tmp":
                    continue
                try:
                    sz = p.stat().st_size
                except OSError:
                    continue
                out.append(VaultFile(name=p.name, bytes_size=sz))
            return out

        return await asyncio.to_thread(_list)

    async def fetch(self, filename: str) -> bytes:
        path = self.inbox_dir / filename

        def _read() -> bytes:
            return path.read_bytes()

        return await asyncio.to_thread(_read)

    async def archive(self, filename: str) -> None:
        src = self.inbox_dir / filename
        # Prepend a timestamp to dedup if the same filename re-arrives.
        dst = self.archive_dir / f"{int(time.time())}_{filename}"

        def _move() -> None:
            shutil.move(str(src), str(dst))

        await asyncio.to_thread(_move)
        logger.info("maslaka.transport.local: archived %s → %s", filename, dst.name)

    async def healthcheck(self) -> bool:
        return all(p.exists() and p.is_dir() for p in (self.outbox_dir, self.inbox_dir, self.archive_dir))


# ─── SFTP (paramiko) ────────────────────────────────────────────────────────
class SftpVaultTransport(VaultTransport):
    """Real vault over SFTP. Activated by `MASLAKA_TRANSPORT=sftp`.

    paramiko is sync-only; every public method runs the blocking work
    through `asyncio.to_thread()`. Each call opens + closes its own
    connection — simpler than a persistent client and matches how the
    clearinghouse expects short-lived sessions.
    """

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        key_path: str,
        outbox: str,
        inbox: str,
        archive: str,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password or None
        self.key_path = key_path or None
        # `_dir` suffix matches LocalVaultTransport — avoids shadowing
        # the `archive()` method.
        self.outbox_dir = outbox
        self.inbox_dir = inbox
        self.archive_dir = archive

    # ── Connection plumbing (sync helpers run via asyncio.to_thread) ────
    def _connect_sync(self) -> tuple["paramiko.SFTPClient", "paramiko.SSHClient"]:
        import paramiko  # imported here so paramiko is only required when SFTP is actually used

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        connect_kwargs: dict = {
            "hostname": self.host,
            "port": self.port,
            "username": self.username,
            "timeout": 20,
            "banner_timeout": 20,
            "auth_timeout": 20,
        }
        if self.key_path:
            connect_kwargs["key_filename"] = self.key_path
        if self.password:
            connect_kwargs["password"] = self.password
        ssh.connect(**connect_kwargs)
        sftp = ssh.open_sftp()
        return sftp, ssh

    def _close_sync(self, sftp: "paramiko.SFTPClient", ssh: "paramiko.SSHClient") -> None:
        try:
            sftp.close()
        finally:
            ssh.close()

    # ── Interface impls ──────────────────────────────────────────────────
    async def send(self, filename: str, payload: bytes) -> None:
        def _send() -> None:
            sftp, ssh = self._connect_sync()
            try:
                # Write to a .tmp file first then rename, so the
                # clearinghouse never picks up a half-written file.
                remote_tmp = f"{self.outbox_dir.rstrip('/')}/{filename}.tmp"
                remote_final = f"{self.outbox_dir.rstrip('/')}/{filename}"
                with sftp.file(remote_tmp, "wb") as f:
                    f.write(payload)
                sftp.posix_rename(remote_tmp, remote_final)
            finally:
                self._close_sync(sftp, ssh)

        await asyncio.to_thread(_send)
        logger.info("maslaka.transport.sftp: sent %d bytes → %s/%s", len(payload), self.outbox_dir, filename)

    async def list_inbox(self) -> list[VaultFile]:
        def _list() -> list[VaultFile]:
            sftp, ssh = self._connect_sync()
            try:
                out: list[VaultFile] = []
                for attr in sftp.listdir_attr(self.inbox_dir):
                    name = attr.filename
                    if name.startswith(".") or name.endswith(".tmp"):
                        continue
                    out.append(VaultFile(name=name, bytes_size=int(attr.st_size or 0)))
                return sorted(out, key=lambda v: v.name)
            finally:
                self._close_sync(sftp, ssh)

        return await asyncio.to_thread(_list)

    async def fetch(self, filename: str) -> bytes:
        def _fetch() -> bytes:
            sftp, ssh = self._connect_sync()
            try:
                with sftp.file(f"{self.inbox_dir.rstrip('/')}/{filename}", "rb") as f:
                    return f.read()
            finally:
                self._close_sync(sftp, ssh)

        return await asyncio.to_thread(_fetch)

    async def archive(self, filename: str) -> None:
        def _archive() -> None:
            sftp, ssh = self._connect_sync()
            try:
                src = f"{self.inbox_dir.rstrip('/')}/{filename}"
                dst = f"{self.archive_dir.rstrip('/')}/{int(time.time())}_{filename}"
                sftp.rename(src, dst)
            finally:
                self._close_sync(sftp, ssh)

        await asyncio.to_thread(_archive)
        logger.info("maslaka.transport.sftp: archived %s/%s", self.inbox_dir, filename)

    async def healthcheck(self) -> bool:
        def _check() -> bool:
            try:
                sftp, ssh = self._connect_sync()
                self._close_sync(sftp, ssh)
                return True
            except Exception as e:
                logger.warning("maslaka.transport.sftp: healthcheck failed: %s", e)
                return False

        return await asyncio.to_thread(_check)


# ─── Factory ───────────────────────────────────────────────────────────────
_singleton: VaultTransport | None = None


def get_transport() -> VaultTransport:
    """Return the configured transport, cached.

    Selection mirrors `is_cardcom_configured()` in `services/payment_service.py:24`:
    if SFTP settings are missing we silently fall back to the local mock so
    dev environments keep working out of the box.
    """
    global _singleton
    if _singleton is not None:
        return _singleton

    transport_kind = (settings.MASLAKA_TRANSPORT or "local").lower()
    if transport_kind == "sftp" and settings.MASLAKA_SFTP_HOST:
        _singleton = SftpVaultTransport(
            host=settings.MASLAKA_SFTP_HOST,
            port=settings.MASLAKA_SFTP_PORT,
            username=settings.MASLAKA_SFTP_USERNAME,
            password=settings.MASLAKA_SFTP_PASSWORD,
            key_path=settings.MASLAKA_SFTP_KEY_PATH,
            outbox=settings.MASLAKA_SFTP_OUTBOX,
            inbox=settings.MASLAKA_SFTP_INBOX,
            archive=settings.MASLAKA_SFTP_ARCHIVE,
        )
        logger.info("maslaka.transport: using SFTP vault at %s", settings.MASLAKA_SFTP_HOST)
    else:
        _singleton = LocalVaultTransport(
            outbox=settings.MASLAKA_LOCAL_OUTBOX,
            inbox=settings.MASLAKA_LOCAL_INBOX,
            archive=settings.MASLAKA_LOCAL_ARCHIVE,
        )
        if transport_kind == "sftp":
            logger.warning(
                "maslaka.transport: MASLAKA_TRANSPORT=sftp but MASLAKA_SFTP_HOST is empty — "
                "falling back to local mock"
            )
        else:
            logger.info(
                "maslaka.transport: using local-filesystem vault (outbox=%s)",
                settings.MASLAKA_LOCAL_OUTBOX,
            )

    return _singleton


def reset_transport_for_tests() -> None:
    """Clear the cached singleton — used in unit tests to swap transports."""
    global _singleton
    _singleton = None
