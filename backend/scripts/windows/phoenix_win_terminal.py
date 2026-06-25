r"""Phoenix PowerTerm terminal driver (WINDOWS side, invoked via Windows Python).

Drives the native PowerTerm WebConnect "HostView" terminal window (class TERM)
because it exposes no COM interface. Two safe-by-default actions:

  wait-grab [timeout_s]   poll for the TERM window, then capture it to a PNG
                          (read-only — sends NO keystrokes). Default action.
  grab                    one-shot capture of the TERM window to PNG.
  send "<keys>"           focus the TERM window and type <keys>. Use \n for
                          Enter, e.g.  send "13\n"  to pick menu option 13.

PNG out: C:\fnxbox\phoenix_term.png  (override with --out PATH)

Run via:  /mnt/c/Python313/python.exe scripts/windows/phoenix_win_terminal.py wait-grab 180
"""

import sys
import time
import ctypes

# DPI-awareness — WITHOUT this, on a scaled display (125%/150%) GetWindowRect /
# SetCursorPos return mismatched coordinates, so synthetic clicks land in the
# wrong place (and window grabs catch the wrong window). Set it before any
# window/cursor calls.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_DPI_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

TARGET_CLASS = "TERM"
TITLE_NEEDLE = "powerterm"
DEFAULT_OUT = r"C:\fnxbox\phoenix_term.png"


LOG_PATH = r"C:\fnxbox\term_action.log"


def _log(msg):
    """Print and append to a log file — so elevated runs (separate window) can
    report results back to us via the file."""
    print(msg)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(str(msg) + "\n")
    except Exception:
        pass


def _utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# Browser window classes that can carry "PowerTerm" in their TAB title — these
# are NOT the terminal and must be excluded.
_BROWSER_CLASSES = {"Chrome_WidgetWin_1", "Chrome_WidgetWin_0", "MozillaWindowClass"}


def find_term():
    import win32gui
    strong = []  # class == TERM — the real native terminal
    weak = []    # title match on a non-browser window (fallback only)

    def cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        cls = win32gui.GetClassName(hwnd)
        title = win32gui.GetWindowText(hwnd) or ""
        if cls == TARGET_CLASS:
            strong.append((hwnd, cls, title))
        elif TITLE_NEEDLE in title.lower() and cls not in _BROWSER_CLASSES:
            weak.append((hwnd, cls, title))

    win32gui.EnumWindows(cb, None)
    return strong or weak


def force_foreground(hwnd):
    """Reliably bring hwnd to the foreground despite Windows' focus-steal lock,
    using the AttachThreadInput trick."""
    import win32gui
    import win32process
    import win32con
    import win32api
    import ctypes
    user32 = ctypes.windll.user32
    fg = user32.GetForegroundWindow()
    t_fg = win32process.GetWindowThreadProcessId(fg)[0] if fg else 0
    t_tgt = win32process.GetWindowThreadProcessId(hwnd)[0]
    cur = win32api.GetCurrentThreadId()
    for t in (t_fg, t_tgt):
        if t and t != cur:
            try:
                user32.AttachThreadInput(cur, t, True)
            except Exception:
                pass
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        user32.BringWindowToTop(hwnd)
        # Set TOPMOST and LEAVE it — caller restores via restore_window(). This
        # keeps the terminal above the console window through the capture.
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        user32.SetForegroundWindow(hwnd)
    except Exception:
        pass
    for t in (t_fg, t_tgt):
        if t and t != cur:
            try:
                user32.AttachThreadInput(cur, t, False)
            except Exception:
                pass


def restore_window(hwnd):
    import win32gui
    import win32con
    try:
        win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
    except Exception:
        pass


def grab(hwnd, out):
    """Capture the terminal by bringing it to the foreground and screen-grabbing
    its rectangle. PrintWindow returns black for this GPU-rendered TERM window,
    so we grab real screen pixels instead."""
    import win32gui
    from PIL import ImageGrab
    import time as _t

    force_foreground(hwnd)
    _t.sleep(0.8)
    left, top, right, bot = win32gui.GetWindowRect(hwnd)
    w, h = right - left, bot - top
    img = ImageGrab.grab(bbox=(left, top, right, bot), all_screens=True)
    img.save(out)
    restore_window(hwnd)
    return w, h


