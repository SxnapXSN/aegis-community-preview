"""Bounded local document-to-Markdown conversion for Aegis Community."""

from __future__ import annotations

import csv
import hashlib
import html
import importlib.util
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
import zlib
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence
from xml.etree import ElementTree as ET

from .public_text import redact_public_text


DOCUMENT_PROTOCOL_VERSION = "1.0"
SUPPORTED_EXTENSIONS = frozenset(
    {
        ".bat",
        ".bmp",
        ".c",
        ".cfg",
        ".cmd",
        ".cpp",
        ".cs",
        ".css",
        ".csv",
        ".docx",
        ".epub",
        ".go",
        ".h",
        ".hpp",
        ".html",
        ".ini",
        ".java",
        ".jpeg",
        ".jpg",
        ".js",
        ".json",
        ".jsx",
        ".kt",
        ".log",
        ".md",
        ".odp",
        ".ods",
        ".odt",
        ".pdf",
        ".png",
        ".pptx",
        ".ps1",
        ".py",
        ".rs",
        ".rst",
        ".rtf",
        ".scss",
        ".sh",
        ".sql",
        ".svg",
        ".tex",
        ".toml",
        ".ts",
        ".tsv",
        ".tsx",
        ".txt",
        ".webp",
        ".xlsx",
        ".xml",
        ".yaml",
        ".yml",
    }
)
_TEXT_EXTENSIONS = SUPPORTED_EXTENSIONS - {
    ".bmp",
    ".docx",
    ".epub",
    ".jpeg",
    ".jpg",
    ".pdf",
    ".png",
    ".pptx",
    ".odp",
    ".ods",
    ".odt",
    ".webp",
    ".xlsx",
}
_IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".webp"}
_MAX_INPUT_BYTES = 100 * 1024 * 1024
_MAX_ARCHIVE_MEMBERS = 5000
_MAX_ARCHIVE_BYTES = 400 * 1024 * 1024
_MAX_ROWS = 5000
_MAX_COLUMNS = 256
_DEFAULT_MAX_CHARS = 200_000


class DocumentConversionError(ValueError):
    """Raised when a local document cannot be safely converted."""


@dataclass(frozen=True)
class _ConversionRecord:
    source_name: str
    source_type: str
    size_bytes: int
    content_hash: str
    status: str
    markdown: str
    summary: str
    metadata: dict[str, Any]
    warnings: tuple[str, ...]


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _attribute(element: ET.Element, local_name: str) -> str | None:
    for key, value in element.attrib.items():
        if _local(key) == local_name:
            return value
    return None


def _normalise_block(value: str) -> str:
    return re.sub(r"[ \t]+", " ", value.replace("\r", "").strip())


def _safe_output_stem(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-")
    return (clean or "document")[:80]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def _validate_input(path_value: str | Path, *, max_input_bytes: int = _MAX_INPUT_BYTES) -> Path:
    path = Path(path_value).expanduser()
    try:
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise DocumentConversionError("input document is not readable") from error
    if not resolved.is_file():
        raise DocumentConversionError("input document must be a file")
    if resolved.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise DocumentConversionError("document format is not supported by Community")
    try:
        size = resolved.stat().st_size
    except OSError as error:
        raise DocumentConversionError("input document metadata is unavailable") from error
    if size > max(1, min(int(max_input_bytes), _MAX_INPUT_BYTES)):
        raise DocumentConversionError("input document exceeds the Community size limit")
    return resolved


def _fence(language: str, value: str) -> str:
    fence = "````" if "```" in value else "```"
    return f"{fence}{language}\n{value.rstrip()}\n{fence}"


def _escape_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    text = text.replace("\r", "").replace("\n", "<br>")
    return text.replace("|", "\\|").strip()


def _table(rows: Sequence[Sequence[Any]]) -> str:
    cleaned = [[_escape_cell(cell) for cell in row] for row in rows[:_MAX_ROWS]]
    width = max((len(row) for row in cleaned), default=0)
    width = max(1, min(width, _MAX_COLUMNS))
    if not cleaned:
        return "| Value |\n| --- |\n| |"
    normalised = [(row + [""] * width)[:width] for row in cleaned]
    lines = ["| " + " | ".join(normalised[0]) + " |", "| " + " | ".join("---" for _ in range(width)) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in normalised[1:])
    return "\n".join(lines)


def _csv_body(text: str, suffix: str) -> tuple[str, dict[str, Any]]:
    sample = text[:4096]
    delimiter = "\t" if suffix == ".tsv" else ","
    if suffix == ".csv":
        try:
            delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
        except csv.Error:
            pass
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))[:_MAX_ROWS]
    return _table(rows), {"rows": len(rows), "columns": max((len(row) for row in rows), default=0)}


