# Game Blocker

A Windows focus tool. A background **service** blocks chosen games; a **React
app** (in a native window) lets family members enroll numbers and lets you
lock/unlock. Visible and honestly named — no hiding, no disguise.

## What's here

| File | Job |
|------|-----|
| `blocker_core.py` | config, hashing, 3-of-N unlock logic, lock state |
| `blocker_service.py` | the Windows service that kills blocked games |
| `blocker_app.py` | the app window (pywebview) + Python↔JS bridge |
| `blocker_detect.py` | auto-scan for installed games |
| `frontend/` | the React UI (source in `src/`, **built** in `dist/`) |
| `GameBlocker.spec` | PyInstaller build (makes the two .exe files) |
| `GameBlocker.iss` | Inno Setup build (makes the install wizard) |
| `requirements.txt` | Python deps |

## How it works

Games start **unlocked**. Press **Lock games** (free, no timer) and they stay
blocked until someone unlocks with the family code.

Each person enrolls a 1–3 digit favorite number (stored as a salted hash — you
never see it again). Enroll **3 or more** people before you can lock. To unlock,
everyone types their number into one box, any order, e.g. `14, 12, 13` →
`141213` or `121314`. The program tries every split into three 1–3 digit numbers
and unlocks if three *different* people match.

Editing the blocked list is free while unlocked; while locked it needs the
family code (so you can't delete a game to cheat). 5 themes live in Settings.

## Build the installer (on Windows)

The React UI is **already built** into `frontend/dist`, so you do NOT need Node.
Just:

```powershell
pip install -r requirements.txt
python -m PyInstaller GameBlocker.spec
& "C:\Program Files\Inno Setup 7\ISCC.exe" GameBlocker.iss
```

- `pyinstaller` → `dist\GameBlocker.exe` + `dist\GameBlockerService.exe`
- `iscc` → `Output\GameBlockerSetup.exe` (the shareable wizard)

> The app uses the Edge **WebView2** runtime, which ships with Windows 11. If a
> machine lacks it, the free "Evergreen" installer from Microsoft adds it.

## Test without building

```powershell
pip install -r requirements.txt
python blocker_app.py        # the app window
python blocker_service.py debug   # blocking loop in a console
```

## Changing the UI (optional, needs Node)

Only if you want to edit the look:
```powershell
cd frontend
npm install
npm run build     # rewrites frontend/dist
```
Then rebuild the exe. If you never touch the UI, ignore this — `dist` is already
built.

## Shipping an update

Keep the `AppId` in `GameBlocker.iss`, bump `MyAppVersion`, rebuild, rerun
`iscc`. The new installer upgrades in place and keeps enrolled numbers
(they live in `C:\ProgramData\GameBlocker`).

## The honest limit

You stay administrator, so you *can* still beat this (disable the service in
`services.msc`, or boot Safe Mode) with a few minutes of deliberate effort. The
self-restart stops a lazy kill, not a determined one. For a true lock, run your
daily account as **Standard** and have a family member hold the admin password.
