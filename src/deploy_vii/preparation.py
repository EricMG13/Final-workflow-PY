"""Freeze explicitly selected sources; extraction never asserts analytical sufficiency."""

import hashlib
import io
import json
import logging
import posixpath
import re
import shutil
import subprocess
import tempfile
import zlib
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Literal, Self
from urllib.parse import quote
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

from pydantic import model_validator
from pypdf import PageObject, PdfReader
from pypdf.errors import DependencyError, PyPdfError

from deploy_vii.contracts import Contract, Coverage, Identifier, Run, Source, Span, Text

MAX_BYTES = 50 * 1024 * 1024
MAX_EXPANDED_BYTES = 200 * 1024 * 1024
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
LOGGER = logging.getLogger(__name__)
OCR_PAGE_CAP = 20  # pages OCR'd per document; one subprocess pair each
# ponytail: ceiling: a very large page renders at a low dpi and OCRs poorly, so its arithmetic
# checks fail closed; upgrade: tile the page if real documents need it.
OCR_MAX_PIXELS = 3300  # longest rendered side: 11 in at 300 dpi
OCR_MARK = "OCR text: the page has no text layer"
EMPTY_PAGE = "No extractable text; inspect original, OCR may be required"
OCR_UNAVAILABLE = "No extractable text; OCR unavailable: pdftoppm or tesseract not found"
OCR_CAP_REACHED = "No extractable text; OCR page cap reached"


class SourceRequest(Contract):
    source_id: Identifier
    path: Text
    media_type: Literal[
        "text/plain",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ]


class PreparationRequest(Contract):
    schema_version: Literal["preparation-request/1"] = "preparation-request/1"
    run: Run
    sources: tuple[SourceRequest, ...]

    @model_validator(mode="after")
    def identities(self) -> Self:
        if len({item.source_id for item in self.sources}) != len(self.sources):
            raise ValueError("duplicate source identity")
        return self


class PreparedPack(Contract):
    schema_version: Literal["prepared-pack/1"] = "prepared-pack/1"
    run: Run
    sources: tuple[Source, ...]

    @model_validator(mode="after")
    def identities(self) -> Self:
        if len({source.source_id for source in self.sources}) != len(self.sources):
            raise ValueError("duplicate prepared source identity")
        return self


class Extraction(Contract):
    spans: tuple[Span, ...]
    coverage: tuple[Coverage, ...]
    limitations: tuple[str, ...] = ()
    ocr_version: str | None = None

    @model_validator(mode="after")
    def distinct_locators(self) -> Self:
        if len({span.locator for span in self.spans}) != len(self.spans):
            raise ValueError("Duplicate extracted locators")
        if len({item.locator for item in self.coverage}) != len(self.coverage):
            raise ValueError("Duplicate extraction coverage")
        return self


def text_content(raw: bytes) -> Extraction:
    text = raw.decode("utf-8-sig", errors="strict")
    if "\x00" in text:
        raise ValueError("NUL bytes: not supported UTF-8 text")
    spans = tuple(
        Span(locator=f"line:{i}", text=line) for i, line in enumerate(text.splitlines(), 1)
    )
    return Extraction(
        spans=spans,
        coverage=(Coverage(locator="document", status="retained" if text.strip() else "empty"),),
    )


def _tesseract_version() -> str:
    """The version `tesseract --version` prints on its first line (`tesseract X.Y.Z`)."""
    done = subprocess.run(["tesseract", "--version"], check=True, capture_output=True, timeout=30)
    lines = (done.stdout or done.stderr).decode("utf-8").splitlines()
    found = lines[0].removeprefix("tesseract").strip() if lines else ""
    if not found:
        raise OSError("tesseract --version printed no version")
    return found


def _ocr_page(source: Path, number: int, dpi: int) -> str:
    """OCR one page of a PDF file through the installed pdftoppm and tesseract binaries."""
    image = source.parent / f"page-{number}"
    subprocess.run(
        ["pdftoppm", "-r", str(dpi), "-gray", "-f", str(number), "-l", str(number)]
        + ["-png", "-singlefile", str(source), str(image)],
        check=True,
        capture_output=True,
        timeout=60,
    )
    done = subprocess.run(
        ["tesseract", f"{image}.png", "stdout", "--psm", "4"]
        + ["-c", "preserve_interword_spaces=1"],
        check=True,
        capture_output=True,
        timeout=120,
    )
    return done.stdout.decode("utf-8")


