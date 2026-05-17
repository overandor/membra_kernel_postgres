from __future__ import annotations

from typing import Any, Dict

from sqlalchemy.orm import Session

from .models import AuditEvent
from .security import Principal
from .utils import new_id

SENSITIVE_KEYS = {
    "legal_name",
    "email",
    "phone",
    "verified_address",
    "address",
    "provider_payload",
    "provider_response",
    "partner_raw_json",
    "description",
    "claim_description",
    "signed_qr_payload",
}


def redact_payload(payload: Dict[str, Any] | None) -> Dict[str, Any]:
    if not payload:
        return {}
    redacted: Dict[str, Any] = {}
    for key, value in payload.items():
        if key in SENSITIVE_KEYS:
            redacted[key] = "[redacted]"
        elif isinstance(value, dict):
            redacted[key] = redact_payload(value)
        else:
            redacted[key] = value
    return redacted


def audit(
    session: Session,
    entity_type: str,
    entity_id: str,
    event_type: str,
    payload: Dict[str, Any] | None = None,
    principal: Principal | None = None,
) -> None:
    session.add(
        AuditEvent(
            audit_id=new_id("aud"),
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            actor_role=principal.role.value if principal else None,
            payload_json=redact_payload(payload),
        )
    )
