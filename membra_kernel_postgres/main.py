from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .audit import audit
from .config import settings
from .crypto import decrypt_sensitive, encrypt_sensitive, sha256_hex, sign_access_payload, verify_access_payload
from .db import engine, get_db
from .enums import ClaimStatus, CoverageStatus, Role, VisitStatus
from .insurance import bind_policy, open_provider_claim, request_quote
from .models import AccessToken, Asset, AuditEvent, Base, Claim, Coverage, IdempotencyKey, Party, Visit
from .risk import evaluate_risk
from .schemas import (
    AccessTokenOut,
    AccessVerifyRequest,
    AccessVerifyResponse,
    AssetCreate,
    AssetInternal,
    AssetPublic,
    ClaimCreate,
    ClaimOut,
    CoverageBindRequest,
    CoverageOut,
    CoverageQuoteRequest,
    HealthResponse,
    PartyCreate,
    PartyInternal,
    RiskResult,
    VisitCreate,
    VisitOut,
    WebhookPayload,
)
from .security import Principal, require_roles
from .utils import json_dumps, minutes_between, new_id, parse_dt, utcnow

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .public_routes import public_router
app.include_router(public_router)
from .mfl import mfl_router
app.include_router(mfl_router)


@app.on_event("startup")
def startup() -> None:
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)


def _party_internal(party: Party) -> PartyInternal:
    return PartyInternal(
        party_id=party.party_id,
        party_type=party.party_type,
        legal_name=decrypt_sensitive(party.legal_name_enc),
        email=decrypt_sensitive(party.email_enc),
        phone=decrypt_sensitive(party.phone_enc),
        identity_verified=party.identity_verified,
        risk_score=party.risk_score,
        banned=party.banned,
        created_at=party.created_at,
    )


def _party_public(party: Party) -> Dict[str, Any]:
    badges: List[str] = []
    if party.identity_verified:
        badges.append("identity_verified")
    return {
        "party_id": party.party_id,
        "party_type": party.party_type,
        "identity_verified": party.identity_verified,
        "trust_badges": badges,
    }


def _asset_internal(asset: Asset) -> AssetInternal:
    return AssetInternal(
        asset_id=asset.asset_id,
        owner_party_id=asset.owner_party_id,
        asset_type=asset.asset_type,
        title=asset.title,
        description=asset.description,
        verified_address=decrypt_sensitive(asset.verified_address_enc),
        address_verified=asset.address_verified,
        owner_authorized=asset.owner_authorized,
        insurable=asset.insurable,
        rules=asset.rules or {},
        trust_badges=asset.trust_badges or [],
        price_cents=asset.price_cents,
        created_at=asset.created_at,
    )


def _asset_public(asset: Asset) -> AssetPublic:
    return AssetPublic(
        asset_id=asset.asset_id,
        asset_type=asset.asset_type,
        title=asset.title,
        description=asset.description,
        rules=asset.rules or {},
        trust_badges=asset.trust_badges or [],
        price_cents=asset.price_cents,
    )


def _visit_out(visit: Visit) -> VisitOut:
    return VisitOut(
        visit_id=visit.visit_id,
        asset_id=visit.asset_id,
        host_id=visit.host_id,
        guest_id=visit.guest_id,
        purpose=visit.purpose,
        start_time=visit.start_time,
        end_time=visit.end_time,
        duration_minutes=visit.duration_minutes,
        requested_coverage_limit_cents=visit.requested_coverage_limit_cents,
        requested_deductible_cents=visit.requested_deductible_cents,
        covered_events=visit.covered_events or [],
        payment_authorized=visit.payment_authorized,
        security_deposit_authorized=visit.security_deposit_authorized,
        host_approval=visit.host_approval,
        host_present=visit.host_present,
        emergency_contact_available=visit.emergency_contact_available,
        status=visit.status,
        risk_score=visit.risk_score,
        risk_reasons=visit.risk_reasons or [],
    )