def _dpi(page: PageObject) -> int:
    """300, or lower so that the longest rendered side is at most `OCR_MAX_PIXELS`."""
    longest = max(abs(float(page.mediabox.width)), abs(float(page.mediabox.height)))
    return int(min(300, OCR_MAX_PIXELS * 72 / longest)) if longest > 0 else 300


def _substantive(text: str) -> bool:
    """At least one line holds both an ASCII letter and a digit (a blank page does not)."""
    return any(
        re.search("[A-Za-z]", line) and re.search("[0-9]", line) for line in text.splitlines()
    )


class _Ocr:
    """The OCR backup for one PDF (CP1H-R23.23). A page that cannot be read stays empty, with
    the reason as its limitation; each failure is logged. `read_pages` holds the locators whose
    OCR text was kept."""

    def __init__(self, raw: bytes) -> None:
        self.raw = raw
        self.version: str | None = None
        self.read_pages: list[str] = []
        self._attempts = 0
        self._available: bool | None = None
        self._directory: tempfile.TemporaryDirectory[str] | None = None

    def close(self) -> None:
        if self._directory is not None:
            self._directory.cleanup()

    def _file(self) -> Path:
        if self._directory is None:
            self._directory = tempfile.TemporaryDirectory()
            (Path(self._directory.name) / "in.pdf").write_bytes(self.raw)
        return Path(self._directory.name) / "in.pdf"

    def page(self, locator: str, number: int, page: PageObject) -> tuple[str | None, str]:
        """The OCR text to keep (None when none) and the page's limitation when none is kept."""
        if self._available is None:
            self._available = bool(shutil.which("pdftoppm") and shutil.which("tesseract"))
            if not self._available:
                LOGGER.warning("OCR unavailable: pdftoppm or tesseract not found on PATH")
        if not self._available:
            return None, OCR_UNAVAILABLE
        if self._attempts >= OCR_PAGE_CAP:
            return None, OCR_CAP_REACHED
        self._attempts += 1
        try:
            if self.version is None:
                self.version = _tesseract_version()
            text = _ocr_page(self._file(), number, _dpi(page))
        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            OSError,
            ValueError,  # the strict UTF-8 decode (UnicodeDecodeError) and a malformed mediabox
        ) as error:
            LOGGER.warning("OCR failed for %s: %s: %s", locator, type(error).__name__, error)
            return None, f"No extractable text; OCR failed: {type(error).__name__}"
        if not _substantive(text):
            return None, EMPTY_PAGE
        self.read_pages.append(locator)
        return text, f"{OCR_MARK} (tesseract {self.version}); verify against the original"


def pdf_content(raw: bytes) -> Extraction:
    reader = PdfReader(io.BytesIO(raw), strict=True)
    if reader.is_encrypted:
        raise ValueError("Encrypted PDF: supply an authorized decrypted copy")
    ocr = _Ocr(raw)
    with closing(ocr):
        return _pdf_pages(reader, ocr)


# What reading one page can raise: pypdf's own errors (a bad filter, a stream it cannot decode, a
# filter whose binary is absent), an unsupported filter, malformed objects and deep nesting.
_PAGE_ERRORS = (
    PyPdfError,
    DependencyError,
    NotImplementedError,
    ValueError,
    KeyError,
    TypeError,
    RecursionError,
)


