# Public Architecture

Community is designed as a small public edge around a private product. The
public edge is useful on its own and gives an AI client enough context to use
it correctly without revealing private implementation details.

```text
AI client
   |
   v
Local Bootstrap and MCP Bridge
   |
   v
Public Manifest and Capability Gateway
   |--------------------|
   v                    v
Safe Planner          Approved MD Adapter
   |
   |------------------------|
   v                        v
Document Pipeline      Privacy-safe Evidence
   |
   v
AI Context Pack
```

## Discovery First

The first interaction is a contract handshake. The client reads the public
manifest, capabilities, system map, and preflight result before planning a
task. Unknown capabilities fail closed instead of being guessed.

## Public Context

The system map describes public roles and relationships. It does not return
private module names, local installation details, machine identifiers,
addresses, credentials, or internal operational data.

## Execution Boundary

The Community planner validates input and produces a plan. It never treats a
label in `allowed_actions` as executable code. High-risk work exposes no
enabled actions and requires human review.

## MD Boundary

MD is an adapter contract. A separate local backend may implement the public
request and response shape. Community does not copy its source, weights,
cache, or license material into this repository. MCP exposes planning only;
the local CLI runs an adapter only after explicit approval, validates the
artifact header, and compares the final file hash after saving it.

## Private Core

The Stable control plane remains private. Community communicates its public
limits rather than attempting to mirror or describe the private engine.

## Document Boundary

The document pipeline is a separate public capability. It reads supported
local text, structured data, modern Office Open XML, PDF, and image inputs and
writes three bounded artifacts: Markdown content, a compact summary, and a
source-hash manifest. Office parsing uses the local XML package structure.
PDF text uses a local reader when available and a small built-in fallback.
Image OCR is an optional local adapter and is never silently assumed to exist.

The context-pack layer combines those artifacts into `context.md`, a manifest,
and finite chunks sized for an AI context window. Redaction is on by default,
and output results contain logical names and hashes rather than machine paths.
Conversion and packaging are explicit approved local writes; planning remains
non-executing.