def _coverage_out(coverage: Coverage) -> CoverageOut:
    return CoverageOut(
        coverage_id=coverage.coverage_id,
        visit_id=coverage.visit_id,
        provider=coverage.provider,
        status=coverage.status,
        external_quote_id=coverage.external_quote_id,
        external_policy_id=coverage.external_policy_id,
        premium_cents=coverage.premium_cents,
        coverage_limit_cents=coverage.coverage_limit_cents,
        deductible_cents=coverage.deductible_cents,
        quote_expires_at=coverage.quote_expires_at,
        coverage_start=coverage.coverage_start,
        coverage_end=coverage.coverage_end,
    )


def _claim_out(claim: Claim) -> ClaimOut:
    return ClaimOut(
        claim_id=claim.claim_id,
        visit_id=claim.visit_id,
        coverage_id=claim.coverage_id,
        claimant_party_id=claim.claimant_party_id,
        incident_type=claim.incident_type,
        incident_time=claim.incident_time,
        description=decrypt_sensitive(claim.description_enc),
        status=claim.status,
        external_claim_id=claim.external_claim_id,
        created_at=claim.created_at,
    )


def _get_party(session: Session, party_id: str) -> Party:
    party = session.get(Party, party_id)
    if not party:
        raise HTTPException(404, "Party not found.")
    return party


def _get_asset(session: Session, asset_id: str) -> Asset:
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found.")
    return asset


def _get_visit(session: Session, visit_id: str, for_update: bool = False) -> Visit:
    if for_update:
        visit = session.scalars(select(Visit).where(Visit.visit_id == visit_id).with_for_update()).one_or_none()
    else:
        visit = session.get(Visit, visit_id)
    if not visit:
        raise HTTPException(404, "Visit not found.")
    return visit


def _get_coverage(session: Session, coverage_id: str, for_update: bool = False) -> Coverage:
    if for_update:
        coverage = session.scalars(select(Coverage).where(Coverage.coverage_id == coverage_id).with_for_update()).one_or_none()
    else:
        coverage = session.get(Coverage, coverage_id)
    if not coverage:
        raise HTTPException(404, "Coverage not found.")
    return coverage


def _idempotency_get(session: Session, key: str, endpoint: str) -> Optional[Dict[str, Any]]:
    record = session.get(IdempotencyKey, key)
    if not record:
        return None
    if record.endpoint != endpoint:
        raise HTTPException(409, "Idempotency key was already used for a different endpoint.")
    return record.response_json


def _idempotency_store(session: Session, key: str, endpoint: str, response_json: Dict[str, Any]) -> None:
    session.add(IdempotencyKey(key=key, endpoint=endpoint, response_json=response_json))


def _require_idempotency_key(value: Optional[str]) -> str:
    if not value:
        raise HTTPException(400, "Idempotency-Key header is required for this operation.")
    if len(value) < 12:
        raise HTTPException(400, "Idempotency-Key is too short.")
    return value


def revoke_access_tokens_for_visit(session: Session, visit_id: str, reason: str, principal: Principal | None = None) -> None:
    session.query(AccessToken).filter(AccessToken.visit_id == visit_id, AccessToken.revoked.is_(False)).update(
        {"revoked": True, "revoked_reason": reason},
        synchronize_session=False,
    )
    audit(session, "visit", visit_id, "access_tokens_revoked", {"reason": reason}, principal)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        app=settings.app_name,
        version=settings.app_version,
        database="postgres",
        insurance_provider=settings.insurance_provider_name,
    )


