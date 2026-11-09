"""Damaged issuer files become unreadable sources, never a crash of the whole pack (S15 A01).

Before the fix, zlib.error and RuntimeError (zipfile) and AttributeError and LimitReachedError
(pypdf) escaped `prepare_source`, so one bad file among the issuer files stopped `prepare()` and
no pack was written for the good sources either. Each file below is built by hand, so the
expected status follows from its construction, not from the production reader.
"""

import io
import logging
import zipfile
from datetime import date
from pathlib import Path

import pytest

from deploy_vii import preparation
from deploy_vii.contracts import Run
from deploy_vii.preparation import PreparationRequest, SourceRequest, prepare, prepare_source

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PDF = "application/pdf"
NS = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
WORKBOOK = f"<workbook {NS}><sheets/></workbook>"


@pytest.fixture(autouse=True)
def _no_ocr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(preparation.shutil, "which", lambda name: None)
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


def _workbook_zip() -> tuple[bytes, zipfile.ZipInfo]:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("xl/workbook.xml", WORKBOOK)
    raw = buffer.getvalue()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        return raw, archive.getinfo("xl/workbook.xml")


def _bad_deflate_xlsx() -> bytes:
    """workbook.xml's compressed bytes become 0xFF: BFINAL=1 with the reserved block type 11,
    which zlib refuses ("invalid block type")."""
    raw, info = _workbook_zip()
    name_length = int.from_bytes(raw[info.header_offset + 26 : info.header_offset + 28], "little")
    extra_length = int.from_bytes(raw[info.header_offset + 28 : info.header_offset + 30], "little")
    start = info.header_offset + 30 + name_length + extra_length
    data = bytearray(raw)
    data[start : start + info.compress_size] = b"\xff" * info.compress_size
    return bytes(data)


def _encrypted_member_xlsx() -> bytes:
    """Bit 0 of the general-purpose flags (local header offset 6, central entry offset 8) marks
    workbook.xml encrypted; zipfile then refuses it without a password (RuntimeError)."""
    raw, info = _workbook_zip()
    data = bytearray(raw)
    data[info.header_offset + 6] |= 0x01
    central = raw.index(b"PK\x01\x02")
    data[central + 8] |= 0x01
    return bytes(data)


def _pdf(objects: list[str], trailer: str = "<< /Size {size} /Root 1 0 R >>") -> bytes:
    """A PDF whose xref offsets are computed here, so strict pypdf reads its structure."""
    body = b"%PDF-1.4\n"
    offsets = []
    for number, text in enumerate(objects, 1):
        offsets.append(len(body))
        body += f"{number} 0 obj\n{text}\nendobj\n".encode()
    xref = len(body)
    body += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    body += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    body += f"trailer\n{trailer.format(size=len(objects) + 1)}\nstartxref\n{xref}\n%%EOF\n".encode()
    return body


FONT = "<< /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >>"


def _page(contents: str) -> str:
    return f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources {FONT} {contents} >>"


def _stream(text: str) -> str:
    return f"<< /Length {len(text)} >>\nstream\n{text}\nendstream"


def _damaged_page_pdf() -> bytes:
    """Page 1's /Contents is a plain dictionary where a stream belongs (pypdf raises
    AttributeError: no get_data); page 2 holds the text "Revenue 100"."""
    return _pdf(
        [
            "<< /Type /Catalog /Pages 2 0 R >>",
            "<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>",
            _page("/Contents 5 0 R"),
            _page("/Contents 6 0 R"),
            "<< /Foo 1 >>",
            _stream("BT /F1 12 Tf 72 700 Td (Revenue 100) Tj ET"),
        ]
    )


def _self_reference_pdf() -> bytes:
    """Object 3, the only page, is the reference `3 0 R` itself; flattening the page tree makes
    pypdf raise AttributeError (an IndirectObject's indirect_reference has no setter)."""
    return _pdf(
        [
            "<< /Type /Catalog /Pages 2 0 R >>",
            "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "3 0 R",
        ]
    )


def _numeric_trailer_pdf() -> bytes:
    """The trailer is the number 5 where a dictionary belongs (pypdf's AttributeError: items)."""
    return _pdf(["<< /Type /Catalog >>"], trailer="5")


@pytest.mark.parametrize(
    ("raw", "media_type", "error"),
    [
        (_bad_deflate_xlsx(), XLSX, "error"),  # zlib.error's class name
        (_encrypted_member_xlsx(), XLSX, "RuntimeError"),
        (_self_reference_pdf(), PDF, "PyPdfError"),
        (_numeric_trailer_pdf(), PDF, "PyPdfError"),
    ],
    ids=["zlib", "encrypted-member", "self-reference", "numeric-trailer"],
)
def test_a_damaged_source_is_unreadable_with_its_reason(
    raw: bytes, media_type: str, error: str
) -> None:
    source = prepare_source(SourceRequest(source_id="bad", path="bad", media_type=media_type), raw)
    assert source.status == "unreadable"
    assert source.extraction_status == "blocked"
    assert source.limitation is not None
    assert source.limitation.startswith(f"Preparation failed ({error}): ")
    assert source.spans == ()


