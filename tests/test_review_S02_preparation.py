"""Review S02 (preparation): one damaged source never stops `prepare`, a bad PDF page costs only
that page, and cells without their optional `r` reference keep their positions. Expected
statuses, locators and limitation texts are written out literally."""

import io
from datetime import date
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, StreamObject

from deploy_vii.contracts import Run
from deploy_vii.preparation import (
    PreparationRequest,
    SourceRequest,
    column_letters,
    column_number,
    prepare,
    prepare_source,
)

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
RELNS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WORKBOOK = (
    f'<workbook xmlns="{MAIN}" xmlns:r="{RELNS}"><sheets>'
    '<sheet name="S" sheetId="1" r:id="rId1"/></sheets></workbook>'
)
RELS = (
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="x" Target="worksheets/sheet1.xml"/></Relationships>'
)


def workbook(sheet_data: str) -> bytes:
    stream = io.BytesIO()
    with ZipFile(stream, "w", ZIP_DEFLATED) as archive:
        archive.writestr("xl/workbook.xml", WORKBOOK)
        archive.writestr("xl/_rels/workbook.xml.rels", RELS)
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            f'<worksheet xmlns="{MAIN}"><sheetData>{sheet_data}</sheetData></worksheet>',
        )
    return stream.getvalue()


def one_member(payload: bytes, *, deflated: bool, encrypted: bool) -> bytes:
    """A ZIP whose `xl/workbook.xml` header claims deflate or ZipCrypto its bytes do not honour."""
    stream = io.BytesIO()
    with ZipFile(stream, "w", ZIP_STORED) as archive:
        archive.writestr("xl/workbook.xml", payload)
    raw = bytearray(stream.getvalue())
    central = raw.index(b"PK\x01\x02")
    if deflated:
        raw[8:10] = raw[central + 10 : central + 12] = ZIP_DEFLATED.to_bytes(2, "little")
    if encrypted:
        raw[6] |= 1
        raw[central + 8] |= 1
    return bytes(raw)


def xlsx(raw: bytes):  # type: ignore[no-untyped-def]
    return prepare_source(SourceRequest(source_id="w", path="w.xlsx", media_type=XLSX), raw)


@pytest.mark.parametrize(
    ("raw", "limitation"),
    [
        (
            one_member(b"\xff" * 64, deflated=True, encrypted=False),
            (
                "Preparation failed (DamagedMember): damaged ZIP member (zlib.error: Error -3 while "
                "decompressing data: invalid block type)"
            ),
        ),
        (
            one_member(b"<workbook/>", deflated=False, encrypted=True),
            (
                "Preparation failed (DamagedMember): damaged ZIP member (RuntimeError: File "
                "'xl/workbook.xml' is encrypted, password required for extraction)"
            ),
        ),
        (
            workbook('<row r="1"><c r="A1"><f>' + "<x>" * 3000 + "</x>" * 3000 + "</f></c></row>"),
            "Preparation failed (RecursionError): maximum recursion depth exceeded",
        ),
    ],
    ids=["corrupt-deflate", "encrypted-member", "deep-formula"],
)
def test_a_damaged_workbook_is_an_unreadable_source(raw: bytes, limitation: str) -> None:
    source = xlsx(raw)
    assert (source.status, source.extraction_status) == ("unreadable", "blocked")
    assert source.limitation is not None
    assert source.limitation.startswith(limitation)


def test_prepare_keeps_the_good_sources_beside_a_damaged_one(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "bad.xlsx").write_bytes(one_member(b"\xff" * 64, deflated=True, encrypted=False))
    (root / "good.txt").write_bytes(b"Revenue 1,234\n")
    run = Run(
        run_id="r", issuer_id="i", issuer_name="I", as_of=date(2026, 1, 1), case_kind="public"
    )
    request = PreparationRequest(
        run=run,
        sources=(
            SourceRequest(source_id="bad", path="bad.xlsx", media_type=XLSX),
            SourceRequest(source_id="good", path="good.txt", media_type="text/plain"),
        ),
    )
    pack = prepare(request, root, tmp_path / "pack")
    assert [(s.source_id, s.status) for s in pack.sources] == [
        ("bad", "unreadable"),
        ("good", "ready"),
    ]
    assert (tmp_path / "pack" / "complete.json").is_file()


