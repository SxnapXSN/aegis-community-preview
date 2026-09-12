# Aegis Community

> A privacy-first local MCP bridge that lets an AI client understand the
> public Aegis contract before it plans a task.

Aegis Community is the public, high-capability surface of Aegis. It is small
enough to inspect, safe enough to run locally, and explicit about its limits.
It does not expose or bundle the private Stable engine.

## What Makes It Useful

- One local install for the public CLI and MCP bridge.
- A machine-readable manifest that AI clients read before using tools.
- A conservative task planner with human approval for high-risk work.
- A universal local document-to-Markdown pipeline for text, structured data,
  DOCX, PPTX, XLSX, ODT, ODP, ODS, EPUB, RTF, PDF, and image metadata.
- Redacted, chunked AI context packs with source hashes, freshness signals,
  and read-back evidence.
- A bounded folder scan mode that never leaves an unbounded background daemon.
- A high-quality MD image-to-3D workflow through a separately installed local
  adapter, with artifact read-back and explicit approval before generation.
- Privacy-safe output: no machine paths, network addresses, credentials, or
  telemetry are returned by the public contract.

## Quick Start

Python 3.10 or newer is required. The core package uses only the Python
standard library.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1
aegis-community preflight
aegis-community manifest
aegis-community documents
```

When Codex or Claude CLI is installed, connect the available clients with a
single opt-in command. Existing client settings are backed up first:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1 -ConnectClients
```

Run the included safe task plan:

```powershell
aegis-community run --input examples/sample_task.json --format pretty
```

Convert a local document set into AI-readable Markdown:

```powershell
aegis-community documents-plan --path input/report.docx --path input/data.xlsx
aegis-community documents-convert --folder input --output-dir output/markdown --approve
aegis-community context-pack --folder input --output-dir output/context --approve
```

The converter writes Markdown, compact summaries, manifests, and bounded
context chunks. Redaction is enabled by default; scanned images and scanned
PDF pages can use an explicitly configured local OCR adapter. See
[Document Integration](docs/DOCUMENT_INTEGRATION.md).

Run the public MD capability check and plan:

```powershell
aegis-community md
aegis-community md-plan --input examples/md_request.json --format pretty
```

To generate from a local image, choose the destination yourself and approve
the run explicitly:

```powershell
aegis-community md-run --input examples/md_request.json --image $image --output $output --approve
```

`$image` and `$output` are local PowerShell variables chosen by the user. The
command reports a logical artifact name, byte count, hash, and read-back state;
it does not print the machine paths.

## Connect An MCP Client

The bridge uses local stdio and makes no network request. Use the portable
example in `examples/mcp-client-config.json` where the client supports MCP
configuration import, or register the same module command in the client's
MCP settings.

After connection, the client should call these tools in order:

1. `aegis_manifest`
2. `aegis_capabilities`
3. `aegis_system_map`
4. `aegis_preflight`

Only then should it call `aegis_plan_task`, `aegis_document_plan`, or
`aegis_md_plan`.

## Public Surface

| Capability | Community behavior |
| --- | --- |
| Architecture context | Public system map and capability descriptions |
| Task planning | Local validation and plan-only execution briefs |
| Safety | High-risk tasks require human review |
| Documents | Local multi-format conversion into Markdown artifacts |
| Context | Redacted summaries, chunks, hashes, and read-back checks |
| MD | High-quality approved local image-to-3D workflow with artifact read-back |
| Evidence | Per-run checks and approval state |
| Transport | Local stdio MCP, no public listener |

The Community surface does not execute arbitrary actions, expose private
routing, or include private models and optimizers. Document conversion and
context packaging are bounded local writes that require explicit approval.

## MD Boundary

MD is intentionally an adapter boundary. The Community package does not copy
model code, model weights, cache files, or upstream license material. A user
may connect a separately installed local MD backend through the documented
adapter contract. The MCP surface only creates a plan; the CLI requires an
explicit approval flag before starting a local generation and verifies the
result before delivery. Adapter commands and local installation details are
never printed by the manifest, preflight, or MCP responses.

Read [MD integration](docs/MD_INTEGRATION.md) before connecting a backend.

## Privacy Boundary

The release checker rejects common credential files, private runtime paths,
machine paths, local host names, and IP addresses in public text. The runtime
also redacts those values from task briefs. This is a release safeguard, not a
replacement for human review.

## Verification

```powershell
python -m unittest discover -s tests -v
python scripts/verify_preview_boundary.py .
```

## Release Status

The current line is `Community 1.1.0`, a local release candidate. It includes
the universal document pipeline and AI context-pack workflow. It is not
published yet: a final staged-file review and owner approval are still required
before any push. No donation or
monetization information is part of this release.

## License

The Community code is licensed under Apache-2.0. Any separately installed MD
backend remains subject to its own upstream license and is not relicensed by
this repository.
