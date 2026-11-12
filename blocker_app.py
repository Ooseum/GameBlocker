"""
GameBlocker - the app window. Renders the React UI (frontend/dist) in a native
window via pywebview, and bridges button clicks to the Python core.

The service (blocker_service.py) is what actually blocks games; this app only
sets state (lock/unlock, enroll, blocklist, theme) in the shared config.

Run from source:   python blocker_app.py   (needs: pip install pywebview)
A tiny localhost server serves the built files, so ES modules load correctly
(file:// blocks them in some engines).
"""

import os
import sys
import time
import threading
import functools
import http.server
import socketserver

import webview


def _round_corners(_title=None):
    """Ask Windows 11 to round this window's corners. Called after the window is
    shown (the app is foreground then), so we use the foreground window handle —
    more reliable than FindWindow on a frameless window."""
    try:
        import ctypes
        time.sleep(0.15)
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return
        pref = ctypes.c_int(2)  # DWMWCP_ROUND
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(pref), ctypes.sizeof(pref))
    except Exception:
        pass

from blocker_core import (
    load_config, save_config, enroll, valid_unlock, lock, unlock,
    is_locked, set_number, MIN_ENROLLED,
)


def _base_dir():
    # PyInstaller unpacks bundled data to sys._MEIPASS
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def _dist_dir():
    return os.path.join(_base_dir(), "frontend", "dist")


class _Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # never let WebView2 cache the UI, so a rebuild always loads fresh
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def log_message(self, *a, **k):
        pass


def _serve(directory):
    handler = functools.partial(_Handler, directory=directory)
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)  # 0 = any free port
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd.server_address[1]


# The window lives at module scope, NOT as an attribute of Api. pywebview
# serializes the js_api object to expose it to JavaScript; if the native window
# were an attribute, that serialization recurses into it forever
# (window.native.AccessibilityObject.Bounds.Empty.Empty... -> recursion crash).
_window = None


class Api:
    def __init__(self):
        self.settings_unlocked = False
        self.manage_unlocked = False   # set once a valid code is entered on the manage page

    def _manage_allowed(self, cfg, code):
        """Editing/removing enrolled people is allowed when: there are fewer than
        MIN_ENROLLED people (no lock can exist), OR the manage page was already
        unlocked this session, OR a valid family code is supplied now (which also
        unlocks the page for the rest of the session)."""
        if len(cfg.get("enrolled", [])) < MIN_ENROLLED:
            return True
        if self.manage_unlocked:
            return True
        if code and valid_unlock(cfg, code):
            self.manage_unlocked = True
            return True
        return False

    def minimize(self):
        try:
            _window.minimize()
        except Exception:
            pass

    def close(self):
        try:
            _window.destroy()
        except Exception:
            pass

    def start_drag(self):
        """Native window drag: tell Windows to move the focused window, as if its
        title bar were grabbed. Uses the foreground window (the app has focus when
        you click its title bar) — more reliable than FindWindow on a frameless
        window. Called from the title bar's mousedown while the button is held."""
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                return
            ctypes.windll.user32.ReleaseCapture()
            WM_NCLBUTTONDOWN, HTCAPTION = 0x00A1, 2
            ctypes.windll.user32.SendMessageW(hwnd, WM_NCLBUTTONDOWN, HTCAPTION, 0)
        except Exception:
            pass

    def get_state(self):
        cfg = load_config()
        enrolled = cfg.get("enrolled", [])
        return {
            "locked": is_locked(cfg),
            "theme": cfg.get("theme", "Daylight"),
            "blocklist": cfg.get("blocklist", []),
            "enrolledCount": len(enrolled),
            "enrolledNames": [m.get("name", "?") for m in enrolled],
            "minEnrolled": MIN_ENROLLED,
        }

    def lock(self):
        cfg = load_config()
        if len(cfg.get("enrolled", [])) < MIN_ENROLLED:
            return {"ok": False, "error": f"Enroll at least {MIN_ENROLLED} people before locking."}
        lock(cfg)
        return {"ok": True}

    def try_unlock(self, code):
        cfg = load_config()
        if valid_unlock(cfg, code or ""):
            unlock(cfg)
            self.settings_unlocked = True
            return {"ok": True}
        return {"ok": False, "error": "That didn't match 3 different people."}

    def enroll(self, name, number):
        cfg = load_config()
        try:
            enroll(cfg, name or "", number or "")
            save_config(cfg)
            return {"ok": True}
        except ValueError as e:
            return {"ok": False, "error": str(e)}

    def edit_number(self, index, code, new_number):
        cfg = load_config()
        if not self._manage_allowed(cfg, code):
            return {"ok": False, "needCode": True}
        try:
            set_number(cfg, int(index), new_number or "")
            save_config(cfg)
            return {"ok": True}
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        except IndexError:
            return {"ok": False, "error": "Person not found."}

    def remove_enrolled(self, index, code=""):
        cfg = load_config()
        if not self._manage_allowed(cfg, code):
            return {"ok": False, "needCode": True}
        try:
            cfg["enrolled"].pop(int(index))
            save_config(cfg)
            return {"ok": True}
        except (IndexError, ValueError):
            return {"ok": False, "error": "Person not found."}

    def can_edit(self):
        return (not is_locked(load_config())) or self.settings_unlocked

    def unlock_settings(self, code):
        if valid_unlock(load_config(), code or ""):
            self.settings_unlocked = True
            return {"ok": True}
        return {"ok": False, "error": "Need the family code to edit while locked."}

    def add_game(self, name):
        name = (name or "").strip()
        if name:
            cfg = load_config()
            cfg.setdefault("blocklist", []).append(name)
            save_config(cfg)
        return {"ok": True}

    def remove_game(self, index):
        cfg = load_config()
        try:
            cfg["blocklist"].pop(int(index))
            save_config(cfg)
        except (IndexError, ValueError, KeyError):
            pass
        return {"ok": True}

    def scan(self):
        try:
            from blocker_detect import detect_games
            return detect_games()
        except Exception:
            return []

    def set_theme(self, name):
        cfg = load_config()
        cfg["theme"] = name
        save_config(cfg)
        return {"ok": True}


def main():
    global _window
    port = _serve(_dist_dir())
    _window = webview.create_window(
        "Game Blocker",
        f"http://127.0.0.1:{port}/index.html",
        js_api=Api(),
        width=380, height=520, min_size=(360, 480),
        frameless=True,          # we draw our own title bar
        easy_drag=False,         # only the .pywebview-drag-region (title bar) drags
    )
    # round the corners only AFTER the window is shown, so it can't race init;
    # run in a thread so the brief wait doesn't block the UI thread
    try:
        _window.events.shown += lambda: threading.Thread(target=_round_corners, daemon=True).start()
    except Exception:
        pass
    webview.start(debug=("--debug" in sys.argv))


if __name__ == "__main__":
    main()
