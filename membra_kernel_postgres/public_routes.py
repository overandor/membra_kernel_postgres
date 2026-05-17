from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .config import settings
from .crypto import decrypt_sensitive, sha256_hex, sign_access_payload, verify_access_payload
from .db import get_db
from .enums import AssetType, CoverageStatus, PartyType, VisitPurpose, VisitStatus
from .api_helpers import _asset_public, _get_asset, _get_coverage, _get_party, _get_visit, _visit_out, _coverage_out
from .models import Asset, Coverage, Party, Visit
from .utils import minutes_between, new_id, parse_dt, utcnow

public_router = APIRouter(prefix="/public/v1")


# ─── Consumer Auth (simplified; production uses OAuth/JWT) ──
class ConsumerRegister(BaseModel):
    email: str
    name: str
    phone: Optional[str] = None
    party_type: PartyType = PartyType.guest


class ConsumerOut(BaseModel):
    party_id: str
    name: str
    email: str
    identity_verified: bool = False


class ConsumerLogin(BaseModel):
    email: str


@public_router.post("/register", response_model=ConsumerOut)
def consumer_register(payload: ConsumerRegister, session: Session = Depends(get_db)) -> ConsumerOut:
    from .crypto import encrypt_sensitive
    party = Party(
        party_id=new_id("pty"),
        party_type=payload.party_type.value,
        legal_name_enc=encrypt_sensitive(payload.name),
        email_enc=encrypt_sensitive(payload.email),
        phone_enc=encrypt_sensitive(payload.phone) if payload.phone else None,
        identity_verified=False,
        risk_score=50,
        banned=False,
    )
    session.add(party)
    return ConsumerOut(
        party_id=party.party_id,
        name=payload.name,
        email=payload.email,
        identity_verified=False,
    )


@public_router.post("/login", response_model=ConsumerOut)
def consumer_login(payload: ConsumerLogin, session: Session = Depends(get_db)) -> ConsumerOut:
    from .crypto import encrypt_sensitive
    enc_email = encrypt_sensitive(payload.email)
    party = session.query(Party).filter(Party.email_enc == enc_email).first()
    if not party:
        raise HTTPException(404, "Account not found")
    return ConsumerOut(
        party_id=party.party_id,
        name=decrypt_sensitive(party.legal_name_enc) or "",
        email=payload.email,
        identity_verified=party.identity_verified,
    )


# ─── Public Asset Browsing ──────────────────────────────────
class NearbyQuery(BaseModel):
    lat: float
    lng: float
    radius_miles: float = 5.0
    category: Optional[AssetType] = None


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    import math
    R = 3959
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


