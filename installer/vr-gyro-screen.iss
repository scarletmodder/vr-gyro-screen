; Inno Setup script of the Windows installer of VR Gyro Screen.
; It installs the program for the current user (no administrator prompt), in English or in
; Brazilian Portuguese. It installs nothing else: one page shows what the program needs, says
; whether each item was found on this computer and opens the official site of whoever makes it.
; Uninstalling from Windows removes the program and asks whether to remove the settings too.
;
; Build with scripts\build.ps1, which freezes the program first and passes the version.

#if VER < EncodeVer(6, 7, 0)
  #error Inno Setup 6.7 or newer is required (the version this script is built and tested with)
#endif

#define AppName "VR Gyro Screen"
#define AppPublisher "Scarlet Modder"
#define AppURL "https://github.com/scarletmodder/vr-gyro-screen"
#define AppExe "vr-gyro-screen.exe"
; Identifies the installation across upgrades: never change it.
#define AppGuid "B7E4A1C2-5D38-4F96-A0C7-3E9D1B6F2A54"
; The same places the program itself looks at (src\vr_gyro_screen\prerequisites.py).
#define DriverKey "SYSTEM\CurrentControlSet\Services\ViGEmBus"
#define RuntimeKey "SOFTWARE\Khronos\OpenXR\1"
#define DriverURL "https://github.com/nefarius/ViGEmBus/releases/latest"
#define VirtualDesktopURL "https://www.vrdesktop.net/"
; The folder the program keeps its settings in, under the user's application data.
#define DataDirName "vr-gyro-screen"
; Where scripts\build.ps1 leaves the frozen program.
#define FrozenDir "..\work\dist\vr-gyro-screen"

#ifndef AppVersion
  #error AppVersion is missing: run scripts\build.ps1
#endif

