"""
GameBlocker - Windows service (the part that does the blocking).

Runs under the Service Control Manager with an honest, visible name
(GameBlockerService). While locked, it scans running processes every 2s and
terminates anything on the blocklist. On startup it scans immediately, so a
game launched during the brief restart gap gets killed as soon as the service
is back.

Self-restart: configured via SCM failure-recovery in install.ps1
(`sc failure ... actions= restart/5000`). If the process is force-killed,
Windows relaunches it. A clean admin "Stop" is still possible because you are
the administrator in this build -- that is the honest ceiling (see README).

Install / run: see README.md.
Run in console for testing:   python blocker_service.py debug
"""

import os
import json
import time

import psutil  # pip install psutil

from blocker_core import load_config, is_locked, LAST_BLOCK_PATH, CONFIG_DIR

SCAN_SECONDS = 2
NOTIFY_COOLDOWN = 20          # seconds before the same game notifies again
_recent = {}                  # name -> last-notified timestamp


def _record_block(display_name):
    """Tell the notifier a game was just blocked (with a per-game cooldown)."""
    now = time.time()
    if now - _recent.get(display_name, 0) < NOTIFY_COOLDOWN:
        return
    _recent[display_name] = now
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        tmp = LAST_BLOCK_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"name": display_name, "ts": now}, f)
        os.replace(tmp, LAST_BLOCK_PATH)
    except OSError:
        pass


def enforce_once():
    cfg = load_config()
    if not is_locked(cfg):
        return
    blocked = {n.lower() for n in cfg.get("blocklist", [])}
    for proc in psutil.process_iter(["name"]):
        try:
            raw = proc.info["name"] or ""
            if raw.lower() in blocked:
                proc.kill()
                _record_block(raw[:-4] if raw.lower().endswith(".exe") else raw)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass


def run_loop(stop_check=lambda: False):
    while not stop_check():
        try:
            enforce_once()
        except Exception:
            pass  # never let one bad scan kill the loop
        time.sleep(SCAN_SECONDS)


# ---- Windows service wrapper (pywin32) ----
try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager

    class GameBlockerService(win32serviceutil.ServiceFramework):
        _svc_name_ = "GameBlockerService"
        _svc_display_name_ = "Game Blocker Service"
        _svc_description_ = "Blocks selected games until unlocked with the family code."

        def __init__(self, args):
            super().__init__(args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self._running = True

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            self._running = False
            win32event.SetEvent(self.stop_event)

        def SvcDoRun(self):
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, ""),
            )
            run_loop(stop_check=lambda: not self._running)

    _HAS_PYWIN32 = True
except ImportError:
    _HAS_PYWIN32 = False


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "debug":
        # Console mode for testing without installing the service.
        print("GameBlocker running in console mode. Ctrl+C to stop.")
        run_loop()
    elif not _HAS_PYWIN32:
        print("pywin32 not installed. Run: pip install pywin32")
        print("Or test logic with: python blocker_service.py debug")
    elif len(sys.argv) == 1:
        # No args => started by the Windows Service Control Manager. Hand control
        # to the service dispatcher. This is REQUIRED for the PyInstaller-frozen
        # service to actually run; without it the service "starts" but the
        # blocking loop never executes (HandleCommandLine would just print usage).
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(GameBlockerService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        # install / remove / start / stop / --startup ... from the installer.
        win32serviceutil.HandleCommandLine(GameBlockerService)