def _json_body(text: str) -> tuple[str, dict[str, Any]]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return _fence("json", text), {"json_valid": False}
    pretty = json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True)
    top_level = list(value.keys())[:50] if isinstance(value, dict) else []
    return _fence("json", pretty), {"json_valid": True, "top_level_keys": top_level}


class _HtmlMarkdownParser(HTMLParser):
    """Small dependency-free HTML reader focused on document structure."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self.current: list[str] = []
        self.heading: int | None = None
        self.list_depth = 0
        self.in_pre = False
        self.ignored_depth = 0
        self.table_rows: list[list[str]] | None = None
        self.table_row: list[str] | None = None
        self.table_cell: list[str] | None = None

    def _flush(self, prefix: str = "") -> None:
        value = "".join(self.current) if self.in_pre else _normalise_block("".join(self.current))
        self.current = []
        if value:
            self.blocks.append(prefix + value)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "template"}:
            self.ignored_depth += 1
            return
        if self.ignored_depth:
            return
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._flush()
            self.heading = int(tag[1])
        elif tag in {"p", "div", "section", "article", "header", "footer", "blockquote"}:
            self._flush()
        elif tag == "br":
            self.current.append("\n")
        elif tag in {"ul", "ol"}:
            self._flush()
            self.list_depth += 1
        elif tag == "li":
            self._flush()
        elif tag == "pre":
            self._flush()
            self.in_pre = True
        elif tag == "table":
            self._flush()
            self.table_rows = []
        elif tag == "tr" and self.table_rows is not None:
            self.table_row = []
        elif tag in {"th", "td"} and self.table_row is not None:
            self.table_cell = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "template"}:
            self.ignored_depth = max(0, self.ignored_depth - 1)
            return
        if self.ignored_depth:
            return
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._flush("#" * (self.heading or 1) + " ")
            self.heading = None
        elif tag in {"p", "div", "section", "article", "header", "footer", "blockquote"}:
            self._flush("> " if tag == "blockquote" else "")
        elif tag == "li":
            prefix = "- " if self.list_depth else ""
            self._flush(prefix)
        elif tag in {"ul", "ol"}:
            self._flush()
            self.list_depth = max(0, self.list_depth - 1)
        elif tag == "pre":
            value = "".join(self.current).strip()
            self.current = []
            if value:
                self.blocks.append(_fence("text", value))
            self.in_pre = False
        elif tag in {"th", "td"} and self.table_row is not None:
            self.table_row.append(_normalise_block("".join(self.table_cell or [])))
            self.table_cell = None
        elif tag == "tr" and self.table_rows is not None and self.table_row is not None:
            self.table_rows.append(self.table_row)
            self.table_row = None
        elif tag == "table" and self.table_rows is not None:
            if self.table_rows:
                self.blocks.append(_table(self.table_rows))
            self.table_rows = None

    def handle_data(self, data: str) -> None:
        if self.ignored_depth:
            return
        if self.table_cell is not None:
            self.table_cell.append(data)
        else:
            self.current.append(data)

    def result(self) -> str:
        self._flush()
        return "\n\n".join(block for block in self.blocks if block.strip())


def _html_body(text: str) -> tuple[str, dict[str, Any]]:
    parser = _HtmlMarkdownParser()
    parser.feed(text)
    parser.close()
    result = parser.result() or "_(empty HTML document)_"
    return result, {"sections": len(parser.blocks)}


def _safe_zip_members(path: Path) -> dict[str, bytes]:
    members: dict[str, bytes] = {}
    total_size = 0
    try:
        with zipfile.ZipFile(path) as archive:
            infos = [info for info in archive.infolist() if not info.is_dir()]
            if len(infos) > _MAX_ARCHIVE_MEMBERS:
                raise DocumentConversionError("document archive contains too many members")
            for info in infos:
                logical = PurePosixPath(info.filename)
                if logical.is_absolute() or ".." in logical.parts:
                    raise DocumentConversionError("document archive contains an unsafe member")
                total_size += info.file_size
                if total_size > _MAX_ARCHIVE_BYTES:
                    raise DocumentConversionError("document archive exceeds the safety limit")
                members[logical.as_posix()] = archive.read(info)
    except zipfile.BadZipFile as error:
        raise DocumentConversionError("document archive is invalid") from error
    except OSError as error:
        raise DocumentConversionError("document archive could not be read") from error
    return members


def _xml_member(members: Mapping[str, bytes], name: str) -> ET.Element:
    raw = members.get(name)
    if raw is None:
        raise DocumentConversionError("document structure is incomplete")
    try:
        return ET.fromstring(raw)
    except ET.ParseError as error:
        raise DocumentConversionError("document XML is invalid") from error


def _element_text(element: ET.Element) -> str:
    parts: list[str] = []
    for node in element.iter():
        local = _local(node.tag)
        if local in {"t", "text"} and node.text:
            parts.append(node.text)
        elif local in {"tab", "br"}:
            parts.append(" ")
    return _normalise_block("".join(parts))


def _docx_body(path: Path) -> tuple[str, dict[str, Any]]:
    members = _safe_zip_members(path)
    root = _xml_member(members, "word/document.xml")
    blocks: list[str] = []
    paragraphs = 0
    tables = 0
    body = next((node for node in root.iter() if _local(node.tag) == "body"), root)
    for child in list(body):
        kind = _local(child.tag)
        if kind == "p":
            text = _element_text(child)
            if not text:
                continue
            paragraphs += 1
            style = next(
                (
                    _attribute(node, "val")
                    for node in child.iter()
                    if _local(node.tag) == "pStyle"
                ),
                "",
            )
            if style and (style.lower().startswith("heading") or style.lower() == "title"):
                match = re.search(r"(\d+)$", style)
                level = int(match.group(1)) if match else 1
                blocks.append("#" * max(1, min(level, 6)) + " " + text)
            else:
                blocks.append(text)
        elif kind == "tbl":
            rows: list[list[str]] = []
            for row in child.iter():
                if _local(row.tag) != "tr":
                    continue
                cells: list[str] = []
                for cell in row.iter():
                    if _local(cell.tag) == "tc":
                        cells.append(_element_text(cell))
                if cells:
                    rows.append(cells)
            if rows:
                tables += 1
                blocks.append(_table(rows))
    return "\n\n".join(blocks) or "_(empty DOCX document)_", {"paragraphs": paragraphs, "tables": tables}


def _odf_text(element: ET.Element) -> str:
    return _normalise_block("".join(element.itertext()))


def _odf_table(element: ET.Element) -> str:
    rows: list[list[str]] = []
    for row in element.iter():
        if _local(row.tag) != "table-row":
            continue
        cells: list[str] = []
        for cell in row:
            if _local(cell.tag) == "table-cell":
                cells.append(_odf_text(cell))
        if cells:
            rows.append(cells)
    return _table(rows)


def _odf_body(path: Path, suffix: str) -> tuple[str, dict[str, Any]]:
    members = _safe_zip_members(path)
    root = _xml_member(members, "content.xml")
    blocks: list[str] = []
    if suffix == ".ods":
        sheets = 0
        for table in root.iter():
            if _local(table.tag) != "table":
                continue
            rendered = _odf_table(table)
            if rendered and rendered != "| Value |\n| --- |\n| |":
                sheets += 1
                name = _attribute(table, "name") or f"Sheet {sheets}"
                blocks.extend([f"## Sheet: {_normalise_block(name)}", rendered])
        return "\n\n".join(blocks) or "_(empty ODS document)_", {"sheets": sheets}
    if suffix == ".odp":
        slides = 0
        for page in root.iter():
            if _local(page.tag) != "page":
                continue
            texts = []
            for node in page.iter():
                if _local(node.tag) in {"p", "h"}:
                    text = _odf_text(node)
                    if text:
                        texts.append(text)
            if texts:
                slides += 1
                blocks.append("## Slide " + str(slides))
                blocks.extend("- " + text for text in texts)
        return "\n\n".join(blocks) or "_(empty ODP document)_", {"slides": slides}
    paragraphs = 0
    tables = 0
    for node in root.iter():
        kind = _local(node.tag)
        if kind == "h":
            text = _odf_text(node)
            if text:
                try:
                    level = int(_attribute(node, "outline-level") or "1")
                except ValueError:
                    level = 1
                blocks.append("#" * max(1, min(level, 6)) + " " + text)
                paragraphs += 1
        elif kind == "p":
            text = _odf_text(node)
            if text:
                blocks.append(text)
                paragraphs += 1
        elif kind == "table":
            rendered = _odf_table(node)
            if rendered and rendered != "| Value |\n| --- |\n| |":
                blocks.append(rendered)
                tables += 1
    return "\n\n".join(blocks) or "_(empty ODT document)_", {"paragraphs": paragraphs, "tables": tables}


def _epub_body(path: Path) -> tuple[str, dict[str, Any]]:
    members = _safe_zip_members(path)
    names = sorted(name for name in members if name.lower().endswith((".html", ".xhtml", ".htm")))
    blocks: list[str] = []
    sections = 0
    for name in names:
        section, _ = _html_body(members[name].decode("utf-8", errors="replace"))
        if section:
            sections += 1
            blocks.extend([f"## Section {sections}: {Path(name).stem}", section])
    return "\n\n".join(blocks) or "_(empty EPUB document)_", {"sections": sections}


def _rtf_body(text: str) -> tuple[str, dict[str, Any]]:
    slash = re.escape(chr(92))
    value = re.sub(slash + r"par\b", "\n", text, flags=re.IGNORECASE)
    value = re.sub(slash + r"'[0-9a-fA-F]{2}", "", value)
    value = re.sub(slash + r"[a-zA-Z]+-?\d* ?", "", value)
    value = value.replace("{", "").replace("}", "")
    return value.strip() or "_(empty RTF document)_", {}


def _pptx_body(path: Path) -> tuple[str, dict[str, Any]]:
    members = _safe_zip_members(path)
    slide_names = sorted(
        (name for name in members if name.startswith("ppt/slides/slide") and name.endswith(".xml")),
        key=lambda name: int(re.search(r"slide(\d+)", name).group(1)) if re.search(r"slide(\d+)", name) else 0,
    )
    blocks: list[str] = []
    slides = 0
    for index, name in enumerate(slide_names, start=1):
        root = _xml_member(members, name)
        paragraphs: list[str] = []
        for paragraph in root.iter():
            if _local(paragraph.tag) != "p":
                continue
            text = _element_text(paragraph)
            if text:
                paragraphs.append(text)
        if paragraphs:
            slides += 1
            blocks.append("## Slide " + str(index))
            blocks.extend("- " + paragraph for paragraph in paragraphs)
    return "\n\n".join(blocks) or "_(empty PPTX document)_", {"slides": slides}


def _column_number(reference: str | None) -> int:
    if not reference:
        return 1
    letters = re.match(r"([A-Za-z]+)", reference)
    if not letters:
        return 1
    value = 0
    for char in letters.group(1).upper():
        value = value * 26 + ord(char) - ord("A") + 1
    return max(1, min(value, _MAX_COLUMNS))


def _xlsx_body(path: Path) -> tuple[str, dict[str, Any]]:
    members = _safe_zip_members(path)
    shared: list[str] = []
    if "xl/sharedStrings.xml" in members:
        root = _xml_member(members, "xl/sharedStrings.xml")
        shared = [_element_text(item) for item in root if _local(item.tag) == "si"]

    workbook = _xml_member(members, "xl/workbook.xml")
    relationships: dict[str, str] = {}
    if "xl/_rels/workbook.xml.rels" in members:
        rel_root = _xml_member(members, "xl/_rels/workbook.xml.rels")
        for rel in rel_root:
            rel_id = _attribute(rel, "Id")
            target = _attribute(rel, "Target")
            if rel_id and target:
                relationships[rel_id] = target.replace("\\", "/").lstrip("/")

    sheets: list[tuple[str, str]] = []
    for sheet in workbook.iter():
        if _local(sheet.tag) != "sheet":
            continue
        name = _attribute(sheet, "name") or "Sheet"
        rel_id = _attribute(sheet, "id") or ""
        target = relationships.get(rel_id, "")
        if target.startswith("/xl/"):
            target = target[1:]
        elif not target.startswith("xl/"):
            target = "xl/" + target
        if target in members:
            sheets.append((name, target))
    if not sheets:
        sheets = [
            (Path(name).stem, name)
            for name in sorted(members)
            if name.startswith("xl/worksheets/") and name.endswith(".xml")
        ]

    blocks: list[str] = []
    sheet_count = 0
    for sheet_name, sheet_path in sheets:
        root = _xml_member(members, sheet_path)
        rows: list[list[str]] = []
        for row in root.iter():
            if _local(row.tag) != "row":
                continue
            values: dict[int, str] = {}
            for cell in row:
                if _local(cell.tag) != "c":
                    continue
                column = _column_number(_attribute(cell, "r"))
                kind = _attribute(cell, "t") or ""
                value_node = next((node for node in cell if _local(node.tag) == "v"), None)
                inline_node = next((node for node in cell if _local(node.tag) == "is"), None)
                value = _element_text(inline_node) if inline_node is not None else (value_node.text or "" if value_node is not None else "")
                if kind == "s" and value.isdigit() and int(value) < len(shared):
                    value = shared[int(value)]
                formula = next((node.text or "" for node in cell if _local(node.tag) == "f"), "")
                if formula:
                    value = f"{value} [formula: {formula}]" if value else f"[formula: {formula}]"
                values[column] = value
            if values:
                width = max(values)
                rows.append([values.get(index, "") for index in range(1, width + 1)])
        if rows:
            sheet_count += 1
            blocks.append("## Sheet: " + _normalise_block(sheet_name))
            blocks.append(_table(rows))
    return "\n\n".join(blocks) or "_(empty XLSX document)_", {"sheets": sheet_count}


def _decode_pdf_literals(data: bytes) -> list[str]:
    values: list[str] = []
    index = 0
    while index < len(data):
        marker = data[index]
        if marker == ord("("):
            index += 1
            depth = 1
            value = bytearray()
            while index < len(data) and depth:
                char = data[index]
                if char == ord("\\") and index + 1 < len(data):
                    index += 1
                    escaped = data[index]
                    escapes = {ord("n"): 10, ord("r"): 13, ord("t"): 9, ord("b"): 8, ord("f"): 12}
                    value.append(escapes.get(escaped, escaped))
                elif char == ord("("):
                    depth += 1
                    value.append(char)
                elif char == ord(")"):
                    depth -= 1
                    if depth:
                        value.append(char)
                else:
                    value.append(char)
                index += 1
            text = value.decode("utf-8", errors="replace").strip()
            if text:
                values.append(text)
        elif marker == ord("<") and index + 1 < len(data) and data[index + 1] != ord("<"):
            end = data.find(b">", index + 1)
            if end != -1:
                raw = re.sub(rb"\s+", b"", data[index + 1 : end])
                if len(raw) % 2:
                    raw += b"0"
                try:
                    text = bytes.fromhex(raw.decode("ascii")).decode("utf-8", errors="replace").strip()
                except (ValueError, UnicodeDecodeError):
                    text = ""
                if text:
                    values.append(text)
                index = end
        index += 1
    return values


def _pdf_fallback_pages(raw: bytes) -> list[str]:
    pages: list[str] = []
    position = 0
    while True:
        marker = raw.find(b"stream", position)
        if marker == -1:
            break
        start = marker + len(b"stream")
        if raw[start : start + 2] == b"\r\n":
            start += 2
        elif raw[start : start + 1] in {b"\n", b"\r"}:
            start += 1
        end = raw.find(b"endstream", start)
        if end == -1:
            break
        stream = raw[start:end].rstrip(b"\r\n")
        header = raw[max(0, marker - 160) : marker]
        if b"/FlateDecode" in header:
            try:
                stream = zlib.decompress(stream)
            except zlib.error:
                stream = b""
        values = _decode_pdf_literals(stream)
        if values:
            pages.append(" ".join(values))
        position = end + len(b"endstream")
    if not pages:
        printable = re.findall(rb"[ -~]{5,}", raw)
        filtered = [item.decode("latin-1").strip() for item in printable if b"obj" not in item and b"end" not in item]
        if filtered:
            pages.append(" ".join(filtered))
    return pages


def _pdf_body(path: Path, *, ocr: bool) -> tuple[str, dict[str, Any], list[str]]:
    warnings: list[str] = []
    pages: list[str] = []
    parser = "builtin"
    if importlib.util.find_spec("pypdf") is not None:
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path), strict=False)
            pages = [(page.extract_text() or "").strip() for page in reader.pages]
            parser = "pypdf"
        except Exception:
            pages = []
    if not any(pages):
        try:
            pages = _pdf_fallback_pages(path.read_bytes())
            parser = "builtin"
        except OSError as error:
            raise DocumentConversionError("PDF could not be read") from error
    if not any(pages) and ocr and importlib.util.find_spec("fitz") is not None:
        try:
            import fitz

            with tempfile.TemporaryDirectory(prefix="aegis-community-pdf-ocr-") as temp_dir:
                document = fitz.open(str(path))
                for index, page in enumerate(document, start=1):
                    image_path = Path(temp_dir) / f"page-{index}.png"
                    page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).save(str(image_path))
                    text, _ = _ocr_text(image_path)
                    if text:
                        pages.append(text)
                document.close()
            parser = "local-pdf-render-plus-ocr"
        except Exception:
            pages = []
    pages = [page for page in pages if page]
    if not pages:
        warnings.append("PDF text was not extractable; configure a local OCR adapter for scanned pages")
        return "_(no extractable PDF text)_", {"pages": 0, "parser": parser}, warnings
    blocks = []
    for index, page in enumerate(pages, start=1):
        blocks.extend([f"## Page {index}", page])
    return "\n\n".join(blocks), {"pages": len(pages), "parser": parser}, warnings


def _parse_command(value: str) -> list[str] | None:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, list) and all(isinstance(item, str) and item for item in parsed):
        return list(parsed)
    try:
        tokens = shlex.split(value, posix=False)
    except ValueError:
        return None
    return [token[1:-1] if len(token) > 1 and token[0] == token[-1] and token[0] in {"'", '"'} else token for token in tokens] or None


def _ocr_text(path: Path) -> tuple[str | None, str | None]:
    command_value = os.environ.get("AEGIS_OCR_COMMAND", "").strip()
    command = _parse_command(command_value) if command_value else None
    if command is None and command_value:
        return None, "OCR adapter configuration is invalid"
    if command is None:
        tesseract = shutil.which("tesseract")
        command = [tesseract, "{input}", "stdout"] if tesseract else None
    if command is None:
        return None, "No local OCR adapter is configured"
    expanded = [token.replace("{input}", str(path)) for token in command]
    if not any("{input}" in token for token in command):
        expanded.append(str(path))
    try:
        completed = subprocess.run(
            expanded,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None, "Local OCR adapter did not complete"
    if completed.returncode != 0:
        return None, "Local OCR adapter returned an error"
    text = completed.stdout.strip()
    return (text or None), (None if text else "OCR returned no text")


def _image_body(path: Path, *, ocr: bool) -> tuple[str, dict[str, Any], list[str]]:
    warnings: list[str] = []
    metadata: dict[str, Any] = {"ocr_requested": ocr}
    try:
        from PIL import Image

        with Image.open(path) as image:
            metadata.update({"width": image.width, "height": image.height, "format": image.format})
    except Exception:
        metadata["format"] = path.suffix.lower().lstrip(".")
        warnings.append("Image could not be inspected by the optional local image reader")
    blocks = ["## Image Metadata", "", _table([["Property", "Value"], *[[key, value] for key, value in metadata.items()]])]
    if ocr:
        text, warning = _ocr_text(path)
        if text:
            blocks.extend(["", "## OCR Text", "", text])
            metadata["ocr"] = "completed"
        else:
            metadata["ocr"] = "unavailable"
            if warning:
                warnings.append(warning)
    else:
        warnings.append("OCR was not requested; image content is represented by metadata only")
    return "\n".join(blocks), metadata, warnings


_LANGUAGES = {
    ".bat": "bat",
    ".cmd": "bat",
    ".cpp": "cpp",
    ".cs": "csharp",
    ".css": "css",
    ".go": "go",
    ".html": "html",
    ".java": "java",
    ".js": "javascript",
    ".json": "json",
    ".jsx": "jsx",
    ".kt": "kotlin",
    ".md": "markdown",
    ".ps1": "powershell",
    ".py": "python",
    ".rs": "rust",
    ".scss": "scss",
    ".sh": "bash",
    ".sql": "sql",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
}


def _text_body(path: Path, text: str) -> tuple[str, dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix in {".csv", ".tsv"}:
        return _csv_body(text, suffix)
    if suffix == ".json":
        return _json_body(text)
    if suffix in {".html", ".svg"}:
        return _html_body(text)
    if suffix == ".md":
        return text.strip() or "_(empty Markdown document)_", {}
    return _fence(_LANGUAGES.get(suffix, "text"), text), {}


def _convert_internal(path: Path, *, ocr: bool, max_input_bytes: int, redact: bool) -> _ConversionRecord:
    path = _validate_input(path, max_input_bytes=max_input_bytes)
    size = path.stat().st_size
    content_hash = _sha256(path)
    suffix = path.suffix.lower()
    warnings: list[str] = []
    metadata: dict[str, Any] = {}
    if suffix in _TEXT_EXTENSIONS:
        raw_text = _read_text(path)
        if suffix == ".rtf":
            body, metadata = _rtf_body(raw_text)
        else:
            body, metadata = _text_body(path, raw_text)
    elif suffix == ".docx":
        body, metadata = _docx_body(path)
    elif suffix in {".odt", ".odp", ".ods"}:
        body, metadata = _odf_body(path, suffix)
    elif suffix == ".epub":
        body, metadata = _epub_body(path)
    elif suffix == ".pptx":
        body, metadata = _pptx_body(path)
    elif suffix == ".xlsx":
        body, metadata = _xlsx_body(path)
    elif suffix == ".pdf":
        body, metadata, warnings = _pdf_body(path, ocr=ocr)
    elif suffix in _IMAGE_EXTENSIONS:
        body, metadata, warnings = _image_body(path, ocr=ocr)
    else:
        raise DocumentConversionError("document format is not supported by Community")

    title = _normalise_block(path.stem.replace("_", " ").replace("-", " ")) or "Document"
    status = "complete" if not warnings else "partial"
    safe_body = redact_public_text(body) if redact else body
    markdown = "\n".join(
        [
            f"# {redact_public_text(title) if redact else title}",
            "",
            "## Document Metadata",
            "",
            f"- Source name: `{redact_public_text(path.name) if redact else path.name}`",
            f"- Source type: `{suffix.lstrip('.')}`",
            f"- Content hash: `{content_hash}`",
            f"- Conversion protocol: `document-md/{DOCUMENT_PROTOCOL_VERSION}`",
            f"- Status: `{status}`",
            f"- Size bytes: `{size}`",
            *([f"- Warning: {redact_public_text(warning) if redact else warning}" for warning in warnings]),
            "",
            "## Content",
            "",
            safe_body.rstrip(),
            "",
        ]
    )
    line_count = len(safe_body.splitlines())
    summary_lines = [
        f"# Summary: {redact_public_text(title) if redact else title}",
        "",
        f"- Status: `{status}`",
        f"- Source type: `{suffix.lstrip('.')}`",
        f"- Content hash: `{content_hash}`",
        f"- Size bytes: `{size}`",
        f"- Lines: `{line_count}`",
        f"- Estimated tokens: `{max(1, (len(safe_body) + 3) // 4)}`",
    ]
    if metadata:
        summary_lines.extend(["", "## Detected structure", ""])
        summary_lines.extend(f"- {key}: `{value}`" for key, value in metadata.items())
    if warnings:
        summary_lines.extend(["", "## Warnings", ""])
        summary_lines.extend(f"- {redact_public_text(warning) if redact else warning}" for warning in warnings)
    summary = "\n".join(summary_lines) + "\n"
    metadata = {**metadata, "title": title, "lines": line_count, "estimated_tokens": max(1, (len(safe_body) + 3) // 4)}
    return _ConversionRecord(
        source_name=path.name,
        source_type=suffix.lstrip("."),
        size_bytes=size,
        content_hash=content_hash,
        status=status,
        markdown=markdown,
        summary=summary,
        metadata=metadata,
        warnings=tuple(warnings),
    )


def _atomic_write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    os.replace(temporary, path)


def _manifest_for(record: _ConversionRecord, output_files: Mapping[str, str], *, redacted: bool) -> dict[str, Any]:
    return {
        "schema": "aegis.document-manifest/v1",
        "protocol": f"document-md/{DOCUMENT_PROTOCOL_VERSION}",
        "source_name": redact_public_text(record.source_name),
        "source_type": record.source_type,
        "source_hash": record.content_hash,
        "size_bytes": record.size_bytes,
        "status": record.status,
        "warnings": [redact_public_text(item) for item in record.warnings],
        "metadata": record.metadata,
        "redacted": redacted,
        "output_files": dict(output_files),
        "generated_at": _now(),
    }


def _public_result(
    record: _ConversionRecord,
    output_files: Mapping[str, str],
    *,
    cached: bool,
    wrote: bool,
    read_back: bool,
) -> dict[str, Any]:
    return {
        "source_name": redact_public_text(record.source_name),
        "source_type": record.source_type,
        "status": "cached" if cached else record.status,
        "content_hash": record.content_hash,
        "size_bytes": record.size_bytes,
        "warnings": [redact_public_text(item) for item in record.warnings],
        "output_files": dict(output_files),
        "wrote_files": wrote,
        "read_back": read_back,
        "privacy": {"paths_returned": False, "addresses_returned": False, "credentials_returned": False},
    }


def convert_document(
    path: str | Path,
    output_dir: str | Path | None = None,
    *,
    ocr: bool = False,
    redact: bool = True,
    max_input_bytes: int = _MAX_INPUT_BYTES,
    include_content: bool = False,
) -> dict[str, Any]:
    """Convert one local document and optionally write a verified artifact set."""

    record = _convert_internal(path if isinstance(path, Path) else Path(path), ocr=ocr, max_input_bytes=max_input_bytes, redact=redact)
    stem = _safe_output_stem(Path(record.source_name).stem)
    root = Path(output_dir).expanduser().resolve() if output_dir is not None else None
    cached = False
    wrote = False
    if root is not None:
        root.mkdir(parents=True, exist_ok=True)
        manifest_path = root / f"{stem}.manifest.json"
        if manifest_path.exists():
            try:
                existing = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                existing = {}
            if existing.get("source_hash") not in {None, record.content_hash}:
                stem = f"{stem}-{record.content_hash[:8]}"
                manifest_path = root / f"{stem}.manifest.json"
                try:
                    existing = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
                except (OSError, json.JSONDecodeError):
                    existing = {}
            if (
                existing.get("source_hash") == record.content_hash
                and existing.get("source_name") == redact_public_text(record.source_name)
                and existing.get("redacted") is redact
                and (root / f"{stem}.md").is_file()
                and (root / f"{stem}.summary.md").is_file()
            ):
                cached = True
        if not cached:
            output_files = {
                "markdown": f"{stem}.md",
                "summary": f"{stem}.summary.md",
                "manifest": f"{stem}.manifest.json",
            }
            _atomic_write(root / output_files["markdown"], record.markdown)
            _atomic_write(root / output_files["summary"], record.summary)
            _atomic_write(root / output_files["manifest"], json.dumps(_manifest_for(record, output_files, redacted=redact), indent=2, ensure_ascii=False) + "\n")
            wrote = True
        else:
            output_files = {
                "markdown": f"{stem}.md",
                "summary": f"{stem}.summary.md",
                "manifest": f"{stem}.manifest.json",
            }
    else:
        output_files = {
            "markdown": f"{stem}.md",
            "summary": f"{stem}.summary.md",
            "manifest": f"{stem}.manifest.json",
        }
    read_back = False
    if root is not None:
        read_back = all(
            (root / name).is_file()
            for name in output_files.values()
        )
        if read_back:
            try:
                for name in output_files.values():
                    (root / name).read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                read_back = False
    result = _public_result(record, output_files, cached=cached, wrote=wrote, read_back=read_back)
    if include_content:
        result["markdown"] = record.markdown
        result["summary"] = record.summary
        result["metadata"] = record.metadata
    return result


def convert_documents(
    paths: Iterable[str | Path],
    output_dir: str | Path | None = None,
    *,
    ocr: bool = False,
    redact: bool = True,
    max_input_bytes: int = _MAX_INPUT_BYTES,
) -> dict[str, Any]:
    """Convert a bounded batch; one bad document does not hide other results."""

    items: list[dict[str, Any]] = []
    for path in paths:
        try:
            items.append(convert_document(path, output_dir, ocr=ocr, redact=redact, max_input_bytes=max_input_bytes))
        except (DocumentConversionError, OSError) as error:
            name = Path(path).name
            items.append(
                {
                    "source_name": redact_public_text(name),
                    "status": "failed",
                    "error": redact_public_text(str(error)),
                    "privacy": {"paths_returned": False, "addresses_returned": False, "credentials_returned": False},
                }
            )
    failed = sum(1 for item in items if item.get("status") == "failed")
    return {
        "workflow": "document.to_markdown",
        "status": "completed" if items and failed == 0 else "partial" if items else "failed",
        "processed": len(items),
        "succeeded": len(items) - failed,
        "failed": failed,
        "documents": items,
        "redacted": redact,
        "privacy": {"paths_returned": False, "addresses_returned": False, "credentials_returned": False},
    }


def document_status() -> dict[str, Any]:
    """Return capability status without revealing local installation details."""

    return {
        "id": "document.to_markdown",
        "name": "Universal document to Markdown",
        "protocol": f"document-md/{DOCUMENT_PROTOCOL_VERSION}",
        "tier": "community_high",
        "status": "ready",
        "network_required": False,
        "inputs": ["text", "pdf", "docx", "pptx", "xlsx", "csv", "image"],
        "outputs": ["markdown", "summary", "manifest", "context_pack"],
        "supported_extensions": sorted(SUPPORTED_EXTENSIONS),
        "optional_backends": {
            "pdf_pypdf": importlib.util.find_spec("pypdf") is not None,
            "image_ocr": bool(os.environ.get("AEGIS_OCR_COMMAND", "").strip()) or shutil.which("tesseract") is not None,
        },
        "limits": [
            "Maximum input size is 100 MB per document.",
            "Office files are parsed from their local Open XML structure.",
            "Scanned images and scanned PDF pages need a separately configured local OCR adapter.",
            "Legacy binary Office formats are intentionally not accepted.",
        ],
        "privacy": {
            "network_required": False,
            "paths_returned": False,
            "addresses_returned": False,
            "credentials_returned": False,
        },
    }


def build_document_plan(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a document request without reading or writing local files."""

    if not isinstance(payload, Mapping):
        raise DocumentConversionError("document request must be a JSON object")
    paths = payload.get("paths")
    if not isinstance(paths, list) or not paths or not all(isinstance(item, str) and item.strip() for item in paths):
        raise DocumentConversionError("paths must be a non-empty array of local document names")
    ocr = payload.get("ocr", False)
    redact = payload.get("redact", True)
    if not isinstance(ocr, bool) or not isinstance(redact, bool):
        raise DocumentConversionError("ocr and redact must be boolean values")
    supported = sum(1 for item in paths if Path(item).suffix.lower() in SUPPORTED_EXTENSIONS)
    return {
        "workflow": "document.to_markdown",
        "status": "ready_for_review" if supported == len(paths) else "partial_ready",
        "execution": "approval_gated_local_write",
        "requires_human_review": True,
        "documents_requested": len(paths),
        "supported_count": supported,
        "unsupported_count": len(paths) - supported,
        "ocr_requested": ocr,
        "redaction_enabled": redact,
        "capability": document_status(),
        "privacy": {"paths_returned": False, "addresses_returned": False, "credentials_returned": False},
        "notice": "Review the local inputs and destination before approving conversion.",
    }


def execute_document_conversion(payload: Mapping[str, Any], *, approved: bool = False) -> dict[str, Any]:
    """Execute only the bounded document conversion after explicit approval."""

    if not approved:
        raise PermissionError("document conversion requires explicit human approval")
    if not isinstance(payload, Mapping):
        raise DocumentConversionError("document request must be a JSON object")
    plan = build_document_plan(payload)
    output_dir = payload.get("output_dir")
    if not isinstance(output_dir, str) or not output_dir.strip():
        raise DocumentConversionError("output_dir is required for an approved conversion")
    result = convert_documents(
        payload["paths"],
        output_dir,
        ocr=bool(payload.get("ocr", False)),
        redact=bool(payload.get("redact", True)),
    )
    result["execution"] = "approved_local_document_conversion"
    result["requires_human_review"] = plan["requires_human_review"]
    return result
