"""Discovery over a hand-written workspace; expected values are written here by hand."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from issuer_library_support import EVIDENCE, add_delivery, fixture, put, put_json

from issuer_library.discovery import assess_checklist, discover, go_quote, stated_numbers
from issuer_library.model import (
    Artifact,
    Catalogue,
    Checklist,
    DeliveryView,
    Run,
    digest,
    pinned_url,
    read_file,
)

ROOT = Path(__file__).resolve().parents[1]
CHECKLIST = {
    "scope": "Annual review",
    "requirements": [
        {"id": "s", "stage": "sources", "done": True, "evidence": ["check"]},
        {"id": "a", "stage": "analysis", "done": True, "evidence": ["check"]},
        {"id": "v", "stage": "verification", "done": False},
        {"id": "c", "stage": "downstream", "done": False},
        {"id": "d", "stage": "delivery", "done": False},
    ],
}


def run_named(cat: Catalogue, run_id: str) -> Run:
    return next(run for run in cat.real if run.id == run_id)


def test_discovery_preserves_zero_and_finds_new_run(tmp_path: Path) -> None:
    fixture(tmp_path)
    cat = discover(str(tmp_path), Catalogue())
    assert cat.issues == [] and len(cat.real) == 1
    revenue = cat.real[0].metrics["revenue"]
    assert revenue is not None and (revenue.value, revenue.period) == ("0", "FY2024")
    assert cat.real[0].completion is None
    put(tmp_path, "runs/new-case/CP-0.md", b"New evidence")
    cat = discover(str(tmp_path), Catalogue())
    assert len(cat.real) == 2
    assert cat.real[1].issuer == "Unclassified", "filename became issuer identity"


def test_changed_and_malformed_metadata_remain_visible(tmp_path: Path) -> None:
    fixture(tmp_path)
    put(tmp_path, "runs/case-a/CP-0.md", b"changed")
    cat = discover(str(tmp_path), Catalogue())
    assert len(cat.real) == 1 and cat.issues and cat.real[0].metrics == {} and cat.sources == {}
    put(tmp_path, "runs/case-a/library.json", b"{")
    cat = discover(str(tmp_path), Catalogue())
    assert len(cat.real) == 1 and cat.issues


@pytest.mark.parametrize(
    "change",
    [
        {"value": "1"},
        {"value": "NaN"},
        {"value": "1e0"},
        {"basis": ""},
        {"period": ""},
        {"source": "missing"},
    ],
)
def test_metric_cannot_lose_basis_or_invent_value(tmp_path: Path, change: dict[str, str]) -> None:
    manifest = fixture(tmp_path)
    metric = manifest.run.metrics["revenue"]
    assert metric is not None
    manifest.run.metrics["revenue"] = metric.model_copy(update=change)
    put_json(tmp_path, "runs/case-a/library.json", manifest)
    cat = discover(str(tmp_path), Catalogue())
    assert cat.issues and cat.real[0].metrics == {}, "invalid metric admitted"


@pytest.mark.parametrize("kind", ["", "cited", "calculated", "synthetic", "unknown", "C1"])
def test_metric_provenance_is_only_producer_declared(tmp_path: Path, kind: str) -> None:
    manifest = fixture(tmp_path)
    metric = manifest.run.metrics["revenue"]
    assert metric is not None
    metric.provenance = kind
    put_json(tmp_path, "runs/case-a/library.json", manifest)
    cat = discover(str(tmp_path), Catalogue())
    if kind in ("unknown", "C1"):
        assert cat.issues and cat.real[0].metrics == {}, "unsupported provenance admitted"
        return
    admitted = cat.real[0].metrics["revenue"]
    assert cat.issues == [] and admitted is not None
    assert (admitted.provenance, admitted.value) == (kind, "0")


def test_checklist_requires_all_stages_and_pins(tmp_path: Path) -> None:
    manifest = fixture(tmp_path)
    manifest.checklist = Checklist.model_validate(CHECKLIST)
    put_json(tmp_path, "runs/case-a/library.json", manifest)
    cat = discover(str(tmp_path), Catalogue())
    assert cat.real[0].completion == 40, cat.issues  # 2 of 5, written by hand.
    manifest.checklist.requirements[0].evidence = []
    put_json(tmp_path, "runs/case-a/library.json", manifest)
    cat = discover(str(tmp_path), Catalogue())
    assert cat.real[0].completion is None and cat.issues
    with pytest.raises(ValueError, match="scope and required"):
        assess_checklist(Checklist(scope="empty"), {})


def test_delivery_revision_identity_and_corruption(tmp_path: Path) -> None:
    fixture(tmp_path)
    add_delivery(tmp_path, "revision-1", "case-a", "EX")
    add_delivery(tmp_path, "revision-2", "different-run", "EX")
    cat = discover(str(tmp_path), Catalogue())
    assert len(cat.real) == 2, "unrelated report must have its own row"
    run = run_named(cat, "case-a")
    assert len(run.artifacts) == 1 and run.artifacts[0].available
    put(tmp_path, "deliverables/revision-1/report.html", b"changed")
    cat = discover(str(tmp_path), Catalogue())
    assert "deliverables/revision-1/report.html" not in cat._allowed
    assert cat.issues, "missing corruption notice"


def test_paths_and_symlinks_cannot_escape(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    fixture(root)
    outside = tmp_path / "outside"
    put(outside, "secret.txt", b"secret")
    os.symlink(outside / "secret.txt", root / "runs/case-a/escape.txt")
    os.symlink(outside, root / "runs/case-a/outside")
    for name in [
        "../secret.txt",
        "/secret.txt",
        "runs/case-a/escape.txt",
        "runs/case-a/outside/secret.txt",
        "C:/secret.txt",
        "runs/a:stream",
        "runs\\a.txt",
        "runs/./case-a/CP-0.md",
        "",
    ]:
        with pytest.raises((OSError, ValueError)):
            read_file(root, name)
    assert read_file(root, "runs/case-a/CP-0.md") == EVIDENCE
    cat = discover(str(root), Catalogue())
    assert "runs/case-a/escape.txt" not in cat._allowed, "symlink enumerated"
    assert all(not name.startswith("runs/case-a/outside/") for name in cat._allowed)


def test_current_retained_workspace() -> None:
    if not (ROOT / "runs/tdg-002").is_dir():
        pytest.skip("not applicable: retained workspace not present")
    seeds = Catalogue.model_validate_json(
        (ROOT / "apps/issuer-library/web/legacy-catalog.json").read_bytes()
    )
    cat = discover(str(ROOT), seeds)
    assert cat.issues == []
    annual = run_named(cat, "tdg-002")
    leverage, coverage = annual.metrics["leverage"], annual.metrics["coverage"]
    assert leverage is not None and coverage is not None
    assert (leverage.value, coverage.value, annual.completion) == ("5.96", "3.60", None)
    run_folders = sum(not run.id.startswith("delivery:") for run in cat.real)
    reports = {
        artifact.folder for run in cat.real for artifact in run.artifacts if artifact.available
    }
    # Counted from the folders here, not through discovery.
    want_runs = sum(path.is_dir() for path in (ROOT / "runs").iterdir())
    delivered = list(ROOT.glob("deliverables/*/report.html"))
    delivered += ROOT.glob("deliverables/*/model.html")
    launched = list(ROOT.glob("runs/*/deliveries/*/report.html"))
    assert (run_folders, len(reports)) == (want_runs, len(delivered) + len(launched))


def test_manifest_cannot_supply_derived_links_or_null_collections(tmp_path: Path) -> None:
    manifest = fixture(tmp_path)
    manifest.run.handoff = ""
    manifest.run.handoff_href = "javascript:alert(1)"
    raw = manifest.model_dump(mode="json", by_alias=True)
    raw["run"]["artifacts"] = None
    raw["run"]["gaps"] = None
    put_json(tmp_path, "runs/case-a/library.json", raw)
    cat = discover(str(tmp_path), Catalogue())
    assert cat.issues == []
    assert cat.real[0].handoff_href == "", "untrusted derived handoff URL survived admission"
    assert cat.real[0].artifacts == [] and cat.real[0].gaps == []
    served = json.loads(cat.model_dump_json())
    assert served["real"][0]["artifacts"] == [] and "allowed" not in served


def test_wrong_issuer_mapping_does_not_hide_discovered_delivery(tmp_path: Path) -> None:
    manifest = fixture(tmp_path)
    manifest.run.artifacts = [Artifact(folder="deliverables/foreign", label="Bad mapping")]
    put_json(tmp_path, "runs/case-a/library.json", manifest)
    add_delivery(tmp_path, "foreign", "foreign-run", "OTHER")
    cat = discover(str(tmp_path), Catalogue())
    assert len(cat.real) == 2, "wrong-issuer mapping hid a valid delivery from discovery"
    mapped = run_named(cat, "case-a").artifacts[0]
    assert not mapped.available and mapped.issue == "Delivery issuer does not match run"


def test_delivery_checkpoint_requires_available_direct_bundle(tmp_path: Path) -> None:
    manifest = fixture(tmp_path)
    complete = {
        **CHECKLIST,
        "requirements": [
            {**item, "done": True, "evidence": ["check"]} for item in CHECKLIST["requirements"]
        ],
    }
    manifest.checklist = Checklist.model_validate(complete)
    put_json(tmp_path, "runs/case-a/library.json", manifest)
    cat = discover(str(tmp_path), Catalogue())
    assert cat.real[0].completion is None, "checklist claimed delivery without any deliverable"
    add_delivery(tmp_path, "complete", "case-a", "EX")
    cat = discover(str(tmp_path), Catalogue())
    assert run_named(cat, "case-a").completion == 100
    put(tmp_path, "deliverables/complete/report.html", b"corrupted")
    cat = discover(str(tmp_path), Catalogue())
    assert run_named(cat, "case-a").completion is None, "changed delivery retained completeness"


def test_metric_with_a_typed_mismatch_is_rejected_whole(tmp_path: Path) -> None:
    """A number where the producer must write an exact string is a rejected manifest, not 0."""
    manifest = fixture(tmp_path)
    raw = manifest.model_dump(mode="json", by_alias=True)
    raw["run"]["metrics"]["revenue"]["value"] = 0
    put_json(tmp_path, "runs/case-a/library.json", raw)
    cat = discover(str(tmp_path), Catalogue())
    assert cat.real[0].metrics == {} and cat.issues[0].startswith("runs/case-a: ")
    assert "run.metrics.revenue.value" in cat.issues[0]


def test_listed_files_follow_name_order_and_skip_hidden_entries(tmp_path: Path) -> None:
    fixture(tmp_path)
    put(tmp_path, "runs/case-a/b/notes.md", b"b")
    put(tmp_path, "runs/case-a/a.txt", b"a")
    put(tmp_path, "runs/case-a/.hidden/skip.md", b"h")
    put(tmp_path, "runs/case-a/.dotfile.md", b"h")
    put(tmp_path, "runs/case-a/picture.png", b"p")
    cat = discover(str(tmp_path), Catalogue())
    names = [item.name for item in cat.real[0].files]
    assert names == ["CP-0.md", "a.txt", "b/notes.md", "library.json"]
    assert cat.real[0].files[2].href == "/files/runs/case-a/b/notes.md"


def test_run_inputs_can_be_committed_and_the_cp8_rule_is_current() -> None:
    import hashlib
    import subprocess

    for folder in [
        "tdg-002",
        "tdg-003",
        "tdg-004",
        "tdg-guidance-001",
        "tdg-peers-2024-001",
        "tdg-run-comparison-001",
        "ford-otosan-2024-001",
        "frontier-2020-001",
    ]:
        ignored = subprocess.run(
            ["git", "check-ignore", "-q", f"runs/{folder}/x.md"], cwd=ROOT, check=False
        )
        assert ignored.returncode == 1, folder
    lock = subprocess.run(
        ["git", "check-ignore", "-q", "runs/tdg-002/x.lock"], cwd=ROOT, check=False
    )
    assert lock.returncode == 0
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "CP-8 compares deliverables from prior runs with the latest current run" in agents
    method = (ROOT / "src/deploy_vii/methods/cp8.md").read_bytes()
    assert method.decode("utf-8").split("\n")[0] == "# CP-8 — prior/current deliverable comparison"
    assert (ROOT / "docs/reuse/legacy-cp8-decision-ledger.md").exists()
    digest = hashlib.sha256(method).hexdigest()
    mapping = (ROOT / "docs/visualisations/MAP.md").read_text(encoding="utf-8")
    assert f"| src/deploy_vii/methods/cp8.md | {digest} |" in mapping


def admits_metric(tmp_path: Path, quote: str, value: str) -> bool:
    """Whether discovery admits value as the revenue metric quoted by quote."""
    manifest = fixture(tmp_path)
    revenue = manifest.run.metrics["revenue"]
    assert revenue is not None
    revenue.value = value
    raw = f"Issuer: Example Industries\nSector: Industrials\n{quote}\nVerified scope\n".encode()
    put(tmp_path, "runs/case-a/CP-0.md", raw)
    for key, source in manifest.sources.items():
        source.sha256 = digest(raw)
        if key == "revenue":
            source.quote = quote
    put_json(tmp_path, "runs/case-a/library.json", manifest)
    for run in discover(str(tmp_path), Catalogue()).real:
        if run.id == "case-a":
            return run.metrics.get("revenue") is not None
    return False


# A03: a metric must equal a whole number the quote states, sign and scale included; a
# fragment of a date, range, list or other-convention figure is not evidence of it.
METRIC_CASES = [
    # The reported fragments (all admitted before the fix).
    ("Net loss: (12.3)", "12.3", False),
    ("As of 2024-12-31 net debt was 450", "-12", False),
    ("Guidance: margin 3-5%", "-5", False),
    ("Yield: .5%", "5", False),
    ("Covenant tests 1,2,3 passed", "123", False),
    ("Revenue 1.234,5 (EUR format)", "1.234", False),
    # Whole numbers keep their sign, thousands grouping and decimals.
    ("Net loss: (12.3)", "-12.3", True),
    ("Net sales | 7,940 | 6,585", "7940", True),
    ("Closing cash | -1,676 | x", "-1676", True),
    ("Leverage 5.96x", "5.96", True),
    ("As Defined 4,685.", "4685", True),
    ("Revenue USD 1,234.5m, up 4%", "1234.5", True),
    ("Revenue 450, 500 and 600.", "500", True),
    ("As of 2024-12-31 net debt was 450", "450", True),
    # Dates, ranges and lists state none of their parts.
    ("As of 2024-12-31 net debt was 450", "2024", False),
    ("As of 2024-12-31 net debt was 450", "12", False),
    ("Guidance: margin 3-5%", "3", False),
    ("Guidance: margin 3\u20135%", "5", False),
    ("Covenant tests 1,2,3 passed", "1", False),
    ("COVID-19 costs", "-19", False),
    ("COVID-19 costs", "19", False),
    # A typographic minus or a sign inside parentheses is not dropped.
    ("Net loss \u221212.3", "12.3", False),
    ("Net loss: (-12.3)", "-12.3", False),
    ("Net loss: (-12.3)", "12.3", False),
    ("Net loss (USD 12.3m)", "12.3", False),
    ("Net loss (USD 12.3m)", "-12.3", False),
    ("Net loss (12.3m)", "12.3", False),
    ("Net change -(12.3)", "-12.3", False),
    ("Net change -(12.3)", "12.3", False),
    ("Net loss (12.3).", "-12.3", True),
    ("| Net loss | (1,676) |", "-1676", True),
    ("Net loss (12.3)5", "-12.3", False),
    ("Net loss \u2013(12.3)", "-12.3", False),
    # Other separator conventions and malformed groups are refused, never truncated.
    ("Revenue 1.234,5", "1234.5", False),
    ("Revenue 1.234.567", "1.234", False),
    ("Revenue 1,2345", "1", False),
    ("Revenue 12,34", "12", False),
    ("Revenue 1 234,5", "1", False),
    ("Revenue 1 234 567", "234", False),
    ("Revenue 1 234 567", "1", False),
    ("Umsatz 1\u00a0234,5", "1", False),
    ("Revenue 1'234.5", "234.5", False),
    ("Yield: .5%", ".5", False),
    # Exponents and a parenthesis opened before the quote also hide scale or sign.
    ("Notional 1.2e3", "1.2", False),
    ("Notional 1.2E+3", "3", False),
    ("Notional 1.2e-3", "-3", False),
    ("USD 12.3)", "12.3", False),
    ("Revenue 450 (2023: 400)", "450", True),
    ("Revenue 450 (2023: 400)", "400", False),
]


@pytest.mark.parametrize(("quote", "value", "admitted"), METRIC_CASES)
def test_metric_must_be_a_whole_number_of_the_quote_with_its_sign_and_scale(
    tmp_path: Path, quote: str, value: str, admitted: bool
) -> None:
    assert admits_metric(tmp_path, quote, value) == admitted


STATED_CASES: list[tuple[str, list[str]]] = [
    ("Revenue $1,234.50 million", ["1234.50"]),
    ("Loss of $(1,234)", ["-1234"]),
    ("(1,234) and (567)", ["-1234", "-567"]),
    ("up 12.5% from 11.9%", ["12.5", "11.9"]),
    ("FY2023 revenue of 5,000 vs 4,500 in FY2022", ["2023", "5000", "4500", "2022"]),
    ("EUR 1.234,56", []),
    ("CHF 1'234.50", []),
    ("INR 1,23,456", []),
    ("EUR -45.2m", ["-45.2"]),
    ("Loss -$5", []),
    ("Loss \u2212$5", []),
    ("Loss $-5", ["-5"]),
    ("Loss -\u20ac1,200.", []),
    ("Gain $5", ["5"]),
    ("1,000.5.", ["1000.5"]),
    ("10,000,000", ["10000000"]),
    ("1,000,00", []),
    ("1,0000", []),
    ("(12.5%)", []),
    ("rose 3.5 points (from 2.1)", ["3.5"]),
    ("5 - 3", ["5", "3"]),
    ("Q2 2024 EBITDA 1,200", ["2", "2024", "1200"]),
    ("2023/24 sales 9", ["9"]),
    ("As of 12/31/2024 cash 450", ["450"]),
]


@pytest.mark.parametrize(("quote", "want"), STATED_CASES)
def test_stated_numbers_adversarial(quote: str, want: list[str]) -> None:
    assert stated_numbers(quote) == want


def test_seed_metrics_all_stated() -> None:
    seeds = Catalogue.model_validate_json(
        (ROOT / "apps/issuer-library/web/legacy-catalog.json").read_bytes()
    )
    for run in seeds.real:
        for key, metric in run.metrics.items():
            if metric is None:
                continue
            quote = seeds.sources[metric.source].quote
            assert metric.value in stated_numbers(quote), (
                f"{run.id}/{key} {metric.value!r} {quote!r}"
            )


def add_model_delivery(root: Path, folder: str, run_id: str = "model-run") -> bytes:
    """A deliverables/ folder holding only a published model."""
    view = DeliveryView()
    view.run.run_id, view.run.issuer_id = run_id, "TDG" if run_id == "model-run" else "EX"
    view.run.issuer_name, view.run.as_of = "Example Industries", "2024-12-31"
    raw = view.model_dump_json().encode()
    model = b"<!doctype html><title>Model</title><p>Published model</p>"
    for name, content in (("view.json", raw), ("model.html", model)):
        put(root, f"deliverables/{folder}/{name}", content)
    files = {"view.json": digest(raw), "model.html": digest(model)}
    put_json(root, f"deliverables/{folder}/delivery.json", {"files": files})
    return model


def find_artifact(cat: Catalogue, folder: str) -> Artifact | None:
    return next((a for run in cat.real for a in run.artifacts if a.folder == folder), None)


def deliver(root: Path, run: str, *specs: tuple[str, str, str]) -> list[str]:
    """Verified deliveries (folder, view run id, issuer) placed inside a run, as a copy would."""
    placed = []
    for folder, run_id, issuer in specs:
        add_delivery(root, folder, run_id, issuer)
        target = root / "runs" / run / "deliveries"
        target.mkdir(parents=True, exist_ok=True)
        shutil.move(str(root / "deliverables" / folder), str(target / folder))
        placed.append(f"runs/{run}/deliveries/{folder}")
    return placed


def attached(cat: Catalogue, run_id: str, folder: str) -> bool:
    return any(
        a.folder == folder and a.available for r in cat.real if r.id == run_id for a in r.artifacts
    )


def complete_checklist(root: Path, *declared: Artifact) -> None:
    manifest = fixture(root)
    manifest.run.artifacts = list(declared)
    done = [{**item, "done": True, "evidence": ["check"]} for item in CHECKLIST["requirements"]]
    manifest.checklist = Checklist.model_validate({**CHECKLIST, "requirements": done})
    put_json(root, "runs/case-a/library.json", manifest)


def test_model_delivery_verifies_as_a_model_and_a_report_keeps_its_kind(tmp_path: Path) -> None:
    fixture(tmp_path)
    model = add_model_delivery(tmp_path, "m-1")
    add_delivery(tmp_path, "r-1", "case-a", "other")
    cat = discover(str(tmp_path), Catalogue())
    assert cat.issues == []
    artifact = find_artifact(cat, "deliverables/m-1")
    assert artifact is not None and artifact.available and artifact.kind == "model"
    assert artifact.href == pinned_url("deliverables/m-1/model.html", digest(model))
    report = find_artifact(cat, "deliverables/r-1")
    assert report is not None and report.kind == "report"
    assert report.href.split("?")[0].endswith("/report.html")
    assert cat._allowed["deliverables/m-1/model.html"] == digest(model)
    assert '"kind":"model"' in artifact.model_dump_json()


def test_delivery_with_neither_page_keeps_its_issue(tmp_path: Path) -> None:
    fixture(tmp_path)
    put_json(tmp_path, "deliverables/empty/delivery.json", {"files": {"view.json": "x"}})
    cat = discover(str(tmp_path), Catalogue())
    assert "deliverables/empty: Delivery manifest requires report.html and view.json" in cat.issues


def test_changed_model_makes_its_delivery_unavailable(tmp_path: Path) -> None:
    fixture(tmp_path)
    add_model_delivery(tmp_path, "m-1")
    put(tmp_path, "deliverables/m-1/model.html", b"changed")
    cat = discover(str(tmp_path), Catalogue())
    artifact = find_artifact(cat, "deliverables/m-1")
    assert artifact is None or not artifact.available
    assert "deliverables/m-1: Missing or changed delivery file: model.html" in cat.issues


def test_run_internal_delivery_must_match_its_run_and_issuer(tmp_path: Path) -> None:
    fixture(tmp_path)
    own, *rejected = deliver(
        tmp_path,
        "case-a",
        ("own", "case-a", "EX"),
        ("foreign-run", "other-run", "EX"),
        ("foreign-issuer", "case-a", "ZZZ"),
        ("foreign-both", "other-run", "ZZZ"),
    )
    cat = discover(str(tmp_path), Catalogue())
    assert attached(cat, "case-a", own), cat.issues
    for folder in rejected:
        assert not attached(cat, "case-a", folder), folder
        assert cat._allowed.get(f"{folder}/report.html", "") == "", folder
        assert any(issue.startswith(f"{folder}: Delivery ") for issue in cat.issues), folder


def test_run_internal_delivery_accepts_the_launcher_recorded_identity_only(tmp_path: Path) -> None:
    fixture(tmp_path)
    put(tmp_path, "runs/web-1/CP-0.md", b"x")
    recorded = b'{"run":{"run_id":"ex-2024-12-31-full-a","issuer_id":"EX"}}'
    put(tmp_path, "runs/web-1/workflow.json", recorded)
    mine, wrong_issuer, other_launch = deliver(
        tmp_path,
        "web-1",
        ("mine", "ex-2024-12-31-full-a", "EX"),
        ("wrong-issuer", "ex-2024-12-31-full-a", "ZZZ"),
        ("other-launch", "zzz-2024-12-31-full-a", "EX"),
    )
    cat = discover(str(tmp_path), Catalogue())
    assert attached(cat, "web-1", mine), cat.issues
    assert not attached(cat, "web-1", wrong_issuer)
    assert not attached(cat, "web-1", other_launch)


def test_foreign_run_delivery_does_not_satisfy_the_delivery_checkpoint(tmp_path: Path) -> None:
    complete_checklist(tmp_path)
    deliver(tmp_path, "case-a", ("foreign", "other-run", "ZZZ"))
    cat = discover(str(tmp_path), Catalogue())
    assert run_named(cat, "case-a").completion is None, "a foreign delivery restored completeness"
    deliver(tmp_path, "case-a", ("mine", "case-a", "EX"))
    cat = discover(str(tmp_path), Catalogue())
    assert run_named(cat, "case-a").completion == 100, "the run's own delivery must still count"


def test_review_run_delivery_identity_adversarial(tmp_path: Path) -> None:
    fixture(tmp_path)
    for run in ("web-2", "web-3", "web-4"):
        put(tmp_path, f"runs/{run}/CP-0.md", b"x")
    # web-2: workflow.json whose issuer_id has the wrong type counts as unreadable, so only the
    # folder id is accepted; the recorded run id is not honoured without its issuer.
    put(tmp_path, "runs/web-2/workflow.json", b'{"run":{"run_id":"ex-run","issuer_id":7}}')
    typed, folder_id = deliver(
        tmp_path, "web-2", ("typed", "ex-run", "ZZZ"), ("folder-id", "web-2", "EX")
    )
    # web-3: no workflow.json at all; only a view run_id equal to "web-3" is accepted.
    none_own, none_other = deliver(
        tmp_path, "web-3", ("none-own", "web-3", "EX"), ("none-other", "ex-run", "EX")
    )
    # web-4: a CP-8 comparison plan recorded as workflow.json; an issuer differing in case is not.
    plan = (
        b'{"run":{"run_id":"tdg-cp8-comparison","issuer_id":"TDG"},'
        b'"prior":{"path":"p","sha256":"x"}}'
    )
    put(tmp_path, "runs/web-4/workflow.json", plan)
    cp8, cp8_case = deliver(
        tmp_path,
        "web-4",
        ("cp8", "tdg-cp8-comparison", "TDG"),
        ("cp8-case", "tdg-cp8-comparison", "tdg"),
    )
    # case-a has an admitted manifest (issuer EX): another issuer or another run is refused.
    case_issuer, case_run = deliver(
        tmp_path, "case-a", ("case-other-issuer", "case-a", "ex"), ("case-other-run", "web-3", "EX")
    )
    cat = discover(str(tmp_path), Catalogue())
    for run_id, folder, ok in [
        ("web-2", typed, False),
        ("web-2", folder_id, True),
        ("web-3", none_own, True),
        ("web-3", none_other, False),
        ("web-4", cp8, True),
        ("web-4", cp8_case, False),
        ("case-a", case_issuer, False),
        ("case-a", case_run, False),
    ]:
        assert attached(cat, run_id, folder) == ok, (folder, cat.issues)
        assert (cat._allowed.get(f"{folder}/report.html", "") != "") == ok, folder
    # A refused run delivery never appears as an available artifact under any run.
    for artifact in (a for run in cat.real for a in run.artifacts if a.available):
        assert artifact.folder not in (typed, case_issuer, case_run)


def test_declared_run_delivery_is_listed_once(tmp_path: Path) -> None:
    manifest = fixture(tmp_path)
    own, superseded, foreign = (f"runs/case-a/deliveries/{n}" for n in ("v1", "v0", "vx"))
    manifest.run.artifacts = [
        Artifact(folder=own, label="Annual report", state="candidate", relationship="related"),
        Artifact(folder=superseded, label="Earlier", state="superseded", relationship="direct"),
        Artifact(folder=foreign, label="Copied", state="candidate", relationship="direct"),
    ]
    put_json(tmp_path, "runs/case-a/library.json", manifest)
    deliver(tmp_path, "case-a", ("v1", "case-a", "EX"), ("v0", "case-a", "EX"))
    deliver(tmp_path, "case-a", ("vx", "other-run", "EX"))
    cat = discover(str(tmp_path), Catalogue())
    listed = [a for run in cat.real for a in run.artifacts if a.folder.startswith("runs/case-a/")]
    refusal = "Delivery run identity does not match this run"
    wanted = {
        own: ("Annual report", "candidate", "related", True, ""),
        superseded: ("Earlier", "superseded", "direct", True, ""),
        foreign: ("Copied", "candidate", "direct", False, refusal),
    }
    assert sorted(a.folder for a in listed) == sorted(wanted), "each declared folder listed once"
    for a in listed:
        got = (a.label, a.state, a.relationship, a.available, a.issue)
        assert got == wanted[a.folder] and (a.href != "") == a.available, a
    assert cat._allowed[f"{own}/report.html"] != ""
    assert cat._allowed.get(f"{foreign}/report.html", "") == ""


def test_a_published_model_alone_does_not_restore_a_runs_completeness(tmp_path: Path) -> None:
    complete_checklist(tmp_path)
    add_model_delivery(tmp_path, "m-only", "case-a")
    run = run_named(discover(str(tmp_path), Catalogue()), "case-a")
    assert run.completion is None, "a model-only delivery restored completeness"
    assert any("no available direct report" in gap for gap in run.gaps)


@pytest.mark.parametrize(
    ("declared", "completion", "kind"),
    [
        (None, 100, "report"),  # both pages listed: the report wins and completes the run
        (Artifact(folder="deliverables/r", label="Old", state="superseded"), None, "report"),
        (Artifact(folder="deliverables/r", label="Rel", relationship="related"), None, "report"),
    ],
)
def test_the_delivery_checkpoint_counts_only_a_current_direct_report(
    tmp_path: Path, declared: Artifact | None, completion: int | None, kind: str
) -> None:
    complete_checklist(tmp_path, *([declared] if declared else []))
    add_delivery(tmp_path, "r", "case-a", "EX")
    model = b"<!doctype html><title>Model</title>"
    put(tmp_path, "deliverables/r/model.html", model)
    record = json.loads((tmp_path / "deliverables/r/delivery.json").read_bytes())
    record["files"]["model.html"] = digest(model)
    put_json(tmp_path, "deliverables/r/delivery.json", record)
    cat = discover(str(tmp_path), Catalogue())
    artifact = find_artifact(cat, "deliverables/r")
    assert artifact is not None and artifact.available and artifact.kind == kind
    assert run_named(cat, "case-a").completion == completion


# Admission of classification, private side, facilities and user provenance, checked against the
# hand-written answer key in tests/fixtures/library-manifest (ported from Go d877d8ce, not edited).
MANIFEST_FIXTURES = ROOT / "tests" / "fixtures" / "library-manifest"
RETAINED_RUN = "runs/web-04cd5a5d02ea7d1dea714a8a6632cd21"
RETAINED_INPUT = "inputs/ec0a711fe74781d81973060c2e34ae47b1129e9ff5aea9f5ef6218a082b4f984"
RETAINED_CP1_SHA = "7f0578c02be6bce6849863c7105d17f6d09674ed595b86626286e57d61268e3a"
ANSWER_KEYS = ("synthetic", "retained-cp1")


def read_fixture_json(name: str) -> Any:
    return json.loads((MANIFEST_FIXTURES / name).read_text())


def copy_file(source: Path, root: Path, name: str) -> bytes:
    raw = source.read_bytes()
    put(root, name, raw)
    return raw


def copy_tree(base: Path, root: Path) -> None:
    for path in sorted(base.rglob("*")):
        if path.is_file():
            copy_file(path, root, path.relative_to(base).as_posix())


def fixture_workspace(tmp_path: Path, name: str) -> tuple[Path, str]:
    """A temp workspace for the named fixture, with the run id."""
    if name == "synthetic":
        copy_tree(MANIFEST_FIXTURES / "synthetic" / "workspace", tmp_path)
        return tmp_path, "synthetic-hy-001"
    if name == "retained-cp1":
        repo = ROOT / RETAINED_RUN
        if not (repo / "CP-1.md").exists():
            pytest.skip("not applicable: retained CP-1.md not present")
        raw = copy_file(repo / "CP-1.md", tmp_path, f"{RETAINED_RUN}/CP-1.md")
        assert hashlib.sha256(raw).hexdigest() == RETAINED_CP1_SHA, "retained CP-1.md changed"
        copy_file(repo / RETAINED_INPUT, tmp_path, f"{RETAINED_RUN}/{RETAINED_INPUT}")
        return tmp_path, "web-04cd5a5d02ea7d1dea714a8a6632cd21"
    raise AssertionError(f"unknown fixture {name}")


def set_pointer(doc: Any, pointer: str, value: Any) -> Any:
    """Set an RFC 6901 location, replacing the member or adding it when the parent object lacks it.

    Array elements are replaced in place; only what the case files use is supported.
    """
    parts = [
        part.replace("~1", "/").replace("~0", "~") for part in pointer.removeprefix("/").split("/")
    ]
    node = doc
    for part in parts[:-1]:
        if isinstance(node, dict):
            node = node[part]
        elif isinstance(node, list):
            assert part.isdigit() and int(part) < len(node), f"bad array index {part!r}"
            node = node[int(part)]
        else:
            raise TypeError(f"pointer {pointer} leaves the document at {part!r}")
    last = parts[-1]
    if isinstance(node, dict):
        node[last] = value
    elif isinstance(node, list):
        assert last.isdigit() and int(last) < len(node), f"bad array index {last!r}"
        node[int(last)] = value
    else:
        raise TypeError(f"pointer {pointer} has no container")
    return doc


def discover_fixture(
    tmp_path: Path, name: str, change: Callable[[Any], Any] | None = None
) -> tuple[Catalogue, Run]:
    root, run_id = fixture_workspace(tmp_path, name)
    doc = read_fixture_json(f"{name}/library.json")
    if change is not None:
        doc = change(doc)
    put_json(root, f"runs/{run_id}/library.json", doc)
    cat = discover(str(root), Catalogue())
    for run in cat.real:
        if run.id == run_id:
            return cat, run
    raise AssertionError(f"run {run_id} not served")


def is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def subset_leaf_diff(want: Any, got: Any, where: str) -> str:
    """Leaves: a JSON number is one kind (int and float alike); a bool, string or null equals only
    its own kind (Python would otherwise equate True with 1).
    """
    same_kind = (is_number(want) and is_number(got)) or type(want) is type(got)
    return "" if same_kind and want == got else f"{where}: want {want} got {got}"


MISSING = object()


def subset_children(want: Any, got: Any, where: str) -> list[tuple[Any, Any, str]] | str:
    """The (wanted, served, place) pairs under a container, in order, or why it cannot match."""
    if isinstance(want, dict):
        if not isinstance(got, dict):
            return f"{where}: not an object"
        return [(value, got.get(key, MISSING), f"{where}/{key}") for key, value in want.items()]
    if not isinstance(got, list) or len(got) != len(want):
        return f"{where}: array length differs ({got})"
    return [(item, got[i], f"{where}/{i}") for i, item in enumerate(want)]


def subset_diff(want: Any, got: Any, where: str) -> str:
    """The first place served differs from want: every key and element the answer key holds must be
    present and equal; arrays must have the same length.
    """
    if not isinstance(want, dict | list):
        return subset_leaf_diff(want, got, where)
    children = subset_children(want, got, where)
    if isinstance(children, str):
        return children
    for value, have, place in children:
        if have is MISSING:
            return f"{place}: missing"
        if diff := subset_diff(value, have, place):
            return diff
    return ""


def served_json(run: Run) -> dict[str, Any]:
    served = json.loads(run.model_dump_json())
    assert isinstance(served, dict)
    return served


@pytest.mark.parametrize("name", ANSWER_KEYS)
def test_manifest_admits_answer_key(tmp_path: Path, name: str) -> None:
    cat, run = discover_fixture(tmp_path, name)
    assert cat.issues == [], "answer-key manifest rejected"
    served = served_json(run)
    want = read_fixture_json(f"{name}/expected-served.json")
    assert subset_diff(want, served, "") == ""
    # A key the answer key does not hold must be absent or empty when served.
    for key in (
        "classification",
        "classification_source",
        "private_side",
        "private_side_source",
        "facilities",
    ):
        if key in want:
            continue
        value = served.get(key)
        if isinstance(value, list):
            assert value == [], f"{key} served but not in the answer key: {value}"
        else:
            assert value is None or value is False or value == "", (
                f"{key} served but not in the answer key: {value}"
            )
    facilities = served["facilities"]
    want_facilities = want.get("facilities")
    assert isinstance(facilities, list) and isinstance(want_facilities, list), (
        f"facilities must be served as an array: {facilities} (answer key {want_facilities})"
    )
    assert want_facilities or facilities == []


def case_change(case: dict[str, Any]) -> Callable[[Any], Any]:
    return lambda doc: set_pointer(doc, case["pointer"], case["value"])


REJECT_CASES = read_fixture_json("reject-cases.json")
ACCEPT_CASES = read_fixture_json("accept-cases.json")


@pytest.mark.parametrize("case", REJECT_CASES, ids=[case["name"] for case in REJECT_CASES])
def test_manifest_reject_cases(tmp_path: Path, case: dict[str, Any]) -> None:
    cat, run = discover_fixture(tmp_path, case["fixture"], case_change(case))
    assert run.gaps and run.gaps[-1].startswith("Run metadata rejected:") and cat.issues, (
        f"not rejected ({case['why']}): gaps {run.gaps} issues {cat.issues}"
    )
    assert (run.classification, run.classification_source) == ("", "")
    assert (run.private_side, run.private_side_source) == (False, "")
    assert run.facilities == [] and len(run.metrics) == 0, f"rejected run still serves: {run}"
    for key in cat.sources:
        assert not key.startswith(f"{run.id}."), f"rejected manifest published source {key}"


@pytest.mark.parametrize("case", ACCEPT_CASES, ids=[case["name"] for case in ACCEPT_CASES])
def test_manifest_accept_cases(tmp_path: Path, case: dict[str, Any]) -> None:
    cat, run = discover_fixture(tmp_path, case["fixture"], case_change(case))
    assert cat.issues == [], f"rejected ({case['why']})"
    assert len(run.metrics) != 0, "admitted run lost metrics"
    assert run.facilities is not None


def test_manifest_omitted_facility_collections_served_empty(tmp_path: Path) -> None:
    """A facility written without quotes or terms is still served with [] and {}, never null."""

    def change(doc: Any) -> Any:
        facilities = doc["run"]["facilities"]
        del facilities[0]["quotes"]
        del facilities[1]["terms"]
        return doc

    _, run = discover_fixture(tmp_path, "synthetic", change)
    assert len(run.facilities) == 2, f"facilities not admitted: {run.gaps}"
    raw = json.dumps(served_json(run)["facilities"])
    assert "null" not in raw, f"facility served with null collection: {raw}"
    assert run.facilities[0].quotes == [] and run.facilities[1].terms == {}


@pytest.mark.parametrize("attempt", range(20))
def test_manifest_term_error_names_sorted_first_key(tmp_path: Path, attempt: int) -> None:
    """Two bad terms must always be reported by the same key (the sorted-first one)."""

    def change(doc: Any) -> Any:
        terms = doc["run"]["facilities"][0]["terms"]
        for key in ("zz_bad", "aa_bad", "mm_bad"):
            terms[key] = terms["size_m"]
        return doc

    _, run = discover_fixture(tmp_path, "synthetic", change)
    assert run.gaps and '"aa_bad"' in run.gaps[-1], (
        f"run {attempt}: error does not name the sorted-first bad key: {run.gaps}"
    )


WRITER_KEYS = sorted((MANIFEST_FIXTURES / "writer").glob("*/expected-library.json"))


def test_writer_answer_keys_exist() -> None:
    assert WRITER_KEYS, "no writer answer keys found"


@pytest.mark.parametrize("key_file", WRITER_KEYS, ids=[path.parent.name for path in WRITER_KEYS])
def test_writer_key_is_admitted_with_its_checklist(tmp_path: Path, key_file: Path) -> None:
    directory = key_file.parent
    copy_tree(directory / "workspace", tmp_path)
    plan_file = directory / "copy.json"
    plan = json.loads(plan_file.read_text()) if plan_file.exists() else []
    for item in plan:
        source = ROOT / item["from"]
        if not source.exists():
            pytest.skip(f"not applicable: {item['from']} not present")
        copy_file(source, tmp_path, item["to"])
    raw = key_file.read_bytes()
    key = json.loads(raw)
    run_id = key["run"]["id"]
    put(tmp_path, f"runs/{run_id}/library.json", raw)
    cat = discover(str(tmp_path), Catalogue())
    assert not [issue for issue in cat.issues if run_id in issue], "issue names the run"
    run = run_named(cat, run_id)
    requirements = key["checklist"]["requirements"]
    done = sum(1 for item in requirements if item.get("done"))
    total = len(requirements)
    assert not [gap for gap in run.gaps if gap.startswith("Run metadata rejected")]
    assert run.checkpoints is not None
    assert (run.checkpoints.done, run.checkpoints.total) == (done, total)
    assert run.completion == done * 100 // total


@pytest.mark.parametrize(
    ("text", "want"),
    [
        ("size_m", '"size_m"'),
        ('a"b\\c', '"a\\"b\\\\c"'),
        ("a\nb\x01\x7f", '"a\\nb\\x01\\x7f"'),
        ("\u00e9\u00a0\u200b", '"\u00e9\\u00a0\\u200b"'),
        ("\U0001f600\U000e0001", '"\U0001f600\\U000e0001"'),
    ],
)
def test_go_quote_matches_strconv_quote(text: str, want: str) -> None:
    assert go_quote(text) == want
