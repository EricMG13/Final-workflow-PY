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
from contextlib import closing
from importlib.metadata import version
from pathlib import Path
from typing import Literal, Self
from urllib.parse import quote
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

from pydantic import model_validator
from pypdf import PageObject, PdfReader
from pypdf.errors import PyPdfError

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
    # `line:N` follows str.splitlines(): besides \n, \r\n and \r it breaks on \v, \f, \x1c-\x1e,
    # \x85, U+2028 and U+2029. This is the canonical source-span numbering (user ruling on
    # S15-C05, 2026-11-07): retained citations depend on it. Handoff delivery numbers its own
    # lines on \n only (handoff_delivery.physical_lines); the two are separate citation spaces.
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
    try:
        reader = PdfReader(io.BytesIO(raw), strict=True)
        if reader.is_encrypted:
            raise ValueError("Encrypted PDF: supply an authorized decrypted copy")
        pages = list(reader.pages)
    # pypdf meets a damaged trailer or page tree (a number where a dictionary belongs, an object
    # that is a reference to itself) with AttributeError; the document has no readable structure.
    except AttributeError as error:
        raise PyPdfError(f"Damaged PDF structure: {error}") from error
    ocr = _Ocr(raw)
    with closing(ocr):
        return _pdf_pages(pages, ocr)


def _pdf_pages(pages: list[PageObject], ocr: _Ocr) -> Extraction:
    spans: list[Span] = []
    coverage: list[Coverage] = []
    for index, page in enumerate(pages, 1):
        locator = f"page:{index}"
        try:
            content = page.get_contents()
            if content is not None and len(content.get_data()) > MAX_BYTES:
                coverage.append(
                    Coverage(
                        locator=locator,
                        status="unreadable",
                        limitation="Content stream exceeds extraction limit",
                    )
                )
                continue
            text = page.extract_text(extraction_mode="layout", layout_mode_strip_rotated=False)
        # A damaged page object (a loop of self references, a dictionary where a stream belongs)
        # makes pypdf raise PyPdfError or AttributeError; that page alone is unreadable.
        except (PyPdfError, AttributeError, ValueError, KeyError, TypeError) as error:
            coverage.append(
                Coverage(
                    locator=locator,
                    status="unreadable",
                    limitation=f"Extraction failed: {type(error).__name__}",
                )
            )
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


def xml_part(archive: ZipFile, path: str) -> ET.Element:
    # Reject alternate encodings before the declaration check: UTF-16 NUL bytes
    # must not hide an entity declaration from this boundary.
    raw = archive.read(path).decode("utf-8-sig", errors="strict")
    if "\x00" in raw or "<!DOCTYPE" in raw.upper() or "<!ENTITY" in raw.upper():
        raise ValueError("DTD/entity declarations are not supported")
    return ET.fromstring(raw)


def _cell_address(stated: str | None, row_number: int, previous: int) -> tuple[str, int]:
    """A cell's address and 1-based column index: the stated `r`, or, when the cell has none (or
    an empty one), the column after the row's previous cell (`previous`) in row `row_number`
    (ECMA-376 18.3.1.4)."""
    if not stated:
        column, letters = previous + 1, ""
        while column:
            column, rest = divmod(column - 1, 26)
            letters = chr(65 + rest) + letters
        return f"{letters}{row_number}", previous + 1
    index = 0
    for char in stated:
        if char.isalpha():
            index = index * 26 + ord(char.upper()) - 64
    return stated, index


def _sheet_status(spans: list[Span]) -> Literal["retained", "empty"]:
    """A sheet's coverage: retained when a cell holds non-blank text or a formula. Blank styled
    cells and merged-range metadata are no content (S15-C06)."""
    content = any(
        span.data_type != "metadata" and (span.text.strip() or span.formula) for span in spans
    )
    return "retained" if content else "empty"