@app.post("/v1/parties", response_model=PartyInternal, dependencies=[Depends(require_roles(Role.admin, Role.ops))])
def create_party(payload: PartyCreate, session: Session = Depends(get_db), principal: Principal = Depends(require_roles(Role.admin, Role.ops))) -> PartyInternal:
    party = Party(
        party_id=new_id("pty"),
        party_type=payload.party_type.value,
        legal_name_enc=encrypt_sensitive(payload.legal_name),
        email_enc=encrypt_sensitive(payload.email),
        phone_enc=encrypt_sensitive(payload.phone),
        identity_verified=payload.identity_verified,
        risk_score=payload.risk_score,
        banned=payload.banned,
    )
    session.add(party)
    audit(session, "party", party.party_id, "created", {"party_type": party.party_type}, principal)
    return _party_internal(party)


@app.get("/v1/parties/{party_id}", response_model=PartyInternal, dependencies=[Depends(require_roles(Role.admin, Role.ops, Role.insurance))])
def get_party(party_id: str, session: Session = Depends(get_db)) -> PartyInternal:
    return _party_internal(_get_party(session, party_id))


@app.get("/v1/parties/{party_id}/public", dependencies=[Depends(require_roles(Role.admin, Role.ops, Role.readonly))])
def get_party_public(party_id: str, session: Session = Depends(get_db)) -> Dict[str, Any]:
    return _party_public(_get_party(session, party_id))


@app.post("/v1/assets", response_model=AssetInternal, dependencies=[Depends(require_roles(Role.admin, Role.ops))])
def create_asset(payload: AssetCreate, session: Session = Depends(get_db), principal: Principal = Depends(require_roles(Role.admin, Role.ops))) -> AssetInternal:
    _get_party(session, payload.owner_party_id)
    asset = Asset(
        asset_id=new_id("ast"),
        owner_party_id=payload.owner_party_id,
        asset_type=payload.asset_type.value,
        title=payload.title,
        description=payload.description,
        verified_address_enc=encrypt_sensitive(payload.verified_address),
        address_verified=payload.address_verified,
        owner_authorized=payload.owner_authorized,
        insurable=payload.insurable,
        rules=payload.rules,
        trust_badges=payload.trust_badges,
        price_cents=payload.price_cents,
    )
    session.add(asset)
    audit(session, "asset", asset.asset_id, "created", {"asset_type": asset.asset_type, "owner_party_id": asset.owner_party_id}, principal)
    return _asset_internal(asset)


@app.get("/v1/assets/{asset_id}", response_model=AssetInternal, dependencies=[Depends(require_roles(Role.admin, Role.ops, Role.insurance))])
def get_asset(asset_id: str, session: Session = Depends(get_db)) -> AssetInternal:
    return _asset_internal(_get_asset(session, asset_id))


@app.get("/v1/assets/{asset_id}/public", response_model=AssetPublic, dependencies=[Depends(require_roles(Role.admin, Role.ops, Role.readonly))])
def get_asset_public(asset_id: str, session: Session = Depends(get_db)) -> AssetPublic:
    return _asset_public(_get_asset(session, asset_id))


@app.post("/v1/visits", response_model=VisitOut, dependencies=[Depends(require_roles(Role.admin, Role.ops))])
def create_visit(payload: VisitCreate, session: Session = Depends(get_db), principal: Principal = Depends(require_roles(Role.admin, Role.ops))) -> VisitOut:
    _get_asset(session, payload.asset_id)
    _get_party(session, payload.host_id)
    _get_party(session, payload.guest_id)
    duration = minutes_between(payload.start_time, payload.end_time)
    visit = Visit(
        visit_id=new_id("vis"),
        asset_id=payload.asset_id,
        host_id=payload.host_id,
        guest_id=payload.guest_id,
        purpose=payload.purpose.value,
        start_time=parse_dt(payload.start_time),
        end_time=parse_dt(payload.end_time),
        duration_minutes=duration,
        requested_coverage_limit_cents=payload.requested_coverage_limit_cents,
        requested_deductible_cents=payload.requested_deductible_cents,
        covered_events=payload.covered_events,
        payment_authorized=payload.payment_authorized,
        security_deposit_authorized=payload.security_deposit_authorized,
        host_approval=payload.host_approval,
        host_present=payload.host_present,
        emergency_contact_available=payload.emergency_contact_available,
        status=VisitStatus.requested.value,
    )
    session.add(visit)
    audit(session, "visit", visit.visit_id, "created", {"asset_id": visit.asset_id, "purpose": visit.purpose}, principal)
    return _visit_out(visit)


