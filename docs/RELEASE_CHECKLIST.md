# Release Checklist

## Product

- [x] The installer completes in an isolated clean-target test.
- [x] The opt-in client connector registers supported Codex and Claude CLI
      installations and preserves existing settings.
- [x] The MCP bridge starts with no extra stdout noise.
- [x] The client reads manifest, capabilities, system map, and preflight.
- [x] A safe task completes from input to evidence.
- [x] High-risk input remains approval-gated and non-executing.
- [x] Supported local documents convert to Markdown, summaries, and manifests.
- [x] DOCX, PPTX, XLSX, CSV/TSV, JSON, PDF, and text fixtures pass parsing tests.
- [x] Context packs are redacted by default, chunked, and read back after save.
- [x] Folder ingestion is finite and excludes its output tree.
- [x] MD has a real adapter test before `ready` is advertised.
- [x] MD output is saved to an explicit destination and read back after save.

## Privacy And Boundary

- [x] No machine-specific path, address, endpoint, or identifier is in public
      text or generated examples.
- [x] No credential, environment file, model weight, cache, log, telemetry,
      or private runtime artifact is staged.
- [x] No private Stable source or policy is included.
- [x] No donation or payment account is included before its later approval.

## Verification

```powershell
python -m unittest discover -s tests -v
python scripts/verify_preview_boundary.py .
```

Document smoke checks:

```powershell
aegis-community documents --format json
aegis-community documents-plan --input examples/document_request.json
```

The maintainer must review the final staged file list before publication. A
passing unit suite alone is not an end-to-end release claim; the companion
evidence record documents the real MCP client and MD backend checks.
