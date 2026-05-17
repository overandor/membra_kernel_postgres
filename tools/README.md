# RAM Optimizer - macOS Menu Bar App

Aggressively frees reclaimable memory via safe OS commands. Runs in the macOS menu bar for quick access.

## Features

- **Memory Info**: Display current memory statistics
- **Aggressive Decompress**: Clear disk caches, application caches, and compress inactive memory
- **Purge Disk Cache**: Quick disk cache purge only
- **Auto-Optimize**: Toggle automatic optimization every 5 minutes

## Installation

### Option 1: Download DMG (Recommended)

Download `RAM Optimizer.dmg` from the [Releases](../../releases) page, open it, and drag the app to your Applications folder.

### Option 2: Run from Source

```bash
pip install -r ../requirements.txt
python tools/ram_optimizer.py
```

## Usage

The app will appear in your menu bar as "🧠 RAM". Click to access:
- Memory Info
- Aggressive Decompress
- Purge Disk Cache
- Auto-Optimize toggle
- Quit

## Requirements

- macOS 10.9+
- `sudo` access for `purge` and `memory_pressure` commands (when using aggressive decompress)

## Safety Notes

This tool uses only safe macOS commands:
- `purge`: Clears disk cache (built-in macOS tool)
- `memory_pressure`: Compresses inactive pages (built-in macOS tool)
- Cache clearing: Removes temporary cache files

No kernel tweaks or unsafe modifications are made.

## Permissions

The aggressive decompress feature requires sudo privileges. You may be prompted for your password when first running these commands.

## Auto-Optimization

When enabled, auto-optimization runs every 5 minutes in the background. This can be toggled on/off from the menu.

## Building from Source

To build the .app bundle and DMG:

```bash
cd tools
pip install pyinstaller
pyinstaller --onefile --name="RAM Optimizer" ram_optimizer.py
mkdir -p "dist/RAM Optimizer.app/Contents/MacOS"
cp "dist/RAM Optimizer" "dist/RAM Optimizer.app/Contents/MacOS/"
# Create Info.plist (see existing file)
hdiutil create -volname "RAM Optimizer" -srcfolder <temp_folder_with_app> -ov -format UDZO "dist/RAM Optimizer.dmg"
```