@app.get("/v1/visits/{visit_id}", response_model=VisitOut, dependencies=[Depends(require_roles(Role.admin, Role.ops, Role.insurance, Role.claims))])
def get_visit(visit_id: str, session: Session = Depends(get_db)) -> VisitOut:
    return _visit_out(_get_visit(session, visit_id))


@app.post("/v1/visits/{visit_id}/risk", response_model=RiskResult, dependencies=[Depends(require_roles(Role.admin, Role.ops))])
def score_visit_risk(visit_id: str, session: Session = Depends(get_db), principal: Principal = Depends(require_roles(Role.admin, Role.ops))) -> RiskResult:
    visit = _get_visit(session, visit_id, for_update=True)
    asset = _get_asset(session, visit.asset_id)
    host = _get_party(session, visit.host_id)
    guest = _get_party(session, visit.guest_id)
    score, reasons, approved = evaluate_risk(asset, host, guest, visit)
    visit.risk_score = score
    visit.risk_reasons = reasons
    visit.status = VisitStatus.risk_approved.value if approved else VisitStatus.risk_denied.value
    audit(session, "visit", visit.visit_id, "risk_evaluated", {"score": score, "approved": approved, "reasons": reasons}, principal)
    return RiskResult(visit_id=visit.visit_id, approved=approved, risk_score=score, reasons=reasons, status=visit.status)


@app.post("/v1/insurance/quote", response_model=CoverageOut, dependencies=[Depends(require_roles(Role.admin, Role.ops, Role.insurance))])
def quote_coverage(
    payload: CoverageQuoteRequest,
    session: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(Role.admin, Role.ops, Role.insurance)),
    idempotency_key_header: Optional[str] = Header(default=None, alias="Idempotency-Key"),
) -> CoverageOut | Dict[str, Any]:
    idempotency_key = _require_idempotency_key(idempotency_key_header)
    cached = _idempotency_get(session, idempotency_key, "insurance_quote")
    if cached:
        return cached

    visit = _get_visit(session, payload.visit_id, for_update=True)
    if visit.status != VisitStatus.risk_approved.value:
        raise HTTPException(409, "Visit must be risk_approved before requesting insurance quote.")
    asset = _get_asset(session, visit.asset_id)
    host = _get_party(session, visit.host_id)
    guest = _get_party(session, visit.guest_id)

    provider_payload = {
        "visit_id": visit.visit_id,
        "asset_id": asset.asset_id,
        "asset_type": asset.asset_type,
        "purpose": visit.purpose,
        "verified_address": decrypt_sensitive(asset.verified_address_enc),
        "start_time": visit.start_time.isoformat(),
        "end_time": visit.end_time.isoformat(),
        "coverage_limit_cents": visit.requested_coverage_limit_cents,
        "deductible_cents": visit.requested_deductible_cents,
        "covered_events": visit.covered_events,
        "host": _party_public(host),
        "guest": _party_public(guest),
    }
    partner_quote = request_quote(provider_payload, idempotency_key)
    external_quote_id = partner_quote.get("external_quote_id")
    if not external_quote_id:
        raise HTTPException(502, "Insurance quote provider response was missing external_quote_id.")

    coverage = Coverage(
        coverage_id=new_id("cov"),
        visit_id=visit.visit_id,
        provider=settings.insurance_provider_name,
        status=CoverageStatus.quoted.value,
        external_quote_id=str(external_quote_id),
        premium_cents=int(partner_quote.get("premium_cents", 0)),
        coverage_limit_cents=int(partner_quote.get("coverage_limit_cents", visit.requested_coverage_limit_cents)),
        deductible_cents=int(partner_quote.get("deductible_cents", visit.requested_deductible_cents)),
        quote_expires_at=parse_dt(partner_quote["quote_expires_at"]) if partner_quote.get("quote_expires_at") else None,
        partner_raw_json_enc=encrypt_sensitive(partner_quote),
    )
    session.add(coverage)
    visit.status = VisitStatus.coverage_quoted.value
    response = _coverage_out(coverage).model_dump(mode="json")
    _idempotency_store(session, idempotency_key, "insurance_quote", response)
    audit(
        session,
        "coverage",
        coverage.coverage_id,
        "quote_created",
        {
            "visit_id": visit.visit_id,
            "provider": coverage.provider,
            "external_quote_id": coverage.external_quote_id,
            "premium_cents": coverage.premium_cents,
            "coverage_limit_cents": coverage.coverage_limit_cents,
        },
        principal,
    )
    return response