[Setup]
AppId={{{#AppGuid}}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
VersionInfoVersion={#AppVersion}.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName}
; Per user: the program needs no administrator rights, so the installer asks for none.
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DefaultDirName={autopf}\{#AppName}
DisableWelcomePage=no
DisableProgramGroupPage=yes
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExe}
SetupIconFile=..\src\vr_gyro_screen\assets\icon.ico
; The settings window holds this mutex while it is open, so Setup asks to close it first.
AppMutex=VRGyroScreenWindow
WizardStyle=modern dynamic windows11
WizardSizePercent=115
ShowLanguageDialog=auto
OutputDir=..\dist
OutputBaseFilename=VRGyroScreen-Setup-v{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
; Fixed date on the installed files: the build time is not recorded.
TimeStampsInUTC=yes
TouchDate=2026-01-01
TouchTime=00:00

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Messages]
en.WelcomeLabel2=This installs [name/ver] on your computer.%n%nIt shows the Virtual Desktop virtual monitor on a big screen inside a Meta Quest headset, and turns the headset controllers into a gamepad with a motion sensor.%n%nNo other program is installed: the next page shows what [name] needs and where to get each item.
pt.WelcomeLabel2=Este assistente instala o [name/ver] no seu computador.%n%nEle mostra o monitor virtual do Virtual Desktop em uma tela grande dentro de um headset Meta Quest, e transforma os controles do headset em um gamepad com sensor de movimento.%n%nNenhum outro programa é instalado: a próxima página mostra o que o [name] precisa e onde conseguir cada item.

[CustomMessages]
en.NeedsTitle=What this program needs
en.NeedsSubtitle=Two programs made by other people. This installer does not install them.
en.NeedsIntro=VR Gyro Screen works together with the two programs below. Each button opens the official site, where you download and install it yourself. You can continue without them and install them later: the program shows this same check on its first page.
en.NeedsDriver=Virtual gamepad driver (ViGEmBus)
en.NeedsDriverWhy=A free driver that lets programs create the gamepad your games will see.
en.NeedsRuntime=Virtual Desktop, as the program that links the headset to this PC
en.NeedsRuntimeWhy=In Virtual Desktop Streamer, on the PC, open Options and choose VDXR as the OpenXR runtime.
en.NeedsFound=found
en.NeedsMissing=not found
en.NeedsOpenDriver=Open the ViGEmBus page
en.NeedsOpenRuntime=Open the Virtual Desktop site
en.NeedsAgain=Check again
en.RemoveSettings=Also remove your VR Gyro Screen settings (screen, motion and buttons)?%n%nChoose No to keep them for a future installation.
en.LaunchNow=Open VR Gyro Screen now
pt.NeedsTitle=O que este programa precisa
pt.NeedsSubtitle=Dois programas feitos por outras pessoas. Este instalador não instala nenhum deles.
pt.NeedsIntro=O VR Gyro Screen funciona junto com os dois programas abaixo. Cada botão abre o site oficial, onde você mesma baixa e instala. Dá para continuar sem eles e instalar depois: o programa mostra esta mesma conferência na primeira página.
pt.NeedsDriver=Driver de controle virtual (ViGEmBus)
pt.NeedsDriverWhy=Um driver gratuito que deixa programas criarem o controle que os seus jogos vão enxergar.
pt.NeedsRuntime=Virtual Desktop, como o programa que liga o headset a este PC
pt.NeedsRuntimeWhy=No Virtual Desktop Streamer, no PC, abra Options e escolha VDXR em OpenXR Runtime.
pt.NeedsFound=encontrado
pt.NeedsMissing=não encontrado
pt.NeedsOpenDriver=Abrir a página do ViGEmBus
pt.NeedsOpenRuntime=Abrir o site do Virtual Desktop
pt.NeedsAgain=Conferir de novo
pt.RemoveSettings=Remover também as suas configurações do VR Gyro Screen (tela, movimento e botões)?%n%nEscolha Não para guardar para uma instalação futura.
pt.LaunchNow=Abrir o VR Gyro Screen agora

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#FrozenDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\THIRD-PARTY-NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchNow}"; Flags: nowait postinstall skipifsilent

[Code]
var
  NeedsPage: TWizardPage;
  DriverStatus, RuntimeStatus: TNewStaticText;

function DriverFound(): Boolean;
var
  Value: String;
begin
  Result := RegQueryStringValue(HKLM64, '{#DriverKey}', 'ImagePath', Value) and (Value <> '');
end;

{ True when the active OpenXR runtime is the one that comes with Virtual Desktop. }
function RuntimeFound(): Boolean;
var
  Value: String;
begin
  Result := False;
  if not RegQueryStringValue(HKLM64, '{#RuntimeKey}', 'ActiveRuntime', Value) then
    exit;
  { Same rule as the program: the file name, without hyphens and underscores. }
  Value := Lowercase(ExtractFileName(Value));
  StringChangeEx(Value, '-', '', True);
  StringChangeEx(Value, '_', '', True);
  Result := Pos('virtualdesktop', Value) > 0;
end;

procedure ShowStatus(Status: TNewStaticText; const Name: String; Found: Boolean);
begin
  if Found then
    Status.Caption := Name + ': ' + CustomMessage('NeedsFound')
  else
    Status.Caption := Name + ': ' + CustomMessage('NeedsMissing');
end;

procedure RefreshNeeds();
begin
  ShowStatus(DriverStatus, CustomMessage('NeedsDriver'), DriverFound());
  ShowStatus(RuntimeStatus, CustomMessage('NeedsRuntime'), RuntimeFound());
end;

procedure OpenSite(const Url: String);
var
  Code: Integer;
begin
  ShellExec('open', Url, '', '', SW_SHOWNORMAL, ewNoWait, Code);
end;

procedure DriverClick(Sender: TObject);
begin
  OpenSite('{#DriverURL}');
end;

procedure RuntimeClick(Sender: TObject);
begin
  OpenSite('{#VirtualDesktopURL}');
end;

procedure AgainClick(Sender: TObject);
begin
  RefreshNeeds();
end;

function AddText(Top: Integer; const Caption: String; Bold: Boolean): TNewStaticText;
begin
  Result := TNewStaticText.Create(NeedsPage);
  Result.Parent := NeedsPage.Surface;
  Result.AutoSize := False;
  Result.WordWrap := True;
  Result.Top := Top;
  Result.Width := NeedsPage.SurfaceWidth;
  if Bold then
    Result.Font.Style := [fsBold];
  Result.Caption := Caption;
  Result.AdjustHeight();
end;

function AddButton(Top, Left: Integer; const Caption: String; OnClick: TNotifyEvent): TNewButton;
begin
  Result := TNewButton.Create(NeedsPage);
  Result.Parent := NeedsPage.Surface;
  Result.Caption := Caption;
  Result.Top := Top;
  Result.Left := Left;
  Result.Width := ScaleX(230);
  Result.Height := WizardForm.NextButton.Height;
  Result.OnClick := OnClick;
end;

procedure InitializeWizard();
var
  Last: TControl;
begin
  NeedsPage := CreateCustomPage(wpWelcome, CustomMessage('NeedsTitle'), CustomMessage('NeedsSubtitle'));
  Last := AddText(0, CustomMessage('NeedsIntro'), False);

  DriverStatus := AddText(Last.Top + Last.Height + ScaleY(14), CustomMessage('NeedsDriver'), True);
  Last := AddText(DriverStatus.Top + DriverStatus.Height + ScaleY(2), CustomMessage('NeedsDriverWhy'), False);
  Last := AddButton(Last.Top + Last.Height + ScaleY(6), 0, CustomMessage('NeedsOpenDriver'), @DriverClick);

  RuntimeStatus := AddText(Last.Top + Last.Height + ScaleY(14), CustomMessage('NeedsRuntime'), True);
  Last := AddText(RuntimeStatus.Top + RuntimeStatus.Height + ScaleY(2), CustomMessage('NeedsRuntimeWhy'), False);
  Last := AddButton(Last.Top + Last.Height + ScaleY(6), 0, CustomMessage('NeedsOpenRuntime'), @RuntimeClick);
  AddButton(Last.Top, Last.Left + Last.Width + ScaleX(8), CustomMessage('NeedsAgain'), @AgainClick).Width := ScaleX(150);

  RefreshNeeds();
end;

{ Coming back from the browser after installing something: show the new situation. }
procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = NeedsPage.ID then
    RefreshNeeds();
end;

{ The settings are the person's, not the program's: they only go away when the person says so. }
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Dir: String;
begin
  if CurUninstallStep <> usPostUninstall then
    exit;
  Dir := ExpandConstant('{userappdata}\{#DataDirName}');
  if not DirExists(Dir) then
    exit;
  if SuppressibleMsgBox(CustomMessage('RemoveSettings'), mbConfirmation, MB_YESNO or MB_DEFBUTTON2, IDNO) = IDYES then
    DelTree(Dir, True, True, True);
end;
