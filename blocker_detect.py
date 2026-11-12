"""
GameBlocker - auto-detect installed games.

Best-effort scan, like the big blockers do it:
  * Steam: find the install path, read libraryfolders.vdf for every library
    drive, read each appmanifest (.acf) for the game folder, collect the .exe
    files inside steamapps/common/<game>/.
  * Known launchers: check default install locations.
  * Roblox / Minecraft: known per-user locations.

Returns a sorted list of executable names (e.g. "RobloxPlayerBeta.exe") you can
add to the blocklist. It SUGGESTS; the UI lets you pick, so nothing critical
gets blocked by accident.

Windows-only (uses winreg + Windows paths). Safe to import elsewhere: every
step is guarded, so on failure it just returns fewer results.
"""

import os
import re
import glob

# exe names that live in game folders but aren't the game
_IGNORE = re.compile(
    r"(unins|redist|vcredist|vc_redist|dotnet|directx|dxsetup|crashhandler|"
    r"crashpad|setup|installer|launcher_installer|uninstall)",
    re.IGNORECASE,
)

_LAUNCHER_DEFAULTS = {
    "steam.exe": [r"C:\Program Files (x86)\Steam\steam.exe"],
    "EpicGamesLauncher.exe": [
        r"C:\Program Files (x86)\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe",
        r"C:\Program Files\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe",
    ],
    "Battle.net.exe": [r"C:\Program Files (x86)\Battle.net\Battle.net.exe"],
    "RiotClientServices.exe": [r"C:\Riot Games\Riot Client\RiotClientServices.exe"],
}


def _steam_path():
    try:
        import winreg
        for root, sub in [
            (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
        ]:
            try:
                with winreg.OpenKey(root, sub) as k:
                    val, _ = winreg.QueryValueEx(k, "SteamPath" if root == winreg.HKEY_CURRENT_USER else "InstallPath")
                    if val and os.path.isdir(val):
                        return val
            except OSError:
                continue
    except Exception:
        pass
    default = r"C:\Program Files (x86)\Steam"
    return default if os.path.isdir(default) else None


def _steam_libraries(steam):
    libs = [steam]
    vdf = os.path.join(steam, "steamapps", "libraryfolders.vdf")
    try:
        with open(vdf, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        for p in re.findall(r'"path"\s+"([^"]+)"', text):
            p = p.replace("\\\\", "\\")
            if os.path.isdir(p) and p not in libs:
                libs.append(p)
    except OSError:
        pass
    return libs


def _steam_games(steam):
    found = set()
    for lib in _steam_libraries(steam):
        apps = os.path.join(lib, "steamapps")
        for acf in glob.glob(os.path.join(apps, "appmanifest_*.acf")):
            try:
                with open(acf, "r", encoding="utf-8", errors="ignore") as f:
                    m = re.search(r'"installdir"\s+"([^"]+)"', f.read())
                if not m:
                    continue
                game_dir = os.path.join(apps, "common", m.group(1))
                if not os.path.isdir(game_dir):
                    continue
                # collect exes, limited depth to keep it fast
                for base, _dirs, files in os.walk(game_dir):
                    if base[len(game_dir):].count(os.sep) > 2:
                        _dirs[:] = []
                        continue
                    for fn in files:
                        if fn.lower().endswith(".exe") and not _IGNORE.search(fn):
                            found.add(fn)
            except OSError:
                continue
    return found


def _per_user_games():
    found = set()
    local = os.environ.get("LOCALAPPDATA", "")
    # Roblox
    for exe in glob.glob(os.path.join(local, "Roblox", "Versions", "*", "RobloxPlayerBeta.exe")):
        found.add(os.path.basename(exe))
    # Minecraft (Java launcher)
    for cand in [
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Minecraft Launcher", "MinecraftLauncher.exe"),
        os.path.join(local, "Programs", "Minecraft Launcher", "MinecraftLauncher.exe"),
    ]:
        if cand and os.path.isfile(cand):
            found.add(os.path.basename(cand))
    return found


def detect_games():
    """Return a sorted list of suggested executable names to block."""
    found = set()
    steam = _steam_path()
    if steam:
        found.add("steam.exe")
        try:
            found |= _steam_games(steam)
        except Exception:
            pass
    for exe, paths in _LAUNCHER_DEFAULTS.items():
        if any(os.path.isfile(p) for p in paths):
            found.add(exe)
    found |= _per_user_games()
    return sorted(found, key=str.lower)


if __name__ == "__main__":
    for g in detect_games():
        print(g)
