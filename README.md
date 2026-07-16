# Gangcord

Gangcord is a Windows media controller for Valorant and League of Legends. It watches only a screen region selected by the user and changes normal Windows media playback or the volume of a selected audio session.

Gangcord does not inject code, inspect game memory, modify game files, communicate with anti-cheat components, or automate gameplay.

## Features

- Separate Valorant and League of Legends profiles
- Valorant target-color detection with visual color swatch and manual RGB/hex input
- League of Legends number and countdown-region detection
- Selectable Windows audio session
- Direct Play/Pause control or volume-only control
- Separate dead and alive volume values
- Automatic launch with Valorant, League of Legends, both games, or neither
- Light, dark, and system themes
- Scrollable interface for small displays and high Windows scaling
- Single-instance protection for the application and watcher
- Installer-based updates from GitHub releases

## Getting Started

1. Open the Valorant or LoL tab.
2. Select the smallest practical screen region containing the relevant state indicator.
3. For Valorant, select the target color or enter it manually, such as `#ff4655`, `255,70,85`, `rgb(255,70,85)`, or `rgba(255,70,85,1)`.
4. Open the media player you want to control and select **Refresh**.
5. Choose the media session.
6. Select **Control Play/Pause** or **Adjust volume only**.
7. Test the selected behavior and select **Start**.

## Automatic Game Detection

`GangcordWatcher.exe` checks running process names at a low frequency and opens Gangcord when a selected game starts. It never reads process memory.

Detected Valorant processes:

- `VALORANT-Win64-Shipping.exe`
- `RiotClientServices.exe`

Detected League of Legends processes:

- `LeagueClient.exe`
- `LeagueClientUx.exe`
- `League of Legends.exe`

## Storage Locations

Gangcord keeps the installation directory clean.

- Settings: `%LOCALAPPDATA%\Gangcord\config.json`
- Logs: `%LOCALAPPDATA%\Gangcord\Logs\`
- Cache: `%LOCALAPPDATA%\Gangcord\Cache\`
- Temporary update files: `%TEMP%\Gangcord\`

Settings are written atomically as UTF-8 JSON. Existing settings from `%LOCALAPPDATA%\Game Media Control\config.json` are migrated when possible.

## Installation

The Inno Setup installer offers both installation modes:

- Current user: `%LOCALAPPDATA%\Programs\Gangcord\`, without administrator rights
- All users: `C:\Program Files\Gangcord\` for the 64-bit build, with administrator rights

The desktop shortcut is optional. A Start menu shortcut is always created. Personal settings remain in each user's `%LOCALAPPDATA%` folder for both installation modes.

The setup includes the application, watcher, icon, README, license, and Python runtime. Python and development tools are not required on the destination computer.

## Build

Requirements on the build computer:

- Windows 10 or Windows 11
- 64-bit Python 3.13 or a compatible supported Python version
- PyInstaller
- Inno Setup 6

Build and test the complete release:

```powershell
.\build-installer.ps1
```

The final installer is written to:

```text
dist\Gangcord-Setup-2.0.1.exe
```

## Project Structure

```text
assets/                  Windows application icon
installer/               Inno Setup script and license
src/                     Gangcord application and watcher
tests/                   Unit and UI smoke tests
Gangcord.spec             PyInstaller definition for the application
GangcordWatcher.spec      PyInstaller definition for the watcher
build-installer.ps1       Reproducible release build
README.md                 Project documentation
```

## Troubleshooting

- Use borderless or windowed fullscreen if exclusive fullscreen produces black captures.
- Select a small and stable region without unrelated UI elements.
- Increase **Stable reads** when brief transitions trigger unwanted actions.
- Refresh media sessions after opening Spotify, a browser, or another player.
- Use the **System** theme to follow the Windows app theme automatically.

## Privacy

All detection happens locally. Gangcord does not upload screenshots or media-session information.

## License

Gangcord is free for private, non-commercial use. Commercial use requires prior written permission. See [LICENSE.txt](installer/LICENSE.txt) for the complete terms.
