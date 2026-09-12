# Community Scope

## Purpose

Community is the public, privacy-safe Aegis surface. It provides a real local
contract, AI discovery, conservative planning, and a high-quality approved MD
workflow without publishing the private Stable engine.

## Public Allow-List

- `aegis_community/`
- `docs/`
- `examples/`
- `tests/`
- `scripts/`
- Preview-specific documentation, Apache-2.0 license, and CI configuration.

## Allowed Public Behavior

- Local JSON task validation.
- Public manifest, capability discovery, system map, and preflight.
- Local stdio MCP responses.
- Plan-only task and MD workflows.
- Local multi-format document-to-Markdown conversion for supported text,
  structured data, Office Open XML, PDF, and image inputs.
- AI context packs with summaries, chunks, source hashes, redaction, and
  read-back checks.
- Explicit bounded folder scans for repeatable local ingestion.
- Privacy-safe per-run evidence.
- Approved local MD generation through an adapter, with artifact read-back.
- Adapter contracts that do not bundle upstream model code or weights.

## Explicit Exclusions

- Private Stable source, policies, runtime artifacts, and operational data.
- Model weights, model caches, customer data, logs, telemetry, and snapshots.
- Credentials, certificates, environment files, or license material from a
  private runtime.
- IP addresses, local host names, machine-specific paths, and private
  endpoints in public documentation or generated output.
- Autonomous arbitrary execution, unbounded background daemons, private
  provider routing, or hidden connectors.

## Safety Model

Community validates and plans. It does not execute arbitrary task actions.
High-risk tasks always require human review and expose no enabled actions.
The MCP MD and document surfaces prepare plans first. The CLI or MCP may run a
bounded local adapter or document write only after explicit approval and
returns logical artifact summaries after validation and read-back.

## Release Rule

Every release must pass the unit suite and the boundary checker. A passing
local test is not a claim of full Stable or MD end-to-end readiness; those
claims require a separate real-client and backend test record.
