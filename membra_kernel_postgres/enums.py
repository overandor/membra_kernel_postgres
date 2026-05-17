from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    admin = "admin"
    ops = "ops"
    insurance = "insurance"
    claims = "claims"
    scanner = "scanner"
    readonly = "readonly"


class PartyType(str, Enum):
    host = "host"
    guest = "guest"
    property_manager = "property_manager"
    owner = "owner"
    delivery_hero = "delivery_hero"
    service_hero = "service_hero"


class AssetType(str, Enum):
    apartment_unit = "apartment_unit"
    apartment_room = "apartment_room"
    apartment_common_area = "apartment_common_area"
    private_garage = "private_garage"
    shared_garage = "shared_garage"
    parking_garage = "parking_garage"
    storage_garage = "storage_garage"
    bathroom = "bathroom"
    parking_spot = "parking_spot"
    storage_shelf = "storage_shelf"
    tool = "tool"
    ev_charger = "ev_charger"
    workspace = "workspace"
    wifi_access = "wifi_access"
    seating = "seating"
    laundry = "laundry"
    printer = "printer"
    pickup_dropoff = "pickup_dropoff"


class VisitPurpose(str, Enum):
    bathroom_access = "bathroom_access"
    short_term_stay = "short_term_stay"
    storage_access = "storage_access"
    parking = "parking"
    maintenance = "maintenance"
    viewing = "viewing"
    pickup_dropoff = "pickup_dropoff"
    emergency_access = "emergency_access"
    tool_rental = "tool_rental"
    ev_charging = "ev_charging"
    workspace_access = "workspace_access"
    wifi_access = "wifi_access"
    laundry = "laundry"
    printing = "printing"
    seating = "seating"


class CoverageStatus(str, Enum):
    draft = "draft"
    quoted = "quoted"
    payment_authorized = "payment_authorized"
    active = "active"
    expired = "expired"
    claimable = "claimable"
    denied = "denied"
    cancelled = "cancelled"
    failed = "failed"


class VisitStatus(str, Enum):
    requested = "requested"
    risk_approved = "risk_approved"
    risk_denied = "risk_denied"
    coverage_quoted = "coverage_quoted"
    covered = "covered"
    access_issued = "access_issued"
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class ClaimStatus(str, Enum):
    opened = "opened"
    submitted_to_provider = "submitted_to_provider"
    under_review = "under_review"
    approved = "approved"
    denied = "denied"
    closed = "closed"
