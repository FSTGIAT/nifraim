r"""Phoenix PowerTerm — WINDOWS-side discovery probe.

Run this ON WINDOWS (not WSL/Linux), while the Phoenix green-screen terminal
is OPEN, to learn how we can automate it. It answers three things:

  1. Which top-level window is the PowerTerm terminal (title + class + pid) —
     so a script can target it.
  2. Whether PowerTerm exposes a COM/OLE automation interface (the clean way
     to send "13" and read the screen buffer programmatically).
  3. Whether we can read the on-screen text via the clipboard (Select-All →
     Copy), as a fallback if COM isn't available.

It does NOT change anything in the terminal — read-only discovery.

PREREQUISITES (Windows, not WSL):
    - Windows Python (e.g. C:\Python312\python.exe) — NOT the WSL python.
    - pip install pywin32

HOW TO RUN (from a Windows terminal, with the terminal already open):
    python phoenix_win_probe.py

Or from WSL, invoking the Windows Python:
    /mnt/c/Path/To/python.exe scripts/windows/phoenix_win_probe.py

Send me the printed output (especially the PowerTerm window's title/class and
the COM result) and I'll build the keystroke automation from it.
"""

import sys

# Windows consoles default to cp1252 and choke on Hebrew window titles. Force
# UTF-8 so we can print the PowerTerm window's (Hebrew) title.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def _require_win32():
    try:
        import win32gui  # noqa: F401
        import win32process  # noqa: F401
        import win32com.client  # noqa: F401
        import win32clipboard  # noqa: F401
    except Exception as e:
        print("ERROR: this must run on WINDOWS Python with pywin32 installed.")
        print("       pip install pywin32")
        print(f"       import error: {e}")
        raise SystemExit(1)


def list_windows():
    import win32gui
    import win32process
    found = []

    def cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        cls = win32gui.GetClassName(hwnd)
        if not title and not cls:
            return
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
        except Exception:
            pid = None
        found.append((hwnd, title, cls, pid))

    win32gui.EnumWindows(cb, None)
    return found


# Heuristics for the PowerTerm/HostView window.
NEEDLES = ["powerterm", "hostview", "webconnect", "ericom", "fnx", "פניקס", "מסוף"]


def main():
    _require_win32()
    print("=" * 70)
    print("PHOENIX POWERTERM — WINDOWS PROBE")
    print("=" * 70)

    wins = list_windows()
    print(f"\n[1] Visible top-level windows: {len(wins)}")
    cands = []
    for hwnd, title, cls, pid in wins:
        tl = (title or "").lower()
        cl = (cls or "").lower()
        if any(n in tl or n in cl for n in NEEDLES):
            cands.append((hwnd, title, cls, pid))

    print("\n[1a] LIKELY PowerTerm/terminal windows (matched keywords):")
    if cands:
        for hwnd, title, cls, pid in cands:
            print(f"   hwnd={hwnd} pid={pid} class={cls!r} title={title!r}")
    else:
        print("   (none matched — printing ALL windows below so we can spot it)")

    print("\n[1b] ALL visible windows (find the terminal by its title):")
    for hwnd, title, cls, pid in wins:
        if title.strip():
            print(f"   pid={pid} class={cls!r} title={title[:70]!r}")

    # [2] COM automation probe.
    print("\n[2] COM/OLE automation probe (the clean way to script PowerTerm):")
    import win32com.client
    for progid in ("PowerTerm", "PowerTerm.PowerTermApp", "Ericom.PowerTerm",
                   "PTSession.Application", "PowerTermPro"):
        try:
            obj = win32com.client.Dispatch(progid)
            print(f"   OK   Dispatch({progid!r}) succeeded → {obj}")
            try:
                methods = [m for m in dir(obj) if not m.startswith("_")][:40]
                print(f"        members: {methods}")
            except Exception:
                pass
        except Exception as e:
            print(f"   no   {progid}: {type(e).__name__}: {str(e)[:80]}")

    # [3] Clipboard read of the focused terminal (fallback screen-scrape).
    print("\n[3] Clipboard test (fallback to read screen text):")
    print("    -> If a PowerTerm window is focused, in PowerTerm use")
    print("       Edit > Select All, Edit > Copy, then re-run with --clip to dump it.")
    if "--clip" in sys.argv:
        import win32clipboard
        try:
            win32clipboard.OpenClipboard()
            data = win32clipboard.GetClipboardData()
            win32clipboard.CloseClipboard()
            print("    clipboard text (first 1500 chars):")
            print(data[:1500])
        except Exception as e:
            print(f"    clipboard read failed: {e}")

    print("\nDONE. Send me section [1a]/[1b] (the terminal window's title+class)")
    print("and section [2] (any COM 'OK' line). That tells me how to send '13'.")


if __name__ == "__main__":
    main()
