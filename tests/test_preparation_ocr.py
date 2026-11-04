"""The OCR backup of PDF preparation (CP1H-R23.23, T22).

A page whose text layer is empty is read through the installed `pdftoppm` and `tesseract`
binaries. Answer key (read, never written): ``tests/fixtures/pdf_ocr/tdg-ocr.pdf``, four pages built
from the real TDG FY2024 10-K: page 1 has its text layer, pages 2 and 3 are images of the balance
sheet and the income statement, page 4 is a blank image.
"""

import io
import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, NameObject, NumberObject

from deploy_vii import preparation as prep
from deploy_vii.contracts import Coverage, Source
from deploy_vii.preparation import SourceRequest

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "pdf_ocr" / "tdg-ocr.pdf"
REQUEST = SourceRequest(source_id="doc", path="tdg-ocr.pdf", media_type="application/pdf")
EMPTY = "No extractable text; inspect original, OCR may be required"
NOTE = (
    "PDF text/layout extracted only; visual tables, charts, image regions and reading order "
    "require fidelity review. No OCR performed."
)
TODAY = (NOTE,)
needs_binaries = pytest.mark.skipif(
    shutil.which("pdftoppm") is None or shutil.which("tesseract") is None,
    reason="the OCR tests need the pdftoppm and tesseract binaries on PATH",
)


def _source(raw: bytes | None = None) -> Source:
    return prep.prepare_source(REQUEST, FIXTURE.read_bytes() if raw is None else raw)


def _coverage(source: Source) -> dict[str, Coverage]:
    return {item.locator: item for item in source.coverage}


def _text(source: Source, locator: str) -> str:
    return next(span.text for span in source.spans if span.locator == locator)


def _page_one() -> bytes:
    writer = PdfWriter()
    writer.add_page(PdfReader(FIXTURE).pages[0])
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def _no_subprocess(*args: Any, **kwargs: Any) -> Any:
    pytest.fail(f"a subprocess was started: {args}")


@needs_binaries
def test_a1_pages_without_a_text_layer_are_ocrd_and_marked() -> None:
    source = _source()
    covered = _coverage(source)
    page = PdfReader(FIXTURE, strict=True).pages[0]
    own = page.extract_text(extraction_mode="layout", layout_mode_strip_rotated=False)
    assert _text(source, "page:1") == own
    assert (covered["page:1"].status, covered["page:1"].limitation) == ("retained", None)
    for locator, title in (
        ("page:2", "CONSOLIDATED BALANCE SHEETS"),
        ("page:3", "CONSOLIDATED STATEMENTS OF INCOME"),
    ):
        assert covered[locator].status == "retained"
        assert (covered[locator].limitation or "").startswith(prep.OCR_MARK)
        assert title in _text(source, locator)
    assert (covered["page:4"].status, covered["page:4"].limitation) == ("empty", EMPTY)
    assert source.extractor is not None
    assert re.fullmatch(r"pypdf/6\.21\.2\+tesseract/\d+\.\d+\.\d+", source.extractor)
    assert "with no text layer: page:2, page:3." in (source.limitation or "")
    version = source.extractor.rsplit("/", 1)[1]
    assert covered["page:2"].limitation == (
        f"{prep.OCR_MARK} (tesseract {version}); verify against the original"
    )


def test_a2_missing_binaries_leave_the_pages_empty_and_log_once(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: None)
    monkeypatch.setattr(subprocess, "run", _no_subprocess)
    caplog.set_level(logging.WARNING, logger="deploy_vii.preparation")
    source = _source()
    covered = _coverage(source)
    for locator in ("page:2", "page:3", "page:4"):
        assert covered[locator].status == "empty"
        assert covered[locator].limitation == (
            "No extractable text; OCR unavailable: pdftoppm or tesseract not found"
        )
    assert source.extractor == "pypdf/6.21.2"
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1 and warnings[0].name == "deploy_vii.preparation"


def test_a3_a_document_with_a_text_layer_is_prepared_as_before(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subprocess, "run", _no_subprocess)
    raw = _page_one()
    assert prep.pdf_content(raw).limitations == TODAY
    source = _source(raw)
    assert source.extractor == "pypdf/6.21.2"
    assert _coverage(source)["page:1"].limitation is None


def _binaries_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """The tests that stub every OCR call run without the binaries: `which` finds them."""
    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: f"/usr/bin/{name}")