# ── Real input injection via SendInput (terminals read the focus queue, not
#    posted messages). Unicode mode is layout-independent. Requires the target
#    window to be foreground — we elevate + force_foreground first.
import ctypes as _ctypes
from ctypes import wintypes as _wt

_PUL = _ctypes.POINTER(_ctypes.c_ulong)


class _KBD(_ctypes.Structure):
    _fields_ = [("wVk", _wt.WORD), ("wScan", _wt.WORD), ("dwFlags", _wt.DWORD),
                ("time", _wt.DWORD), ("dwExtraInfo", _PUL)]


class _MOUSE(_ctypes.Structure):
    _fields_ = [("dx", _wt.LONG), ("dy", _wt.LONG), ("mouseData", _wt.DWORD),
                ("dwFlags", _wt.DWORD), ("time", _wt.DWORD), ("dwExtraInfo", _PUL)]


class _INPUT(_ctypes.Structure):
    class _I(_ctypes.Union):
        _fields_ = [("ki", _KBD), ("mi", _MOUSE)]
    _anonymous_ = ("i",)
    _fields_ = [("type", _wt.DWORD), ("i", _I)]


def _click_abs(x, y):
    """Real left-click at screen (x,y) via SendInput with absolute virtual-
    desktop coordinates — works across DPI scaling and multiple monitors,
    unlike mouse_event which wasn't registering."""
    u = _ctypes.windll.user32
    vx, vy = u.GetSystemMetrics(76), u.GetSystemMetrics(77)   # SM_X/YVIRTUALSCREEN
    vw, vh = u.GetSystemMetrics(78), u.GetSystemMetrics(79)   # SM_CX/CYVIRTUALSCREEN
    nx = int((x - vx) * 65535 / max(1, vw))
    ny = int((y - vy) * 65535 / max(1, vh))
    MOVE, ABS, VIRT, LDOWN, LUP = 0x0001, 0x8000, 0x4000, 0x0002, 0x0004
    for flags in (MOVE | ABS | VIRT, LDOWN | ABS | VIRT, LUP | ABS | VIRT):
        inp = _INPUT(type=0, mi=_MOUSE(nx, ny, 0, flags, 0, None))
        _ctypes.windll.user32.SendInput(1, _ctypes.byref(inp), _ctypes.sizeof(inp))


_KEYUP = 0x0002
_UNICODE = 0x0004


def _emit(kbd):
    inp = _INPUT(type=1, ki=kbd)
    _ctypes.windll.user32.SendInput(1, _ctypes.byref(inp), _ctypes.sizeof(inp))


def _press_unicode(ch):
    code = ord(ch)
    _emit(_KBD(0, code, _UNICODE, 0, None))
    _emit(_KBD(0, code, _UNICODE | _KEYUP, 0, None))


def _press_vk(vk):
    _emit(_KBD(vk, 0, 0, 0, None))
    _emit(_KBD(vk, 0, _KEYUP, 0, None))


_SCANCODE = 0x0008


def _press_scancode(sc):
    """Inject a raw keyboard SCANCODE (how host terminals actually read keys —
    they map scancode+mode to the host charset, ignoring Unicode WM_CHAR)."""
    _emit(_KBD(0, sc, _SCANCODE, 0, None))
    _emit(_KBD(0, sc, _SCANCODE | _KEYUP, 0, None))


def _press_alt_shift():
    """Send Alt+Shift — the Windows layout toggle (English <-> Hebrew)."""
    import time as _t
    VK_ALT, VK_SHIFT = 0x12, 0x10
    _emit(_KBD(VK_ALT, 0, 0, 0, None))           # Alt down
    _emit(_KBD(VK_SHIFT, 0, 0, 0, None))         # Shift down
    _t.sleep(0.05)
    _emit(_KBD(VK_SHIFT, 0, _KEYUP, 0, None))    # Shift up
    _emit(_KBD(VK_ALT, 0, _KEYUP, 0, None))      # Alt up


