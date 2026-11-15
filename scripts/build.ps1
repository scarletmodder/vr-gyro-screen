# Builds the Windows installer: freezes the program with PyInstaller, checks that the frozen
# copy loads its own libraries, packs it with Inno Setup and writes SHA256SUMS.txt next to it.
# The version comes from pyproject.toml; the installer goes to dist\.
[CmdletBinding()]
param([string]$Iscc, [string]$Python = 'python')

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2
$root = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $root

$project = [IO.File]::ReadAllText((Join-Path $root 'pyproject.toml'))
if ($project -notmatch '(?m)^version\s*=\s*"(\d+\.\d+\.\d+)"') { throw 'No version = "X.Y.Z" in pyproject.toml' }
$version = $Matches[1]

if (-not $Iscc) {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
        (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe')
    )
    $Iscc = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $Iscc) { throw 'ISCC.exe (Inno Setup 6.7 or newer) not found. Pass -Iscc.' }

# 1. The program and everything it needs, in one folder (work\ is not versioned).
& $Python -m PyInstaller --noconfirm --log-level WARN --distpath work\dist --workpath work\build packaging\vr-gyro-screen.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with code $LASTEXITCODE" }

# 2. The frozen copy must load its own libraries. What is installed on this computer (driver,
#    headset program) is printed too, but only a library that fails to load stops the build.
$frozen = Join-Path $root 'work\dist\vr-gyro-screen'
& (Join-Path $frozen 'vr-gyro-screen-cli.exe') check
if ($LASTEXITCODE -ne 0) { throw 'The frozen program failed its own check' }

# 3. The installer. Only this build stays in dist\, so nobody picks an older one by mistake.
$dist = Join-Path $root 'dist'
New-Item -ItemType Directory -Force -Path $dist | Out-Null
Get-ChildItem -LiteralPath $dist -Filter 'VRGyroScreen-Setup-*' | Remove-Item -Force
& $Iscc /Qp "/DAppVersion=$version" (Join-Path $root 'installer\vr-gyro-screen.iss')
if ($LASTEXITCODE -ne 0) { throw "ISCC failed with code $LASTEXITCODE" }

$setup = Join-Path $dist "VRGyroScreen-Setup-v$version.exe"
$line = "$((Get-FileHash -LiteralPath $setup -Algorithm SHA256).Hash.ToLowerInvariant())  $(Split-Path $setup -Leaf)"
[IO.File]::WriteAllText((Join-Path $dist 'SHA256SUMS.txt'), $line + "`n", (New-Object Text.UTF8Encoding($false)))
Write-Host "Built $setup"
Write-Host $line
