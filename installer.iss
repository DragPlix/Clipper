; Inno Setup script for Clipper by Flexibles AI
; Produces a single Clipper-Setup-<ver>.exe that installs to %LocalAppData%\Clipper.

#define MyAppName        "Clipper"
#define MyAppVersion     "1.0.0"
#define MyAppPublisher   "Flexibles AI"
#define MyAppExeName     "Clipper.exe"
#define MyAppId          "{{C1A0E6F7-1D2F-4B6E-8E4A-CB1F3A5E8A10}}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://flexibles.ai
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} by {#MyAppPublisher}
VersionInfoVersion={#MyAppVersion}
VersionInfoProductName={#MyAppName}

; Install per-user (no admin required) — nice for hobby distribution.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
DisableDirPage=yes

OutputDir=dist
OutputBaseFilename=Clipper-Setup-{#MyAppVersion}
Compression=lzma2/ultra
SolidCompression=yes
LZMAUseSeparateProcess=yes
WizardStyle=modern

UninstallDisplayName={#MyAppName} ({#MyAppPublisher})
UninstallDisplayIcon={app}\{#MyAppExeName}

SetupIconFile=
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"
Name: "startwithwindows"; Description: "Start {#MyAppName} when I sign in to Windows"; GroupDescription: "Startup:"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{userprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "{#MyAppName} by {#MyAppPublisher}"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Autostart when user signs in — opt-in via the task above.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "{#MyAppName}"; \
    ValueData: """{app}\{#MyAppExeName}"""; \
    Tasks: startwithwindows; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; \
    Description: "Launch {#MyAppName}"; \
    Flags: nowait postinstall skipifsilent
