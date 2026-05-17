# Membra Folder Link - macOS Finder Extension

A macOS Finder Sync Extension that adds "Create Public Link" to Finder's right-click menu, integrating with the MIP-008 MEMBRA Public Folder Link Gateway backend.

## Features

- **Right-click menu integration**: Adds "Create Public Link" to Finder's context menu for folders
- **Configuration modal**: Choose expiration (Never, 24h, 7d, 30d) before creating share
- **Instant feedback**: Shows success alert with share URL, copy to clipboard, or open in browser
- **Status bar app**: Menu bar indicator showing extension status
- **Backend integration**: Calls FastAPI backend at `http://localhost:8000/api/share/folder`

## Requirements

- macOS 13.0 (Ventura) or later
- Xcode 15.0 or later
- MEMBRA backend running (see parent directory)

## Building with Xcode

1. Open Xcode
2. Create a new macOS App project:
   - File → New → Project
   - Choose "macOS" → "App"
   - Product Name: `MembraFolderLink`
   - Interface: Storyboard
   - Language: Swift
3. Add Finder Sync Extension target:
   - File → New → Target
   - Choose "macOS" → "Extension" → "Finder Sync Extension"
   - Product Name: `MembraFolderLinkExtension`
4. Replace the generated files with the files in this directory:
   - Copy `MembraFolderLinkApp/AppDelegate.swift` to your app target
   - Copy `MembraFolderLinkExtension/FinderSync.swift` to your extension target
   - Copy the `Info.plist` files to their respective locations
5. Configure the extension in your app target:
   - Select your app target → Build Phases
   - Add "Copy Files" phase
   - Destination: "PlugIns"
   - Add the extension product
6. Build and run:
   - Select "My Mac" as destination
   - Press Cmd+R to build and run
7. Enable the extension:
   - System Settings → Privacy & Security → Extensions → Finder
   - Enable "Membra Folder Link"
   - Grant Full Disk Access if prompted

## Manual Build Script (Alternative)

For a simplified build process without full Xcode project setup:

```bash
# This script requires Xcode command-line tools
xcodebuild -project MembraFolderLink.xcodeproj -scheme MembraFolderLink -configuration Release build
```

Note: A full Xcode project file would need to be generated for this to work. The provided files are the source code that would go into such a project.

## Usage

1. Ensure MEMBRA backend is running:
   ```bash
   cd /Users/alep/Desktop/membra_kernel_postgres
   docker-compose up -d
   alembic upgrade head
   uvicorn app:app --reload
   ```

2. Enable the Finder extension:
   - System Settings → Privacy & Security → Extensions → Finder
   - Enable "Membra Folder Link"

3. Use the extension:
   - Right-click any folder in Finder
   - Select "Create Public Link"
   - Choose expiration option
   - Click "Create"
   - Copy or open the generated share URL

## Architecture

```
MembraFolderLink.app
├── Contents/
│   ├── MacOS/
│   │   └── MembraFolderLink (main app executable)
│   ├── PlugIns/
│   │   └── MembraFolderLinkExtension.appex/
│   │       └── Contents/
│   │           ├── MacOS/
│   │           │   └── MembraFolderLinkExtension (extension executable)
│   │           └── Info.plist
│   └── Info.plist
```

## API Integration

The extension calls the MIP-008 backend API:

**POST /api/share/folder**

```json
{
  "folder_path": "/path/to/folder",
  "owner_wallet": "local_user",
  "expiration": "never",
  "download_allowed": true,
  "index_enabled": true,
  "proof_manifest_enabled": true,
  "qr_enabled": true,
  "solana_anchor": false,
  "base_url": "http://localhost:8000"
}
```

**Response:**

```json
{
  "share_id": "folder_abc123",
  "folder": "/path/to/folder",
  "visibility": "Public",
  "files_visible": 42,
  "blocked_files": 3,
  "blocked_message": "3 files were blocked for safety...",
  "public_link": "http://localhost:8000/share/folder_abc123",
  "proof_manifest": "http://localhost:8000/share/folder_abc123/manifest.json",
  "qr": "http://localhost:8000/share/folder_abc123",
  "manifest": { ... }
}
```

## Troubleshooting

**Extension not appearing in Finder:**
- Check System Settings → Extensions → Finder
- Ensure the extension is enabled
- Restart Finder: `killall Finder`

**Backend connection errors:**
- Verify MEMBRA backend is running on port 8000
- Check firewall settings
- Ensure backend URL in code matches your setup

**Permission errors:**
- Grant Full Disk Access to the app in System Settings
- Grant Finder extension permissions

## Security Notes

- The extension requires Full Disk Access to read folder paths
- All file scanning and blocking happens on the backend
- The extension only sends folder paths to the backend
- No file contents are sent by the extension
