"""
GameBlocker - system tray icon. Runs in your user session (launched at login),
so there's always a padlock in the tray showing the blocker is active — even
when the app window is closed.

  * Left-click (or "Open Game Blocker")  -> opens the control-panel window.
  * "Quit"                               -> removes the tray icon only. It does
                                            NOT stop blocking (the service keeps
                                            running); it just hides this icon.

Run from source:  python blocker_tray.py   (needs: pip install pystray pillow)
"""

import os
import sys
import subprocess

import pystray
from PIL import Image, ImageDraw


def _base_dir():
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def _icon_image():
    for p in (os.path.join(_base_dir(), "assets", "icon.png"),
              os.path.join(_base_dir(), "icon.png")):
        try:
            if os.path.exists(p):
                return Image.open(p)
        except Exception:
            pass
    # fallback: draw a simple padlock tile
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([2, 2, 62, 62], radius=14, fill=(45, 108, 223, 255))
    d.rounded_rectangle([20, 32, 44, 52], radius=5, fill=(255, 255, 255, 255))
    d.arc([22, 16, 42, 40], start=180, end=360, fill=(255, 255, 255, 255), width=5)
    return img


def _app_command():
    """Path to launch the control panel: the built exe if present, else the
    python script (dev)."""
    frozen = getattr(sys, "frozen", False)
    folder = os.path.dirname(sys.executable if frozen else os.path.abspath(__file__))
    exe = os.path.join(folder, "GameBlocker.exe")
    if os.path.exists(exe):
        return [exe]
    return [sys.executable, os.path.join(folder, "blocker_app.py")]


def open_app(icon, item):
    try:
        subprocess.Popen(_app_command(), close_fds=True)
    except Exception:
        pass


def quit_tray(icon, item):
    icon.stop()


def main():
    menu = pystray.Menu(
        pystray.MenuItem("Open Game Blocker", open_app, default=True),
        pystray.MenuItem("Quit", quit_tray),
    )
    pystray.Icon("GameBlocker", _icon_image(), "Game Blocker — running", menu).run()


if __name__ == "__main__":
    main()
