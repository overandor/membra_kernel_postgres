from __future__ import annotations

import fnmatch
import hashlib
import html
import mimetypes
import os
import posixpath
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .db import get_db
from .models import FolderShare
from .utils import new_id, utcnow


MFL_VERSION = "mip-008"
BLOCKED_NAMES = {
    ".env",
    "id_rsa",
    "id_ed25519",
    "wallet.json",
    "secrets.json",
    "credentials.json",
    ".DS_Store",
}
BLOCKED_DIRS = {
    "node_modules",
    ".venv",
    ".git",
    "__pycache__",
    "private_keys",
}
BLOCKED_PATTERNS = {
    ".env.*",
    "*.pem",
    "*.key",
    "*.seed",
    "*.mnemonic",
    "~/.config/solana/id.json",
}
EXPIRATION_OPTIONS = {"never", "24h", "7d", "30d"}


class FolderShareCreate(BaseModel):
    folder_path: str = Field(..., min_length=1)
    owner_wallet: str = "local_user"
    expiration: str = "never"
    download_allowed: bool = True
    index_enabled: bool = True
    proof_manifest_enabled: bool = True
    qr_enabled: bool = True
    solana_anchor: bool = False
    base_url: str = "https://membra.network"


class FolderShareOut(BaseModel):
    share_id: str
    folder: str
    visibility: str
    files_visible: int
    blocked_files: int
    blocked_message: str
    public_link: str
    proof_manifest: str
    qr: Optional[str]
    manifest: Dict[str, Any]


class FolderShareRevoke(BaseModel):
    reason: str = "owner_revoked"


mfl_router = APIRouter()


def _is_blocked_path(relative_path: str, is_dir: bool) -> Optional[str]:
    normalized = relative_path.replace(os.sep, "/").strip("/")
    parts = [part for part in normalized.split("/") if part]
    name = parts[-1] if parts else normalized
    if is_dir and name in BLOCKED_DIRS:
        return f"blocked directory: {name}"
    if any(part in BLOCKED_DIRS for part in parts):
        return "inside blocked directory"
    if name in BLOCKED_NAMES or normalized in BLOCKED_NAMES:
        return f"blocked file: {name}"
    for pattern in BLOCKED_PATTERNS:
        if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(normalized, pattern):
            return f"blocked pattern: {pattern}"
    return None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _merkle_root(hashes: Iterable[str]) -> str:
    layer = sorted(hashes)
    if not layer:
        return hashlib.sha256(b"").hexdigest()
    while len(layer) > 1:
        if len(layer) % 2 == 1:
            layer.append(layer[-1])
        layer = [hashlib.sha256((layer[i] + layer[i + 1]).encode("utf-8")).hexdigest() for i in range(0, len(layer), 2)]
    return layer[0]


def _safe_expiry(expiration: str):
    if expiration not in EXPIRATION_OPTIONS:
        raise HTTPException(400, f"Unsupported expiration. Use one of: {', '.join(sorted(EXPIRATION_OPTIONS))}")
    if expiration == "24h":
        return utcnow() + timedelta(hours=24)
    if expiration == "7d":
        return utcnow() + timedelta(days=7)
    if expiration == "30d":
        return utcnow() + timedelta(days=30)
    return None


