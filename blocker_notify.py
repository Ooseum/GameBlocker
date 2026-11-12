"""
GameBlocker - notifier. Runs in your user session (launched at login). Watches
the file the service writes when it blocks a game, and shows a small themed
popup bottom-right: "Games are locked - <name> can't run right now."

Matches the theme you picked in the app. One hidden window that we show for a
few seconds per block, then hide again. Opaque + Windows-rounded corners (no
transparency, which proved unstable in WebView2).

Run from source:        python blocker_notify.py
See it immediately:      python blocker_notify.py --test
"""

import os
import sys
import json
import time
import threading

import webview

from blocker_core import load_config, LAST_BLOCK_PATH

THEMES = {
    "Daylight": dict(card="#FFFFFF", fg="#1A1A1A", sub="#8A877D", border="#E6E4DC", lock="#B23B3B"),
    "Midnight": dict(card="#202227", fg="#E8E8EA", sub="#8B8E95", border="#2E3036", lock="#E86A6A"),
    "Focus":    dict(card="#241E34", fg="#EFECF6", sub="#9A92AD", border="#352C4A", lock="#E68FD0"),
    "Slate":    dict(card="#25282C", fg="#E6E8EA", sub="#9BA0A5", border="#363A3F", lock="#E09A6A"),
    "Rose":     dict(card="#FFFFFF", fg="#2A1F1F", sub="#9A8683", border="#EBDAD8", lock="#B2502F"),
}

W, H = 330, 84

HTML = """
<!doctype html><html><head><meta charset="utf-8"><style>
  html,body{margin:0;height:100%;overflow:hidden;
    font-family:-apple-system,"Segoe UI",Roboto,sans-serif;background:#202227;}
  #card{position:fixed;inset:0;display:flex;align-items:center;gap:12px;padding:0 16px;
    opacity:0;transform:translateY(8px);transition:opacity .22s ease,transform .22s ease;}
  #card.show{opacity:1;transform:none;}
  #dot{width:34px;height:34px;border-radius:10px;flex:none;display:flex;
    align-items:center;justify-content:center;}
  #dot svg{width:18px;height:18px;}
  #txt{min-width:0;}
  #t1{font-size:13px;font-weight:600;line-height:1.2;}
  #t2{font-size:12px;line-height:1.3;margin-top:2px;overflow:hidden;
    white-space:nowrap;text-overflow:ellipsis;}
</style></head><body>
  <div id="card">
    <div id="dot"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
      stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg></div>
    <div id="txt"><div id="t1">Games are locked</div><div id="t2"></div></div>
  </div>
<script>
  function showToast(data){
    document.body.style.background=data.card;
    var c=document.getElementById('card');
    document.getElementById('t1').style.color=data.fg;
    document.getElementById('t2').style.color=data.sub;
    var dot=document.getElementById('dot');
    dot.style.background=data.lock+'22'; dot.style.color=data.lock;
    document.getElementById('t2').textContent=data.name+' can\\'t run right now';
    void c.offsetWidth; c.classList.add('show');
  }
  function hideToast(){ document.getElementById('card').classList.remove('show'); }
</script></body></html>
"""


def _round_corners(title):
    try:
        import ctypes
        for _ in range(40):
            hwnd = ctypes.windll.user32.FindWindowW(None, title)
            if hwnd:
                break
            time.sleep(0.1)
        else:
            return
        pref = ctypes.c_int(2)  # DWMWCP_ROUND
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(pref), ctypes.sizeof(pref))
    except Exception:
        pass


def _screen_bottom_right():
    # Position above the taskbar like the native Windows flyouts, using the work
    # area (screen minus taskbar) rather than the full screen height.
    # NOTE: do NOT call SetProcessDPIAware here — pywebview positions windows in
    # logical pixels, and the work-area rect comes back in the same logical units.
    try:
        import ctypes
        from ctypes import wintypes
        rect = wintypes.RECT()
        # SPI_GETWORKAREA = 0x0030
        ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
        return rect.right - W - 16, rect.bottom - H - 70
    except Exception:
        return 900, 600


def _popup(window, name):
    theme = THEMES.get(load_config().get("theme", "Daylight"), THEMES["Daylight"])
    payload = dict(theme); payload["name"] = name
    window.show()
    window.evaluate_js(f"showToast({json.dumps(payload)})")
    time.sleep(4.2)
    window.evaluate_js("hideToast()")
    time.sleep(0.3)
    window.hide()


def watch(window, test=False):
    time.sleep(1.2)  # let the window finish loading
    if test:
        print("notify: showing test toast")
        _popup(window, "Steam")

    last_ts = 0.0
    try:
        if os.path.exists(LAST_BLOCK_PATH):
            with open(LAST_BLOCK_PATH, encoding="utf-8") as f:
                last_ts = json.load(f).get("ts", 0.0)
    except Exception:
        pass

    while True:
        time.sleep(1.0)
        try:
            if not os.path.exists(LAST_BLOCK_PATH):
                continue
            with open(LAST_BLOCK_PATH, encoding="utf-8") as f:
                ev = json.load(f)
            ts = float(ev.get("ts", 0.0))
            if ts <= last_ts:
                continue
            last_ts = ts
            print("notify: block ->", ev.get("name"))
            _popup(window, ev.get("name", "That game"))
        except Exception as e:
            print("notify: watch error", e)
            time.sleep(1.0)


def main():
    test = "--test" in sys.argv
    x, y = _screen_bottom_right()
    win = webview.create_window(
        "GameBlocker Notifier", html=HTML,
        width=W, height=H, x=x, y=y,
        frameless=True, on_top=True, resizable=False,
        easy_drag=False,   # not draggable — dragging a frameless WebView2 window blanks it
        focus=False, hidden=True,
    )
    threading.Thread(target=_round_corners, args=("GameBlocker Notifier",), daemon=True).start()
    threading.Thread(target=watch, args=(win, test), daemon=True).start()
    webview.start()


if __name__ == "__main__":
    main()
