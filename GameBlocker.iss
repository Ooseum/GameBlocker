; GameBlocker - Inno Setup script (the traditional install wizard)
; Build:  iscc GameBlocker.iss   ->  produces Output\GameBlockerSetup.exe
;
; Keep the AppId the same across versions so new installers UPGRADE in place
; (your enrolled numbers in C:\ProgramData\GameBlocker are kept).
; To ship an update: bump MyAppVersion, rebuild the exes, rerun iscc.

#define MyAppName "Game Blocker"
#define MyAppVersion "1.1.0"
#define MyAppExe "GameBlocker.exe"
#define MySvcExe "GameBlockerService.exe"
#define MyNotifyExe "GameBlockerNotify.exe"
#define MyTrayExe "GameBlockerTray.exe"
#define MySvcName "GameBlockerService"

[Setup]
AppId={{8F3C2B14-5D7A-4E9B-9C21-1A2B3C4D5E6F}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\GameBlocker
DefaultGroupName=Game Blocker
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExe}
OutputBaseFilename=GameBlockerSetup
SetupIconFile=assets\icon.ico
Compression=lzma2
SolidCompression=yes
; admin rights are needed to install a service
PrivilegesRequired=admin
WizardStyle=modern

[Files]
Source: "dist\{#MyAppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\{#MySvcExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\{#MyNotifyExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\{#MyTrayExe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Game Blocker"; Filename: "{app}\{#MyAppExe}"
Name: "{group}\Uninstall Game Blocker"; Filename: "{uninstallexe}"
; launch the popup notifier and the tray icon at login
Name: "{userstartup}\Game Blocker Notifier"; Filename: "{app}\{#MyNotifyExe}"
Name: "{userstartup}\Game Blocker Tray"; Filename: "{app}\{#MyTrayExe}"

[Run]
; install + configure the service, then start it
Filename: "{app}\{#MySvcExe}"; Parameters: "--startup auto install"; Flags: runhidden waituntilterminated
Filename: "{sys}\sc.exe"; Parameters: "failure {#MySvcName} reset= 0 actions= restart/5000/restart/5000/restart/5000"; Flags: runhidden waituntilterminated
Filename: "{sys}\sc.exe"; Parameters: "start {#MySvcName}"; Flags: runhidden waituntilterminated
; start the notifier and tray now (so the user doesn't have to log out/in first)
Filename: "{app}\{#MyNotifyExe}"; Flags: nowait runhidden
Filename: "{app}\{#MyTrayExe}"; Flags: nowait runhidden
; offer to open the app to set up family numbers
Filename: "{app}\{#MyAppExe}"; Description: "Set up family numbers now"; Flags: postinstall nowait skipifsilent

[UninstallRun]
Filename: "{sys}\sc.exe"; Parameters: "stop {#MySvcName}"; Flags: runhidden waituntilterminated; RunOnceId: "StopSvc"
Filename: "{app}\{#MySvcExe}"; Parameters: "remove"; Flags: runhidden waituntilterminated; RunOnceId: "RemoveSvc"
Filename: "{sys}\taskkill.exe"; Parameters: "/im {#MyNotifyExe} /f"; Flags: runhidden; RunOnceId: "StopNotify"
Filename: "{sys}\taskkill.exe"; Parameters: "/im {#MyTrayExe} /f"; Flags: runhidden; RunOnceId: "StopTray"
