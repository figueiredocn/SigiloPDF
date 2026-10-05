#ifndef AppVersion
  #error Informe AppVersion pelo script build_windows.ps1
#endif
#ifndef BuildDir
  #define BuildDir "..\dist"
#endif

[Setup]
AppId={{4D915352-1A99-48AD-9702-0B4C321CA698}
AppName=SigiloPDF
AppVersion={#AppVersion}
AppPublisher=Felipe Figueiredo
AppPublisherURL=https://github.com/figueiredocn/SigiloPDF
DefaultDirName={localappdata}\Programs\SigiloPDF
DisableDirPage=no
DefaultGroupName=SigiloPDF
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.19041
OutputDir={#BuildDir}\installer
OutputBaseFilename=SigiloPDF-{#AppVersion}-windows-x64-setup
SetupIconFile=..\app\ui\brand_assets\sigilopdf.ico
UninstallDisplayIcon={app}\SigiloPDF.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
CloseApplications=yes
LicenseFile=..\licenses\AGPL-3.0-only.txt
InfoBeforeFile=..\build\metadata\installer_notice.txt

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar um atalho na área de trabalho"; Flags: unchecked

[Files]
Source: "{#BuildDir}\SigiloPDF\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\SigiloPDF"; Filename: "{app}\SigiloPDF.exe"; AppUserModelID: "SigiloPDF.Desktop"
Name: "{autodesktop}\SigiloPDF"; Filename: "{app}\SigiloPDF.exe"; Tasks: desktopicon; AppUserModelID: "SigiloPDF.Desktop"

[Run]
Filename: "{app}\SigiloPDF.exe"; Description: "Abrir o SigiloPDF"; Flags: nowait postinstall skipifsilent
