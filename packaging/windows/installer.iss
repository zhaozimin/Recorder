; ============================================================================
;  VoiceLog · Windows 安装包脚本 (Inno Setup) —— 已实装,经 GitHub Actions CI 构建发布(测试版)
;  把 PyInstaller 产出的 dist\VoiceLog\ 打成单文件安装程序 VoiceLog-Windows.exe(固定名,含开机自启选项)。
;  由 .github/workflows/build-windows.yml(标准)/build-windows-offline.yml(含模型离线版)调用。
; ============================================================================
; 显示名「言壤」(开始菜单/控制面板/向导可见);安装目录/输出文件名/exe 名保持 ASCII(VoiceLog)。
#define MyAppName "言壤"
#define MyAppNameAscii "VoiceLog"
#define MyAppVersion "0.9.12"
#define MyAppPublisher "Zimin Zhao"
#define MyAppExeName "VoiceLog.exe"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppNameAscii}
DefaultGroupName={#MyAppName}
OutputDir=Output
; 固定名(不带版本号)→ 配合 GitHub Release「latest/download/VoiceLog-Windows.exe」稳定下载链接，官网写死永远拉最新
OutputBaseFilename=VoiceLog-Windows
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
PrivilegesRequired=lowest
SetupIconFile=VoiceLog.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
; 仅用内置英文向导(简体中文 .isl 非 Inno Setup 自带,CI 上不可得)。App 本身仍是中文/多语言。
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; PyInstaller onedir 产物整目录打入
Source: "..\..\dist\VoiceLog\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startup

[Tasks]
Name: "startup"; Description: "开机自动启动言壤"; GroupDescription: "附加任务:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "立即启动言壤"; Flags: nowait postinstall skipifsilent
