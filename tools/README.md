# RAM Optimizer - macOS Menu Bar App

Aggressively frees reclaimable memory via safe OS commands. Runs in the macOS menu bar for quick access.

## Features

- **Memory Info**: Display current memory statistics
- **Aggressive Decompress**: Clear disk caches, application caches, and compress inactive memory
- **Purge Disk Cache**: Quick disk cache purge only
- **Auto-Optimize**: Toggle automatic optimization every 5 minutes

## Installation

```bash
pip install -r ../requirements.txt
```

## Usage

```bash
python tools/ram_optimizer.py
```

The app will appear in your menu bar as "🧠 RAM".

## Requirements

- macOS 10.9+
- Python 3.11+ (recommended for stability)
- `sudo` access for `purge` and `memory_pressure` commands

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
