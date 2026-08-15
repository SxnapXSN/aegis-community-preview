# Community Preview Scope

## Purpose

Offer a small educational tool that turns a validated task envelope into a
conservative execution brief without connecting to external services.

## Public Allow-List

- `aegis_community/`
- `docs/`
- `examples/`
- `tests/`
- `scripts/verify_preview_boundary.py`
- Preview-specific documentation, Apache-2.0 license, and CI configuration in
  this directory.

## Explicit Exclusions

- Any module or artifact from the private `Aegis Stable/TEST1` working tree.
- Runtime storage, logs, snapshots, telemetry, provider integrations, model
  configuration, license material, and internal operational documents.
- Credentials, certificates, secrets, `.env` files, and customer data.

## Safety Model

The preview only evaluates a JSON document. It does not execute task actions.
Tasks marked `high` always require human review and expose no enabled actions.
