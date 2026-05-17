# Membra Folder Link - Quick Start

## What This Is

A macOS Finder extension that adds "Create Public Link" to right-click menus, integrating with the MIP-008 backend.

## Files Created

```
MembraFolderLink/
├── MembraFolderLinkApp/
│   ├── AppDelegate.swift          # Main app with status bar menu
│   └── Info.plist                  # App configuration
├── MembraFolderLinkExtension/
│   ├── FinderSync.swift            # Finder Sync Extension (right-click menu)
│   └── Info.plist                  # Extension configuration
├── build.sh                        # Build helper script
└── README.md                       # Full documentation
```

## To Build (Requires Xcode)

1. Open Xcode
2. File → New → Project → macOS → App
3. Product Name: `MembraFolderLink`
4. File → New → Target → macOS → Extension → Finder Sync Extension
5. Product Name: `MembraFolderLinkExtension`
6. Replace generated files with the provided Swift and Info.plist files
7. Build (Cmd+R)
8. Enable in System Settings → Extensions → Finder

## To Use

1. Start MEMBRA backend:
   ```bash
   docker-compose up -d
   alembic upgrade head
   uvicorn app:app --reload
   ```

2. Enable the Finder extension in System Settings

3. Right-click any folder → "Create Public Link"

## Integration

The extension calls `POST http://localhost:8000/api/share/folder` with:
- folder_path
- expiration (never/24h/7d/30d)
- download_allowed, index_enabled, proof_manifest_enabled, qr_enabled

Returns share URL, manifest URL, and file counts.
