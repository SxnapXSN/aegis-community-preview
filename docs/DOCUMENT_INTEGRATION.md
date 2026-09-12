# Document Integration

Aegis Community includes a local document-to-Markdown pipeline for building
context that an AI client can scan, search, and cite without receiving a raw
binary file.

## Supported Inputs

- Text and source: TXT, MD, RST, LOG, Python, JavaScript, TypeScript, JSX,
  TSX, Java, Kotlin, C/C++, C#, Rust, Go, CSS/SCSS, HTML, XML, SQL, YAML,
  TOML, INI, CFG, PowerShell, BAT/CMD, and shell scripts.
- Structured data: CSV, TSV, and JSON.
- Office Open XML: DOCX, PPTX, and XLSX.
- OpenDocument and ebook: ODT, ODP, ODS, and EPUB.
- RTF: bounded text extraction with formatting controls removed.
- PDF: text extraction through a local PDF reader when available, with a
  dependency-free text-stream fallback.
- Images: PNG, JPG/JPEG, WEBP, and BMP metadata; OCR is optional through a
  separately configured local command.

Legacy binary Office formats are rejected rather than silently producing a
misleading result.

## Output Set

Each document produces three logical artifacts:

- `<name>.md`: readable content with metadata and detected structure.
- `<name>.summary.md`: compact summary and token estimate.
- `<name>.manifest.json`: source hash, status, warnings, parser metadata, and
  output names.

Artifacts are written atomically. A second run with the same source hash is
reported as `cached`. A changed source produces a fresh artifact while
preserving the source hash in its manifest.

## Convert Documents

Plan first:

```powershell
aegis-community documents-plan --path input/report.docx --path input/data.xlsx
```

Approve a local write explicitly:

```powershell
aegis-community documents-convert --path input/report.docx --path input/data.xlsx --output-dir output/markdown --approve
```

A folder can be scanned in one bounded run:

```powershell
aegis-community documents-convert --folder input --output-dir output/markdown --approve
```

Redaction is enabled by default. Use `--no-redact` only when the destination
is trusted and the source is known not to contain secrets or machine details.

## Build An AI Context Pack

```powershell
aegis-community context-plan --path input/report.pdf --path input/notes.md --output-dir output/context
aegis-community context-pack --path input/report.pdf --path input/notes.md --output-dir output/context --approve
```

The pack contains `context.md`, `context.manifest.json`, and bounded files in
`chunks/`. The context file includes a document index, source hashes, status,
token estimates, summaries, and the converted content. It is redacted by
default and never returns local paths through the public CLI/MCP result.

## OCR

OCR is intentionally an adapter boundary. Configure a local command that
accepts an input placeholder and writes recognized text to standard output:

```powershell
$env:AEGIS_OCR_COMMAND = '["python", "local_ocr_adapter.py", "{input}"]'
aegis-community documents --format json
aegis-community documents-convert --path input/scan.png --output-dir output/markdown --ocr --approve
```

The command is executed without a shell, has a bounded timeout, and its path
or command line is never returned by the public manifest or MCP response.

## Bounded Folder Watch

The watch command is intentionally bounded. It performs one scan by default,
or a finite number of scans when `--iterations` is supplied; it does not leave
an unbounded background daemon running:

```powershell
aegis-community watch --folder input --output-dir output/markdown --iterations 3 --interval 10 --approve
```

The output directory is excluded automatically when it is inside the watched
folder, preventing generated Markdown from feeding back into the next scan.

## MCP Tools

The local stdio bridge exposes:

- `aegis_document_capability`
- `aegis_document_plan`
- `aegis_document_convert`
- `aegis_context_plan`
- `aegis_context_pack`

Planning tools do not read or write local files. Conversion and context-pack
tools require an explicit `approved: true` field and return logical names,
hashes, statuses, warnings, and read-back evidence rather than machine paths.

## Honest Boundary

This is deterministic local parsing and packaging, not a guarantee that every
PDF layout, spreadsheet formula, embedded chart, handwriting sample, or
semantic claim is understood perfectly. The manifest and warnings preserve
that distinction so an AI client can request review when extraction is
partial. No embedding model, vector database, cloud upload, private model, or
Stable control-plane code is bundled here.
