"""Independent integrity checks for the frozen printed-PDF period-header key."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
KEY = ROOT / "cases/pdf-header-periods/expected.json"
MANIFEST = ROOT / "cases/pdf-header-periods/manifest.json"
DISPOSITION = ROOT / "cases/pdf-header-periods/full-pack-disposition.json"
PINS = ROOT / "cases/PINS.json"
PINNED_PATHS = {
    KEY.name: "cases/pdf-header-periods/expected.json",
    MANIFEST.name: "cases/pdf-header-periods/manifest.json",
    DISPOSITION.name: "cases/pdf-header-periods/full-pack-disposition.json",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_key() -> dict[str, Any]:
    """Verify the independent oracle, fixture provenance, and exact header locators."""
    key = json.loads(KEY.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert key["schema"] == "pdf-header-periods/1", "unexpected printed-header key schema"
    assert key["decision"] == "R24-C1"
    pins = json.loads(PINS.read_text(encoding="utf-8"))
    for path in (KEY, MANIFEST, DISPOSITION):
        relative = PINNED_PATHS[path.name]
        assert pins.get(relative) == sha256(path), f"shared pin mismatch: {relative}"
    assert sha256(KEY) == manifest["expected_sha256"], "manifest expected key hash mismatch"
    assert len(key["periods"]) == 29
    assert len(key["refusal_expectations"]) == 16
    period_ids = {p["period_id"] for u in key["periods"] for p in u["periods"]}
    candidate_ids = {p["period_id"] for p in key["declared_period_candidates"]}
    assert len(period_ids) == 75
    assert len(candidate_ids) == 6
    assert not period_ids & candidate_ids
    assert len(period_ids | candidate_ids) == 81
    assert len({entry["case_id"] for entry in key["periods"]}) == 29

    for doc, source in manifest["sources"].items():
        unit_manifest = ROOT / source["unit_manifest"]
        page_manifest = ROOT / source["page_manifest"]
        assert sha256(unit_manifest) == source["unit_manifest_sha256"], doc
        assert sha256(page_manifest) == source["page_manifest_sha256"], doc
        page_index = json.loads(page_manifest.read_text(encoding="utf-8"))
        page_hashes = {int(page): digest for page, digest in page_index["pages"].items()}
        source_units = json.loads(unit_manifest.read_text(encoding="utf-8"))
        assert source_units["doc"] == doc
        assert source_units["source_name"] == source["source_name"]
        assert source_units["source_sha256"] == source["source_sha256"]
        unit_pages = {
            (unit["kind"], page)
            for unit in source_units["units"]
            for page in unit["pages"]
            if unit["kind"] != "SE"
        }
        for entry in (e for e in key["periods"] if e["doc"] == doc):
            page_path = ROOT / "tests/fixtures/pdf_pages" / entry["doc"] / f"p{entry['page_number']:03}.txt"
            actual = sha256(page_path)
            assert actual == entry["page_sha256"] == entry["manifest_page_sha256"] == page_hashes[entry["page_number"]]
            assert (entry["kind"], entry["page_number"]) in unit_pages
            lines = page_path.read_text(encoding="utf-8").splitlines()
            for header in entry["header_lines"]:
                assert 1 <= header["line"] <= len(lines)
                assert lines[header["line"] - 1] == header["text"], entry["case_id"]
            assert len(entry["periods"]) == manifest_page_columns(manifest, entry)
            assert all(period["period_id"] for period in entry["periods"])
    validate_full_pack_disposition(key, manifest)
    return key


def validate_full_pack_disposition(key: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    """Validate the separate reviewed full-pack locator dispositions and period inputs."""
    disposition = json.loads(DISPOSITION.read_text(encoding="utf-8"))
    assert disposition["schema"] == "pdf-header-full-pack-disposition/1"
    assert disposition["decision"] == "R24-C2"
    source = disposition["source"]
    frozen_source = manifest["sources"]["VMO2Q3"]
    assert source["document"] == "VMO2Q3"
    assert source["source_name"] == frozen_source["source_name"]
    assert source["source_sha256"] == frozen_source["source_sha256"]
    pages = disposition["page_text_hashes"]
    assert set(pages) == {"46", "48"}
    for page_facts in pages.values():
        assert re.fullmatch(r"[0-9a-f]{64}", page_facts["utf8_text_sha256"])
        assert page_facts["line_count"] > 0
        assert page_facts["extractor"]

    units = {unit["locator"]: unit for unit in disposition["units"]}
    assert set(units) == {"page:46", "page:48"}
    summary = units["page:46"]
    assert summary["kind"] == "CFS"
    assert summary["disposition"] == "positive_period_mapping"
    assert summary["printed_title"] == "Condensed Consolidated Statements of Cash Flows"
    expected_ytd = (
        ("2025-01-01", "2025-09-30", 9, 2025),
        ("2024-01-01", "2024-09-30", 9, 2024),
    )
    actual_ytd = tuple(
        (p["start_date"], p["end_date"], p["duration_months"], p["fiscal_year"])
        for p in summary["period_columns"]
    )
    assert actual_ytd == expected_ytd, "R24-C2 page 46 nine-month periods changed"
    assert [row["line"] for row in summary["table_rows"]] == [17, 18, 19, 20, 21]

    appendix = units["page:48"]
    assert appendix["kind"] == "IS"
    assert appendix["disposition"] == "refuse_non_period_mappable"
    assert appendix["expected_mapping"] == "refuse_all_entity_columns"
    assert appendix["printed_period"]["start_date"] == "2025-01-01"
    assert appendix["printed_period"]["end_date"] == "2025-09-30"
    assert len(appendix["entity_columns"]) == 5
    assert {item["kind"] for item in disposition["co_located_statement_blocks_on_page48"]} == {"BS", "CI"}
    assert len(key["periods"]) == 29 and sum(len(unit["periods"]) for unit in key["periods"]) == 75
    return disposition


def manifest_page_columns(manifest: dict[str, Any], entry: dict[str, Any]) -> int:
    page = next(
        p for p in manifest["pages"]
        if p["doc"] == entry["doc"] and p["page"] == entry["page_number"]
    )
    return page["column_count"]


def main() -> int:
    """CLI entry: return nonzero on any key, pin, fixture, or locator failure."""
    try:
        key = validate_key()
    except (AssertionError, OSError, ValueError, KeyError, StopIteration) as error:
        print(f"PDF header key validation failed: {error}", file=sys.stderr)
        return 1
    identifiers = {p["period_id"] for unit in key["periods"] for p in unit["periods"]}
    identifiers.update(p["period_id"] for p in key["declared_period_candidates"])
    disposition = json.loads(DISPOSITION.read_text(encoding="utf-8"))
    print(
        f"Validated {len(key['periods'])} statement entries, "
        f"{sum(len(p['periods']) for p in key['periods'])} columns, "
        f"{len(key['declared_period_candidates'])} declared candidates, "
        f"{len(identifiers)} period IDs, {len(key['refusal_expectations'])} refusal controls, "
        f"and {len(disposition['units'])} supplemental full-pack dispositions."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
