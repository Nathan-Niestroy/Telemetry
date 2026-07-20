#define MyAppName "Telemetry"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Telemetry"
#define MyAppExeName "Telemetry.exe"

[Setup]
AppId={{2BA28D5B-417D-42D8-84B0-BAB1CB36E06E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Telemetry
DefaultGroupName=Telemetry
OutputDir=..\dist\installer
OutputBaseFilename=Telemetry-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "..\dist\Telemetry.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Telemetry"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Telemetry"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Telemetry"; Flags: nowait postinstall skipifsilent