@app.post("/v1/insurance/bind", response_model=CoverageOut, dependencies=[Depends(require_roles(Role.admin, Role.ops, Role.insurance))])
def bind_coverage(
    payload: CoverageBindRequest,
    session: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(Role.admin, Role.ops, Role.insurance)),
    idempotency_key_header: Optional[str] = Header(default=None, alias="Idempotency-Key"),
) -> CoverageOut | Dict[str, Any]:
    idempotency_key = _require_idempotency_key(idempotency_key_header)
    cached = _idempotency_get(session, idempotency_key, "insurance_bind")
    if cached:
        return cached

    coverage = _get_coverage(session, payload.coverage_id, for_update=True)
    visit = _get_visit(session, coverage.visit_id, for_update=True)
    if coverage.status == CoverageStatus.active.value:
        return _coverage_out(coverage)
    if coverage.status != CoverageStatus.quoted.value:
        raise HTTPException(409, "Coverage must be quoted before bind.")
    if coverage.quote_expires_at and utcnow() > parse_dt(coverage.quote_expires_at):
        raise HTTPException(409, "Insurance quote has expired. Request a new quote.")
    if not visit.payment_authorized:
        raise HTTPException(409, "Payment must be authorized before binding coverage.")

    provider_payload = {
        "coverage_id": coverage.coverage_id,
        "visit_id": visit.visit_id,
        "external_quote_id": coverage.external_quote_id,
        "start_time": visit.start_time.isoformat(),
        "end_time": visit.end_time.isoformat(),
        "coverage_limit_cents": coverage.coverage_limit_cents,
        "deductible_cents": coverage.deductible_cents,
    }
    partner_bind = bind_policy(provider_payload, idempotency_key)
    external_policy_id = partner_bind.get("external_policy_id")
    if not external_policy_id:
        raise HTTPException(502, "Insurance bind provider response was missing external_policy_id.")

    coverage_start = parse_dt(partner_bind.get("coverage_start", visit.start_time))
    coverage_end = parse_dt(partner_bind.get("coverage_end", visit.end_time))
    if coverage_start > parse_dt(visit.start_time) or coverage_end < parse_dt(visit.end_time):
        raise HTTPException(502, "Provider coverage window does not fully cover the reservation window.")

    coverage.external_policy_id = str(external_policy_id)
    coverage.coverage_start = coverage_start
    coverage.coverage_end = coverage_end
    coverage.status = CoverageStatus.active.value
    coverage.partner_raw_json_enc = encrypt_sensitive(partner_bind)
    visit.status = VisitStatus.covered.value
    response = _coverage_out(coverage).model_dump(mode="json")
    _idempotency_store(session, idempotency_key, "insurance_bind", response)
    audit(
        session,
        "coverage",
        coverage.coverage_id,
        "bound",
        {"visit_id": visit.visit_id, "provider": coverage.provider, "external_policy_id": coverage.external_policy_id},
        principal,
    )
    return response


