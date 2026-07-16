#define AppName "Gangcord"
#define AppPublisher "GallA"
#define AppExeName "Gangcord.exe"
#define WatcherExeName "GangcordWatcher.exe"
#define AppURL "https://github.com/AlexBarono/Valorant-Media-Control"

#ifndef AppVersion
  #define AppVersion "2.0.1"
#endif

#ifndef AppArchitecture
  #define AppArchitecture "x64"
#endif

[Setup]
AppId={{8F93F3D2-8118-49AF-B4BD-6E55F931DC36}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases/latest
VersionInfoVersion={#AppVersion}.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Setup
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
LicenseFile=LICENSE.txt
OutputDir=..\dist
OutputBaseFilename={#AppName}-Setup-{#AppVersion}
SetupIconFile=..\assets\gangcord.ico
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
CloseApplications=yes
RestartApplications=no
CloseApplicationsFilter={#AppExeName},{#WatcherExeName}
MinVersion=10.0.17763
UsePreviousAppDir=yes
UsePreviousTasks=yes
UsedUserAreasWarning=no
#if AppArchitecture == "x64"
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
PrivilegesRequiredOverrideCurrentUser=Install for &current user
PrivilegesRequiredOverrideCurrentUserRecommended=Install for &current user (recommended)
PrivilegesRequiredOverrideAllUsers=Install for &all users
PrivilegesRequiredOverrideAllUsersRecommended=Install for &all users (recommended)

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\app\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\app\{#WatcherExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#WatcherExeName}"; Parameters: "{code:GetAutoLaunchParameters}"; StatusMsg: "Configuring automatic game detection..."; Flags: runhidden nowait runasoriginaluser
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent runasoriginaluser

[UninstallRun]
Filename: "{app}\{#WatcherExeName}"; Parameters: "--configure none"; RunOnceId: "DisableGangcordWatcher"; Flags: runhidden waituntilterminated
Filename: "{sys}\taskkill.exe"; Parameters: "/IM ""{#WatcherExeName}"" /T /F"; RunOnceId: "StopGangcordWatcherFallback"; Flags: runhidden waituntilterminated

[Code]
var
  AutoLaunchPage: TInputOptionWizardPage;
  UserDataPromptShown: Boolean;

function ExistingAutoLaunchIndex: Integer;
var
  ConfigText: AnsiString;
  ConfigPath: String;
begin
  Result := 0;
  ConfigPath := ExpandConstant('{localappdata}\Gangcord\config.json');
  if LoadStringFromFile(ConfigPath, ConfigText) then
  begin
    if Pos('"auto_launch_mode": "both"', ConfigText) > 0 then
      Result := 3
    else if Pos('"auto_launch_mode": "lol"', ConfigText) > 0 then
      Result := 2
    else if Pos('"auto_launch_mode": "valorant"', ConfigText) > 0 then
      Result := 1;
  end;
end;

procedure InitializeWizard;
begin
  AutoLaunchPage := CreateInputOptionPage(
    wpSelectTasks,
    'Automatic Game Detection',
    'Choose when Gangcord should open automatically.',
    'The watcher only checks Windows process names. It does not inspect game memory, files, or anti-cheat components.',
    True,
    False
  );
  AutoLaunchPage.Add('Do not start automatically');
  AutoLaunchPage.Add('Start with Valorant');
  AutoLaunchPage.Add('Start with League of Legends');
  AutoLaunchPage.Add('Start with Valorant and League of Legends');
  AutoLaunchPage.SelectedValueIndex := ExistingAutoLaunchIndex;
end;

function GetAutoLaunchParameters(Param: String): String;
begin
  case AutoLaunchPage.SelectedValueIndex of
    1: Result := '--configure valorant';
    2: Result := '--configure lol';
    3: Result := '--configure both';
  else
    Result := '--configure none';
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  Exec(
    ExpandConstant('{sys}\taskkill.exe'),
    '/IM "{#WatcherExeName}" /T /F',
    '',
    SW_HIDE,
    ewWaitUntilTerminated,
    ResultCode
  );
  Result := '';
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usUninstall) and not UserDataPromptShown then
  begin
    UserDataPromptShown := True;
    if not UninstallSilent then
    begin
      if MsgBox(
        'Delete all Gangcord settings, logs, cache, and personal application data?',
        mbConfirmation,
        MB_YESNO
      ) = IDYES then
        DelTree(ExpandConstant('{localappdata}\Gangcord'), True, True, True);
    end;

    DelTree(ExpandConstant('{%TEMP}\Gangcord'), True, True, True);
  end;
end;
