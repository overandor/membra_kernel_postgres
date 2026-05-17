from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .config import settings
from .enums import AssetType, ClaimStatus, CoverageStatus, PartyType, VisitPurpose, VisitStatus
from .utils import minutes_between, parse_dt


class PartyCreate(BaseModel):
    party_type: PartyType
    legal_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    identity_verified: bool = False
    risk_score: int = Field(default=0, ge=0, le=100)
    banned: bool = False


class PartyInternal(BaseModel):
    party_id: str
    party_type: PartyType
    legal_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    identity_verified: bool
    risk_score: int
    banned: bool
    created_at: datetime


class PartyPublic(BaseModel):
    party_id: str
    party_type: PartyType
    identity_verified: bool
    trust_badges: List[str] = []


class AssetCreate(BaseModel):
    owner_party_id: str
    asset_type: AssetType
    title: str
    description: Optional[str] = None
    verified_address: str
    address_verified: bool = False
    owner_authorized: bool = False
    insurable: bool = False
    rules: Dict[str, Any] = Field(default_factory=dict)
    trust_badges: List[str] = Field(default_factory=list)
    price_cents: Optional[int] = Field(default=None, ge=0)


class AssetInternal(BaseModel):
    asset_id: str
    owner_party_id: str
    asset_type: AssetType
    title: str
    description: Optional[str]
    verified_address: Optional[str]
    address_verified: bool
    owner_authorized: bool
    insurable: bool
    rules: Dict[str, Any]
    trust_badges: List[str]
    price_cents: Optional[int]
    created_at: datetime


class AssetPublic(BaseModel):
    asset_id: str
    asset_type: AssetType
    title: str
    description: Optional[str]
    rules: Dict[str, Any]
    trust_badges: List[str]
    price_cents: Optional[int]


class VisitCreate(BaseModel):
    asset_id: str
    host_id: str
    guest_id: str
    purpose: VisitPurpose
    start_time: datetime
    end_time: datetime
    requested_coverage_limit_cents: int = Field(default_factory=lambda: settings.min_coverage_limit_cents, ge=1)
    requested_deductible_cents: int = Field(default_factory=lambda: settings.default_deductible_cents, ge=0)
    covered_events: List[str] = Field(default_factory=lambda: [
        "property_damage",
        "personal_injury",
        "theft",
        "host_liability",
        "guest_liability",
        "accidental_damage",
        "emergency_incident",
    ])
    payment_authorized: bool = False
    security_deposit_authorized: bool = False
    host_approval: bool = False
    host_present: bool = False
    emergency_contact_available: bool = False

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, end_time: datetime, info: Any) -> datetime:
        start_time = info.data.get("start_time")
        if start_time and parse_dt(end_time) <= parse_dt(start_time):
            raise ValueError("end_time must be after start_time")
        return end_time


class VisitOut(BaseModel):
    visit_id: str
    asset_id: str
    host_id: str
    guest_id: str
    purpose: VisitPurpose
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    requested_coverage_limit_cents: int
    requested_deductible_cents: int
    covered_events: List[str]
    payment_authorized: bool
    security_deposit_authorized: bool
    host_approval: bool
    host_present: bool
    emergency_contact_available: bool
    status: VisitStatus
    risk_score: Optional[int]
    risk_reasons: List[str]


class RiskResult(BaseModel):
    visit_id: str
    approved: bool
    risk_score: int
    reasons: List[str]
    status: VisitStatus


class CoverageQuoteRequest(BaseModel):
    visit_id: str


class CoverageBindRequest(BaseModel):
    coverage_id: str


class CoverageOut(BaseModel):
    coverage_id: str
    visit_id: str
    provider: str
    status: CoverageStatus
    external_quote_id: Optional[str]
    external_policy_id: Optional[str]
    premium_cents: Optional[int]
    coverage_limit_cents: int
    deductible_cents: int
    quote_expires_at: Optional[datetime]
    coverage_start: Optional[datetime]
    coverage_end: Optional[datetime]


class AccessTokenOut(BaseModel):
    access_token_id: str
    visit_id: str
    coverage_id: str
    asset_id: str
    signed_qr_payload: str
    expires_at: datetime


class AccessVerifyRequest(BaseModel):
    signed_qr_payload: str


class AccessVerifyResponse(BaseModel):
    access_allowed: bool
    reason: str
    visit_id: Optional[str] = None
    coverage_id: Optional[str] = None
    asset_id: Optional[str] = None


class ClaimCreate(BaseModel):
    visit_id: str
    coverage_id: str
    claimant_party_id: str
    incident_type: str
    incident_time: datetime
    description: str


class ClaimOut(BaseModel):
    claim_id: str
    visit_id: str
    coverage_id: str
    claimant_party_id: str
    incident_type: str
    incident_time: datetime
    description: Optional[str]
    status: ClaimStatus
    external_claim_id: Optional[str]
    created_at: datetime


class WebhookPayload(BaseModel):
    coverage_id: Optional[str] = None
    external_quote_id: Optional[str] = None
    external_policy_id: Optional[str] = None
    status: CoverageStatus
    external_claim_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    app: str
    version: str
    database: str
    insurance_provider: str
    status: str = "ok"
