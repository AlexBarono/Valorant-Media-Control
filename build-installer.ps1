[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BuildDirectory = Join-Path $Root "build"
$DistDirectory = Join-Path $Root "dist"
$PayloadDirectory = Join-Path $DistDirectory "app"

function Invoke-NativeCommand {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$StepName
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$StepName failed with exit code $LASTEXITCODE."
    }
}

function Remove-ControlledDirectory {
    param([Parameter(Mandatory = $true)][string]$Path)

    $fullRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd('\') + '\'
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    if (-not $fullPath.StartsWith($fullRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove a path outside the project: $fullPath"
    }
    if (Test-Path -LiteralPath $fullPath) {
        Remove-Item -LiteralPath $fullPath -Recurse -Force
    }
}

Set-Location $Root
$env:PYTHONDONTWRITEBYTECODE = "1"

$RequiredFiles = @(
    "src\gangcord.py",
    "src\game_watcher.py",
    "assets\gangcord.ico",
    "assets\version_info.txt",
    "assets\watcher_version_info.txt",
    "installer\Gangcord.iss",
    "installer\LICENSE.txt",
    "Gangcord.spec",
    "GangcordWatcher.spec",
    "README.md"
)

foreach ($relativePath in $RequiredFiles) {
    $absolutePath = Join-Path $Root $relativePath
    if (-not (Test-Path -LiteralPath $absolutePath -PathType Leaf)) {
        throw "Required release file is missing: $absolutePath"
    }
}

$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCommand) {
    throw "Python was not found. Install 64-bit Python 3.13, then run this script again."
}

$SourceText = Get-Content -Raw -Encoding utf8 -LiteralPath (Join-Path $Root "src\gangcord.py")
if ($SourceText -notmatch 'APP_VERSION\s*=\s*"(\d+\.\d+\.\d+)"') {
    throw "APP_VERSION could not be read from src\gangcord.py."
}
$Version = $Matches[1]

$WatcherText = Get-Content -Raw -Encoding utf8 -LiteralPath (Join-Path $Root "src\game_watcher.py")
if ($WatcherText -notmatch ('APP_VERSION\s*=\s*"' + [regex]::Escape($Version) + '"')) {
    throw "The application and watcher versions do not match."
}

$InnoCandidates = @(
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe")
) | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) }
$InnoCompiler = $InnoCandidates | Select-Object -First 1
if (-not $InnoCompiler) {
    throw "Inno Setup 6 was not found. Install it with: winget install --id JRSoftware.InnoSetup --exact --scope user"
}

Write-Host "[1/6] Cleaning controlled build output..."
Remove-ControlledDirectory -Path $BuildDirectory
Remove-ControlledDirectory -Path $DistDirectory
New-Item -ItemType Directory -Path $BuildDirectory, $PayloadDirectory -Force | Out-Null

Write-Host "[2/6] Running automated tests..."
Invoke-NativeCommand -FilePath $PythonCommand.Source -Arguments @("-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v") -StepName "Automated tests"

Write-Host "[3/6] Building Gangcord.exe..."
Invoke-NativeCommand -FilePath $PythonCommand.Source -Arguments @(
    "-m", "PyInstaller", "--noconfirm", "--clean",
    "--distpath", $PayloadDirectory,
    "--workpath", (Join-Path $BuildDirectory "Gangcord"),
    (Join-Path $Root "Gangcord.spec")
) -StepName "Gangcord application build"

Write-Host "[4/6] Building GangcordWatcher.exe..."
Invoke-NativeCommand -FilePath $PythonCommand.Source -Arguments @(
    "-m", "PyInstaller", "--noconfirm", "--clean",
    "--distpath", $PayloadDirectory,
    "--workpath", (Join-Path $BuildDirectory "GangcordWatcher"),
    (Join-Path $Root "GangcordWatcher.spec")
) -StepName "Gangcord watcher build"

$ArchitectureBits = (& $PythonCommand.Source -c "import struct; print(struct.calcsize('P') * 8)").Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Could not determine the Python architecture."
}
$AppArchitecture = if ($ArchitectureBits -eq "64") { "x64" } else { "x86" }

Write-Host "[5/6] Compiling the Inno Setup installer for $AppArchitecture..."
Invoke-NativeCommand -FilePath $InnoCompiler -Arguments @(
    "/DAppVersion=$Version",
    "/DAppArchitecture=$AppArchitecture",
    (Join-Path $Root "installer\Gangcord.iss")
) -StepName "Inno Setup build"

$SetupPath = Join-Path $DistDirectory "Gangcord-Setup-$Version.exe"
if (-not (Test-Path -LiteralPath $SetupPath -PathType Leaf)) {
    throw "The expected setup file was not created: $SetupPath"
}

$Header = [System.IO.File]::ReadAllBytes($SetupPath)[0..1]
if ($Header[0] -ne 0x4D -or $Header[1] -ne 0x5A) {
    throw "The generated setup file is not a valid Windows executable."
}

Write-Host "[6/6] Removing temporary payload and build files..."
Remove-ControlledDirectory -Path $PayloadDirectory
Remove-ControlledDirectory -Path $BuildDirectory

$SetupInfo = Get-Item -LiteralPath $SetupPath
Write-Host ""
Write-Host "Gangcord $Version release completed."
Write-Host "Setup: $($SetupInfo.FullName)"
Write-Host "Size:  $([math]::Round($SetupInfo.Length / 1MB, 2)) MB"
