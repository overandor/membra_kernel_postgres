from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Any, Dict

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException

from .config import settings
from .utils import json_dumps


def _derive_fernet_key(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


_secret = settings.membra_data_encryption_key or settings.platform_api_key
_fernet = Fernet(_derive_fernet_key(_secret)) if _secret else None


def encrypt_sensitive(value: Any) -> str | None:
    if value is None:
        return None
    if _fernet is None:
        if settings.allow_plaintext_pii:
            return f"plain:{value}"
        raise HTTPException(503, "MEMBRA_DATA_ENCRYPTION_KEY is required before storing sensitive data.")
    text = value if isinstance(value, str) else json_dumps(value)
    return "fernet:" + _fernet.encrypt(text.encode("utf-8")).decode("utf-8")


def decrypt_sensitive(value: str | None) -> str | None:
    if value is None:
        return None
    if value.startswith("plain:"):
        return value.removeprefix("plain:")
    if not value.startswith("fernet:"):
        return value if settings.allow_plaintext_pii else None
    if _fernet is None:
        raise HTTPException(503, "MEMBRA_DATA_ENCRYPTION_KEY is required before reading sensitive data.")
    token = value.removeprefix("fernet:")
    try:
        return _fernet.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise HTTPException(500, "Sensitive field decryption failed.") from exc


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sign_access_payload(payload: Dict[str, Any]) -> str:
    if not settings.access_signing_secret:
        raise HTTPException(503, "ACCESS_SIGNING_SECRET or PLATFORM_API_KEY is required before signing QR access tokens.")
    body = json_dumps(payload)
    sig = hmac.new(
        settings.access_signing_secret.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return json_dumps({"typ": "MEMBRA_ACCESS_V1", "alg": "HS256", "payload": payload, "signature": sig})


def verify_access_payload(token: str) -> Dict[str, Any]:
    if not settings.access_signing_secret:
        raise HTTPException(503, "ACCESS_SIGNING_SECRET or PLATFORM_API_KEY is required before verifying QR access tokens.")
    try:
        import json

        wrapper = json.loads(token)
        if wrapper.get("typ") != "MEMBRA_ACCESS_V1":
            raise HTTPException(401, "Invalid QR token type.")
        if wrapper.get("alg") != "HS256":
            raise HTTPException(401, "Invalid QR token algorithm.")
        payload = wrapper["payload"]
        signature = str(wrapper["signature"])
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, "Malformed QR token payload.") from exc

    body = json_dumps(payload)
    expected = hmac.new(
        settings.access_signing_secret.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(401, "Invalid QR token signature.")
    return payload
