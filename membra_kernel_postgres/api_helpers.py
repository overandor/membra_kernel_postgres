from __future__ import annotations

from typing import Any, Dict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .crypto import decrypt_sensitive
from .models import Asset, Claim, Coverage, Party, Visit
from .schemas import AssetPublic, ClaimOut, CoverageOut, VisitOut


def _party_public(party: Party) -> Dict[str, Any]:
    badges = []
    if party.identity_verified:
        badges.append("identity_verified")
    return {
        "party_id": party.party_id,
        "party_type": party.party_type,
        "identity_verified": party.identity_verified,
        "trust_badges": badges,
    }


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
    from sqlalchemy import select
    if for_update:
        visit = session.scalars(select(Visit).where(Visit.visit_id == visit_id).with_for_update()).one_or_none()
    else:
        visit = session.get(Visit, visit_id)
    if not visit:
        raise HTTPException(404, "Visit not found.")
    return visit


def _get_coverage(session: Session, coverage_id: str, for_update: bool = False) -> Coverage:
    from sqlalchemy import select
    if for_update:
        coverage = session.scalars(select(Coverage).where(Coverage.coverage_id == coverage_id).with_for_update()).one_or_none()
    else:
        coverage = session.get(Coverage, coverage_id)
    if not coverage:
        raise HTTPException(404, "Coverage not found.")
    return coverage