def xlsx_content(raw: bytes) -> Extraction:  # noqa: C901, PLR0912, PLR0915 - pre-existing (C901 21, 21 branches, 72 statements at base)
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
        strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = [
                "".join(
                    node.text or ""
                    for node in (*item.findall("s:t", NS), *item.findall("s:r/s:t", NS))
                )
                for item in xml_part(archive, "xl/sharedStrings.xml")
            ]
        formats: dict[str, str] = {}
        styles: list[str] = []
        if "xl/styles.xml" in archive.namelist():
            style = xml_part(archive, "xl/styles.xml")
            formats = {
                item.attrib["numFmtId"]: item.attrib["formatCode"]
                for item in style.findall("s:numFmts/s:numFmt", NS)
            }
            styles = [
                formats.get(item.get("numFmtId", "0"), "builtin:" + item.get("numFmtId", "0"))
                for item in style.findall("s:cellXfs/s:xf", NS)
            ]
        spans: list[Span] = []
        coverage: list[Coverage] = []
        limitations = [
            (
                "Workbook values are raw stored lexemes, not Excel display values. Formula caches "
                "may be absent or stale; no recalculation. Charts, drawings and embedded objects "
                "require separate visual review."
            )
        ]
        date_system = workbook.find("s:workbookPr", NS)
        epoch = (
            "1904"
            if date_system is not None and date_system.get("date1904") in {"1", "true"}
            else "1900"
        )
        limitations.append(
            f"Workbook date system: {epoch}; date serials are retained without conversion."
        )
        for sheet in workbook.findall("s:sheets/s:sheet", NS):
            name = sheet.attrib["name"]
            prefix = "sheet:" + quote(name, safe="")
            relationship = relationships[sheet.attrib[REL]]
            if relationship.get("TargetMode") == "External":
                raise ValueError("External worksheet relationship is unsupported")
            target = relationship.attrib["Target"]
            path = posixpath.normpath(
                target.lstrip("/") if target.startswith("/") else "xl/" + target
            )
            if not path.startswith("xl/"):
                raise ValueError("Worksheet relationship escapes workbook")
            tree = xml_part(archive, path)
            hidden_sheet = sheet.get("state", "visible") != "visible"
            columns = tree.findall("s:cols/s:col", NS)
            before = len(spans)
            row_number = 0
            for row in tree.findall("s:sheetData/s:row", NS):
                # `r` is optional on a row and on a cell: one without it follows the previous
                row_number = int(row.get("r", row_number + 1))
                column_index = 0
                for cell in row.findall("s:c", NS):
                    address, column_index = _cell_address(cell.get("r"), row_number, column_index)
                    kind = cell.get("t", "n")
                    value = cell.find("s:v", NS)
                    stored = value.text if value is not None else None
                    formula_node = cell.find("s:f", NS)
                    formula = (
                        None
                        if formula_node is None
                        else ET.tostring(formula_node, encoding="unicode")
                    )
                    if kind == "s":
                        string_index = int(stored or "-1")
                        if not 0 <= string_index < len(strings):
                            raise ValueError("Invalid shared-string index")
                        text = strings[string_index]
                    elif kind == "inlineStr":
                        text = "".join(
                            node.text or ""
                            for node in (
                                *cell.findall("s:is/s:t", NS),
                                *cell.findall("s:is/s:r/s:t", NS),
                            )
                        )
                    else:
                        text = stored or ""
                    if formula_node is not None:
                        formula_label = (
                            formula_node.text or "[shared/array formula; see formula metadata]"
                        )
                        cache_label = stored if stored is not None else "[absent]"
                        text = f"Formula: {formula_label}\nStored cache: {cache_label}"
                    hidden_column = any(
                        item.get("hidden") in {"1", "true"}
                        and int(item.attrib["min"]) <= column_index <= int(item.attrib["max"])
                        for item in columns
                    )
                    style_index = int(cell.get("s", "0"))
                    if style_index < 0 or (styles and style_index >= len(styles)):
                        raise ValueError("Invalid cell style index")
                    spans.append(
                        Span(
                            locator=prefix + "!" + address,
                            text=text,
                            formula=formula,
                            cached_value=stored if formula_node is not None else None,
                            data_type=kind,
                            number_format=styles[style_index] if styles else None,
                            hidden=hidden_sheet
                            or row.get("hidden") in {"1", "true"}
                            or hidden_column,
                        )
                    )
            for merged in tree.findall("s:mergeCells/s:mergeCell", NS):
                spans.append(
                    Span(
                        locator=prefix + "!merged:" + merged.attrib["ref"],
                        text="",
                        note="Merged range; only anchor cell carries the stored value",
                        data_type="metadata",
                        hidden=hidden_sheet,
                    )
                )
            coverage.append(Coverage(locator=prefix, status=_sheet_status(spans[before:])))
        # Keep cell comments with their native XML identity; no linked source is fetched.
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
        return Extraction(
            spans=tuple(spans), coverage=tuple(coverage), limitations=tuple(limitations)
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
    extractor = {
        "text/plain": "utf8-lines/1",
        "application/pdf": "pypdf/" + version("pypdf"),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "ooxml-lexemes/1",
    }[request.media_type]
    try:
        if len(raw) > MAX_BYTES:
            raise ValueError("Source exceeds extraction byte limit")
        extraction = {
            "text/plain": text_content,
            "application/pdf": pdf_content,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": xlsx_content,
        }[request.media_type](raw)
    # Damaged input in any of the three readers is an unreadable source, never a crash of the
    # whole pack: zlib.error, EOFError and RuntimeError (an encrypted member) come from zipfile,
    # PyPdfError (LimitReachedError, PdfReadError) from pypdf outside a single page.
    except (
        ValueError,
        UnicodeError,
        PyPdfError,
        BadZipFile,
        zlib.error,
        EOFError,
        RuntimeError,
        ET.ParseError,
        KeyError,
        IndexError,
        TypeError,
        NotImplementedError,
    ) as error:
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
