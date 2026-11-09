"""Discovery over a hand-written workspace; expected values are written here by hand."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from issuer_library_support import EVIDENCE, add_delivery, fixture, put, put_json

from issuer_library.discovery import assess_checklist, discover, stated_numbers
from issuer_library.model import Artifact, Catalogue, Checklist, Run, digest, read_file

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
        pytest.skip("retained workspace not present")
    seeds = Catalogue.model_validate_json(
        (ROOT / "apps/issuer-library/web/legacy-catalog.json").read_bytes()
    )
    cat = discover(str(ROOT), seeds)
    # These hold an HTML Model and no report, which the library does not present yet.
    assert cat.issues == [
        f"deliverables/tdg-model-{number}: Delivery manifest requires report.html and view.json"
        for number in (1, 2, 3)
    ]
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
    ("Umsatz 1 234,5", "1", False),
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
