# Membra Permission + Coverage Kernel — Postgres Edition

This is the Postgres production skeleton for Membra's access/insurance control plane.

Core invariant:

```text
risk → quote → bind → signed QR → backend verification → access
```

And the hard product rule:

```text
No identity
→ no payment
→ no risk approval
→ no bound insurance
→ no signed QR
→ no backend verification
→ no access
```

## What this version changes from the SQLite demo

- Uses Postgres through SQLAlchemy + psycopg.
- Includes Alembic migrations.
- Uses row locks for bind/quote critical sections via `SELECT ... FOR UPDATE`.
- Stores idempotency responses in Postgres.
- Uses partial unique indexes for provider quote and policy IDs.
- Uses a unique token hash index for QR/access tokens.
- Uses JSONB for rules, covered events, token payloads, audit payloads, and idempotency responses.
- Removes spoofable role headers. Role is derived server-side from the API key.

## Install

```bash
pip install -r requirements.txt
```

## Environment

Copy `.env.example` to `.env` and set real secrets.

Required production variables:

```bash
export DATABASE_URL='postgresql+psycopg://membra_user:membra_pass@localhost:5432/membra'
export MEMBRA_ADMIN_KEY='admin-secret'
export MEMBRA_OPS_KEY='ops-secret'
export MEMBRA_INSURANCE_KEY='insurance-secret'
export MEMBRA_CLAIMS_KEY='claims-secret'
export MEMBRA_SCANNER_KEY='scanner-secret'
export MEMBRA_READONLY_KEY='readonly-secret'
export MEMBRA_DATA_ENCRYPTION_KEY='separate-data-encryption-secret'
export ACCESS_SIGNING_SECRET='separate-access-signing-secret'
```

Insurance still fails closed unless a real licensed partner is configured:

```bash
export INSURANCE_PROVIDER_NAME='your_licensed_partner'
export INSURANCE_API_KEY='partner-api-key'
export INSURANCE_QUOTE_URL='https://partner.example.com/quote'
export INSURANCE_BIND_URL='https://partner.example.com/bind'
export INSURANCE_CLAIM_URL='https://partner.example.com/claims'
```

## Migrations

```bash
alembic upgrade head
```

For local throwaway development only:

```bash
export AUTO_CREATE_TABLES=true
```

## Run

```bash
uvicorn app:app --host 0.0.0.0 --port 7860
```

## Docker

```bash
cp .env.example .env
# edit .env

docker compose up --build
```

## Key endpoints

```text
GET  /health
POST /v1/parties
GET  /v1/parties/{party_id}
GET  /v1/parties/{party_id}/public
POST /v1/assets
GET  /v1/assets/{asset_id}
GET  /v1/assets/{asset_id}/public
POST /v1/visits
POST /v1/visits/{visit_id}/risk
POST /v1/insurance/quote
POST /v1/insurance/bind
POST /v1/access/{visit_id}/qr
POST /v1/access/verify
POST /v1/claims
POST /v1/webhooks/insurance/{provider_name}
GET  /v1/audit/{entity_type}/{entity_id}
GET  /v1/provider/capabilities
```

## Protocol specifications

- `docs/mips/mip-007-membra-network-foundry.md` defines MEMBRA Network Foundry, File-Backed Networks, and the Solana proof-bridge-first design.

## Security controls included

- Server-side API-key-to-role mapping.
- No `X-Membra-Role` header.
- Asset-purpose compatibility matrix.
- Quote expiration checks before bind.
- Coverage-window validation before bind and before QR issue.
- Signed QR wrapper with `typ=MEMBRA_ACCESS_V1` and `alg=HS256` enforcement.
- QR audience validation.
- QR asset-to-visit consistency validation.
- Webhook-triggered QR revocation on coverage cancellation, denial, or failure.
- Claim fraud checks: claimant must belong to visit, incident type must be covered, incident time must be inside coverage window, coverage must have policy ID.
- Sensitive fields encrypted at rest.
- Audit payload redaction.
- Public DTOs do not reveal legal names, emails, phones, or verified addresses.

## Production notes

This code is an application control plane. It is not an insurance carrier, producer, broker, or legal compliance system. Bind/quote/claim operations must be handled through properly licensed insurance partners and reviewed by insurance counsel before production launch.
