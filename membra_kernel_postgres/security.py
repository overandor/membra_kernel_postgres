from __future__ import annotations

import hmac
import os
from typing import Callable, Dict, Optional

from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel

from .config import settings
from .enums import Role


class Principal(BaseModel):
    role: Role


API_KEY_ROLES: Dict[str, Role] = {
    os.getenv("MEMBRA_ADMIN_KEY", "") or settings.platform_api_key: Role.admin,
    os.getenv("MEMBRA_OPS_KEY", ""): Role.ops,
    os.getenv("MEMBRA_INSURANCE_KEY", ""): Role.insurance,
    os.getenv("MEMBRA_CLAIMS_KEY", ""): Role.claims,
    os.getenv("MEMBRA_SCANNER_KEY", ""): Role.scanner,
    os.getenv("MEMBRA_READONLY_KEY", ""): Role.readonly,
}


async def require_platform_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")) -> Principal:
    if not x_api_key:
        raise HTTPException(401, "Missing X-API-Key")
    for key, role in API_KEY_ROLES.items():
        if key and hmac.compare_digest(x_api_key, key):
            return Principal(role=role)
    raise HTTPException(401, "Invalid X-API-Key")


def require_roles(*allowed: Role) -> Callable[[Principal], Principal]:
    allowed_set = set(allowed)

    def dependency(principal: Principal = Depends(require_platform_key)) -> Principal:
        if principal.role not in allowed_set:
            raise HTTPException(403, f"Role {principal.role.value} is not allowed for this endpoint.")
        return principal

    return dependency
