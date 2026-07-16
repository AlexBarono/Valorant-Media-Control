$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "Building Game Media Control app..."
python -m PyInstaller --noconfirm "Game Media Control.spec"

Write-Host "Building watcher..."
python -m PyInstaller `
  --noconfirm `
  --onefile `
  --windowed `
  --name "Game Media Watcher" `
  --icon "game_media_control.ico" `
  "game_media_watcher.py"

Write-Host "Building uninstaller..."
python -m PyInstaller `
  --noconfirm `
  --onefile `
  --windowed `
  --name "Game Media Control Uninstaller" `
  --icon "game_media_control.ico" `
  "uninstall_game_media_control.py"

Write-Host "Building setup..."
if (-not (Test-Path "setup")) {
  New-Item -ItemType Directory -Path "setup" | Out-Null
}

python -m PyInstaller `
  --noconfirm `
  --onefile `
  --windowed `
  --name "Game Media Control Setup" `
  --distpath "setup" `
  --icon "game_media_control.ico" `
  --add-data "dist\Game Media Control.exe;payload" `
  --add-data "dist\Game Media Watcher.exe;payload" `
  --add-data "dist\Game Media Control Uninstaller.exe;payload" `
  --add-data "README.md;payload" `
  --add-data "LICENSE.txt;payload" `
  "installer_setup.py"

Write-Host ""
Write-Host "Done:"
Write-Host "  App:   $Root\dist\Game Media Control.exe"
Write-Host "  Setup: $Root\setup\Game Media Control Setup.exe"