@app.post("/v1/access/{visit_id}/qr", response_model=AccessTokenOut, dependencies=[Depends(require_roles(Role.admin, Role.ops))])
def issue_qr_access(visit_id: str, session: Session = Depends(get_db), principal: Principal = Depends(require_roles(Role.admin, Role.ops))) -> AccessTokenOut:
    visit = _get_visit(session, visit_id, for_update=True)
    coverage = session.scalars(
        select(Coverage)
        .where(Coverage.visit_id == visit_id, Coverage.status == CoverageStatus.active.value)
        .order_by(Coverage.created_at.desc())
        .with_for_update()
    ).first()
    if not coverage:
        raise HTTPException(409, "No active coverage exists for this visit.")
    if not coverage.coverage_start or not coverage.coverage_end:
        raise HTTPException(409, "Coverage window is missing.")
    if parse_dt(coverage.coverage_start) > parse_dt(visit.start_time) or parse_dt(coverage.coverage_end) < parse_dt(visit.end_time):
        raise HTTPException(409, "Coverage window does not fully cover the visit.")

    issued_at = utcnow()
    payload = {
        "aud": "membra_scanner",
        "sub": visit.guest_id,
        "visit_id": visit.visit_id,
        "coverage_id": coverage.coverage_id,
        "asset_id": visit.asset_id,
        "iat": int(issued_at.timestamp()),
        "nbf": int(parse_dt(visit.start_time).timestamp()) - settings.token_leeway_seconds,
        "exp": int(parse_dt(visit.end_time).timestamp()) + settings.token_leeway_seconds,
    }
    signed = sign_access_payload(payload)
    token = AccessToken(
        access_token_id=new_id("tok"),
        visit_id=visit.visit_id,
        coverage_id=coverage.coverage_id,
        asset_id=visit.asset_id,
        token_hash=sha256_hex(signed),
        token_payload=payload,
        expires_at=parse_dt(visit.end_time),
    )
    session.add(token)
    visit.status = VisitStatus.access_issued.value
    audit(session, "visit", visit.visit_id, "qr_issued", {"coverage_id": coverage.coverage_id, "asset_id": visit.asset_id}, principal)
    return AccessTokenOut(
        access_token_id=token.access_token_id,
        visit_id=visit.visit_id,
        coverage_id=coverage.coverage_id,
        asset_id=visit.asset_id,
        signed_qr_payload=signed,
        expires_at=token.expires_at,
    )


