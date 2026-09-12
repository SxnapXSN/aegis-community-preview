from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from aegis_community.document_md import (
    build_document_plan,
    convert_document,
    convert_documents,
    document_status,
)
from aegis_community.context_pack import build_context_pack
from aegis_community.watch import discover_documents


def _write_zip(path: Path, members: dict[str, str]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, value in members.items():
            archive.writestr(name, value)


class DocumentPipelineTests(unittest.TestCase):
    def test_text_csv_json_and_cache_produce_ai_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "out"
            source = root / "notes.txt"
            source.write_text("A small note.\nSecond line.\n", encoding="utf-8")

            first = convert_document(source, output, redact=False)
            second = convert_document(source, output, redact=False)

            self.assertEqual("complete", first["status"])
            self.assertEqual("cached", second["status"])
            self.assertTrue((output / "notes.md").is_file())
            self.assertTrue((output / "notes.summary.md").is_file())
            manifest = json.loads((output / "notes.manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(first["content_hash"], manifest["source_hash"])
            self.assertIn("Second line", (output / "notes.md").read_text(encoding="utf-8"))

            csv_path = root / "table.csv"
            csv_path.write_text("name,value\nalpha,1\nbeta,2\n", encoding="utf-8")
            json_path = root / "config.json"
            json_path.write_text('{"enabled": true, "items": [1, 2]}', encoding="utf-8")
            batch = convert_documents([csv_path, json_path], output, redact=False)
            self.assertEqual("completed", batch["status"])
            self.assertEqual(2, batch["succeeded"])
            self.assertIn("| name | value |", (output / "table.md").read_text(encoding="utf-8"))
            self.assertIn('"enabled": true', (output / "config.md").read_text(encoding="utf-8"))

    def test_docx_pptx_and_xlsx_are_parsed_without_office_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "out"
            docx = root / "report.docx"
            _write_zip(
                docx,
                {
                    "word/document.xml": (
                        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                        '<w:body><w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Report title</w:t></w:r></w:p>'
                        '<w:p><w:r><w:t>Body text</w:t></w:r></w:p>'
                        '<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Key</w:t></w:r></w:p></w:tc>'
                        '<w:tc><w:p><w:r><w:t>Value</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>'
                    )
                },
            )
            pptx = root / "slides.pptx"
            _write_zip(
                pptx,
                {
                    "ppt/slides/slide1.xml": (
                        '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
                        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:cSld><p:spTree>'
                        '<p:sp><p:txBody><a:p><a:r><a:t>Launch plan</a:t></a:r></a:p>'
                        '<a:p><a:r><a:t>First milestone</a:t></a:r></a:p></p:txBody></p:sp>'
                        '</p:spTree></p:cSld></p:sld>'
                    )
                },
            )
            xlsx = root / "data.xlsx"
            _write_zip(
                xlsx,
                {
                    "xl/workbook.xml": (
                        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                        '<sheets><sheet name="Data" r:id="rId1"/></sheets></workbook>'
                    ),
                    "xl/_rels/workbook.xml.rels": (
                        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                        '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>'
                    ),
                    "xl/sharedStrings.xml": (
                        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                        '<si><t>Name</t></si><si><t>Score</t></si><si><t>Alice</t></si></sst>'
                    ),
                    "xl/worksheets/sheet1.xml": (
                        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
                        '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>'
                        '<row r="2"><c r="A2" t="s"><v>2</v></c><c r="B2"><v>95</v></c></row>'
                        '</sheetData></worksheet>'
                    ),
                },
            )

            docx_result = convert_document(docx, output, redact=False)
            pptx_result = convert_document(pptx, output, redact=False)
            xlsx_result = convert_document(xlsx, output, redact=False)

            self.assertEqual("complete", docx_result["status"])
            self.assertEqual("complete", pptx_result["status"])
            self.assertEqual("complete", xlsx_result["status"])
            self.assertIn("# Report title", (output / "report.md").read_text(encoding="utf-8"))
            self.assertIn("| Key | Value |", (output / "report.md").read_text(encoding="utf-8"))
            self.assertIn("Launch plan", (output / "slides.md").read_text(encoding="utf-8"))
            self.assertIn("| Name | Score |", (output / "data.md").read_text(encoding="utf-8"))
            self.assertIn("Alice", (output / "data.md").read_text(encoding="utf-8"))

    def test_pdf_fallback_and_image_boundary_are_truthful(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "out"
            pdf = root / "hello.pdf"
            pdf.write_bytes(
                b"%PDF-1.4\n1 0 obj\n<< /Length 37 >>\nstream\nBT\n(Hello PDF) Tj\nET\nendstream\nendobj\n%%EOF"
            )
            pdf_result = convert_document(pdf, output, redact=False)
            self.assertEqual("complete", pdf_result["status"])
            self.assertIn("Hello PDF", (output / "hello.md").read_text(encoding="utf-8"))

            image = root / "scan.png"
            image.write_bytes(b"not-an-image-but-a-local-test-input")
            image_result = convert_document(image, output, redact=False)
            self.assertEqual("partial", image_result["status"])
            self.assertTrue(image_result["warnings"])

    def test_open_document_epub_and_rtf_inputs_are_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "out"
            odt = root / "writer.odt"
            _write_zip(
                odt,
                {
                    "content.xml": (
                        '<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1" '
                        'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1" '
                        'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1">'
                        '<office:body><office:text><text:h text:outline-level="1">Heading</text:h>'
                        '<text:p>Paragraph</text:p><table:table table:name="Data"><table:table-row>'
                        '<table:table-cell><text:p>Key</text:p></table:table-cell>'
                        '<table:table-cell><text:p>Value</text:p></table:table-cell>'
                        '</table:table-row></table:table></office:text></office:body></office:document-content>'
                    )
                },
            )
            epub = root / "book.epub"
            _write_zip(epub, {"OEBPS/chapter.xhtml": "<h1>Chapter</h1><p>Text from ebook.</p>"})
            backslash = chr(92)
            rtf = root / "note.rtf"
            rtf.write_text("{" + backslash + "rtf1" + backslash + "ansi" + backslash + "par RTF text}", encoding="utf-8")

            odt_result = convert_document(odt, output, redact=False)
            epub_result = convert_document(epub, output, redact=False)
            rtf_result = convert_document(rtf, output, redact=False)

            self.assertEqual("complete", odt_result["status"])
            self.assertEqual("complete", epub_result["status"])
            self.assertEqual("complete", rtf_result["status"])
            self.assertIn("# Heading", (output / "writer.md").read_text(encoding="utf-8"))
            self.assertIn("| Key | Value |", (output / "writer.md").read_text(encoding="utf-8"))
            self.assertIn("Chapter", (output / "book.md").read_text(encoding="utf-8"))
            self.assertIn("RTF text", (output / "note.md").read_text(encoding="utf-8"))

    def test_plan_status_and_context_pack_are_bounded_and_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "pack"
            source = root / "private.txt"
            local_path = "C:" + chr(92) + "private" + chr(92) + "draft.txt"
            source.write_text("api_key='" + "super-secret-value" + "'\n" + local_path + "\n", encoding="utf-8")
            plan = build_document_plan({"paths": [str(source)]})
            self.assertEqual("ready_for_review", plan["status"])
            pack = build_context_pack([source], output, max_chars=10_000, chunk_chars=2_000)
            self.assertEqual("completed", pack["status"])
            self.assertTrue(pack["read_back"])
            context = (output / "context.md").read_text(encoding="utf-8")
            self.assertNotIn("super-secret-value", context)
            self.assertNotIn(local_path, context)
            self.assertTrue((output / "chunks" / "context-0001.md").is_file())

    def test_folder_discovery_excludes_output_tree_and_reports_capability(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "out"
            output.mkdir()
            (root / "source.md").write_text("source", encoding="utf-8")
            (output / "generated.md").write_text("generated", encoding="utf-8")
            found = discover_documents(root, output_dir=output)
            self.assertEqual([root / "source.md"], found)
        status = document_status()
        self.assertEqual("ready", status["status"])
        self.assertIn(".docx", status["supported_extensions"])


if __name__ == "__main__":
    unittest.main()