def focus_click(hwnd):
    """Click inside the terminal CONTENT area to give its input keyboard focus
    — same as the operator clicking the screen. Title-bar clicks only activate
    the frame, not the terminal input. We click high in the green header band
    (just below the toolbar) to avoid changing any selected menu/list row."""
    import win32gui
    import time as _t
    user32 = _ctypes.windll.user32
    l, t, r, b = win32gui.GetWindowRect(hwnd)
    # Click in the menu/content band (this position reliably gives the host
    # input focus — keystrokes land — whereas clicking the bottom input line
    # interfered). SendInput absolute click (DPI/multi-monitor correct).
    x = (l + r) // 2
    y = t + 250
    _click_abs(x, y)
    _t.sleep(0.3)
    try:
        fg = user32.GetForegroundWindow()
        _log(f"    focus_click@({x},{y}) fg={fg} target={hwnd} match={fg == hwnd}")
    except Exception:
        pass


def send_vk(hwnd, vk):
    """Inject a virtual-key (e.g. F3) into the foreground TERM window. Relies on
    the operator having clicked the terminal to give the host input real focus
    (synthetic clicks don't); we only re-assert foreground."""
    import time as _t
    force_foreground(hwnd)
    focus_click(hwnd)
    _t.sleep(0.3)
    _press_vk(vk)
    _t.sleep(0.12)


def send_keys(hwnd, keys):
    """Inject keys into the foreground TERM window via SendInput. '\n' -> Enter.
    A real mouse click (DPI-correct) gives the host input focus first."""
    import time as _t
    VK_RETURN = 0x0D
    force_foreground(hwnd)
    focus_click(hwnd)
    _t.sleep(0.4)
    for ch in keys:
        if ch == "\n":
            _press_vk(VK_RETURN)
        elif ch.isascii() and ch.isalnum():
            # Real key-down event (host menus read scancodes, not WM_CHAR).
            _press_vk(ord(ch.upper()))
        else:
            _press_unicode(ch)  # e.g. Hebrew כ
        _t.sleep(0.25)


