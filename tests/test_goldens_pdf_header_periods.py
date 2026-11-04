"""Independent golden checks for printed issuer-PDF period headers (CP1H-R24)."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from cases.prove import pdf_headers as proof
from deploy_vii.statement_extract import extract_statement_lines
from deploy_workflow import financial_workflow as fw

ROOT = Path(__file__).resolve().parents[1]
PERIOD_TYPES = {
    "instant": "PERIOD_END",
    "year": "FY",
    "quarter": "QUARTER",
    "nine_months": "YTD",
}


def _period(item: dict[str, Any]) -> dict[str, Any]:
    """Convert a frozen key period to the mapper input without deriving period identity."""
    return {
        "period_id": item["period_id"],
        "fiscal_year": "" if item["fiscal_year"] is None else str(item["fiscal_year"]),
        "fiscal_quarter": None,
        "period_type": PERIOD_TYPES[item["kind"]],
        "start_date": item["start_date"],
        "end_date": item["end_date"],
    }


def _period_book(entry: dict[str, Any]) -> dict[str, Any]:
    return {"periods": [_period(item) for item in entry["periods"]]}


def _candidate_book(key: dict[str, Any]) -> dict[str, Any]:
    return {item["period_id"]: _period(item) for item in key["declared_period_candidates"]}


def _page_table(entry: dict[str, Any], raw: str):
    locator = f"page:{entry['page_number']}"
    return extract_statement_lines(raw, locator, source_id=entry["source_name"])


def _call_header_adapter(entry: dict[str, Any], raw: str, book: dict[str, Any], table: Any | None = None):
    """Run the PDF mapper against the real extraction result and source lineage."""
    table = _page_table(entry, raw) if table is None else table
    adapter = getattr(fw, "_header_columns", None)
    if adapter is None:
        return fw._ocr_header(table, book)
    return adapter(table, book, page_text=raw, statement=entry["kind"])


def test_frozen_pdf_header_key_and_source_integrity() -> None:
    proof.validate_key()


def test_printed_headers_map_to_exact_ordered_period_ids() -> None:
    key = proof.validate_key()
    errors = []
    for entry in key["periods"]:
        page = ROOT / "tests/fixtures/pdf_pages" / entry["doc"] / f"p{entry['page_number']:03}.txt"
        raw = page.read_text(encoding="utf-8")
        expected = tuple(frozenset((p["period_id"],)) for p in entry["periods"])
        table = _page_table(entry, raw)
        original_table = deepcopy(table)
        got = _call_header_adapter(entry, raw, _period_book(entry), table)
        assert table == original_table, f"{entry['case_id']}: mapper mutated extracted table"
        if got != expected:
            errors.append(f"{entry['case_id']}: expected {expected!r}, got {got!r}")
    assert not errors, "\n".join(errors)


def test_flow_headers_without_their_own_duration_refuse_mapping() -> None:
    """Removing duration must not reinterpret a flow header as a dated balance."""
    key = proof.validate_key()
    flow = next(p for p in key["periods"] if p["case_id"] == "VMO2Q3-p9-CFS")
    page = ROOT / "tests/fixtures/pdf_pages" / flow["doc"] / f"p{flow['page_number']:03}.txt"
    raw = page.read_text(encoding="utf-8")
    # Keep the printed dates and year row while removing the explicit duration phrase.
    weakened = raw.replace("Nine months ended", "", 1)
    original_table = _page_table(flow, weakened)
    before = deepcopy(original_table)
    assert _call_header_adapter(flow, weakened, _period_book(flow), original_table) is None
    assert original_table == before


def test_candidate_periods_with_same_end_date_do_not_collapse_by_date() -> None:
    """A quarter and nine-month flow ending on 30 September remain distinct."""
    key = proof.validate_key()
    entry = next(p for p in key["periods"] if p["case_id"] == "VMO2Q3-p6-IS")
    page = ROOT / "tests/fixtures/pdf_pages" / entry["doc"] / f"p{entry['page_number']:03}.txt"
    raw = page.read_text(encoding="utf-8")
    table = _page_table(entry, raw)
    before = deepcopy(table)
    got = _call_header_adapter(entry, raw, _period_book(entry), table)
    expected = tuple(frozenset((period["period_id"],)) for period in entry["periods"])
    assert got == expected
    assert table == before


def test_six22_fiscal_year_end_does_not_map_to_same_end_quarter() -> None:
    """The 2022-01-02 fiscal-year column maps to FY 2021, not its same-end quarter."""
    key = proof.validate_key()
    entry = next(p for p in key["periods"] if p["case_id"] == "SIX22-p94-IS")
    candidates = _candidate_book(key)
    expected_periods = _period_book(entry)["periods"]
    book = {
        "periods": [
            candidates["declared-candidate-1"],
            candidates["declared-candidate-2"],
            *expected_periods[1:],
        ]
    }
    page = ROOT / "tests/fixtures/pdf_pages" / entry["doc"] / f"p{entry['page_number']:03}.txt"
    raw = page.read_text(encoding="utf-8")
    table = _page_table(entry, raw)
    before = deepcopy(table)
    got = _call_header_adapter(entry, raw, book, table)
    expected = (
        frozenset(("declared-candidate-1",)),
        frozenset((entry["periods"][1]["period_id"],)),
        frozenset((entry["periods"][2]["period_id"],)),
    )
    assert got == expected
    assert table == before


def test_vmo2_uses_declared_same_end_quarter_and_nine_month_candidates() -> None:
    """The four VMO2 columns map to the frozen 3m/9m candidate IDs in print order."""
    key = proof.validate_key()
    entry = next(p for p in key["periods"] if p["case_id"] == "VMO2Q3-p6-IS")
    candidates = _candidate_book(key)
    book = {
        "periods": [
            candidates[f"declared-candidate-{index}"]
            for index in (3, 5, 4, 6)
        ]
    }
    page = ROOT / "tests/fixtures/pdf_pages" / entry["doc"] / f"p{entry['page_number']:03}.txt"
    raw = page.read_text(encoding="utf-8")
    table = _page_table(entry, raw)
    before = deepcopy(table)
    got = _call_header_adapter(entry, raw, book, table)
    expected = tuple(
        frozenset((candidate_id,))
        for candidate_id in (
            "declared-candidate-3",
            "declared-candidate-5",
            "declared-candidate-4",
            "declared-candidate-6",
        )
    )
    assert got == expected
    assert table == before


def test_duplicate_same_type_span_end_candidate_refuses_mapping() -> None:
    key = proof.validate_key()
    entry = next(p for p in key["periods"] if p["case_id"] == "SIX22-p94-IS")
    book = _period_book(entry)
    duplicate = dict(book["periods"][0], period_id="independent-duplicate-fy-period")
    book["periods"].append(duplicate)
    page = ROOT / "tests/fixtures/pdf_pages" / entry["doc"] / f"p{entry['page_number']:03}.txt"
    raw = page.read_text(encoding="utf-8")
    table = _page_table(entry, raw)
    before = deepcopy(table)
    assert _call_header_adapter(entry, raw, book, table) is None
    assert table == before


def _run_cli_override(tmp_path: Path, *overrides: tuple[str, Path]) -> subprocess.CompletedProcess[str]:
    assignments = "\n".join(f"proof.{name} = Path({str(path)!r})" for name, path in overrides)
    wrapper = tmp_path / "invoke_pdf_header_proof.py"
    wrapper.write_text(
        "from pathlib import Path\n"
        "from cases.prove import pdf_headers as proof\n"
        f"{assignments}\n"
        "raise SystemExit(proof.main())\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, str(wrapper)], cwd=ROOT, env=env,
        text=True, capture_output=True, check=False,
    )


def _fixture_pins(tmp_path: Path) -> Path:
    pins = json.loads(proof.PINS.read_text(encoding="utf-8")) if proof.PINS.exists() else {}
    for path in (proof.KEY, proof.MANIFEST, proof.DISPOSITION):
        pins[proof.PINNED_PATHS[path.name]] = hashlib.sha256(path.read_bytes()).hexdigest()
    output = tmp_path / "PINS.json"
    output.write_text(json.dumps(pins), encoding="utf-8")
    return output


def test_proof_cli_executes_as_module_and_reports_validated_counts():
    result = subprocess.run(
        [sys.executable, str(ROOT / "cases/prove/pdf_headers.py")],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    output = result.stdout
    assert "29 statement entries" in output
    assert "75 columns" in output
    assert "81 period IDs" in output
    assert "16 refusal controls" in output


def test_proof_cli_entry_fails_closed_when_key_validation_fails(monkeypatch, capsys):
    def reject():
        raise AssertionError("frozen key mismatch")

    monkeypatch.setattr(proof, "validate_key", reject)
    assert proof.main() == 1
    captured = capsys.readouterr()
    assert "PDF header key validation failed: frozen key mismatch" in captured.err


def test_proof_cli_rejects_tampered_shared_pin(tmp_path):
    pins = _fixture_pins(tmp_path)
    baseline = _run_cli_override(tmp_path, ("PINS", pins))
    assert baseline.returncode == 0, baseline.stderr
    values = json.loads(pins.read_text(encoding="utf-8"))
    values[proof.PINNED_PATHS[proof.KEY.name]] = "0" * 64
    pins.write_text(json.dumps(values), encoding="utf-8")
    result = _run_cli_override(tmp_path, ("PINS", pins))
    assert result.returncode == 1
    assert "shared pin mismatch" in result.stderr


def test_proof_cli_rejects_tampered_key_even_when_re_pinned(tmp_path):
    key_path = tmp_path / "expected.json"
    key = json.loads(proof.KEY.read_text(encoding="utf-8"))
    key["schema"] = "tampered/1"
    key_path.write_text(json.dumps(key), encoding="utf-8")
    pins = _fixture_pins(tmp_path)
    baseline = _run_cli_override(tmp_path, ("PINS", pins))
    assert baseline.returncode == 0, baseline.stderr
    values = json.loads(pins.read_text(encoding="utf-8"))
    values[proof.PINNED_PATHS[proof.KEY.name]] = hashlib.sha256(key_path.read_bytes()).hexdigest()
    pins.write_text(json.dumps(values), encoding="utf-8")
    result = _run_cli_override(tmp_path, ("KEY", key_path), ("PINS", pins))
    assert result.returncode == 1
    assert "unexpected printed-header key schema" in result.stderr


def test_proof_cli_rejects_tampered_manifest_even_when_re_pinned(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(proof.MANIFEST.read_text(encoding="utf-8"))
    manifest["expected_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    pins = _fixture_pins(tmp_path)
    baseline = _run_cli_override(tmp_path, ("PINS", pins))
    assert baseline.returncode == 0, baseline.stderr
    values = json.loads(pins.read_text(encoding="utf-8"))
    values[proof.PINNED_PATHS[proof.MANIFEST.name]] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    pins.write_text(json.dumps(values), encoding="utf-8")
    result = _run_cli_override(tmp_path, ("MANIFEST", manifest_path), ("PINS", pins))
    assert result.returncode == 1
    assert "manifest expected key hash mismatch" in result.stderr


def test_proof_cli_rejects_tampered_full_pack_disposition_even_when_re_pinned(tmp_path):
    disposition_path = tmp_path / "full-pack-disposition.json"
    disposition = json.loads(proof.DISPOSITION.read_text(encoding="utf-8"))
    disposition["units"][0]["period_columns"][0]["end_date"] = "2025-08-31"
    disposition_path.write_text(json.dumps(disposition), encoding="utf-8")
    pins = _fixture_pins(tmp_path)
    baseline = _run_cli_override(tmp_path, ("PINS", pins))
    assert baseline.returncode == 0, baseline.stderr
    values = json.loads(pins.read_text(encoding="utf-8"))
    values[proof.PINNED_PATHS[proof.DISPOSITION.name]] = hashlib.sha256(
        disposition_path.read_bytes()
    ).hexdigest()
    pins.write_text(json.dumps(values), encoding="utf-8")
    result = _run_cli_override(tmp_path, ("DISPOSITION", disposition_path), ("PINS", pins))
    assert result.returncode == 1
    assert "R24-C2 page 46 nine-month periods changed" in result.stderr


def test_proof_cli_rejects_supplemental_shared_pin_drift(tmp_path):
    pins = _fixture_pins(tmp_path)
    baseline = _run_cli_override(tmp_path, ("PINS", pins))
    assert baseline.returncode == 0, baseline.stderr
    values = json.loads(pins.read_text(encoding="utf-8"))
    values[proof.PINNED_PATHS[proof.DISPOSITION.name]] = "0" * 64
    pins.write_text(json.dumps(values), encoding="utf-8")
    result = _run_cli_override(tmp_path, ("PINS", pins))
    assert result.returncode == 1
    assert f"shared pin mismatch: {proof.PINNED_PATHS[proof.DISPOSITION.name]}" in result.stderr
