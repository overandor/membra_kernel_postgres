---
title: Membra Public Folder Link Gateway
emoji: 🔗
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
license: mit
---

# Membra Public Folder Link Gateway (MIP-008)

A FastAPI backend that turns local folders into public, read-only, shareable web directories with file hashes, proof manifests, and optional Solana anchoring.

## Features

- 📁 **Folder scanning** with SHA-256 hashing
- 🔒 **Safety filters** — blocks .env, *.pem, *.key, node_modules/, etc.
- 📊 **Merkle root computation** for folder integrity
- 🔗 **Public share URLs** with expiration options
- 📄 **Proof manifests** with MIR/MCR IDs
- 🎯 **Optional Solana devnet anchoring**

## API Endpoints

- `POST /api/share/folder` — Create public folder share
- `GET /share/{share_id}` — Public folder index page
- `GET /share/{share_id}/manifest.json` — Proof manifest
- `GET /share/{share_id}/files/{path:path}` — Download file
- `POST /api/share/{share_id}/revoke` — Revoke share
- `POST /api/share/{share_id}/anchor-solana-devnet` — Anchor to Solana

## Deployment

This Space uses Docker. The environment variables are configured in the Space settings.

### Required Environment Variables

- `DATABASE_URL` — PostgreSQL connection string
- `AUTO_CREATE_TABLES` — Set to `true`
- `MEMBRA_DATA_ENCRYPTION_KEY` — Encryption key
- `ACCESS_SIGNING_SECRET` — Token signing secret

### Database Setup

1. Add a PostgreSQL database in Space Settings
2. Copy the connection string
3. Set `DATABASE_URL` environment variable
4. Set `AUTO_CREATE_TABLES=true`

The app will automatically create tables on startup.

## Usage

### Create a folder share

```bash
curl -X POST https://your-space.hf.space/api/share/folder \
  -H "Content-Type: application/json" \
  -d '{
    "folder_path": "/path/to/folder",
    "owner_wallet": "local_user",
    "expiration": "never",
    "base_url": "https://your-space.hf.space"
  }'
```

### Access the share

Use the `public_link` from the response to view the folder in a browser.

## macOS Integration

A macOS Finder Sync Extension is available in the `MembraFolderLink/` directory. Build with Xcode and configure it to use your Hugging Face Space URL.

## License

MIT