def test_a_damaged_page_is_unreadable_and_the_other_page_is_kept() -> None:
    # page 1 raises inside pypdf; page 2 is intact, so the source stays ready on page 2 alone
    source = prepare_source(
        SourceRequest(source_id="pdf", path="a.pdf", media_type=PDF), _damaged_page_pdf()
    )
    assert source.status == "ready"
    assert [(item.locator, item.status) for item in source.coverage] == [
        ("page:1", "unreadable"),
        ("page:2", "retained"),
    ]
    assert source.coverage[0].limitation == "Extraction failed: AttributeError"
    assert [span.locator for span in source.spans] == ["page:2"]
    assert "Revenue 100" in source.spans[0].text


def test_one_damaged_file_still_lets_the_pack_be_written(tmp_path: Path) -> None:
    root = tmp_path / "src"
    root.mkdir()
    (root / "good.txt").write_text("Issuer Co revenue 100\n")
    (root / "bad.xlsx").write_bytes(_bad_deflate_xlsx())
    (root / "bad.pdf").write_bytes(_self_reference_pdf())
    request = PreparationRequest(
        run=Run(
            run_id="r1",
            issuer_id="i",
            issuer_name="Issuer Co",
            as_of=date(2026, 1, 1),
            case_kind="synthetic",
        ),
        sources=(
            SourceRequest(source_id="good", path="good.txt", media_type="text/plain"),
            SourceRequest(source_id="sheet", path="bad.xlsx", media_type=XLSX),
            SourceRequest(source_id="deck", path="bad.pdf", media_type=PDF),
        ),
    )
    pack = prepare(request, root, tmp_path / "out")
    assert [(item.source_id, item.status) for item in pack.sources] == [
        ("good", "ready"),
        ("sheet", "unreadable"),
        ("deck", "unreadable"),
    ]
    assert (tmp_path / "out").exists()


def _two_sheet_xlsx(data: str, notes: str) -> bytes:
    """A workbook of sheets Data and Notes whose sheetData (and any mergeCells) are given."""
    rels = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    sheet = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "xl/workbook.xml",
            f'<workbook {NS} xmlns:r="{rels}"><sheets><sheet name="Data" sheetId="1" r:id="d"/>'
            '<sheet name="Notes" sheetId="2" r:id="n"/></sheets></workbook>',
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="d" Type="{sheet}" Target="worksheets/d.xml"/>'
            f'<Relationship Id="n" Type="{sheet}" Target="worksheets/n.xml"/></Relationships>',
        )
        archive.writestr("xl/worksheets/d.xml", f"<worksheet {NS}>{data}</worksheet>")
        archive.writestr("xl/worksheets/n.xml", f"<worksheet {NS}>{notes}</worksheet>")
    return buffer.getvalue()


def test_cells_and_rows_without_r_take_the_next_address() -> None:
    # S15-C04: `r` is optional (ECMA-376 18.3.1.4). Expected by hand: after B3 comes C3; the row
    # after row 3 is row 4, its first cell A4; after Z5 comes AA5.
    data = (
        '<sheetData><row r="3"><c r="B3"><v>1</v></c><c><v>2</v></c></row>'
        '<row><c><v>3</v></c></row><row r="5"><c r="Z5"><v>4</v></c><c><v>5</v></c></row>'
        "</sheetData>"
    )
    notes = '<sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>n</t></is></c></row></sheetData>'
    source = prepare_source(
        SourceRequest(source_id="wb", path="wb.xlsx", media_type=XLSX), _two_sheet_xlsx(data, notes)
    )
    assert source.status == "ready", source.limitation
    cells = [(s.locator, s.text) for s in source.spans if s.locator.startswith("sheet:Data!")]
    assert cells == [
        ("sheet:Data!B3", "1"),
        ("sheet:Data!C3", "2"),
        ("sheet:Data!A4", "3"),
        ("sheet:Data!Z5", "4"),
        ("sheet:Data!AA5", "5"),
    ]


def test_a_sheet_of_blank_styled_cells_and_merges_is_empty() -> None:
    # S15-C06: blank styled cells and a merged range are no content, so Notes is "empty" and the
    # limitation says so; a formula with no cache is content.
    data = '<sheetData><row r="1"><c r="A1"><f>B1*2</f></c></row></sheetData>'
    notes = (
        '<sheetData><row r="1"><c r="A1" s="0"/><c r="B1" s="0" t="inlineStr"><is><t> </t></is>'
        '</c></row></sheetData><mergeCells count="1"><mergeCell ref="A1:B1"/></mergeCells>'
    )
    source = prepare_source(
        SourceRequest(source_id="wb", path="wb.xlsx", media_type=XLSX), _two_sheet_xlsx(data, notes)
    )
    assert [(c.locator, c.status) for c in source.coverage] == [
        ("sheet:Data", "retained"),
        ("sheet:Notes", "empty"),
    ]
    assert source.limitation is not None and "sheet:Notes: empty" in source.limitation
