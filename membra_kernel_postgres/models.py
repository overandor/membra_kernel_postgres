from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Party(Base):
    __tablename__ = "parties"

    party_id = Column(String, primary_key=True)
    party_type = Column(String, nullable=False, index=True)
    legal_name_enc = Column(Text, nullable=True)
    email_enc = Column(Text, nullable=True)
    phone_enc = Column(Text, nullable=True)
    identity_verified = Column(Boolean, nullable=False, default=False)
    risk_score = Column(Integer, nullable=False, default=0)
    banned = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class Asset(Base):
    __tablename__ = "assets"

    asset_id = Column(String, primary_key=True)
    owner_party_id = Column(String, ForeignKey("parties.party_id"), nullable=False, index=True)
    asset_type = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    verified_address_enc = Column(Text, nullable=True)
    address_verified = Column(Boolean, nullable=False, default=False)
    owner_authorized = Column(Boolean, nullable=False, default=False)
    insurable = Column(Boolean, nullable=False, default=False)
    rules = Column(JSONB, nullable=False, default=dict)
    trust_badges = Column(JSONB, nullable=False, default=list)
    price_cents = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    owner = relationship("Party")


class Visit(Base):
    __tablename__ = "visits"

    visit_id = Column(String, primary_key=True)
    asset_id = Column(String, ForeignKey("assets.asset_id"), nullable=False, index=True)
    host_id = Column(String, ForeignKey("parties.party_id"), nullable=False, index=True)
    guest_id = Column(String, ForeignKey("parties.party_id"), nullable=False, index=True)
    purpose = Column(String, nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False, index=True)
    duration_minutes = Column(Integer, nullable=False)
    requested_coverage_limit_cents = Column(Integer, nullable=False)
    requested_deductible_cents = Column(Integer, nullable=False)
    covered_events = Column(JSONB, nullable=False, default=list)
    payment_authorized = Column(Boolean, nullable=False, default=False)
    security_deposit_authorized = Column(Boolean, nullable=False, default=False)
    host_approval = Column(Boolean, nullable=False, default=False)
    host_present = Column(Boolean, nullable=False, default=False)
    emergency_contact_available = Column(Boolean, nullable=False, default=False)
    status = Column(String, nullable=False, default="requested", index=True)
    risk_score = Column(Integer, nullable=True)
    risk_reasons = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    asset = relationship("Asset")
    host = relationship("Party", foreign_keys=[host_id])
    guest = relationship("Party", foreign_keys=[guest_id])


class Coverage(Base):
    __tablename__ = "coverages"

    coverage_id = Column(String, primary_key=True)
    visit_id = Column(String, ForeignKey("visits.visit_id"), nullable=False, index=True)
    provider = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="draft", index=True)
    external_quote_id = Column(String, nullable=True)
    external_policy_id = Column(String, nullable=True)
    premium_cents = Column(Integer, nullable=True)
    coverage_limit_cents = Column(Integer, nullable=False)
    deductible_cents = Column(Integer, nullable=False)
    quote_expires_at = Column(DateTime(timezone=True), nullable=True)
    coverage_start = Column(DateTime(timezone=True), nullable=True)
    coverage_end = Column(DateTime(timezone=True), nullable=True)
    partner_raw_json_enc = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    visit = relationship("Visit")

    __table_args__ = (
        Index(
            "idx_coverages_provider_quote",
            "provider",
            "external_quote_id",
            unique=True,
            postgresql_where=text("external_quote_id IS NOT NULL"),
        ),
        Index(
            "idx_coverages_provider_policy",
            "provider",
            "external_policy_id",
            unique=True,
            postgresql_where=text("external_policy_id IS NOT NULL"),
        ),
    )


class AccessToken(Base):
    __tablename__ = "access_tokens"

    access_token_id = Column(String, primary_key=True)
    visit_id = Column(String, ForeignKey("visits.visit_id"), nullable=False, index=True)
    coverage_id = Column(String, ForeignKey("coverages.coverage_id"), nullable=False, index=True)
    asset_id = Column(String, ForeignKey("assets.asset_id"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True)
    token_payload = Column(JSONB, nullable=False, default=dict)
    issued_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, nullable=False, default=False, index=True)
    revoked_reason = Column(String, nullable=True)


class Claim(Base):
    __tablename__ = "claims"

    claim_id = Column(String, primary_key=True)
    visit_id = Column(String, ForeignKey("visits.visit_id"), nullable=False, index=True)
    coverage_id = Column(String, ForeignKey("coverages.coverage_id"), nullable=False, index=True)
    claimant_party_id = Column(String, ForeignKey("parties.party_id"), nullable=False, index=True)
    incident_type = Column(String, nullable=False, index=True)
    incident_time = Column(DateTime(timezone=True), nullable=False)
    description_enc = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="opened", index=True)
    external_claim_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    audit_id = Column(String, primary_key=True)
    entity_type = Column(String, nullable=False, index=True)
    entity_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    actor_role = Column(String, nullable=True)
    payload_json = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)


class FolderShare(Base):
    __tablename__ = "folder_shares"

    share_id = Column(String, primary_key=True)
    owner_wallet = Column(String, nullable=False, index=True)
    folder_name = Column(String, nullable=False)
    folder_path = Column(Text, nullable=False)
    visibility = Column(String, nullable=False, default="public", index=True)
    download_allowed = Column(Boolean, nullable=False, default=True)
    index_enabled = Column(Boolean, nullable=False, default=True)
    proof_manifest_enabled = Column(Boolean, nullable=False, default=True)
    qr_enabled = Column(Boolean, nullable=False, default=True)
    revoked = Column(Boolean, nullable=False, default=False, index=True)
    revoked_reason = Column(String, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    manifest_json = Column(JSONB, nullable=False, default=dict)
    blocked_files_json = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    key = Column(String, primary_key=True)
    endpoint = Column(String, nullable=False, index=True)
    response_json = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
