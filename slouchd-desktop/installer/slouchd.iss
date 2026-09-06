; inno setup script for slouchd
; offline windows installer with silent startup, start menu, and desktop shortcuts

#define MyAppName "slouchd"
#ifndef MyAppVersion
  #define MyAppVersion "0.2.1"
#endif
#define MyAppPublisher "Javad Jam (slouchd)"
#define MyAppURL "https://github.com/JavadJam01/slouchd"
#define MyAppExeName "slouchd.exe"
#define MyAppSetupMutex "slouchd_A386D672_setup_mutex"

[Setup]
AppId={{A386D672-8C84-4822-9214-E4B7CA81B43F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\{#MyAppName}
UsePreviousAppDir=yes
DisableDirPage=auto
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline
OutputBaseFilename=slouchd-setup-v{#MyAppVersion}
OutputDir=..\dist\installer
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
SetupMutex={#MyAppSetupMutex},Global\{#MyAppSetupMutex}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
SetupAppRunningError=Another instance of {#MyAppName} Setup is already running.%n%nPlease complete or close the existing installation before running Setup again.

[Files]
Source: "..\dist\slouchd\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; clean old pyinstaller runtime files on update to avoid conflicts with new package versions
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"

[Registry]
; silently register startup on windows boot without admin rights
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\{#MyAppExeName}"; Flags: nowait; Check: WizardSilent

[UninstallDelete]
Type: files; Name: "{app}\*.log"

[Code]
function ShowWindow(hWnd: HWND; uCmdShow: Integer): Boolean;
external 'ShowWindow@user32.dll stdcall';

function SetForegroundWindow(hWnd: HWND): Boolean;
external 'SetForegroundWindow@user32.dll stdcall';

// close running slouchd when setup starts
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
  Wnd: HWND;
begin
  Result := True;

  // prevent multiple installer instances from running concurrently
  if CheckForMutexes('{#MyAppSetupMutex},Global\{#MyAppSetupMutex}') then
  begin
    Wnd := FindWindowByClassName('TWizardForm');
    if Wnd <> 0 then
    begin
      ShowWindow(Wnd, 9); // SW_RESTORE
      SetForegroundWindow(Wnd);
    end;
    SuppressibleMsgBox('Another instance of ' + '{#MyAppName}' + ' Setup is already running.' + #13#10#13#10 +
      'Please complete or close the existing installation window before continuing.',
      mbInformation, MB_OK, MB_OK);
    Result := False;
    Exit;
  end;

  // stop running slouchd process
  Exec('taskkill.exe', '/F /T /IM {#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  // wait for file handles to release
  Sleep(400);
end;

// close running slouchd before install begins (safety net)
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  Result := '';
  // stop running slouchd process
  Exec('taskkill.exe', '/F /T /IM {#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  // wait for file handles to release
  Sleep(400);
end;

// close running slouchd on uninstall
function InitializeUninstall(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;

  // prevent uninstall while setup is currently installing
  if CheckForMutexes('{#MyAppSetupMutex},Global\{#MyAppSetupMutex}') then
  begin
    SuppressibleMsgBox('Setup is currently running for ' + '{#MyAppName}' + '.' + #13#10#13#10 +
      'Please complete or close the setup wizard before uninstalling.',
      mbError, MB_OK, MB_OK);
    Result := False;
    Exit;
  end;

  Exec('taskkill.exe', '/F /T /IM {#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(400);
end;