def main():
    _utf8()
    args = sys.argv[1:]
    action = args[0] if args else "wait-grab"
    out = DEFAULT_OUT
    if "--out" in args:
        out = args[args.index("--out") + 1]

    if action in ("wait-grab", "grab"):
        timeout = int(args[1]) if len(args) > 1 and args[1].isdigit() else (180 if action == "wait-grab" else 0)
        deadline = time.time() + timeout
        while True:
            hits = find_term()
            if hits:
                hwnd, cls, title = hits[0]
                print(f"FOUND hwnd={hwnd} class={cls!r} title={title!r}")
                try:
                    w, h = grab(hwnd, out)
                    print(f"CAPTURED {w}x{h} -> {out}")
                except Exception as e:
                    print(f"capture failed: {e}")
                return
            if time.time() >= deadline:
                print("TERM window not found within timeout.")
                return
            time.sleep(2)

    elif action == "send":
        if len(args) < 2:
            print('usage: send "13\\n"')
            raise SystemExit(2)
        hits = find_term()
        if not hits:
            print("No TERM window — open the terminal first.")
            raise SystemExit(2)
        hwnd = hits[0][0]
        keys = args[1].encode().decode("unicode_escape")
        _log(f"sending {keys!r} to hwnd={hwnd}")
        try:
            send_keys(hwnd, keys)
            _log("send OK")
        except Exception as e:
            _log(f"send FAILED: {type(e).__name__}: {e}")
            raise SystemExit(1)
        time.sleep(1.0)
        try:
            grab(hwnd, out)
            _log(f"post-send capture -> {out}")
        except Exception as e:
            _log(f"capture failed: {e}")
    elif action == "export":
        # Full post-13 export sequence (operator-described):
        #   type "mu" -> Enter x3 -> F3 (select row) -> "כ" (download to PC).
        # Captures each step so we can verify, then reports new C:\fnxbox files.
        import os
        import glob as _glob
        VK_F3 = 0x72
        FNXBOX = r"C:\fnxbox"
        # Wait up to 150s for the terminal window to appear (so there's no
        # timing gap between the operator opening it and us driving it).
        _log("export: waiting up to 300s for the TERM window — do login+OTP and open the terminal…")
        hits = []
        for _ in range(150):
            hits = find_term()
            if hits:
                break
            time.sleep(2)
        if not hits:
            _log("export: no TERM window appeared within 300s.")
            raise SystemExit(2)
        hwnd = hits[0][0]
        _log(f"export: driving hwnd={hwnd}")
        time.sleep(2)  # let the menu settle after it appears

        def snap(tag):
            try:
                grab(hwnd, os.path.join(FNXBOX, f"export_{tag}.png"))
            except Exception as e:
                _log(f"  snap {tag} failed: {e}")

        def files_state():
            # name -> (size, mtime) so we detect overwrites, not just new names.
            return {os.path.basename(p): (os.path.getsize(p), os.path.getmtime(p))
                    for p in _glob.glob(os.path.join(FNXBOX, "MU_*"))}

        before = files_state()
        VK_F3 = 0x72   # select prev file in the list
        VK_F4 = 0x73   # select next (down) file in the list — the on-screen hint
                       # is "(F3/F4)בחירה"; the arrow key registers as numpad-'2'
                       # (NumLock on) and types into the field instead of moving.
        # Operator's EXACT sequence from the MAIN MENU (confirmed 2026-06-25),
        # keyboard-mode-aware — the host reads the Windows layout:
        #   [ENGLISH] "13" + Enter  ->  Enter x5 more  ->  Down-arrow x1
        #   -> [HEBREW] 'כ'  (download MU_NK_HAYV to C:\fnxbox)
        # The Down-arrow selects the right file row before download — without it
        # the כ acts on the wrong/empty selection (the bug we hit).
        def tap(keys, settle=1.2, tag=None):
            force_foreground(hwnd); focus_click(hwnd); time.sleep(0.2)
            send_keys(hwnd, keys); time.sleep(settle)
            if tag: snap(tag)

        snap("0_menu")
        # ENGLISH: 13 + Enter, then 5 more Enters (6 total).
        _log("  [EN] '13' + Enter"); tap("13\n", settle=1.3, tag="1_after13")
        for n in range(1, 6):
            _log(f"  Enter #{n}"); tap("\n", settle=1.3, tag=f"2_enter{n}")
        # F4 once = select the NEXT (down) file row (newest = MU_..._06). The
        # arrow key registers as numpad-'2' and stays on row 1 (the _05 bug).
        _log("  F4 x1 (select next/newest file)")
        force_foreground(hwnd); focus_click(hwnd); time.sleep(0.2)
        send_vk(hwnd, VK_F4); time.sleep(1.0); snap("2b_select")
        # HEBREW: 'כ' (download) — Alt+Shift to Hebrew, scancode 0x21 (physical
        # כ/f key), then Alt+Shift back to English.
        _log("  Alt+Shift -> Hebrew, 'כ' (scancode 0x21), Alt+Shift -> back")
        force_foreground(hwnd); focus_click(hwnd); time.sleep(0.3)
        _press_alt_shift(); time.sleep(0.7)
        _press_scancode(0x21)
        # CRITICAL: 'כ' opens the KERMIT File-Transfer dialog and the receive
        # begins immediately. Do NOT touch the terminal now — NO screenshots
        # (grab() uses PrintWindow + topmost which interrupts PowerTerm's receive
        # message loop and STALLS KERMIT at block 6 / 0 B/s — the bug), no focus
        # changes, no Alt+Shift. Just poll the FILESYSTEM (no window interaction)
        # until the MU file finishes growing. KERMIT for ~668KB takes a while.
        # Keep PowerTerm the ACTIVE FOREGROUND window during the transfer —
        # Windows throttles a backgrounded window's message loop, which starves
        # PowerTerm's KERMIT receive and stalls it at block 6. Re-assert
        # foreground every few seconds via SetForegroundWindow ONLY (NO grab/
        # PrintWindow/topmost — those interrupt the receive).
        changed = []
        stable = 0
        last_sizes = {}
        for i in range(150):  # up to ~150s for the transfer to complete
            if i % 4 == 0:
                try:
                    windll = __import__("ctypes").windll
                    windll.user32.SetForegroundWindow(hwnd)
                except Exception:
                    pass
            now = files_state()
            changed = [n for n, v in now.items() if before.get(n) != v]
            if changed:
                # wait until the changed file's size stops growing (transfer done)
                cur_sizes = {n: now[n][0] for n in changed}
                if cur_sizes == last_sizes:
                    stable += 1
                    if stable >= 3:
                        _log(f"  DOWNLOADED/UPDATED (stable): {sorted(changed)}")
                        break
                else:
                    stable = 0
                last_sizes = cur_sizes
            time.sleep(1.0)
        else:
            _log(f"  no completed file change. before={before} now={files_state()}")
        snap("4_after")
        snap("4_done")
        _log("export: done")

    elif action == "export14":
        # Option 14 = "בנית קבצי פרודוקציה" → builds the PRODUCTION .MBT set
        # (LIFE/COVRLIFE/LIFEHLTH/COMPANY.MBT) into the Windows Downloads folder.
        # The exact post-14 flow is recon'd live, so this captures EVERY step to
        # export14_*.png and watches Downloads for new/updated *.MBT. Refine the
        # keystrokes from the screenshots (mirrors how option-13 `export` was built).
        import os
        import glob as _glob
        FNXBOX = r"C:\fnxbox"
        DL = os.path.join(os.path.expanduser("~"), "Downloads")
        _log(f"export14: waiting up to 300s for the TERM window… (Downloads={DL})")
        hits = []
        for _ in range(150):
            hits = find_term()
            if hits:
                break
            time.sleep(2)
        if not hits:
            _log("export14: no TERM window appeared within 300s.")
            raise SystemExit(2)
        hwnd = hits[0][0]
        _log(f"export14: driving hwnd={hwnd}")
        time.sleep(2)

        def snap14(tag):
            try:
                grab(hwnd, os.path.join(FNXBOX, f"export14_{tag}.png"))
            except Exception as e:
                _log(f"  snap {tag} failed: {e}")

        def mbt_state():
            files = _glob.glob(os.path.join(DL, "*.MBT")) + _glob.glob(os.path.join(DL, "*.mbt"))
            return {os.path.basename(p): (os.path.getsize(p), os.path.getmtime(p)) for p in files}

        # Each keystroke MUST be focus-clicked first — the probe proved a plain
        # send_keys Enter no-ops, but a focus_click'd Enter activates the menu.
        def tap(keys, settle=1.3, tag=None):
            force_foreground(hwnd); focus_click(hwnd); time.sleep(0.25)
            send_keys(hwnd, keys); time.sleep(settle)
            if tag:
                snap14(tag)

        before = mbt_state()
        snap14("0_start")
        # Reset to the main menu first (Escape a few times) so we start clean
        # regardless of where the terminal was left.
        _log("  reset: Escape x3")
        for _ in range(3):
            tap("\x1b", settle=0.6)
        snap14("0_menu")
        # Option 14, then activate with a focus-clicked Enter.
        _log("  '14' + Enter"); tap("14", settle=1.2, tag="1_after14")
        tap("\n", settle=1.5, tag="1b_activated")
        # Step through the build screens one Enter at a time (each focus-clicked),
        # capturing each so we can see exactly what option 14 asks for.
        for n in range(1, 6):
            _log(f"  Enter #{n}"); tap("\n", settle=1.5, tag=f"2_enter{n}")
        # Some screens may need the Hebrew כ confirm like option 13 — attempt it,
        # but the build often writes the .MBT set straight to Downloads on its own.
        _log("  Alt+Shift -> Hebrew, 'כ' (scancode 0x21), Alt+Shift -> back")
        force_foreground(hwnd); focus_click(hwnd); time.sleep(0.3)
        _press_alt_shift(); time.sleep(0.7)
        _press_scancode(0x21); time.sleep(0.8); snap14("3_kaf")
        _press_alt_shift(); time.sleep(0.4)
        _log("  Enter (confirm)"); tap("\n", settle=2.5, tag="4_after")
        # The production build can take a while; wait up to 120s for .MBT to land.
        changed = []
        for _ in range(120):
            now = mbt_state()
            changed = [n for n, v in now.items() if before.get(n) != v]
            if changed:
                _log(f"  BUILT/UPDATED .MBT: {sorted(changed)}")
                break
            time.sleep(1.0)
        else:
            _log(f"  no .MBT change detected. before={sorted(before)} now={sorted(mbt_state())}")
        snap14("5_done")
        _log("export14: done")

    elif action == "testheb":
        # Test the כ keystroke on the CURRENT screen: focus -> Alt+Shift (Hebrew)
        # -> send כ/f key -> capture -> Alt+Shift back. Operator should have the
        # terminal on the screen where כ is expected (the file list).
        import os, glob as _glob
        FNXBOX = r"C:\fnxbox"
        hits = find_term()
        if not hits:
            _log("testheb: no TERM window."); raise SystemExit(2)
        hwnd = hits[0][0]
        before = {os.path.basename(p): (os.path.getsize(p), os.path.getmtime(p))
                  for p in _glob.glob(os.path.join(FNXBOX, "MU_*"))}
        force_foreground(hwnd); focus_click(hwnd); time.sleep(0.4)
        grab(hwnd, os.path.join(FNXBOX, "heb_0_before.png"))
        _log("  Alt+Shift -> Hebrew"); _press_alt_shift(); time.sleep(0.7)
        grab(hwnd, os.path.join(FNXBOX, "heb_1_switched.png"))
        _log("  send כ (scancode 0x21, the f/כ key)"); _press_scancode(0x21); time.sleep(0.8)
        grab(hwnd, os.path.join(FNXBOX, "heb_2_kaf.png"))
        _log("  Alt+Shift -> back to English"); _press_alt_shift(); time.sleep(0.4)
        grab(hwnd, os.path.join(FNXBOX, "heb_3_back.png"))
        now = {os.path.basename(p): (os.path.getsize(p), os.path.getmtime(p))
               for p in _glob.glob(os.path.join(FNXBOX, "MU_*"))}
        changed = [n for n, v in now.items() if before.get(n) != v]
        _log(f"testheb: file changed={changed}")
        _log("testheb: done — see heb_*.png")

    elif action == "type13":
        # Diagnostic: type just "13" (no Enter) and capture, to confirm it
        # registers in the menu selection.
        import os
        hits = find_term()
        if not hits:
            _log("type13: no TERM window."); raise SystemExit(2)
        hwnd = hits[0][0]
        _log(f"type13: sending '13' to hwnd={hwnd}")
        send_keys(hwnd, "13")
        time.sleep(1.0)
        grab(hwnd, r"C:\fnxbox\type13.png")
        _log("type13: done — see type13.png")

    elif action == "kaf":
        # Send just 'כ' (download) to the currently-open export screen.
        import os, glob as _glob
        FNXBOX = r"C:\fnxbox"
        hits = find_term()
        if not hits:
            _log("kaf: no TERM window."); raise SystemExit(2)
        hwnd = hits[0][0]
        before = {os.path.basename(p): (os.path.getsize(p), os.path.getmtime(p))
                  for p in _glob.glob(os.path.join(FNXBOX, "MU_*"))}
        _log(f"kaf: sending 'כ' via SCANCODE 0x21 to hwnd={hwnd}")
        force_foreground(hwnd)
        focus_click(hwnd)
        time.sleep(0.3)
        _press_scancode(0x21)  # physical 'f' key = כ on the Israeli layout
        time.sleep(2.0)
        grab(hwnd, os.path.join(FNXBOX, "kaf_after.png"))
        for _ in range(25):
            now = {os.path.basename(p): (os.path.getsize(p), os.path.getmtime(p))
                   for p in _glob.glob(os.path.join(FNXBOX, "MU_*"))}
            changed = [n for n, v in now.items() if before.get(n) != v]
            if changed:
                _log(f"kaf: DOWNLOADED/UPDATED: {sorted(changed)}"); break
            time.sleep(1.0)
        else:
            _log("kaf: no file change detected.")
        _log("kaf: done")

    else:
        print(__doc__)


if __name__ == "__main__":
    main()