class _Warnings(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


@contextmanager
def _filter_warnings() -> Iterator[list[str]]:
    """The warnings pypdf's stream filters log meanwhile: it decodes a corrupt stream it cannot
    repair to nothing and only logs why."""
    logger = logging.getLogger("pypdf.filters")
    handler, level = _Warnings(), logger.level
    if not logger.isEnabledFor(logging.WARNING):
        logger.setLevel(logging.WARNING)
    logger.addHandler(handler)
    try:
        yield handler.messages
    finally:
        logger.removeHandler(handler)
        logger.setLevel(level)


def _page_text(locator: str, page: PageObject) -> str | Coverage:
    """The page's layout text, or its unreadable coverage: a failure is this page's alone."""
    with _filter_warnings() as warnings:
        try:
            content = page.get_contents()
            data = b"" if content is None else content.get_data()
            if len(data) > MAX_BYTES:
                limitation = "Content stream exceeds extraction limit"
                return Coverage(locator=locator, status="unreadable", limitation=limitation)
            text = page.extract_text(extraction_mode="layout", layout_mode_strip_rotated=False)
        except _PAGE_ERRORS as error:
            limitation = f"Extraction failed: {type(error).__name__}"
            return Coverage(locator=locator, status="unreadable", limitation=limitation)
    if not text.strip() and not data and warnings:
        limitation = f"Content stream could not be decoded: {warnings[0]}"
        return Coverage(locator=locator, status="unreadable", limitation=limitation)
    return text


def _pdf_pages(reader: PdfReader, ocr: _Ocr) -> Extraction:
    spans: list[Span] = []
    coverage: list[Coverage] = []
    for index, page in enumerate(reader.pages, 1):
        locator = f"page:{index}"
        text = _page_text(locator, page)
        if isinstance(text, Coverage):
            coverage.append(text)
            continue
        if text.strip():
            spans.append(Span(locator=locator, text=text))
            coverage.append(Coverage(locator=locator, status="retained"))
            continue
        kept, limitation = ocr.page(locator, index, page)
        if kept is None:
            spans.append(Span(locator=locator, text=text))
            coverage.append(Coverage(locator=locator, status="empty", limitation=limitation))
        else:
            spans.append(Span(locator=locator, text=kept))
            coverage.append(Coverage(locator=locator, status="retained", limitation=limitation))
    notice = "No OCR performed."
    if ocr.read_pages:
        notice = (
            f"OCR (tesseract {ocr.version}) read {len(ocr.read_pages)} page(s) with no text "
            f"layer: {', '.join(ocr.read_pages)}."
        )
    return Extraction(
        spans=tuple(spans),
        coverage=tuple(coverage),
        limitations=(
            "PDF text/layout extracted only; visual tables, charts, image regions and reading "
            "order require fidelity review. " + notice,
        ),
        ocr_version=ocr.version if ocr.read_pages else None,
    )


class DamagedMember(ValueError):
    """A ZIP member that `zipfile` cannot decompress: corrupt compressed data, a truncated member
    or an encrypted one. The message names what failed (`damaged ZIP member (zlib.error: ...)`)."""


def xml_part(archive: ZipFile, path: str) -> ET.Element:
    try:
        data = archive.read(path)
    except NotImplementedError:
        raise  # an unsupported compression method: refused as it is
    except (zlib.error, EOFError, RuntimeError) as error:
        # CPython's zipfile raises these for a corrupt deflate stream, a truncated member and a
        # ZipCrypto-encrypted member (RuntimeError: password required).
        kind = type(error).__name__
        kind = kind if type(error).__module__ == "builtins" else f"{type(error).__module__}.{kind}"
        raise DamagedMember(f"damaged ZIP member ({kind}: {error})") from error
    # Reject alternate encodings before the declaration check: UTF-16 NUL bytes
    # must not hide an entity declaration from this boundary.
    raw = data.decode("utf-8-sig", errors="strict")
    if "\x00" in raw or "<!DOCTYPE" in raw.upper() or "<!ENTITY" in raw.upper():
        raise ValueError("DTD/entity declarations are not supported")
    return ET.fromstring(raw)


def column_number(address: str) -> int:
    """The 1-based column an A1 address's letters name (`A1` 1, `AB12` 28)."""
    number = 0
    for char in address:
        if char.isalpha():
            number = number * 26 + ord(char.upper()) - 64
    return number


def column_letters(number: int) -> str:
    """The A1 letters of a 1-based column (28 `AB`)."""
    letters = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters


def _shared_strings(archive: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    return [
        "".join(
            node.text or "" for node in (*item.findall("s:t", NS), *item.findall("s:r/s:t", NS))
        )
        for item in xml_part(archive, "xl/sharedStrings.xml")
    ]


def _cell_formats(archive: ZipFile) -> list[str]:
    """The number format of each cell style (`cellXfs`), custom codes or `builtin:<id>`."""
    if "xl/styles.xml" not in archive.namelist():
        return []
    style = xml_part(archive, "xl/styles.xml")
    formats = {
        item.attrib["numFmtId"]: item.attrib["formatCode"]
        for item in style.findall("s:numFmts/s:numFmt", NS)
    }
    return [
        formats.get(item.get("numFmtId", "0"), "builtin:" + item.get("numFmtId", "0"))
        for item in style.findall("s:cellXfs/s:xf", NS)
    ]


def _worksheet_path(relationship: ET.Element) -> str:
    if relationship.get("TargetMode") == "External":
        raise ValueError("External worksheet relationship is unsupported")
    target = relationship.attrib["Target"]
    path = posixpath.normpath(target.lstrip("/") if target.startswith("/") else "xl/" + target)
    if not path.startswith("xl/"):
        raise ValueError("Worksheet relationship escapes workbook")
    return path


@dataclass(frozen=True)
class _Book:
    """What every cell of a workbook is read against."""

    strings: list[str]
    styles: list[str]


@dataclass(frozen=True)
class _Place:
    """Where a cell sits: its locator, and whether its sheet, row or column is hidden."""

    locator: str
    hidden: bool


def _cell_text(cell: ET.Element, stored: str | None, book: _Book) -> str:
    kind = cell.get("t", "n")
    if kind == "s":
        string_index = int(stored or "-1")
        if not 0 <= string_index < len(book.strings):
            raise ValueError("Invalid shared-string index")
        return book.strings[string_index]
    if kind == "inlineStr":
        return "".join(
            node.text or ""
            for node in (*cell.findall("s:is/s:t", NS), *cell.findall("s:is/s:r/s:t", NS))
        )
    return stored or ""


def _cell_span(cell: ET.Element, place: _Place, book: _Book) -> Span:
    value = cell.find("s:v", NS)
    stored = value.text if value is not None else None
    formula_node = cell.find("s:f", NS)
    text = _cell_text(cell, stored, book)
    if formula_node is not None:
        formula_label = formula_node.text or "[shared/array formula; see formula metadata]"
        cache_label = stored if stored is not None else "[absent]"
        text = f"Formula: {formula_label}\nStored cache: {cache_label}"
    style_index = int(cell.get("s", "0"))
    if style_index < 0 or (book.styles and style_index >= len(book.styles)):
        raise ValueError("Invalid cell style index")
    return Span(
        locator=place.locator,
        text=text,
        formula=None if formula_node is None else ET.tostring(formula_node, encoding="unicode"),
        cached_value=stored if formula_node is not None else None,
        data_type=cell.get("t", "n"),
        number_format=book.styles[style_index] if book.styles else None,
        hidden=place.hidden,
    )


def _hidden_columns(tree: ET.Element) -> list[tuple[int, int]]:
    return [
        (int(item.attrib["min"]), int(item.attrib["max"]))
        for item in tree.findall("s:cols/s:col", NS)
        if item.get("hidden") in {"1", "true"}
    ]


@dataclass(frozen=True)
class _Sheet:
    """One worksheet's locator prefix and hidden state, with the workbook it belongs to."""

    prefix: str
    hidden: bool
    hidden_columns: list[tuple[int, int]]
    book: _Book


def _row_spans(row: ET.Element, number: int | None, sheet: _Sheet) -> list[Span]:
    """The row's cells. A cell without its optional `r` reference takes the column after the
    previous cell, as OOXML defines; `number` is the row's (None: its own `r` is malformed)."""
    spans: list[Span] = []
    hidden_row = sheet.hidden or row.get("hidden") in {"1", "true"}
    column = 0
    for cell in row.findall("s:c", NS):
        address = cell.get("r")
        if address is None:
            if number is None:
                raise ValueError("A cell without a reference is in a row with a malformed one")
            column += 1
            address = f"{column_letters(column)}{number}"
        else:
            column = column_number(address)
        hidden = hidden_row or any(low <= column <= high for low, high in sheet.hidden_columns)
        spans.append(_cell_span(cell, _Place(f"{sheet.prefix}!{address}", hidden), sheet.book))
    return spans


def _sheet_spans(tree: ET.Element, prefix: str, hidden: bool, book: _Book) -> list[Span]:
    """One span per stored cell, then one per merged range. A row without its optional `r`
    reference is the one after the previous row."""
    has_cells = tree.find("s:sheetData/s:row/s:c", NS) is not None
    sheet = _Sheet(prefix, hidden, _hidden_columns(tree) if has_cells else [], book)
    spans: list[Span] = []
    number: int | None = 0
    for row in tree.findall("s:sheetData/s:row", NS):
        reference = row.get("r")
        if reference is None:
            number = None if number is None else number + 1
        else:
            number = int(reference) if reference.isdecimal() else None
        spans += _row_spans(row, number, sheet)
    for merged in tree.findall("s:mergeCells/s:mergeCell", NS):
        spans.append(
            Span(
                locator=prefix + "!merged:" + merged.attrib["ref"],
                text="",
                note="Merged range; only anchor cell carries the stored value",
                data_type="metadata",
                hidden=hidden,
            )
        )
    return spans


def _comment_spans(archive: ZipFile) -> list[Span]:
    """Cell comments with their native XML identity; no linked source is fetched."""
    spans: list[Span] = []
    for name in sorted(archive.namelist()):
        if ("/comments/" in name and name.endswith(".xml")) or (
            name.startswith("xl/comments") and name.endswith(".xml")
        ):
            comments = xml_part(archive, name)
            authors = [item.text or "" for item in comments.findall("s:authors/s:author", NS)]
            for item in comments.findall("s:commentList/s:comment", NS):
                text = "".join(node.text or "" for node in item.findall("s:text//s:t", NS))
                spans.append(
                    Span(
                        locator="part:" + quote(name, safe="") + "!" + item.attrib["ref"],
                        text=text,
                        note=authors[int(item.get("authorId", "0"))] if authors else None,
                    )
                )
    return spans


def _epoch(workbook: ET.Element) -> str:
    date_system = workbook.find("s:workbookPr", NS)
    return (
        "1904"
        if date_system is not None and date_system.get("date1904") in {"1", "true"}
        else "1900"
    )


def xlsx_content(raw: bytes) -> Extraction:
    """Read OOXML lexemes, never calculate formulas, execute macros or follow links."""
    with ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        if len({info.filename for info in infos}) != len(infos):
            raise ValueError("Duplicate ZIP members")
        if sum(info.file_size for info in infos) > MAX_EXPANDED_BYTES:
            raise ValueError("Expanded workbook exceeds extraction limit")
        workbook = xml_part(archive, "xl/workbook.xml")
        rels = xml_part(archive, "xl/_rels/workbook.xml.rels")
        relationships = {item.attrib["Id"]: item for item in rels}
        book = _Book(strings=_shared_strings(archive), styles=_cell_formats(archive))
        limitations = (
            (
                "Workbook values are raw stored lexemes, not Excel display values. Formula caches "
                "may be absent or stale; no recalculation. Charts, drawings and embedded objects "
                "require separate visual review."
            ),
            (
                f"Workbook date system: {_epoch(workbook)}; date serials are retained without "
                "conversion."
            ),
        )
        spans: list[Span] = []
        coverage: list[Coverage] = []
        for sheet in workbook.findall("s:sheets/s:sheet", NS):
            prefix = "sheet:" + quote(sheet.attrib["name"], safe="")
            tree = xml_part(archive, _worksheet_path(relationships[sheet.attrib[REL]]))
            hidden_sheet = sheet.get("state", "visible") != "visible"
            found = _sheet_spans(tree, prefix, hidden_sheet, book)
            spans += found
            coverage.append(Coverage(locator=prefix, status="retained" if found else "empty"))
        spans += _comment_spans(archive)
        return Extraction(spans=tuple(spans), coverage=tuple(coverage), limitations=limitations)


# Each media type's extractor name (read when used: the pypdf version) and function.
_EXTRACTORS: dict[str, tuple[Callable[[], str], Callable[[bytes], Extraction]]] = {
    "text/plain": (lambda: "utf8-lines/1", text_content),
    "application/pdf": (lambda: "pypdf/" + version("pypdf"), pdf_content),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": (
        lambda: "ooxml-lexemes/1",
        xlsx_content,
    ),
}
# What an extractor raises for a source it cannot read; each becomes an unreadable source, so
# one file never stops `prepare` (RecursionError: a deeply nested formula or PDF object).
_SOURCE_ERRORS = (
    ValueError,
    UnicodeError,
    PyPdfError,
    DependencyError,
    BadZipFile,
    ET.ParseError,
    KeyError,
    IndexError,
    TypeError,
    NotImplementedError,
    RecursionError,
)


def prepare_source(request: SourceRequest, raw: bytes | None) -> Source:
    if raw is None:
        return Source(
            source_id=request.source_id,
            name=request.path,
            media_type=request.media_type,
            status="missing",
            extraction_status="blocked",
            limitation="Requested file is absent",
        )
    digest = hashlib.sha256(raw).hexdigest()
    name, extract = _EXTRACTORS[request.media_type]
    extractor = name()
    try:
        if len(raw) > MAX_BYTES:
            raise ValueError("Source exceeds extraction byte limit")
        extraction = extract(raw)
    except _SOURCE_ERRORS as error:
        return Source(
            source_id=request.source_id,
            name=request.path,
            media_type=request.media_type,
            status="unreadable",
            sha256=digest,
            extractor=extractor,
            extraction_status="blocked",
            limitation=f"Preparation failed ({type(error).__name__}): {error}",
        )
    if extraction.ocr_version:
        extractor += f"+tesseract/{extraction.ocr_version}"
    usable = any(span.text.strip() for span in extraction.spans)
    gaps = [
        item.limitation or f"{item.locator}: {item.status}"
        for item in extraction.coverage
        if item.status != "retained"
    ]
    limitations = list(extraction.limitations) + gaps
    if not usable:
        limitations.append("No extractable content; source cannot supply readiness evidence")
    return Source(
        source_id=request.source_id,
        name=request.path,
        media_type=request.media_type,
        status="ready" if usable else "unreadable",
        sha256=digest,
        extractor=extractor,
        spans=extraction.spans,
        coverage=extraction.coverage,
        extraction_status="blocked" if not usable else "degraded" if limitations else "complete",
        limitation="; ".join(limitations) or None,
    )


def prepare(request: PreparationRequest, root: Path, destination: Path) -> PreparedPack:
    """New snapshot only: preserve original bytes and source hashes; no directory scan."""
    root = root.resolve(strict=True)
    originals: dict[str, bytes] = {}
    sources: list[Source] = []
    for item in request.sources:
        path = (root / item.path).resolve()
        if Path(item.path).is_absolute() or not path.is_relative_to(root):
            raise ValueError("Source path must resolve inside the explicitly selected pack root")
        try:
            with path.open("rb") as stream:
                raw = stream.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                sources.append(
                    Source(
                        source_id=item.source_id,
                        name=item.path,
                        media_type=item.media_type,
                        status="unreadable",
                        extraction_status="blocked",
                        limitation="Source exceeds snapshot limit; no original bytes/hash captured",
                    )
                )
                continue
        except FileNotFoundError:
            raw = None
        except OSError as error:
            sources.append(
                Source(
                    source_id=item.source_id,
                    name=item.path,
                    media_type=item.media_type,
                    status="unreadable",
                    extraction_status="blocked",
                    limitation=f"Original could not be captured: {type(error).__name__}",
                )
            )
            continue
        source = prepare_source(item, raw)
        sources.append(source)
        if raw is not None and source.sha256 is not None:
            originals[source.sha256] = raw
    pack = PreparedPack(run=request.run, sources=tuple(sources))
    # A completion marker is written last. An interrupted directory is never a valid pack.
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "originals").mkdir()
    for digest, raw in originals.items():
        (destination / "originals" / digest).write_bytes(raw)
    payload = pack.model_dump_json(indent=2) + "\n"
    (destination / "pack.json").write_text(payload, encoding="utf-8")
    (destination / "complete.json").write_text(
        json.dumps({"pack_sha256": pack.content_hash()}), encoding="utf-8"
    )
    return pack


def load_pack(directory: Path) -> PreparedPack:
    pack = PreparedPack.model_validate_json((directory / "pack.json").read_bytes())
    complete = json.loads((directory / "complete.json").read_bytes())
    if complete != {"pack_sha256": pack.content_hash()}:
        raise ValueError("Prepared pack hash mismatch")
    for source in pack.sources:
        if source.sha256 is not None:
            raw = (directory / "originals" / source.sha256).read_bytes()
            if hashlib.sha256(raw).hexdigest() != source.sha256:
                raise ValueError("Original source hash mismatch")
    return pack
