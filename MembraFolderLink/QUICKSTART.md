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

### Option A: Local Backend

1. Start MEMBRA backend locally:
   ```bash
   docker-compose up -d
   alembic upgrade head
   uvicorn app:app --reload
   ```

2. Open the Membra Folder Link app
3. Backend URL should be `http://localhost:8000` (default)
4. Enable the Finder extension in System Settings
5. Right-click any folder → "Create Public Link"

### Option B: Hugging Face Spaces (Public)

1. Deploy backend to Hugging Face Spaces (see `deploy_to_hf.sh` in repo root)
2. Open the Membra Folder Link app
3. Enter your Space URL (e.g., `https://your-username-membra-folder-link.hf.space`)
4. Click "Save"
5. Enable the Finder extension in System Settings
6. Right-click any folder → "Create Public Link"

### Option C: Render (Public)

1. Deploy backend to Render (see `DEPLOYMENT.md`)
2. Configure the app with your Render URL
3. Enable extension and use as above

## Integration

The extension calls `POST {backend_url}/api/share/folder` with:
- folder_path
- expiration (never/24h/7d/30d)
- download_allowed, index_enabled, proof_manifest_enabled, qr_enabled

Returns share URL, manifest URL, and file counts.

**Note:** The backend URL is configurable. Change it in the Membra Folder Link app settings.
