# PyInstaller spec - builds four onefile exes:
#   GameBlocker.exe         (the React UI window, shown in your apps)
#   GameBlockerService.exe  (the background service that blocks games)
#   GameBlockerNotify.exe   (user-session popup when a game is blocked)
#   GameBlockerTray.exe     (system-tray icon so you know it's running)
#
# The React app is pre-built into frontend/dist and bundled in, so you do NOT
# need Node to build the installer.
#
# Build on Windows:   pyinstaller GameBlocker.spec   ->   dist\

from PyInstaller.utils.hooks import collect_all

block_cipher = None
ICON = 'assets/icon.ico'

# pywebview ships platform backends + JS that must be bundled.
wv_datas, wv_binaries, wv_hidden = collect_all('webview')

# ---- UI app (pywebview + React) ----
ui_a = Analysis(
    ['blocker_app.py'], pathex=[],
    binaries=wv_binaries,
    datas=wv_datas + [('frontend/dist', 'frontend/dist')],
    hiddenimports=wv_hidden,
    hookspath=[], runtime_hooks=[], excludes=[], cipher=block_cipher,
)
ui_pyz = PYZ(ui_a.pure, ui_a.zipped_data, cipher=block_cipher)
ui_exe = EXE(ui_pyz, ui_a.scripts, ui_a.binaries, ui_a.zipfiles, ui_a.datas, [],
    name='GameBlocker', console=False, onefile=True, upx=False, icon=ICON)

# ---- Notifier (pywebview popup) ----
nt_a = Analysis(
    ['blocker_notify.py'], pathex=[],
    binaries=wv_binaries, datas=wv_datas, hiddenimports=wv_hidden,
    hookspath=[], runtime_hooks=[], excludes=[], cipher=block_cipher,
)
nt_pyz = PYZ(nt_a.pure, nt_a.zipped_data, cipher=block_cipher)
nt_exe = EXE(nt_pyz, nt_a.scripts, nt_a.binaries, nt_a.zipfiles, nt_a.datas, [],
    name='GameBlockerNotify', console=False, onefile=True, upx=False, icon=ICON)

# ---- Tray icon (pystray) ----
tr_a = Analysis(
    ['blocker_tray.py'], pathex=[],
    binaries=[], datas=[('assets/icon.png', 'assets')],
    hiddenimports=['pystray._win32', 'PIL.Image', 'PIL.ImageDraw'],
    hookspath=[], runtime_hooks=[], excludes=[], cipher=block_cipher,
)
tr_pyz = PYZ(tr_a.pure, tr_a.zipped_data, cipher=block_cipher)
tr_exe = EXE(tr_pyz, tr_a.scripts, tr_a.binaries, tr_a.zipfiles, tr_a.datas, [],
    name='GameBlockerTray', console=False, onefile=True, upx=False, icon=ICON)

# ---- Service ----
svc_a = Analysis(
    ['blocker_service.py'], pathex=[], binaries=[], datas=[],
    hiddenimports=['win32timezone', 'win32serviceutil', 'win32service',
                   'win32event', 'servicemanager', 'psutil'],
    hookspath=[], runtime_hooks=[], excludes=[], cipher=block_cipher,
)
svc_pyz = PYZ(svc_a.pure, svc_a.zipped_data, cipher=block_cipher)
svc_exe = EXE(svc_pyz, svc_a.scripts, svc_a.binaries, svc_a.zipfiles, svc_a.datas, [],
    name='GameBlockerService', console=True, onefile=True, upx=False, icon=ICON)
