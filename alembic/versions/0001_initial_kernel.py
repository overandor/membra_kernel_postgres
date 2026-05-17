"""initial Membra Postgres kernel

Revision ID: 0001_initial_kernel
Revises:
Create Date: 2026-05-12
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_kernel"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "parties",
        sa.Column("party_id", sa.String(), primary_key=True),
        sa.Column("party_type", sa.String(), nullable=False),
        sa.Column("legal_name_enc", sa.Text(), nullable=True),
        sa.Column("email_enc", sa.Text(), nullable=True),
        sa.Column("phone_enc", sa.Text(), nullable=True),
        sa.Column("identity_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("risk_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("banned", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_parties_party_type", "parties", ["party_type"])

    op.create_table(
        "assets",
        sa.Column("asset_id", sa.String(), primary_key=True),
        sa.Column("owner_party_id", sa.String(), sa.ForeignKey("parties.party_id"), nullable=False),
        sa.Column("asset_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("verified_address_enc", sa.Text(), nullable=True),
        sa.Column("address_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("owner_authorized", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("insurable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("trust_badges", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("price_cents", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_assets_owner_party_id", "assets", ["owner_party_id"])
    op.create_index("ix_assets_asset_type", "assets", ["asset_type"])

    op.create_table(
        "visits",
        sa.Column("visit_id", sa.String(), primary_key=True),
        sa.Column("asset_id", sa.String(), sa.ForeignKey("assets.asset_id"), nullable=False),
        sa.Column("host_id", sa.String(), sa.ForeignKey("parties.party_id"), nullable=False),
        sa.Column("guest_id", sa.String(), sa.ForeignKey("parties.party_id"), nullable=False),
        sa.Column("purpose", sa.String(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("requested_coverage_limit_cents", sa.Integer(), nullable=False),
        sa.Column("requested_deductible_cents", sa.Integer(), nullable=False),
        sa.Column("covered_events", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("payment_authorized", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("security_deposit_authorized", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("host_approval", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("host_present", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("emergency_contact_available", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(), nullable=False, server_default="requested"),
        sa.Column("risk_score", sa.Integer(), nullable=True),
        sa.Column("risk_reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_visits_asset_id", "visits", ["asset_id"])
    op.create_index("ix_visits_host_id", "visits", ["host_id"])
    op.create_index("ix_visits_guest_id", "visits", ["guest_id"])
    op.create_index("ix_visits_status", "visits", ["status"])
    op.create_index("ix_visits_purpose", "visits", ["purpose"])
    op.create_index("ix_visits_start_time", "visits", ["start_time"])
    op.create_index("ix_visits_end_time", "visits", ["end_time"])

    op.create_table(
        "coverages",
        sa.Column("coverage_id", sa.String(), primary_key=True),
        sa.Column("visit_id", sa.String(), sa.ForeignKey("visits.visit_id"), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("external_quote_id", sa.String(), nullable=True),
        sa.Column("external_policy_id", sa.String(), nullable=True),
        sa.Column("premium_cents", sa.Integer(), nullable=True),
        sa.Column("coverage_limit_cents", sa.Integer(), nullable=False),
        sa.Column("deductible_cents", sa.Integer(), nullable=False),
        sa.Column("quote_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("coverage_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("coverage_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("partner_raw_json_enc", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_coverages_visit_id", "coverages", ["visit_id"])
    op.create_index("ix_coverages_provider", "coverages", ["provider"])
    op.create_index("ix_coverages_status", "coverages", ["status"])
    op.create_index("idx_coverages_provider_quote", "coverages", ["provider", "external_quote_id"], unique=True, postgresql_where=sa.text("external_quote_id IS NOT NULL"))
    op.create_index("idx_coverages_provider_policy", "coverages", ["provider", "external_policy_id"], unique=True, postgresql_where=sa.text("external_policy_id IS NOT NULL"))

    op.create_table(
        "access_tokens",
        sa.Column("access_token_id", sa.String(), primary_key=True),
        sa.Column("visit_id", sa.String(), sa.ForeignKey("visits.visit_id"), nullable=False),
        sa.Column("coverage_id", sa.String(), sa.ForeignKey("coverages.coverage_id"), nullable=False),
        sa.Column("asset_id", sa.String(), sa.ForeignKey("assets.asset_id"), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False, unique=True),
        sa.Column("token_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("revoked_reason", sa.String(), nullable=True),
    )
    op.create_index("ix_access_tokens_visit_id", "access_tokens", ["visit_id"])
    op.create_index("ix_access_tokens_coverage_id", "access_tokens", ["coverage_id"])
    op.create_index("ix_access_tokens_asset_id", "access_tokens", ["asset_id"])
    op.create_index("ix_access_tokens_revoked", "access_tokens", ["revoked"])
    op.create_index("idx_access_tokens_hash", "access_tokens", ["token_hash"], unique=True)

    op.create_table(
        "claims",
        sa.Column("claim_id", sa.String(), primary_key=True),
        sa.Column("visit_id", sa.String(), sa.ForeignKey("visits.visit_id"), nullable=False),
        sa.Column("coverage_id", sa.String(), sa.ForeignKey("coverages.coverage_id"), nullable=False),
        sa.Column("claimant_party_id", sa.String(), sa.ForeignKey("parties.party_id"), nullable=False),
        sa.Column("incident_type", sa.String(), nullable=False),
        sa.Column("incident_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description_enc", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="opened"),
        sa.Column("external_claim_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_claims_visit_id", "claims", ["visit_id"])
    op.create_index("ix_claims_coverage_id", "claims", ["coverage_id"])
    op.create_index("ix_claims_claimant_party_id", "claims", ["claimant_party_id"])
    op.create_index("ix_claims_incident_type", "claims", ["incident_type"])
    op.create_index("ix_claims_status", "claims", ["status"])
    op.create_index("ix_claims_external_claim_id", "claims", ["external_claim_id"])

    op.create_table(
        "audit_events",
        sa.Column("audit_id", sa.String(), primary_key=True),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("actor_role", sa.String(), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_entity_type", "audit_events", ["entity_type"])
    op.create_index("ix_audit_events_entity_id", "audit_events", ["entity_id"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])

    op.create_table(
        "idempotency_keys",
        sa.Column("key", sa.String(), primary_key=True),
        sa.Column("endpoint", sa.String(), nullable=False),
        sa.Column("response_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_idempotency_keys_endpoint", "idempotency_keys", ["endpoint"])


def downgrade() -> None:
    op.drop_table("idempotency_keys")
    op.drop_table("audit_events")
    op.drop_table("claims")
    op.drop_table("access_tokens")
    op.drop_table("coverages")
    op.drop_table("visits")
    op.drop_table("assets")
    op.drop_table("parties")