def test_a4_a_timeout_leaves_the_page_empty_with_the_failure_named(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _binaries_present(monkeypatch)

    def timeout(*args: Any, **kwargs: Any) -> Any:
        raise subprocess.TimeoutExpired(cmd="tool", timeout=1)

    monkeypatch.setattr(subprocess, "run", timeout)
    caplog.set_level(logging.WARNING, logger="deploy_vii.preparation")
    covered = _coverage(_source())
    assert covered["page:2"].status == "empty"
    assert covered["page:2"].limitation == "No extractable text; OCR failed: TimeoutExpired"
    assert any(r.levelno == logging.WARNING for r in caplog.records)


def test_a5_pages_over_the_cap_stay_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    _binaries_present(monkeypatch)
    monkeypatch.setattr(subprocess, "run", _no_subprocess)
    monkeypatch.setattr(prep, "_tesseract_version", lambda: "5.5.2")
    monkeypatch.setattr(prep, "OCR_PAGE_CAP", 1)
    monkeypatch.setattr(prep, "_ocr_page", lambda *args, **kwargs: "BALANCE SHEET 2024 100")
    covered = _coverage(_source())
    assert covered["page:2"].status == "retained"
    assert (covered["page:2"].limitation or "").startswith(prep.OCR_MARK)
    assert covered["page:3"].status == "empty"
    assert covered["page:3"].limitation == "No extractable text; OCR page cap reached"


@pytest.mark.parametrize("text", ["Notes", "12 34", ""], ids=["letters", "digits", "nothing"])
def test_ocr_text_without_a_line_of_letter_and_digit_leaves_the_page_as_today(
    monkeypatch: pytest.MonkeyPatch, text: str
) -> None:
    _binaries_present(monkeypatch)
    monkeypatch.setattr(subprocess, "run", _no_subprocess)
    monkeypatch.setattr(prep, "_tesseract_version", lambda: "5.5.2")
    monkeypatch.setattr(prep, "_ocr_page", lambda *args, **kwargs: text)
    source = _source()
    covered = _coverage(source)
    for locator in ("page:2", "page:3", "page:4"):
        assert (covered[locator].status, covered[locator].limitation) == ("empty", EMPTY)
        assert _text(source, locator) == ""
    assert source.extractor == "pypdf/6.21.2"
    assert TODAY[0] in (source.limitation or "")


def test_tesseract_runs_with_page_segmentation_mode_4(monkeypatch: pytest.MonkeyPatch) -> None:
    _binaries_present(monkeypatch)
    calls: list[list[str]] = []

    def record(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append(command)
        out = b"tesseract 5.5.2\n" if "--version" in command else b"BALANCE SHEET 2024 100\n"
        return subprocess.CompletedProcess(command, 0, stdout=out, stderr=b"")

    monkeypatch.setattr(subprocess, "run", record)
    _source()
    ocr_calls = [c for c in calls if c[0] == "tesseract" and "stdout" in c]
    assert ocr_calls
    for command in ocr_calls:
        assert command[command.index("stdout") + 1 :][:2] == ["--psm", "4"]


def _resolutions(monkeypatch: pytest.MonkeyPatch, raw: bytes) -> list[str]:
    """The `-r` value of each pdftoppm call `pdf_content` makes on `raw`."""
    _binaries_present(monkeypatch)
    calls: list[list[str]] = []

    def record(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append(command)
        out = b"tesseract 5.5.2\n" if "--version" in command else b""
        return subprocess.CompletedProcess(command, 0, stdout=out, stderr=b"")

    monkeypatch.setattr(subprocess, "run", record)
    prep.pdf_content(raw)
    return [c[c.index("-r") + 1] for c in calls if c[0] == "pdftoppm"]


def test_pdftoppm_renders_at_300_dpi_and_a_very_large_page_at_a_lower_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pages = PdfReader(FIXTURE).pages
    writer = PdfWriter()
    writer.add_page(pages[1])
    out = io.BytesIO()
    writer.write(out)
    assert _resolutions(monkeypatch, out.getvalue()) == ["300"]
    huge = PdfWriter()
    huge.add_blank_page(width=7200, height=7200)
    out = io.BytesIO()
    huge.write(out)
    assert _resolutions(monkeypatch, out.getvalue()) == ["33"]


def test_a_reversed_media_box_gives_the_same_resolution_as_the_upright_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    box = [NumberObject(7200), NumberObject(7200), NumberObject(0), NumberObject(0)]
    writer.pages[0][NameObject("/MediaBox")] = ArrayObject(box)
    out = io.BytesIO()
    writer.write(out)
    assert _resolutions(monkeypatch, out.getvalue()) == ["33"]


def test_a_page_with_a_malformed_media_box_stays_empty_and_names_the_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _binaries_present(monkeypatch)

    def record(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(command, 0, stdout=b"tesseract 5.5.2\n", stderr=b"")

    monkeypatch.setattr(subprocess, "run", record)
    writer = PdfWriter()
    writer.add_page(PdfReader(FIXTURE).pages[0])
    writer.add_blank_page(width=612, height=792)
    del writer.pages[1][NameObject("/MediaBox")]
    out = io.BytesIO()
    writer.write(out)
    source = _source(out.getvalue())
    assert source.status == "ready"
    covered = _coverage(source)["page:2"]
    assert (covered.status, covered.limitation) == (
        "empty",
        "No extractable text; OCR failed: ValueError",
    )
