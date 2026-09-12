# Usage Guide

## 1. Install

Install Python 3.10 or newer, then run the bootstrap script from the project
directory:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1
```

The script installs the package without adding runtime dependencies. It does
not register a network service and does not collect credentials.

To connect detected Codex and Claude CLI installations in the same step, add
the opt-in switch:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1 -ConnectClients
```

Existing client settings are backed up before a new Community entry is added.
The connection script does not print the backup location or client command
output.

## 2. Check Readiness

```powershell
aegis-community preflight
```

`ready` means that the local public contract can run. The MD check may remain
`optional` until a local adapter is configured. `e2e_ready` stays false in
preflight because preflight never runs a model; the separate release evidence
records the real client and backend checks.

## 3. Read The Contract

```powershell
aegis-community manifest
aegis-community capabilities
aegis-community system-map
```

Use `--format json` when another program or AI client will consume the result:

```powershell
aegis-community manifest --format json
```

The public output intentionally omits local paths, addresses, credentials,
and private engine details.

## 4. Plan A Task

```powershell
aegis-community run --input examples/sample_task.json --format pretty
```

Task fields are:

- `task_id`: a stable local identifier.
- `title`: a short human-readable name.
- `objective`: what the task is meant to accomplish.
- `risk_level`: `low`, `medium`, or `high`.
- `allowed_actions`: labels for the proposed plan only.

The Community planner never executes the labels in `allowed_actions`. A high
risk task returns no enabled actions and always requires human review.

## 5. Connect MCP

The portable example is in `examples/mcp-client-config.json`:

```json
{
  "mcpServers": {
    "aegis-community": {
      "command": "python",
      "args": ["-m", "aegis_community.mcp_server"]
    }
  }
}
```

Import it where the client supports MCP configuration import. Otherwise add
the same command to the client's MCP settings. The bridge speaks newline-
delimited JSON-RPC over stdio and writes no status text to stdout.

The AI client must call `aegis_manifest`, `aegis_capabilities`,
`aegis_system_map`, and `aegis_preflight` before planning work.

## 6. Use The MD Contract

Check the public MD surface:

```powershell
aegis-community md
aegis-community md-plan --input examples/md_request.json --format pretty
```

The MCP surface accepts an image-to-3D request and returns a plan. It does not
run the model from MCP. For a local, approved generation, provide an image and
destination to the CLI:

```powershell
aegis-community md-run --input examples/md_request.json --image $image --output $output --approve
```

The runner does not bundle model weights, copy upstream code, or print the
configured backend command. See [MD Integration](MD_INTEGRATION.md) for the
adapter protocol and artifact verification rules.

## 7. Verify A Copy

Run both checks before sharing a modified copy:

```powershell
python -m unittest discover -s tests -v
python scripts/verify_preview_boundary.py .
```

The boundary checker is deliberately strict about paths, addresses,
credentials, and private runtime material. It is a release aid and does not
replace a human staged-file review.

## 8. Convert Documents For AI

Check the built-in document capability:

```powershell
aegis-community documents --format json
```

Create a plan, then approve the bounded local write:

```powershell
aegis-community documents-plan --path input/brief.pdf --path input/table.xlsx
aegis-community documents-convert --path input/brief.pdf --path input/table.xlsx --output-dir output/markdown --approve
```

Supported modern Office files are parsed from their Open XML structure, CSV
and JSON retain their structure, and PDFs use a local text reader with a
dependency-free fallback. Scanned files need the optional local OCR adapter.
The output is a Markdown file, a compact summary, and a manifest containing
the source hash and conversion warnings.

## 9. Give An AI A Context Pack

```powershell
aegis-community context-plan --folder input --output-dir output/context
aegis-community context-pack --folder input --output-dir output/context --approve
```

The pack contains `context.md`, a machine-readable manifest, and bounded
chunks. Redaction is enabled by default so common credentials, local paths,
addresses, and URLs are not carried into the AI context. Use `--no-redact`
only for a trusted local workflow.

## 10. Bounded Folder Processing

```powershell
aegis-community watch --folder input --output-dir output/markdown --approve
aegis-community watch --folder input --output-dir output/markdown --iterations 3 --interval 10 --approve
```

The first command performs one scan. The second performs three finite scans.
There is no unbounded daemon or hidden startup process.
