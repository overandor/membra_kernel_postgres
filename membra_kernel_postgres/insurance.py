from __future__ import annotations

from typing import Any, Dict
from uuid import uuid4

import httpx
from fastapi import HTTPException

from .config import settings


def _provider_headers(idempotency_key: str | None = None) -> Dict[str, str]:
    headers = {
        "Authorization": f"Bearer {settings.insurance_api_key}",
        "Content-Type": "application/json",
        "X-Correlation-ID": str(uuid4()),
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return headers


def _ensure_provider_configured(kind: str) -> str:
    url = {
        "quote": settings.insurance_quote_url,
        "bind": settings.insurance_bind_url,
        "claim": settings.insurance_claim_url,
    }.get(kind, "")
    if not settings.insurance_api_key or not url:
        raise HTTPException(503, f"Insurance {kind} provider is not configured. Membra fails closed.")
    return url


def _sanitize_provider_error(kind: str, exc: Exception | None = None, status_code: int = 502) -> HTTPException:
    correlation_id = str(uuid4())
    return HTTPException(
        status_code,
        f"Insurance {kind} provider returned an error. Check internal logs with correlation ID {correlation_id}.",
    )


def request_quote(payload: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
    url = _ensure_provider_configured("quote")
    try:
        with httpx.Client(timeout=settings.insurance_timeout_seconds) as client:
            response = client.post(url, json=payload, headers=_provider_headers(idempotency_key))
    except httpx.HTTPError as exc:
        raise _sanitize_provider_error("quote", exc) from exc
    if response.status_code >= 400:
        raise _sanitize_provider_error("quote", status_code=502)
    return response.json()


def bind_policy(payload: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
    url = _ensure_provider_configured("bind")
    try:
        with httpx.Client(timeout=settings.insurance_timeout_seconds) as client:
            response = client.post(url, json=payload, headers=_provider_headers(idempotency_key))
    except httpx.HTTPError as exc:
        raise _sanitize_provider_error("bind", exc) from exc
    if response.status_code >= 400:
        raise _sanitize_provider_error("bind", status_code=502)
    return response.json()


def open_provider_claim(payload: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
    url = _ensure_provider_configured("claim")
    try:
        with httpx.Client(timeout=settings.insurance_timeout_seconds) as client:
            response = client.post(url, json=payload, headers=_provider_headers(idempotency_key))
    except httpx.HTTPError as exc:
        raise _sanitize_provider_error("claim", exc) from exc
    if response.status_code >= 400:
        raise _sanitize_provider_error("claim", status_code=502)
    return response.json()