@app.post("/v1/access/verify", response_model=AccessVerifyResponse, dependencies=[Depends(require_roles(Role.admin, Role.ops, Role.scanner))])
def verify_qr_access(payload: AccessVerifyRequest, session: Session = Depends(get_db)) -> AccessVerifyResponse:
    token_payload = verify_access_payload(payload.signed_qr_payload)
    if token_payload.get("aud") != "membra_scanner":
        return AccessVerifyResponse(access_allowed=False, reason="Invalid QR token audience.")

    visit_id = str(token_payload.get("visit_id", ""))
    coverage_id = str(token_payload.get("coverage_id", ""))
    if not visit_id or not coverage_id:
        return AccessVerifyResponse(access_allowed=False, reason="QR token is missing visit or coverage ID.")
    visit = _get_visit(session, visit_id)
    if str(token_payload.get("asset_id")) != visit.asset_id:
        return AccessVerifyResponse(
            access_allowed=False,
            reason="QR token asset does not match visit asset.",
            visit_id=visit_id,
            coverage_id=coverage_id,
        )
    token_hash = sha256_hex(payload.signed_qr_payload)
    token_record = session.scalars(select(AccessToken).where(AccessToken.token_hash == token_hash)).one_or_none()
    if not token_record:
        return AccessVerifyResponse(access_allowed=False, reason="QR token is not registered.", visit_id=visit_id, coverage_id=coverage_id)
    if token_record.revoked:
        return AccessVerifyResponse(access_allowed=False, reason="QR token has been revoked.", visit_id=visit_id, coverage_id=coverage_id)

    now_ts = int(utcnow().timestamp())
    if now_ts < int(token_payload.get("nbf", 0)):
        return AccessVerifyResponse(access_allowed=False, reason="QR token is not active yet.", visit_id=visit_id, coverage_id=coverage_id)
    if now_ts > int(token_payload.get("exp", 0)):
        return AccessVerifyResponse(access_allowed=False, reason="QR token has expired.", visit_id=visit_id, coverage_id=coverage_id)

    coverage = _get_coverage(session, coverage_id)
    if coverage.visit_id != visit.visit_id:
        return AccessVerifyResponse(access_allowed=False, reason="Coverage does not belong to this visit.", visit_id=visit_id, coverage_id=coverage_id)
    if coverage.status != CoverageStatus.active.value:
        return AccessVerifyResponse(access_allowed=False, reason="Coverage is not active.", visit_id=visit_id, coverage_id=coverage_id)
    if not coverage.coverage_start or not coverage.coverage_end:
        return AccessVerifyResponse(access_allowed=False, reason="Coverage window is missing.", visit_id=visit_id, coverage_id=coverage_id)
    if not (parse_dt(coverage.coverage_start) <= utcnow() <= parse_dt(coverage.coverage_end)):
        return AccessVerifyResponse(access_allowed=False, reason="Current time is outside coverage window.", visit_id=visit_id, coverage_id=coverage_id)

    return AccessVerifyResponse(
        access_allowed=True,
        reason="Access allowed.",
        visit_id=visit_id,
        coverage_id=coverage_id,
        asset_id=visit.asset_id,
    )


@app.post("/v1/claims", response_model=ClaimOut, dependencies=[Depends(require_roles(Role.admin, Role.ops, Role.claims))])
def create_claim(
    payload: ClaimCreate,
    session: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(Role.admin, Role.ops, Role.claims)),
    idempotency_key_header: Optional[str] = Header(default=None, alias="Idempotency-Key"),
) -> ClaimOut | Dict[str, Any]:
    idempotency_key = _require_idempotency_key(idempotency_key_header)
    cached = _idempotency_get(session, idempotency_key, "claim_create")
    if cached:
        return cached
    coverage = _get_coverage(session, payload.coverage_id, for_update=True)
    visit = _get_visit(session, payload.visit_id)
    if coverage.visit_id != visit.visit_id:
        raise HTTPException(409, "Coverage does not belong to this visit.")
    if not coverage.external_policy_id:
        raise HTTPException(409, "Coverage has no external policy ID.")
    if payload.claimant_party_id not in {visit.host_id, visit.guest_id}:
        raise HTTPException(403, "Claimant is not a party to this visit.")
    if payload.incident_type not in (visit.covered_events or []):
        raise HTTPException(409, "Incident type was not covered for this visit.")
    incident_time = parse_dt(payload.incident_time)
    if coverage.coverage_start and coverage.coverage_end:
        if not (parse_dt(coverage.coverage_start) <= incident_time <= parse_dt(coverage.coverage_end)):
            raise HTTPException(409, "Incident time is outside the coverage window.")

    provider_payload = {
        "visit_id": visit.visit_id,
        "coverage_id": coverage.coverage_id,
        "external_policy_id": coverage.external_policy_id,
        "claimant_party_id": payload.claimant_party_id,
        "incident_type": payload.incident_type,
        "incident_time": incident_time.isoformat(),
        "description": payload.description,
    }
    provider_claim = open_provider_claim(provider_payload, idempotency_key)
    external_claim_id = provider_claim.get("external_claim_id")
    if not external_claim_id:
        raise HTTPException(502, "Insurance claim provider response was missing external_claim_id.")

    claim = Claim(
        claim_id=new_id("clm"),
        visit_id=visit.visit_id,
        coverage_id=coverage.coverage_id,
        claimant_party_id=payload.claimant_party_id,
        incident_type=payload.incident_type,
        incident_time=incident_time,
        description_enc=encrypt_sensitive(payload.description),
        status=ClaimStatus.submitted_to_provider.value,
        external_claim_id=str(external_claim_id),
    )
    session.add(claim)
    response = _claim_out(claim).model_dump(mode="json")
    _idempotency_store(session, idempotency_key, "claim_create", response)
    audit(
        session,
        "claim",
        claim.claim_id,
        "created",
        {"visit_id": visit.visit_id, "coverage_id": coverage.coverage_id, "incident_type": claim.incident_type},
        principal,
    )
    return response


