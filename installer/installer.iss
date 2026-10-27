; Inno Setup script for PoE Inspector. Built by build_installer.ps1 (defines Stage and Out).
; The game's files and the database are NOT part of the package: the first launch builds them from the user's own Path of Exile 2 install.
#define AppName "PoE Inspector"
#define AppVer "1.0"

[Setup]
AppId={{6E2C1B9A-3F54-4B0E-9A4D-5B2F7C0D8E11}
AppName={#AppName}
AppVersion={#AppVer}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
OutputDir={#Out}
OutputBaseFilename=PoE Inspector Setup {#AppVer}
SetupIconFile={#Stage}\poe_inspector.ico
UninstallDisplayIcon={app}\poe_inspector.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#Stage}\runtime\*"; DestDir: "{app}\runtime"; Flags: recursesubdirs ignoreversion
Source: "{#Stage}\app\*"; DestDir: "{app}\app"; Flags: recursesubdirs ignoreversion
Source: "{#Stage}\poe_inspector.ico"; DestDir: "{app}"

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\runtime\pythonw.exe"; Parameters: """{app}\app\app_main.pyw"""; WorkingDir: "{app}\app"; IconFilename: "{app}\poe_inspector.ico"; AppUserModelID: "ColdVision.PoEInspector"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\runtime\pythonw.exe"; Parameters: """{app}\app\app_main.pyw"""; WorkingDir: "{app}\app"; IconFilename: "{app}\poe_inspector.ico"; AppUserModelID: "ColdVision.PoEInspector"; Tasks: desktopicon

[Run]
Filename: "{app}\runtime\pythonw.exe"; Parameters: """{app}\app\app_main.pyw"""; WorkingDir: "{app}\app"; Description: "Запустить {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\app\__pycache__"
Type: filesandordirs; Name: "{app}\app\poe_inspector\__pycache__"
; the database and caches live in %LOCALAPPDATA%\PoE Inspector and are kept on uninstall (about 1 GB, rebuilt on demand)
