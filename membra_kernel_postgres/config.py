from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = "Membra Permission + Coverage Kernel"
    app_version: str = "2.2.0-postgres"

    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://membra_user:membra_pass@localhost:5432/membra",
    )
    auto_create_tables: bool = os.getenv("AUTO_CREATE_TABLES", "false").lower() == "true"

    platform_api_key: str = os.getenv("PLATFORM_API_KEY", "")
    membra_data_encryption_key: str = os.getenv("MEMBRA_DATA_ENCRYPTION_KEY", "")
    access_signing_secret: str = os.getenv("ACCESS_SIGNING_SECRET", "") or os.getenv("PLATFORM_API_KEY", "")
    webhook_secret: str = os.getenv("WEBHOOK_SECRET", "")
    allow_plaintext_pii: bool = os.getenv("MEMBRA_ALLOW_PLAINTEXT_PII", "false").lower() == "true"

    insurance_provider_name: str = os.getenv("INSURANCE_PROVIDER_NAME", "unconfigured")
    insurance_api_key: str = os.getenv("INSURANCE_API_KEY", "")
    insurance_quote_url: str = os.getenv("INSURANCE_QUOTE_URL", "")
    insurance_bind_url: str = os.getenv("INSURANCE_BIND_URL", "")
    insurance_claim_url: str = os.getenv("INSURANCE_CLAIM_URL", "")
    insurance_timeout_seconds: float = float(os.getenv("INSURANCE_TIMEOUT_SECONDS", "12"))

    min_coverage_limit_cents: int = int(os.getenv("MIN_COVERAGE_LIMIT_CENTS", "10000000"))
    default_deductible_cents: int = int(os.getenv("DEFAULT_DEDUCTIBLE_CENTS", "25000"))
    max_private_apartment_minutes: int = int(os.getenv("MAX_PRIVATE_APARTMENT_MINUTES", "240"))
    max_bathroom_access_minutes: int = int(os.getenv("MAX_BATHROOM_ACCESS_MINUTES", "30"))
    max_garage_access_minutes: int = int(os.getenv("MAX_GARAGE_ACCESS_MINUTES", "1440"))
    max_tool_rental_minutes: int = int(os.getenv("MAX_TOOL_RENTAL_MINUTES", "1440"))
    max_workspace_minutes: int = int(os.getenv("MAX_WORKSPACE_MINUTES", "720"))
    max_pickup_dropoff_minutes: int = int(os.getenv("MAX_PICKUP_DROPOFF_MINUTES", "60"))
    token_leeway_seconds: int = int(os.getenv("TOKEN_LEEWAY_SECONDS", "60"))


settings = Settings()
