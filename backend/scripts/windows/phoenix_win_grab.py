r"""Capture the open Phoenix PowerTerm terminal window to a PNG (read-only).

Non-destructive: it only grabs the window's pixels (PrintWindow) — it sends NO
keystrokes, so it can't disturb the live host session. Used to SEE the terminal
menu so we can plan the keystroke automation precisely.

Run on Windows (or via Windows Python from WSL) with the terminal open:
    /mnt/c/Python313/python.exe scripts/windows/phoenix_win_grab.py [out.bmp]

Saves a .bmp (no PIL needed). Default: C:\fnxbox\phoenix_term.bmp
"""

import sys

TARGET_CLASS = "TERM"
TARGET_TITLE_NEEDLE = "PowerTerm"


def main():
    try:
        import win32gui
        import win32ui
        import win32con  # noqa: F401
    except Exception as e:
        print("ERROR: run with Windows Python + pywin32. import error:", e)
        raise SystemExit(1)

    out = sys.argv[1] if len(sys.argv) > 1 else r"C:\fnxbox\phoenix_term.bmp"

    # Find the TERM window.
    hwnd_found = []

    def cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        cls = win32gui.GetClassName(hwnd)
        title = win32gui.GetWindowText(hwnd)
        if cls == TARGET_CLASS or TARGET_TITLE_NEEDLE.lower() in (title or "").lower():
            hwnd_found.append((hwnd, cls, title))

    win32gui.EnumWindows(cb, None)
    if not hwnd_found:
        print("No PowerTerm/TERM window found. Is the terminal open?")
        raise SystemExit(2)

    hwnd, cls, title = hwnd_found[0]
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print(f"Capturing hwnd={hwnd} class={cls!r} title={title!r}")

    left, top, right, bot = win32gui.GetWindowRect(hwnd)
    w, h = right - left, bot - top
    if w <= 0 or h <= 0:
        print(f"bad window size {w}x{h}")
        raise SystemExit(3)

    hwnd_dc = win32gui.GetWindowDC(hwnd)
    mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
    save_dc = mfc_dc.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(mfc_dc, w, h)
    save_dc.SelectObject(bmp)

    # PrintWindow (flag 2 = PW_RENDERFULLCONTENT) captures even some GPU surfaces.
    import ctypes
    res = ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 2)
    if not res:
        # Fallback to BitBlt of the screen region.
        save_dc.BitBlt((0, 0), (w, h), mfc_dc, (0, 0), win32con.SRCCOPY)

    bmp.SaveBitmapFile(save_dc, out)
    print(f"saved {w}x{h} -> {out}  (PrintWindow result={res})")

    win32gui.DeleteObject(bmp.GetHandle())
    save_dc.DeleteDC()
    mfc_dc.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwnd_dc)


if __name__ == "__main__":
    main()
