"""Gateway self-update — staging, self-test, the release gate, probation, rollback.

    source backend/venv/bin/activate && python backend/tests/test_gateway_self_update.py

No DB, no network, no 9100: every Gateway path runs in a temp GATEWAY_HOME with
the network calls stubbed, against the REAL release bundle this checkout would serve.
"""
import io
import json
import os
import sys
import tempfile
import time
import zipfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'} — {label}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILURES.append(label)


def main() -> None:
    from app.services.maslaka import gateway_release as gr
    import gateway_updater as gu
    import gateway_launcher as gl

    print("\nThe release bundle (server side):")
    v = gr.version()
    blob = gr.bundle()
    z = zipfile.ZipFile(io.BytesIO(blob))
    names = set(z.namelist())
    check("version is a stable content hash", v == gr.version() and len(v) == 16, v)
    check("bundle names its own version", z.read("backend/GATEWAY_VERSION").decode().strip() == v)
    for need in ("backend/maslaka_worker.py", "backend/gateway_updater.py", "backend/gateway_launcher.py",
                 "backend/requirements.txt", "backend/gateway_selftest/sample.DAT",
                 "backend/app/services/maslaka/orchestration.py", "backend/app/services/parser_service.py"):
        check(f"bundle carries {need.split('backend/')[1]}", need in names)
    check("the WHOLE app tree, not hand-picked files",
          sum(1 for n in names if n.startswith("backend/app/")) > 300, str(len(names)))
    check("no bytecode in the bundle", not any(n.endswith(".pyc") or "__pycache__" in n for n in names))
    os.environ.pop("GATEWAY_TOKEN", None)
    from app.config import settings
    settings.GATEWAY_TOKEN = ""
    check("no GATEWAY_TOKEN configured → every token refused (endpoints 404)", not gr.token_ok("anything"))
    settings.GATEWAY_TOKEN = "s3cret"
    check("right token accepted, wrong refused", gr.token_ok("s3cret") and not gr.token_ok("nope"))

    with tempfile.TemporaryDirectory() as tmp:
        h = Path(tmp)
        os.environ["GATEWAY_HOME"] = str(h)
        os.environ["GATEWAY_BASE"] = "https://example.invalid"
        os.environ["GATEWAY_TOKEN"] = "s3cret"
        # the "running" legacy tree: an older version, same requirements
        # GATEWAY_HOME has a .env, exactly like C:\Nifraim\app (the dev one stands in)
        import shutil as _sh
        _sh.copy(BACKEND.parent / ".env", h / ".env")
        legacy = h / "backend"
        legacy.mkdir()
        (legacy / "GATEWAY_VERSION").write_text("oldversion000000")
        (legacy / "requirements.txt").write_bytes((BACKEND / "requirements.txt").read_bytes())

        print("\nStaging refuses bad bundles, the live tree untouched:")
        try:
            gu.stage(h, b"not a zip", v); check("garbage refused", False)
        except Exception:
            check("garbage refused", True)
        try:
            gu.stage(h, blob, "someotherversion"); check("a bundle that isn't the RELEASED version is refused", False)
        except RuntimeError as e:
            check("a bundle that isn't the RELEASED version is refused", "not the released" in str(e))
        check("live tree untouched", (legacy / "GATEWAY_VERSION").read_text() == "oldversion000000")

        print("\nSelf-test (separate process — compile + import + parse a real מסלקה file):")
        rel = gu.stage(h, blob, v)
        ok, out = gu.selftest(rel / "backend")
        check("the real release passes its self-test", ok, out.strip().splitlines()[-1] if out.strip() else "")
        broken = h / "broken"
        import shutil
        shutil.copytree(rel / "backend", broken)
        (broken / "app" / "services" / "maslaka" / "orchestration.py").write_text("def broken(:\n")
        ok_b, _ = gu.selftest(broken)
        check("a release that doesn't compile FAILS its self-test", not ok_b)

        # network stubs
        state = {"pinned": False, "released": v}
        gu._get = lambda url, timeout=60: (json.dumps({"deployed": v, **state}).encode()
                                          if "/version/" in url else blob)
        gu.report = lambda *a, **k: None

        print("\nThe release gate:")
        gu._skip.clear()
        state.update(pinned=True)
        check("pinned → no update", gu.maybe_update(legacy) is False)
        state.update(pinned=False, released=None)
        check("nothing released → no update", gu.maybe_update(legacy) is False)
        state.update(released="oldversion000000")
        check("released == running → no update", gu.maybe_update(legacy) is False)
        os.environ["GATEWAY_AUTO_UPDATE"] = "false"
        state.update(released=v)
        check("GATEWAY_AUTO_UPDATE=false → no update", gu.maybe_update(legacy) is False)
        os.environ.pop("GATEWAY_AUTO_UPDATE")

        (legacy / "requirements.txt").write_text("somethingelse==1\n")
        check("requirements.txt changed → NOT switched", gu.maybe_update(legacy) is False)
        check("… and reported as needs_pip", gu.get_event(h).get("state") == "needs_pip")
        check("… and not re-downloaded every minute", gu.maybe_update(legacy) is False and v in gu._skip)
        gu._skip.clear()
        (legacy / "requirements.txt").write_bytes((BACKEND / "requirements.txt").read_bytes())

        print("\nA released version is taken:")
        took = gu.maybe_update(legacy)
        check("maybe_update → True (caller exits 75)", took is True)
        check("current.txt = the released version", gu.read(h / "current.txt") == v)
        check("previous.txt = what ran before", gu.read(h / "previous.txt") == "oldversion000000")
        check("the new release is on trial", (gu.probation(h) or {}).get("version") == v)
        check("the launcher now starts the new release",
              gl.backend_dir(h) == h / "releases" / v / "backend")

        print("\nProbation:")
        check("first healthy tick clears the trial", gu.clear_probation(h) and gu.probation(h) is None)
        gu.start_probation(h, v, "oldversion000000")
        pr = gu.probation(h); pr["started"] = time.time() - gu.PROBATION_S - 5
        gu.write(h / "probation.json", json.dumps(pr))
        check("a trial past PROBATION_S is expired", gu.probation_expired(h))

        print("\nLauncher rollback:")
        gl.HOME = h
        gu.write(h / "previous.txt", "legacy")
        gu.write(h / "current.txt", v)
        gu.start_probation(h, v, "legacy")
        check("exit 75 → start the new release at once", gl.on_exit(gl.EXIT_SWITCH, h) == 0)
        gl.on_exit(1, h)
        check("one crash on trial → still on the new release", gu.read(h / "current.txt") == v)
        gl.on_exit(1, h)
        check("a second crash on trial → rolled back", gu.read(h / "current.txt") == "legacy")
        check("… to the legacy tree", gl.backend_dir(h) == h / "backend")
        check("… and the event says so", gu.get_event(h).get("state") == "rolled_back")
        gu.write(h / "current.txt", v); gu.write(h / "previous.txt", "legacy"); gu.start_probation(h, v, "legacy")
        gl.on_exit(gl.EXIT_PROBATION, h)
        check("exit 76 (trial expired) → rolled back", gu.read(h / "current.txt") == "legacy")
        check("a crash with NO trial → just restart, no rollback",
              gl.on_exit(1, h) > 0 and gu.read(h / "current.txt") == "legacy")
        check("refused-to-start (exit 2) waits 60s instead of spinning", gl.on_exit(2, h) == 60)
        gu.write(h / "current.txt", "missingversion")
        check("a current.txt naming a missing release falls back to legacy", gl.backend_dir(h) == h / "backend")

    print("\n" + ("ALL PASS" if not FAILURES else f"{len(FAILURES)} FAILED: {FAILURES}"))
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()