@app.get("/v1/claims/{claim_id}", response_model=ClaimOut, dependencies=[Depends(require_roles(Role.admin, Role.ops, Role.claims, Role.insurance))])
def get_claim(claim_id: str, session: Session = Depends(get_db)) -> ClaimOut:
    claim = session.get(Claim, claim_id)
    if not claim:
        raise HTTPException(404, "Claim not found.")
    return _claim_out(claim)


@app.post("/v1/webhooks/insurance/{provider_name}", dependencies=[Depends(require_roles(Role.admin, Role.insurance))])
def insurance_webhook(
    provider_name: str,
    payload: WebhookPayload,
    session: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(Role.admin, Role.insurance)),
) -> Dict[str, Any]:
    coverage = None
    if payload.coverage_id:
        coverage = session.scalars(select(Coverage).where(Coverage.coverage_id == payload.coverage_id).with_for_update()).one_or_none()
    if not coverage:
        coverage = session.scalars(
            select(Coverage)
            .where(
                Coverage.provider == provider_name,
                or_(
                    Coverage.external_quote_id == payload.external_quote_id,
                    Coverage.external_policy_id == payload.external_policy_id,
                ),
            )
            .with_for_update()
        ).one_or_none()
    if not coverage:
        raise HTTPException(404, "Coverage not found for webhook.")

    coverage.status = payload.status.value
    if payload.external_policy_id and not coverage.external_policy_id:
        coverage.external_policy_id = payload.external_policy_id
    audit(session, "coverage", coverage.coverage_id, "webhook_status_update", {"status": payload.status.value}, principal)

    if payload.status in {CoverageStatus.cancelled, CoverageStatus.denied, CoverageStatus.failed}:
        visit = _get_visit(session, coverage.visit_id, for_update=True)
        visit.status = VisitStatus.cancelled.value
        revoke_access_tokens_for_visit(session, visit.visit_id, f"coverage_{payload.status.value}", principal)

    return {"ok": True, "coverage_id": coverage.coverage_id, "status": coverage.status}


@app.get("/v1/audit/{entity_type}/{entity_id}", dependencies=[Depends(require_roles(Role.admin, Role.ops))])
def get_audit(entity_type: str, entity_id: str, session: Session = Depends(get_db)) -> Dict[str, Any]:
    rows = session.scalars(
        select(AuditEvent)
        .where(AuditEvent.entity_type == entity_type, AuditEvent.entity_id == entity_id)
        .order_by(AuditEvent.created_at.asc())
    ).all()
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "events": [
            {
                "audit_id": row.audit_id,
                "event_type": row.event_type,
                "actor_role": row.actor_role,
                "payload_json": row.payload_json,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ],
    }


@app.get("/v1/provider/capabilities", dependencies=[Depends(require_roles(Role.admin, Role.ops, Role.insurance, Role.readonly))])
def provider_capabilities() -> Dict[str, Any]:
    return {
        "provider": settings.insurance_provider_name,
        "quote_configured": bool(settings.insurance_api_key and settings.insurance_quote_url),
        "bind_configured": bool(settings.insurance_api_key and settings.insurance_bind_url),
        "claim_configured": bool(settings.insurance_api_key and settings.insurance_claim_url),
        "database": "postgres",
        "fail_closed": True,
    }
