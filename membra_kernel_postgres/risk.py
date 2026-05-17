from __future__ import annotations

from typing import Dict, List, Set, Tuple

from .config import settings
from .enums import AssetType, VisitPurpose
from .models import Asset, Party, Visit

ASSET_PURPOSE_MATRIX: Dict[AssetType, Set[VisitPurpose]] = {
    AssetType.bathroom: {VisitPurpose.bathroom_access},
    AssetType.parking_spot: {VisitPurpose.parking},
    AssetType.tool: {VisitPurpose.tool_rental},
    AssetType.ev_charger: {VisitPurpose.ev_charging},
    AssetType.workspace: {VisitPurpose.workspace_access},
    AssetType.wifi_access: {VisitPurpose.wifi_access},
    AssetType.laundry: {VisitPurpose.laundry},
    AssetType.printer: {VisitPurpose.printing},
    AssetType.seating: {VisitPurpose.seating},
    AssetType.pickup_dropoff: {VisitPurpose.pickup_dropoff},
    AssetType.storage_shelf: {VisitPurpose.storage_access},
    AssetType.private_garage: {VisitPurpose.parking, VisitPurpose.storage_access},
    AssetType.shared_garage: {VisitPurpose.parking, VisitPurpose.storage_access},
    AssetType.parking_garage: {VisitPurpose.parking},
    AssetType.storage_garage: {VisitPurpose.storage_access},
    AssetType.apartment_unit: {
        VisitPurpose.short_term_stay,
        VisitPurpose.viewing,
        VisitPurpose.maintenance,
        VisitPurpose.emergency_access,
    },
    AssetType.apartment_room: {
        VisitPurpose.short_term_stay,
        VisitPurpose.viewing,
        VisitPurpose.maintenance,
    },
    AssetType.apartment_common_area: {
        VisitPurpose.viewing,
        VisitPurpose.maintenance,
        VisitPurpose.pickup_dropoff,
    },
}

HARD_DENIAL_REASONS: Set[str] = {
    "host_identity_not_verified",
    "guest_identity_not_verified",
    "host_banned",
    "guest_banned",
    "asset_address_not_verified",
    "asset_owner_not_authorized",
    "asset_not_insurable",
    "coverage_limit_below_minimum",
    "host_approval_missing",
    "payment_not_authorized",
    "emergency_contact_missing",
    "visit_purpose_not_allowed_for_asset_type",
}


def evaluate_risk(asset: Asset, host: Party, guest: Party, visit: Visit) -> Tuple[int, List[str], bool]:
    score = 0
    reasons: List[str] = []

    if visit.duration_minutes <= 0:
        reasons.append("invalid_visit_duration")
        score += 100

    try:
        asset_type = AssetType(asset.asset_type)
        purpose = VisitPurpose(visit.purpose)
    except ValueError:
        reasons.append("unknown_asset_or_purpose")
        score += 100
    else:
        allowed_purposes = ASSET_PURPOSE_MATRIX.get(asset_type)
        if allowed_purposes and purpose not in allowed_purposes:
            reasons.append("visit_purpose_not_allowed_for_asset_type")
            score += 50

        if asset_type == AssetType.bathroom and visit.duration_minutes > settings.max_bathroom_access_minutes:
            reasons.append("bathroom_visit_too_long")
            score += 35
        if asset_type in {AssetType.private_garage, AssetType.shared_garage, AssetType.parking_garage, AssetType.storage_garage} and visit.duration_minutes > settings.max_garage_access_minutes:
            reasons.append("garage_visit_too_long")
            score += 25
        if asset_type == AssetType.tool and visit.duration_minutes > settings.max_tool_rental_minutes:
            reasons.append("tool_rental_too_long")
            score += 25
        if asset_type == AssetType.workspace and visit.duration_minutes > settings.max_workspace_minutes:
            reasons.append("workspace_visit_too_long")
            score += 20
        if purpose == VisitPurpose.pickup_dropoff and visit.duration_minutes > settings.max_pickup_dropoff_minutes:
            reasons.append("pickup_dropoff_visit_too_long")
            score += 20

    if not host.identity_verified:
        reasons.append("host_identity_not_verified")
        score += 100
    if not guest.identity_verified:
        reasons.append("guest_identity_not_verified")
        score += 100
    if host.banned:
        reasons.append("host_banned")
        score += 100
    if guest.banned:
        reasons.append("guest_banned")
        score += 100
    if not asset.address_verified:
        reasons.append("asset_address_not_verified")
        score += 100
    if not asset.owner_authorized:
        reasons.append("asset_owner_not_authorized")
        score += 100
    if not asset.insurable:
        reasons.append("asset_not_insurable")
        score += 100
    if visit.requested_coverage_limit_cents < settings.min_coverage_limit_cents:
        reasons.append("coverage_limit_below_minimum")
        score += 100
    if not visit.host_approval:
        reasons.append("host_approval_missing")
        score += 100
    if not visit.payment_authorized:
        reasons.append("payment_not_authorized")
        score += 100
    if not visit.emergency_contact_available:
        reasons.append("emergency_contact_missing")
        score += 50
    if host.risk_score > 70:
        reasons.append("host_risk_score_too_high")
        score += 50
    if guest.risk_score > 70:
        reasons.append("guest_risk_score_too_high")
        score += 50

    if AssetType(asset.asset_type) in {AssetType.bathroom, AssetType.apartment_unit, AssetType.apartment_room} and not visit.host_present:
        reasons.append("host_presence_required_for_private_asset")
        score += 40
    if AssetType(asset.asset_type) in {AssetType.private_garage, AssetType.shared_garage, AssetType.storage_garage} and not visit.security_deposit_authorized:
        reasons.append("security_deposit_required_for_garage_or_storage")
        score += 25

    hard_denied = any(reason in HARD_DENIAL_REASONS for reason in reasons)
    approved = not hard_denied and score <= 70
    return min(score, 100), reasons, approved