def test_cells_and_rows_without_a_reference_take_the_next_position() -> None:
    source = xlsx(
        workbook(
            '<row r="2"><c><v>1</v></c><c><v>2</v></c><c r="E2"><v>5</v></c><c><v>6</v></c></row>'
            "<row><c><v>7</v></c></row>"
        )
    )
    assert source.status == "ready"
    cells = [(span.locator, span.text) for span in source.spans]
    assert cells == [
        ("sheet:S!A2", "1"),
        ("sheet:S!B2", "2"),
        ("sheet:S!E2", "5"),
        ("sheet:S!F2", "6"),
        ("sheet:S!A3", "7"),
    ]


def test_a_cell_without_a_reference_in_a_row_with_a_malformed_one_is_refused() -> None:
    source = xlsx(workbook('<row r="x"><c><v>1</v></c></row>'))
    assert source.status == "unreadable"
    assert source.limitation == (
        "Preparation failed (ValueError): A cell without a reference is in a row with a "
        "malformed one"
    )


def test_a_malformed_row_reference_is_ignored_while_its_cells_name_themselves() -> None:
    source = xlsx(workbook('<row r="x"><c r="C7"><v>1</v></c></row>'))
    assert [(span.locator, span.text) for span in source.spans] == [("sheet:S!C7", "1")]


@pytest.mark.parametrize(("letters", "number"), [("A", 1), ("Z", 26), ("AA", 27), ("XFD", 16384)])
def test_column_letters_and_numbers_agree(letters: str, number: int) -> None:
    assert column_number(f"{letters}12") == number
    assert column_letters(number) == letters


def _pdf(second: StreamObject) -> bytes:
    writer = PdfWriter()
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_ref = writer._add_object(font)
    first = DecodedStreamObject()
    first.set_data(b"BT /F1 12 Tf 72 700 Td (Revenue   1,234   1,100) Tj ET")
    for content in (first, second):
        page = writer.add_blank_page(612, 792)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
        )
        page[NameObject("/Contents")] = writer._add_object(content)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


def _stream(data: bytes, name: str) -> StreamObject:
    stream = StreamObject()
    stream._data = data
    stream[NameObject("/Filter")] = NameObject(name)
    return stream


@pytest.mark.parametrize(
    ("data", "name", "limitation"),
    [
        (b"zz", "/ASCIIHexDecode", "Extraction failed: PdfStreamError"),
        (b"abc", "/JBIG2Decode", "Extraction failed: DependencyError"),
        (b"abc", "/Bogus", "Extraction failed: NotImplementedError"),
        (b"<~abc", "/ASCII85Decode", "Extraction failed: ValueError"),
        (
            b"this is not zlib data at all",
            "/FlateDecode",
            (
                "Content stream could not be decoded: Error -3 while decompressing data: incorrect "
                "header check"
            ),
        ),
    ],
    ids=["bad-hex", "jbig2", "unknown-filter", "bad-ascii85", "corrupt-flate"],
)
def test_a_bad_page_stream_costs_only_that_page(data: bytes, name: str, limitation: str) -> None:
    raw = _pdf(_stream(data, name))
    source = prepare_source(
        SourceRequest(source_id="p", path="p.pdf", media_type="application/pdf"), raw
    )
    assert source.status == "ready"
    assert [(c.locator, c.status, c.limitation) for c in source.coverage] == [
        ("page:1", "retained", None),
        ("page:2", "unreadable", limitation),
    ]
    assert [span.locator for span in source.spans] == ["page:1"]
    assert "Revenue" in source.spans[0].text
