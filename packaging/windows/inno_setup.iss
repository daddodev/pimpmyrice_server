[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={pf}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=..\..\dist
OutputBaseFilename={#AppName}-Setup-{#AppVersion}
Compression=lzma
SolidCompression=yes

[Files]
Source: "..\..\dist\{#CmdName}.exe"; DestDir: "{app}"; Flags: ignoreversion

[UninstallDelete]
Type: files; Name: "{app}\{#CmdName}.exe"

[Tasks]
Name: "autostart"; Description: "Start {#AppName} on system startup"; GroupDescription: "Additional tasks"; Flags: unchecked

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#CmdName}.exe"
Name: "{userstartup}\{#AppName}"; Filename: "{app}\{#CmdName}.exe"; Tasks: autostart
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#CmdName}.exe"; \
    Description: "Run {#AppName} now"; \
    Parameters: "start"; \
    Flags: nowait postinstall skipifsilent runhidden

Filename: "cmd"; \
    Parameters: "/C setx PATH ""%PATH%;C:\PROGRA~2\{#AppName}"""; \
    Flags: runhidden

