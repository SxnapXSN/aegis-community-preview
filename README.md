<div align="center">

# Aegis Community

### Local AI context, document intelligence, and MCP tools for the public Aegis surface

Turn a natural-language request into clean, bounded context that an AI client can actually use.
Everything in this repository is inspectable, local-first, and explicit about its limits.

[![Preview CI](https://img.shields.io/github/actions/workflow/status/SxnapXSN/aegis-community-preview/ci.yml?branch=main&label=Preview%20CI&style=for-the-badge)](https://github.com/SxnapXSN/aegis-community-preview/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/SxnapXSN/aegis-community-preview?display_name=tag&style=for-the-badge)](https://github.com/SxnapXSN/aegis-community-preview/releases/latest)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/github/license/SxnapXSN/aegis-community-preview?style=for-the-badge)](LICENSE)

[![Download latest](https://img.shields.io/badge/Download-latest-2ea44f?style=for-the-badge)](https://github.com/SxnapXSN/aegis-community-preview/releases/latest)
[![Download wheel](https://img.shields.io/badge/Download-Wheel-0969da?style=for-the-badge)](https://github.com/SxnapXSN/aegis-community-preview/releases/download/v1.1.1/aegis_community_preview-1.1.1-py3-none-any.whl)
[![Source ZIP](https://img.shields.io/badge/Source-ZIP-6f42c1?style=for-the-badge)](https://github.com/SxnapXSN/aegis-community-preview/archive/refs/heads/main.zip)
[![Windows installer](https://img.shields.io/badge/Windows-One--click-2088ff?style=for-the-badge)](docs/DOWNLOADS.md#windows-one-click-installer)
[![Documentation](https://img.shields.io/badge/Read-Docs-8250df?style=for-the-badge)](docs/USAGE_GUIDE.md)
[![Report issue](https://img.shields.io/badge/Report-Issue-d1242f?style=for-the-badge)](https://github.com/SxnapXSN/aegis-community-preview/issues/new/choose)

**Current public line: Community 1.1.1 · Public Preview**

</div>

## 📚 Table of contents

- [About](#-about)
- [How the handoff works](#-how-the-handoff-works)
- [What you get](#-what-you-get)
- [Download and install](#-download-and-install)
- [Connect an AI client](#-connect-an-ai-client)
- [Convert documents for AI](#-convert-documents-for-ai)
- [Run the MD adapter workflow](#-run-the-md-adapter-workflow)
- [Use the CLI directly](#-use-the-cli-directly)
- [Why it is different from manual file sharing](#-why-it-is-different-from-manual-file-sharing)
- [Public boundary](#-public-boundary)
- [Verification](#-verification)
- [Project map](#-project-map)
- [Status and roadmap](#-status-and-roadmap)
- [Contributing and support](#-contributing-and-support)
- [License](#-license)

## 🧭 About

Aegis Community is the free public tool layer that sits between a user and an
AI client. It lets Codex, Claude, and compatible MCP clients discover the
public Aegis contract, prepare local documents, and receive clean context
without exposing the private Stable engine.

> **In one line:** ask the AI normally; let Community prepare the right local
> context when the AI needs it.

<details>
<summary>✨ What happens after you ask the AI?</summary>

1. The AI discovers the Community manifest and available capabilities.
2. Community returns a bounded plan before any local write.
3. You approve the write when approval is required.
4. Community converts, redacts, chunks, hashes, and verifies the result.
5. The AI reads the structured context and completes the user's task.

</details>

## 🧩 How the handoff works

~~~text
User request
     |
     v
AI client (Codex, Claude, or another MCP client)
     |
     | discovers, plans, and calls approved tools
     v
Aegis Community (local MCP + CLI)
     |
     | converts, redacts, chunks, hashes, and verifies
     v
Structured Markdown and context returned to the AI
~~~

Community is a supporting tool layer, not a second AI model. The user speaks
to the AI normally; the AI uses Community when it needs to understand local
documents, prepare a context pack, or run an explicitly approved local
workflow.

## ✨ What you get

| Area | Included in Community 1.1.1 |
| --- | --- |
| 🧠 AI connection | Discovery-first local stdio MCP bridge for Codex, Claude, and compatible clients |
| 📄 Documents | Text, source, CSV/TSV, JSON, DOCX, PPTX, XLSX, ODT, ODP, ODS, EPUB, RTF, PDF, and image metadata |
| 🧱 AI context | Markdown output, summaries, bounded chunks, source hashes, freshness signals, and manifests |
| 🛡️ Safety | Plan-first behavior, explicit approval for writes, default redaction, and no arbitrary task execution |
| ⚙️ Reliability | Atomic writes, cache reuse, partial-result reporting, output-loop protection, and read-back checks |
| 📁 Folder workflows | Finite scans and bounded watch iterations without a hidden background daemon |
| 🧊 MD adapter | Approved local image-to-3D adapter boundary with GLB/OBJ verification; model code and weights stay external |
| 🔒 Privacy | No telemetry, private Stable source, credentials, machine paths, network addresses, or private runtime data in the public contract |

## 📦 Download and install

### Option A: latest release wheel

Download the wheel from the Download wheel button above, then install it
locally:

~~~powershell
python -m pip install --no-deps .\aegis_community_preview-1.1.1-py3-none-any.whl
aegis-community preflight
~~~

The release also contains a source distribution and SHA256SUMS.txt.

### Option B: Windows one-click installer

This is the easiest route for Windows users. It finds the latest release,
downloads the wheel, verifies SHA-256, installs it, and runs preflight:

~~~powershell
$installer = Join-Path $env:TEMP 'install-aegis-community.ps1'
Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/SxnapXSN/aegis-community-preview/main/scripts/install-community.ps1' -OutFile $installer
powershell -ExecutionPolicy Bypass -File $installer
~~~

The script requires Python 3.10 or newer. It does not install a service or
send project data anywhere. Review the downloaded script before running it if
your local policy requires inspection.

### Option C: source checkout

~~~powershell
git clone https://github.com/SxnapXSN/aegis-community-preview.git
Set-Location aegis-community-preview
powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1
aegis-community preflight
aegis-community manifest
~~~

The bootstrap script installs the package without runtime dependencies. It
does not register a network service or collect credentials.

### Option D: source ZIP

Use the Source ZIP button when Git is not installed. Extract the archive,
open PowerShell in the extracted folder, and run scripts/bootstrap.ps1.

See the full [download guide](docs/DOWNLOADS.md) for release assets,
checksums, source installs, and troubleshooting.

## 🔌 Connect an AI client

Community uses local stdio MCP. Import
[examples/mcp-client-config.json](examples/mcp-client-config.json) when the
client supports MCP configuration import, or register the same command in the
client's MCP settings:

~~~json
{
  "mcpServers": {
    "aegis-community": {
      "command": "python",
      "args": ["-m", "aegis_community.mcp_server"]
    }
  }
}
~~~

After connection, the AI client should discover the public contract in this
order:

1. aegis_manifest
2. aegis_capabilities
3. aegis_system_map
4. aegis_preflight

Only then should it plan a task, document conversion, context pack, or MD
operation. The bridge writes no status text to stdout, so JSON-RPC remains
clean for the client.

## 📄 Convert documents for AI

Plan first, then approve the bounded local write:

~~~powershell
aegis-community documents --format json
aegis-community documents-plan --path input\brief.pdf --path input\table.xlsx
aegis-community documents-convert --path input\brief.pdf --path input\table.xlsx --output-dir output\markdown --approve
aegis-community context-pack --folder input --output-dir output\context --approve
~~~

The result contains Markdown, compact summaries, manifests, and bounded
context chunks. Redaction is enabled by default. Scanned files can use an
explicitly configured local OCR adapter; OCR is optional and is never claimed
as ready when no adapter is present.

Read [Document Integration](docs/DOCUMENT_INTEGRATION.md) for supported
formats, limits, cache behavior, and output contracts.

## 🧊 Run the MD adapter workflow

The public package defines the contract without bundling model code, model
weights, caches, or upstream license material:

~~~powershell
aegis-community md
aegis-community md-plan --input examples/md_request.json --format pretty
aegis-community md-run --input examples/md_request.json --image $image --output $output --approve
~~~

Read [MD Integration](docs/MD_INTEGRATION.md) before connecting a local
backend.

## 🛠️ Use the CLI directly

The CLI is available for advanced users and automation. The intended primary
experience remains User -> AI -> Community through MCP.

~~~powershell
aegis-community --help
aegis-community capabilities --format pretty
aegis-community system-map --format pretty
aegis-community run --input examples/sample_task.json --format pretty
aegis-community watch --folder input --output-dir output\markdown --iterations 3 --interval 10 --approve
~~~

## 💡 Why it is different from manual file sharing

Without Community, a user must find files, convert formats, copy content into
an AI chat, manage context limits, and remember what was included. With
Community, the AI can request a plan and receive a bounded, redacted,
hash-traceable context pack with read-back evidence.

Community does not improve the underlying model by itself. It improves the
quality, consistency, and traceability of the information the model receives.

## 🔒 Public boundary

This repository is the free public Community surface. It intentionally does
not include the private Aegis Stable engine, private routing, private models,
hidden connectors, customer data, telemetry, or unbounded autonomous actions.
The public contract is designed to be useful without revealing private IP or
runtime details.

For the exact allow-list and exclusions, read
[COMMUNITY_SCOPE.md](COMMUNITY_SCOPE.md) and [SECURITY.md](SECURITY.md).

## ✅ Verification

The current release evidence includes 26 passing tests, Python compilation,
wheel build, boundary verification, MCP contract checks, document parsing
fixtures, context-pack read-back, and real CLI smoke conversion.

Run the local gates before sharing a modified copy:

~~~powershell
python -m unittest discover -s tests -v
python scripts/verify_preview_boundary.py .
git diff --check
~~~

Read the [release evidence](docs/RELEASE_EVIDENCE.md) and
[release checklist](docs/RELEASE_CHECKLIST.md) for the publication contract.

## 🗂️ Project map

| Path | Purpose |
| --- | --- |
| aegis_community/ | Public CLI, MCP bridge, manifest, document pipeline, context pack, and adapters |
| docs/ | Architecture, usage, integration, release, and download documentation |
| examples/ | Portable task, document, context, MD, and MCP configuration examples |
| scripts/ | Windows bootstrap, client connection, and boundary verification helpers |
| tests/ | Contract, document, privacy, cache, MCP, and task tests |

## 🚀 Status and roadmap

Community 1.1.1 is a public preview release. The public workflow is ready
for local use and contribution. OCR adapters, broader legacy Office support,
additional diagnostics, and future public-safe workflows remain separate
follow-up work.

Donation and monetization information is intentionally not included yet.

## 🤝 Contributing and support

- Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a change.
- Use [Issues](https://github.com/SxnapXSN/aegis-community-preview/issues) for
  reproducible bugs and focused feature requests.
- Use [SECURITY.md](SECURITY.md) for security-sensitive reports.

## ⚖️ License

The Community code is licensed under [Apache-2.0](LICENSE). Any separately
installed MD backend remains subject to its own upstream license and is not
relicensed by this repository. See [NOTICE](NOTICE) for the project boundary.