@public_router.get("/assets/nearby")
def public_assets_nearby(
    lat: float,
    lng: float,
    radius_miles: float = 5.0,
    category: Optional[AssetType] = None,
    session: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    assets = session.query(Asset).filter(Asset.owner_authorized == True).all()
    results = []
    for asset in assets:
        # Simple lat/lng extraction - in production use PostGIS
        # For demo, we scan all and filter in Python
        if category and asset.asset_type != category.value:
            continue
        # Skip assets without price
        if asset.price_cents is None:
            continue
        # Mock distance: we need lat/lng on asset. Kernel doesn't store them directly.
        # We'll return all and let frontend handle.
        results.append(_asset_public(asset).model_dump(mode="json"))
    return results


@public_router.get("/assets/{asset_id}")
def public_asset_detail(asset_id: str, session: Session = Depends(get_db)) -> Dict[str, Any]:
    asset = _get_asset(session, asset_id)
    return _asset_public(asset).model_dump(mode="json")


# ─── Public Reservation Flow ────────────────────────────────
class PublicReservationCreate(BaseModel):
    asset_id: str
    guest_id: str
    start_time: datetime
    end_time: datetime
    purpose: VisitPurpose


@public_router.post("/reservations")
def public_create_reservation(payload: PublicReservationCreate, session: Session = Depends(get_db)) -> Dict[str, Any]:
    asset = _get_asset(session, payload.asset_id)
    guest = _get_party(session, payload.guest_id)
    host = _get_party(session, asset.owner_party_id)

    if guest.banned:
        raise HTTPException(403, "Guest account is suspended")
    if not asset.owner_authorized:
        raise HTTPException(400, "Asset is not available for booking")

    duration = minutes_between(payload.start_time, payload.end_time)
    visit = Visit(
        visit_id=new_id("vis"),
        asset_id=payload.asset_id,
        host_id=asset.owner_party_id,
        guest_id=payload.guest_id,
        purpose=payload.purpose.value,
        start_time=parse_dt(payload.start_time),
        end_time=parse_dt(payload.end_time),
        duration_minutes=duration,
        requested_coverage_limit_cents=settings.min_coverage_limit_cents,
        requested_deductible_cents=settings.default_deductible_cents,
        covered_events=["property_damage", "personal_injury", "theft", "host_liability", "guest_liability", "accidental_damage"],
        payment_authorized=False,
        security_deposit_authorized=False,
        host_approval=True,  # Auto-approve for public API
        host_present=False,
        emergency_contact_available=True,
        status=VisitStatus.requested.value,
    )
    session.add(visit)
    return _visit_out(visit).model_dump(mode="json")


@public_router.get("/reservations/{visit_id}")
def public_get_reservation(visit_id: str, session: Session = Depends(get_db)) -> Dict[str, Any]:
    visit = _get_visit(session, visit_id)
    return _visit_out(visit).model_dump(mode="json")


# ─── Full Transaction Flow ─────────────────────────────────
class FullFlowRequest(BaseModel):
    visit_id: str
    payment_method_id: str = "pm_demo"


@public_router.post("/reservations/{visit_id}/complete")
def public_complete_flow(visit_id: str, payload: FullFlowRequest, session: Session = Depends(get_db)) -> Dict[str, Any]:
    """End-to-end flow: risk -> insurance quote -> bind -> QR issue"""
    from .risk import evaluate_risk
    from .insurance import request_quote, bind_policy
    from .crypto import sign_access_payload
    from .schemas import CoverageQuoteRequest, CoverageBindRequest

    visit = _get_visit(session, visit_id)

    # 1. Risk
    if visit.status in (VisitStatus.requested.value,):
        asset = _get_asset(session, visit.asset_id)
        host = _get_party(session, visit.host_id)
        guest = _get_party(session, visit.guest_id)
        score, reasons, approved = evaluate_risk(asset, host, guest, visit)
        visit.risk_score = score
        visit.risk_reasons = reasons
        visit.status = VisitStatus.risk_approved.value if approved else VisitStatus.risk_denied.value
        session.commit()
        visit = _get_visit(session, visit_id)

    # 2. Insurance quote (mock since no real provider configured)
    if visit.status == VisitStatus.risk_approved.value:
        coverage = Coverage(
            coverage_id=new_id("cov"),
            visit_id=visit_id,
            provider="membra_mock",
            status=CoverageStatus.quoted.value,
            external_quote_id=new_id("extq"),
            premium_cents=350,
            coverage_limit_cents=visit.requested_coverage_limit_cents,
            deductible_cents=visit.requested_deductible_cents,
            quote_expires_at=utcnow() + timedelta(hours=1),
        )
        session.add(coverage)
        visit.status = VisitStatus.coverage_quoted.value
        session.commit()
        visit = _get_visit(session, visit_id)

    # 3. Simulate payment authorization
    if visit.status == VisitStatus.coverage_quoted.value:
        visit.payment_authorized = True
        session.commit()
        visit = _get_visit(session, visit_id)

    # 4. Bind coverage (mock)
    if visit.status == VisitStatus.coverage_quoted.value:
        coverage = session.query(Coverage).filter(
            Coverage.visit_id == visit_id,
            Coverage.status == CoverageStatus.quoted.value
        ).order_by(Coverage.created_at.desc()).first()
        if coverage:
            coverage.external_policy_id = new_id("pol")
            coverage.coverage_start = visit.start_time
            coverage.coverage_end = visit.end_time
            coverage.status = CoverageStatus.active.value
            session.commit()
        visit.status = VisitStatus.covered.value
        session.commit()
        visit = _get_visit(session, visit_id)

    # 5. Issue QR
    if visit.status == VisitStatus.covered.value:
        from .crypto import sha256_hex
        coverage = session.query(Coverage).filter(
            Coverage.visit_id == visit_id,
            Coverage.status == CoverageStatus.active.value
        ).order_by(Coverage.created_at.desc()).first()
        issued_at = utcnow()
        payload = {
            "aud": "membra_scanner",
            "sub": visit.guest_id,
            "visit_id": visit.visit_id,
            "coverage_id": coverage.coverage_id if coverage else None,
            "asset_id": visit.asset_id,
            "iat": int(issued_at.timestamp()),
            "nbf": int(visit.start_time.timestamp()) - settings.token_leeway_seconds,
            "exp": int(visit.end_time.timestamp()) + settings.token_leeway_seconds,
        }
        signed = sign_access_payload(payload)
        from .models import AccessToken
        token = AccessToken(
            access_token_id=new_id("tok"),
            visit_id=visit.visit_id,
            coverage_id=coverage.coverage_id,
            asset_id=visit.asset_id,
            token_hash=sha256_hex(signed),
            token_payload=payload,
            expires_at=visit.end_time,
        )
        session.add(token)
        visit.status = VisitStatus.access_issued.value
        session.commit()
        return {
            "visit": _visit_out(visit).model_dump(mode="json"),
            "qr_token": signed,
            "coverage": _coverage_out(coverage).model_dump(mode="json") if coverage else None,
        }

    return _visit_out(visit).model_dump(mode="json")


# ─── Access Verification (public scanner endpoint) ────────
class PublicQRVerify(BaseModel):
    qr_payload: str


@public_router.post("/access/verify")
def public_verify_qr(payload: PublicQRVerify, session: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        from .crypto import verify_access_payload, sha256_hex
        token_payload = verify_access_payload(payload.qr_payload)
        if token_payload.get("aud") != "membra_scanner":
            return {"access_allowed": False, "reason": "Invalid QR token audience."}
        v_id = str(token_payload.get("visit_id", ""))
        c_id = str(token_payload.get("coverage_id", ""))
        if not v_id or not c_id:
            return {"access_allowed": False, "reason": "QR token is missing visit or coverage ID."}
        visit = _get_visit(session, v_id)
        if str(token_payload.get("asset_id")) != visit.asset_id:
            return {"access_allowed": False, "reason": "QR token asset does not match visit asset.", "visit_id": v_id, "coverage_id": c_id}
        token_hash = sha256_hex(payload.qr_payload)
        from .models import AccessToken
        from sqlalchemy import select
        token_record = session.scalars(select(AccessToken).where(AccessToken.token_hash == token_hash)).one_or_none()
        if not token_record:
            return {"access_allowed": False, "reason": "QR token is not registered.", "visit_id": v_id, "coverage_id": c_id}
        if token_record.revoked:
            return {"access_allowed": False, "reason": "QR token has been revoked.", "visit_id": v_id, "coverage_id": c_id}
        now_ts = int(utcnow().timestamp())
        if now_ts < int(token_payload.get("nbf", 0)):
            return {"access_allowed": False, "reason": "QR token is not active yet.", "visit_id": v_id, "coverage_id": c_id}
        if now_ts > int(token_payload.get("exp", 0)):
            return {"access_allowed": False, "reason": "QR token has expired.", "visit_id": v_id, "coverage_id": c_id}
        coverage = _get_coverage(session, c_id)
        if coverage.visit_id != visit.visit_id:
            return {"access_allowed": False, "reason": "Coverage does not belong to this visit.", "visit_id": v_id, "coverage_id": c_id}
        if coverage.status != CoverageStatus.active.value:
            return {"access_allowed": False, "reason": "Coverage is not active.", "visit_id": v_id, "coverage_id": c_id}
        return {"access_allowed": True, "reason": "Access allowed.", "visit_id": v_id, "coverage_id": c_id, "asset_id": visit.asset_id}
    except HTTPException as e:
        return {"access_allowed": False, "reason": e.detail}


# ─── Check-in / Check-out ─────────────────────────────────
@public_router.post("/access/check-in/{visit_id}")
def public_check_in(visit_id: str, session: Session = Depends(get_db)) -> Dict[str, Any]:
    visit = _get_visit(session, visit_id, for_update=True)
    if visit.status != VisitStatus.access_issued.value:
        raise HTTPException(409, f"Cannot check in from status {visit.status}")
    visit.status = VisitStatus.active.value
    return _visit_out(visit).model_dump(mode="json")


@public_router.post("/access/check-out/{visit_id}")
def public_check_out(visit_id: str, session: Session = Depends(get_db)) -> Dict[str, Any]:
    visit = _get_visit(session, visit_id, for_update=True)
    if visit.status not in (VisitStatus.active.value, VisitStatus.access_issued.value):
        raise HTTPException(409, f"Cannot check out from status {visit.status}")
    visit.status = VisitStatus.completed.value
    return _visit_out(visit).model_dump(mode="json")


# ─── Payments (simplified; production uses Stripe) ────────
class PaymentCreate(BaseModel):
    visit_id: str
    amount_cents: int
    currency: str = "USD"
    provider: str = "stripe"


class PaymentOut(BaseModel):
    payment_id: str
    visit_id: str
    amount_cents: int
    platform_fee_cents: int
    insurance_premium_cents: int
    host_payout_cents: int
    status: str
    created_at: datetime


@public_router.post("/payments")
def public_create_payment(payload: PaymentCreate, session: Session = Depends(get_db)) -> Dict[str, Any]:
    visit = _get_visit(session, payload.visit_id)
    if not visit.payment_authorized:
        raise HTTPException(409, "Payment not authorized for this visit")

    platform_fee = int(payload.amount_cents * 0.15)
    insurance_premium = int(payload.amount_cents * 0.07)
    host_payout = payload.amount_cents - platform_fee - insurance_premium

    # Store payment in a simple table (using kernel's engine)
    from .db import engine
    from sqlalchemy import text
    payment_id = new_id("pay")
    with engine.begin() as conn:
        conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS public_payments (
                    payment_id TEXT PRIMARY KEY,
                    visit_id TEXT NOT NULL,
                    amount_cents INTEGER NOT NULL,
                    platform_fee_cents INTEGER NOT NULL,
                    insurance_premium_cents INTEGER NOT NULL,
                    host_payout_cents INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
        )
        conn.execute(
            text("""
                INSERT INTO public_payments (payment_id, visit_id, amount_cents, platform_fee_cents,
                    insurance_premium_cents, host_payout_cents, status)
                VALUES (:pid, :vid, :amount, :fee, :ins, :host, :status)
            """),
            {
                "pid": payment_id,
                "vid": payload.visit_id,
                "amount": payload.amount_cents,
                "fee": platform_fee,
                "ins": insurance_premium,
                "host": host_payout,
                "status": "authorized",
            },
        )

    return {
        "payment_id": payment_id,
        "visit_id": payload.visit_id,
        "amount_cents": payload.amount_cents,
        "platform_fee_cents": platform_fee,
        "insurance_premium_cents": insurance_premium,
        "host_payout_cents": host_payout,
        "status": "authorized",
        "created_at": utcnow().isoformat(),
    }


# ─── Health ───────────────────────────────────────────────
@public_router.get("/health")
def public_health() -> Dict[str, Any]:
    return {"status": "ok", "service": "membra-public-api"}