def _scan_folder(root: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    files: List[Dict[str, Any]] = []
    blocked: List[Dict[str, str]] = []
    for current_root, dirnames, filenames in os.walk(root):
        current = Path(current_root)
        for dirname in list(dirnames):
            relative = (current / dirname).relative_to(root).as_posix()
            reason = _is_blocked_path(relative, True)
            if reason:
                blocked.append({"path": relative, "reason": reason})
                dirnames.remove(dirname)
        for filename in filenames:
            path = current / filename
            relative = path.relative_to(root).as_posix()
            reason = _is_blocked_path(relative, False)
            if reason:
                blocked.append({"path": relative, "reason": reason})
                continue
            if not path.is_file():
                continue
            file_hash = _sha256_file(path)
            files.append(
                {
                    "path": relative,
                    "size_bytes": path.stat().st_size,
                    "mime_type": mimetypes.guess_type(relative)[0] or "application/octet-stream",
                    "sha256": file_hash,
                }
            )
    files.sort(key=lambda item: item["path"])
    blocked.sort(key=lambda item: item["path"])
    return files, blocked


def _build_manifest(share_id: str, payload: FolderShareCreate, root: Path, files: List[Dict[str, Any]], blocked: List[Dict[str, str]], expires_at) -> Dict[str, Any]:
    now = utcnow()
    root_hash = _merkle_root(file["sha256"] for file in files)
    mir_id = f"mir_{hashlib.sha256((share_id + root_hash + 'publish').encode('utf-8')).hexdigest()[:24]}"
    mcr_id = f"mcr_{hashlib.sha256((share_id + root_hash + 'appraisal').encode('utf-8')).hexdigest()[:24]}"
    solana_tx = None
    if payload.solana_anchor:
        solana_tx = f"devnet_stub_{hashlib.sha256((share_id + root_hash).encode('utf-8')).hexdigest()[:32]}"
    return {
        "mfl_version": MFL_VERSION,
        "share_id": share_id,
        "owner_wallet": payload.owner_wallet,
        "folder_name": root.name,
        "visibility": "public",
        "created_at": int(now.timestamp()),
        "expires_at": int(expires_at.timestamp()) if expires_at else None,
        "download_allowed": payload.download_allowed,
        "file_count": len(files),
        "blocked_file_count": len(blocked),
        "folder_merkle_root": root_hash,
        "files": files,
        "proof": {
            "mir_id": mir_id,
            "mcr_id": mcr_id,
            "solana_devnet_tx": solana_tx,
        },
    }


def _active_share(session: Session, share_id: str) -> FolderShare:
    share = session.get(FolderShare, share_id)
    if not share or share.visibility != "public":
        raise HTTPException(404, "Shared folder not found")
    if share.revoked:
        raise HTTPException(410, "Shared folder link has been revoked")
    if share.expires_at and share.expires_at <= utcnow():
        raise HTTPException(410, "Shared folder link has expired")
    return share


def _share_urls(base_url: str, share_id: str) -> Tuple[str, str]:
    clean = base_url.rstrip("/")
    return f"{clean}/share/{share_id}", f"{clean}/share/{share_id}/manifest.json"


def _render_share_page(share: FolderShare) -> str:
    manifest = share.manifest_json
    file_rows = "".join(
        f"<tr><td>{html.escape(file['path'])}</td><td>{file['size_bytes']}</td><td><code>{file['sha256']}</code></td><td>"
        f"<a href='/share/{share.share_id}/files/{quote(file['path'])}'>download</a></td></tr>"
        for file in manifest.get("files", [])
    )
    blocked_count = manifest.get("blocked_file_count", 0)
    return f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MEMBRA Folder Link - {html.escape(manifest.get('folder_name', share.folder_name))}</title>
  <style>
    body {{ font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; background: #0b1020; color: #eef2ff; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 40px 20px; }}
    .card {{ background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.14); border-radius: 18px; padding: 24px; box-shadow: 0 24px 80px rgba(0,0,0,.28); }}
    .muted {{ color: #aab4d4; }}
    code {{ color: #93c5fd; word-break: break-all; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 18px; }}
    th, td {{ padding: 12px; border-bottom: 1px solid rgba(255,255,255,.12); text-align: left; vertical-align: top; }}
    a {{ color: #67e8f9; }}
    .warning {{ color: #fde68a; }}
  </style>
</head>
<body>
  <main>
    <section class="card">
      <p class="muted">MIP-008 Public Folder Link Gateway</p>
      <h1>{html.escape(manifest.get('folder_name', share.folder_name))}</h1>
      <p>This is a public, read-only MEMBRA Folder Link. Raw private files are excluded by default.</p>
      <p class="warning">{blocked_count} files were blocked for safety and will not be public.</p>
      <p><strong>Proof root:</strong> <code>{html.escape(manifest.get('folder_merkle_root', ''))}</code></p>
      <p><strong>MIR:</strong> <code>{html.escape(manifest.get('proof', {}).get('mir_id', ''))}</code> · <strong>MCR:</strong> <code>{html.escape(manifest.get('proof', {}).get('mcr_id', ''))}</code></p>
      <p><a href="/share/{share.share_id}/manifest.json">Proof Manifest</a></p>
      <table>
        <thead><tr><th>Path</th><th>Size</th><th>SHA-256</th><th>Action</th></tr></thead>
        <tbody>{file_rows}</tbody>
      </table>
    </section>
  </main>
</body>
</html>
"""


@mfl_router.post("/api/share/folder", response_model=FolderShareOut)
def create_folder_share(payload: FolderShareCreate, session: Session = Depends(get_db)) -> FolderShareOut:
    root = Path(payload.folder_path).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise HTTPException(400, "folder_path must point to an existing folder")
    share_id = new_id("folder")
    files, blocked = _scan_folder(root)
    expires_at = _safe_expiry(payload.expiration)
    manifest = _build_manifest(share_id, payload, root, files, blocked, expires_at)
    share = FolderShare(
        share_id=share_id,
        owner_wallet=payload.owner_wallet,
        folder_name=root.name,
        folder_path=str(root),
        visibility="public",
        download_allowed=payload.download_allowed,
        index_enabled=payload.index_enabled,
        proof_manifest_enabled=payload.proof_manifest_enabled,
        qr_enabled=payload.qr_enabled,
        expires_at=expires_at,
        manifest_json=manifest,
        blocked_files_json=blocked,
    )
    session.add(share)
    public_link, proof_manifest = _share_urls(payload.base_url, share_id)
    return FolderShareOut(
        share_id=share_id,
        folder=str(root),
        visibility="Public",
        files_visible=len(files),
        blocked_files=len(blocked),
        blocked_message=f"{len(blocked)} files were blocked for safety and will not be public.",
        public_link=public_link,
        proof_manifest=proof_manifest,
        qr=public_link if payload.qr_enabled else None,
        manifest=manifest,
    )


@mfl_router.get("/share/{share_id}", response_class=HTMLResponse)
def public_folder_page(share_id: str, session: Session = Depends(get_db)) -> HTMLResponse:
    share = _active_share(session, share_id)
    if not share.index_enabled:
        raise HTTPException(403, "Folder index page is disabled")
    return HTMLResponse(_render_share_page(share))


@mfl_router.get("/share/{share_id}/manifest.json")
def public_folder_manifest(share_id: str, session: Session = Depends(get_db)) -> Dict[str, Any]:
    share = _active_share(session, share_id)
    if not share.proof_manifest_enabled:
        raise HTTPException(403, "Proof manifest is disabled")
    return share.manifest_json


@mfl_router.get("/share/{share_id}/files/{path:path}")
def public_folder_file(share_id: str, path: str, session: Session = Depends(get_db)) -> FileResponse:
    share = _active_share(session, share_id)
    if not share.download_allowed:
        raise HTTPException(403, "Downloads are disabled for this share")
    normalized = posixpath.normpath(path).lstrip("/")
    if normalized.startswith("..") or _is_blocked_path(normalized, False):
        raise HTTPException(403, "File is not public")
    allowed = {file["path"] for file in share.manifest_json.get("files", [])}
    if normalized not in allowed:
        raise HTTPException(404, "File not found in public manifest")
    root = Path(share.folder_path).resolve()
    target = (root / normalized).resolve()
    if root not in target.parents and target != root:
        raise HTTPException(403, "File is outside shared folder")
    return FileResponse(target)


@mfl_router.post("/api/share/{share_id}/revoke")
def revoke_folder_share(share_id: str, payload: FolderShareRevoke, session: Session = Depends(get_db)) -> Dict[str, Any]:
    share = session.get(FolderShare, share_id)
    if not share:
        raise HTTPException(404, "Shared folder not found")
    share.revoked = True
    share.revoked_reason = payload.reason
    return {"share_id": share_id, "revoked": True, "reason": payload.reason}


@mfl_router.post("/api/share/{share_id}/anchor-solana-devnet")
def anchor_folder_share_devnet(share_id: str, session: Session = Depends(get_db)) -> Dict[str, Any]:
    share = _active_share(session, share_id)
    manifest = dict(share.manifest_json)
    proof = dict(manifest.get("proof", {}))
    if not proof.get("solana_devnet_tx"):
        proof["solana_devnet_tx"] = f"devnet_stub_{hashlib.sha256((share_id + manifest.get('folder_merkle_root', '')).encode('utf-8')).hexdigest()[:32]}"
        manifest["proof"] = proof
        share.manifest_json = manifest
    return {"share_id": share_id, "solana_devnet_tx": proof["solana_devnet_tx"], "manifest": manifest}


@mfl_router.get("/api/share/{share_id}/blocked")
def blocked_folder_share_files(share_id: str, session: Session = Depends(get_db)) -> Dict[str, Any]:
    share = session.get(FolderShare, share_id)
    if not share:
        raise HTTPException(404, "Shared folder not found")
    return {"share_id": share_id, "blocked_files": share.blocked_files_json}
