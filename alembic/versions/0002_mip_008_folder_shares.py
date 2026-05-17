"""add MIP-008 folder shares

Revision ID: 0002_mip_008_folder_shares
Revises: 0001_initial_kernel
Create Date: 2026-05-17
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_mip_008_folder_shares"
down_revision: Union[str, None] = "0001_initial_kernel"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "folder_shares",
        sa.Column("share_id", sa.String(), primary_key=True),
        sa.Column("owner_wallet", sa.String(), nullable=False),
        sa.Column("folder_name", sa.String(), nullable=False),
        sa.Column("folder_path", sa.Text(), nullable=False),
        sa.Column("visibility", sa.String(), nullable=False, server_default="public"),
        sa.Column("download_allowed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("index_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("proof_manifest_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("qr_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("revoked_reason", sa.String(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("manifest_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("blocked_files_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_folder_shares_owner_wallet", "folder_shares", ["owner_wallet"])
    op.create_index("ix_folder_shares_visibility", "folder_shares", ["visibility"])
    op.create_index("ix_folder_shares_revoked", "folder_shares", ["revoked"])
    op.create_index("ix_folder_shares_expires_at", "folder_shares", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_folder_shares_expires_at", table_name="folder_shares")
    op.drop_index("ix_folder_shares_revoked", table_name="folder_shares")
    op.drop_index("ix_folder_shares_visibility", table_name="folder_shares")
    op.drop_index("ix_folder_shares_owner_wallet", table_name="folder_shares")
    op.drop_table("folder_shares")
