"""S19 review regressions: discovery admission, in-run deliveries and the pinned handoff link.

Expected values are written here by hand.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from issuer_library_support import HOST, REPORT, client_of, fixture, locations, put, put_json

from issuer_library.discovery import discover, source_numbers
from issuer_library.model import Catalogue, Checklist, DeliveryView, Metric, digest
from issuer_library.server import Application
from issuer_library.settings import save_json

CHECKLIST = {
    "scope": "Annual review",
    "requirements": [
        {"id": stage, "stage": stage, "done": True, "evidence": ["check"]}
        for stage in ("sources", "analysis", "verification", "downstream", "delivery")
    ],
}


def run_named(cat: Catalogue, run_id: str):
    return next(run for run in cat.real if run.id == run_id)


def in_run_delivery(root: Path, run: str, issuer: str, run_id: str) -> str:
    view = DeliveryView(mode="candidate")
    view.run.run_id, view.run.issuer_id = run_id, issuer
    view.run.issuer_name, view.run.as_of = "Other Co", "2019-01-01"
    raw = view.model_dump_json().encode()
    folder = f"runs/{run}/deliveries/abc"
    put(root, f"{folder}/view.json", raw)
    put(root, f"{folder}/report.html", REPORT)
    save_json(
        root / folder / "delivery.json",
        {"files": {"view.json": digest(raw), "report.html": digest(REPORT)}},
    )
    return folder


def checklisted(root: Path) -> None:
    manifest = fixture(root)
    manifest.checklist = Checklist.model_validate(CHECKLIST)
    put_json(root, "runs/case-a/library.json", manifest)


def test_an_in_run_delivery_of_another_issuer_is_refused_and_proves_nothing(tmp_path):
    checklisted(tmp_path)
    folder = in_run_delivery(tmp_path, "case-a", "OTHER", "someone-else")
    cat = discover(str(tmp_path), Catalogue())
    run = run_named(cat, "case-a")
    assert run.artifacts == []
    assert run.completion is None
    assert f"{folder}: Delivery issuer does not match run" in cat.issues
    # Listed as an unverified run file at most; never pinned as a verified delivery.
    assert cat._allowed.get(f"{folder}/report.html", "") == ""


def test_an_in_run_delivery_of_the_admitted_issuer_still_counts(tmp_path):
    checklisted(tmp_path)
    in_run_delivery(tmp_path, "case-a", "EX", "launcher-run-1")
    run = run_named(discover(str(tmp_path), Catalogue()), "case-a")
    assert [(a.folder, a.available) for a in run.artifacts] == [
        ("runs/case-a/deliveries/abc", True)
    ]
    assert run.completion == 100


def test_a_launcher_run_checks_deliveries_against_its_workflow_json(tmp_path):
    put(tmp_path, "runs/web-run/CP-0.md", b"# CP-0\n\nRequest.\n")
    put_json(tmp_path, "runs/web-run/workflow.json", {"run": {"run_id": "r-1", "issuer_id": "AC"}})
    mine = in_run_delivery(tmp_path, "web-run", "AC", "r-1")
    cat = discover(str(tmp_path), Catalogue())
    assert [a.folder for a in run_named(cat, "web-run").artifacts] == [mine]
    put_json(tmp_path, "runs/web-run/workflow.json", {"run": {"run_id": "r-2", "issuer_id": "AC"}})
    cat = discover(str(tmp_path), Catalogue())
    assert run_named(cat, "web-run").artifacts == []
    assert f"{mine}: Delivery run does not match the run's workflow.json" in cat.issues
    put_json(tmp_path, "runs/web-run/workflow.json", {"run": {"run_id": "r-1", "issuer_id": "ZZ"}})
    cat = discover(str(tmp_path), Catalogue())
    assert f"{mine}: Delivery issuer does not match the run's workflow.json" in cat.issues


@pytest.mark.parametrize(
    ("quote", "numbers"),
    [
        ("Leverage 3,4x", set()),
        ("Segments 1,2,3", set()),
        ("FY2020-2021 revenue", {"2021"}),
        ("Revenue US$1,234.5m, down -3.5% from 1,240", {"1234.5", "-3.5", "1240"}),
        ("Debt of 12,345,678 at 4.20x", {"12345678", "4.20"}),
        ("Ratio 1.2.3 and v2", set()),
        ("Net debt -1,000 (2024).", {"-1000", "2024"}),
    ],
)
def test_only_whole_numbers_in_the_excerpt_can_admit_a_metric(quote, numbers):
    assert source_numbers(quote) == numbers


@pytest.mark.parametrize("value", ["34", "123", "-2021"])
def test_a_value_absent_from_the_source_is_refused(tmp_path, value):
    quotes = {"34": "Leverage 3,4x", "123": "Segments 1,2,3", "-2021": "FY2020-2021 revenue"}
    evidence = f"Issuer: Example Industries\nSector: Industrials\n{quotes[value]}\nVerified scope\n"
    raw = evidence.encode()
    manifest = fixture(tmp_path)
    put(tmp_path, "runs/case-a/CP-0.md", raw)
    for key, source in manifest.sources.items():
        manifest.sources[key] = source.model_copy(update={"sha256": digest(raw)})
    manifest.sources["revenue"] = manifest.sources["revenue"].model_copy(
        update={"quote": quotes[value]}
    )
    manifest.run.metrics["revenue"] = Metric(
        value=value, unit="x", period="FY2024", basis="b", source="revenue"
    )
    put_json(tmp_path, "runs/case-a/library.json", manifest)
    cat = discover(str(tmp_path), Catalogue())
    run = run_named(cat, "case-a")
    assert run.issuer == "Unclassified"
    assert run.gaps == ["Run metadata rejected: metric value absent from source excerpt"]


def test_a_pinned_handoff_the_listing_skips_is_still_served(tmp_path):
    root = tmp_path / "workspace"
    manifest = fixture(root)
    body = b"# CP-2\n\nPrimary handoff kept in a hidden folder.\n"
    put(root, "runs/case-a/.work/CP-2.md", body)
    manifest.run.handoff = "runs/case-a/.work/CP-2.md"
    put_json(root, "runs/case-a/library.json", manifest)
    app = Application(locations(tmp_path), str(root), HOST)
    run = run_named(app.catalogue, "case-a")
    assert run.handoff_href == f"/files/runs/case-a/.work/CP-2.md?sha256={digest(body)}"
    assert "runs/case-a/.work/CP-2.md" not in {f"runs/case-a/{f.name}" for f in run.files}
    response = client_of(app).get(run.handoff_href)
    assert (response.status_code, response.content) == (200, body)


def test_the_retained_workspace_keeps_its_launcher_deliveries():
    root = Path(__file__).resolve().parents[1]
    if not (root / "runs/cpos-sol-medium-20261105/deliveries").is_dir():
        pytest.skip("retained workspace not present")
    seeds = Catalogue.model_validate_json(
        (root / "apps/issuer-library/web/legacy-catalog.json").read_bytes()
    )
    cat = discover(str(root), seeds)
    for name in ("cpos-launch-cp2-reader-001", "cpos-sol-medium-20261105"):
        run = run_named(cat, name)
        assert run.artifacts and all(a.available for a in run.artifacts), name
    assert not [issue for issue in cat.issues if "does not match" in issue]
    assert (
        json.loads(
            (root / "runs/cpos-sol-medium-20261105/workflow.json").read_text(encoding="utf-8")
        )["run"]["issuer_id"]
        == "TDG"
    )
