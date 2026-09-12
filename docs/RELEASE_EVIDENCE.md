# Release Evidence

This record describes checks run locally for Community 1.1.0. It does
not disclose machine paths, addresses, credentials, or private Stable data.

## Contract And Package

- Unit suite: 26 tests passed, including Office XML, OpenDocument, PDF fallback, cache,
  redaction, context-pack, and MCP document-boundary coverage.
- Python compilation: passed for package, scripts, and tests.
- Boundary checker: passed.
- Wheel build: passed with the Community package and its public files.
- Editable installation: passed; the `aegis-community` command reported the
  candidate version.

## MCP Clients

- Codex CLI: isolated MCP registration, inspection, and listing passed.
- Claude CLI: isolated MCP registration, health check, listing, and removal
  passed.
- The real client checks used temporary settings and did not modify the user's
  active client configuration.

## MD End To End

- A separately installed local image-to-3D backend completed a real image
  generation through the Community adapter.
- Output format: GLB.
- Artifact size: 2,022,520 bytes.
- The bridge validated the GLB header, read the file back, computed its SHA-256
  digest, saved it to the requested destination, and verified the final digest
  matched.
- The public result contained no machine path, address, or credential.

## Document To Markdown

- DOCX, PPTX, and XLSX Open XML fixtures converted successfully without an
  Office installation.
- CSV, JSON, text, HTML, and source fixtures converted into Markdown,
  summaries, and source-hash manifests.
- A PDF text-stream fixture passed through the local reader/fallback path.
- A context pack created bounded chunks and passed output read-back checks.
- Scanned-image OCR remains an optional local adapter and is reported as
  unavailable when no adapter is configured; it is never claimed as ready.

## Release Decision

These checks are evidence for the local candidate only. A public release still
requires the final staged-file review and an owner decision to publish.
Donation information remains intentionally absent.
