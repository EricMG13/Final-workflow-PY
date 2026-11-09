"""The library's store over a hand-written workspace; expected values are written here."""

import fnmatch
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "library_store", ROOT / "apps/issuer-library/engine/store.py"
)
store = importlib.util.module_from_spec(spec)
spec.loader.exec_module(store)

CP1 = "# CP-1\n\n## Findings\n\n| Item | Value |\n| --- | --- |\n| Revenue | 0 |\n| Debt | not stated |\n"
BETA = "# CP-0\n\n## Request\n\nBeta Group as of 2025-06-30.\n"


def put(root: Path, name: str, text: str) -> str:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode()).hexdigest()


def delivery(root: Path, folder: str, issuer: str, handoffs: dict[str, str]) -> None:
    files = {name: put(root, f"{folder}/{name}", text) for name, text in handoffs.items()}
    files["report.html"] = put(root, f"{folder}/report.html", "<html>report</html>")
    view = {"run": {"issuer_name": issuer, "as_of": "2025-06-30", "pathway": "credit_snapshot"}}
    files["view.json"] = put(root, f"{folder}/view.json", json.dumps(view))
    put(root, f"{folder}/delivery.json", json.dumps({"files": files, "cp_model_published": False}))


def workspace(root: Path) -> dict:
    put(root, "runs/alpha-001/CP-1.md", CP1)
    put(root, "runs/alpha-001/CP-1-instructions.md", "# skipped\n")
    put(root, "runs/alpha-001/CP-1-selected-input.md", "# input\n")
    put(root, "runs/alpha-001/CP-2.md", "Body before any heading\n\n## Later\n\nText\n")
    put(root, "runs/alpha-001/CP-4A.md", "# CP-4A\n\nExtra module.\n")
    put(root, "runs/empty-001/notes.txt", "no handoff\n")
    put(
        root,
        "runs/launched/workflow.json",
        json.dumps(
            {
                "run": {
                    "issuer_name": "Beta Group",
                    "as_of": "2025-06-30",
                    "pathway": "credit_snapshot",
                }
            }
        ),
    )
    delivery(root, "runs/launched/deliveries/abc", "Beta Group", {"CP-0.md": BETA})
    delivery(
        root,
        "deliverables/alpha-report",
        "Alpha Holdings",
        {"CP-1.md": CP1, "CP-9.md": "# Not in any run\n"},
    )
    blank = {"sector": "Unclassified", "period": "", "artifacts": []}
    return {
        "issues": ["runs/x: earlier issue"],
        "real": [
            {
                "id": "alpha-001",
                "name": "Alpha Holdings",
                "sector": "Industrials",
                "period": "FY2024",
                "artifacts": [
                    {
                        "folder": "deliverables/alpha-report",
                        "label": "Alpha annual",
                        "state": "final",
                        "available": True,
                        "href": "/files/deliverables/alpha-report/report.html?sha256=r",
                    }
                ],
            },
            {"id": "empty-001", "name": "empty-001", **blank},
            {
                "id": "launched",
                "name": "launched",
                **blank,
                "artifacts": [
                    {
                        "folder": "runs/launched/deliveries/abc",
                        "label": "abc",
                        "state": "candidate",
                        "available": True,
                        "href": "/files/runs/launched/deliveries/abc/report.html?sha256=s",
                    }
                ],
            },
            {
                "id": "delivery:orphan",
                "name": "Gamma",
                "sector": "",
                "period": "",
                "artifacts": [
                    {
                        "folder": "deliverables/broken",
                        "label": "broken",
                        "state": "candidate",
                        "available": False,
                        "href": "",
                        "issue": "Missing",
                    }
                ],
            },
        ],
    }


def test_runs_take_labels_from_the_catalogue_and_launcher_manifest(tmp_path):
    result = store.workspace_store(tmp_path, workspace(tmp_path))
    assert list(result["runs"]) == ["alpha-001", "empty-001", "launched"]
    alpha, beta = result["runs"]["alpha-001"], result["runs"]["launched"]
    assert (alpha["issuer"], alpha["sector"], alpha["period"]) == (
        "Alpha Holdings",
        "Industrials",
        "FY2024",
    )
    assert (beta["issuer"], beta["title"], beta["period"]) == (
        "Beta Group",
        "Beta Group",
        "As of 30 June 2025",
    )
    assert result["runs"]["empty-001"]["first"] == "W-Overview"
    assert beta["first"] == "CP-0"


def test_outputs_keep_exact_values_identity_and_a_serving_link(tmp_path):
    result = store.workspace_store(tmp_path, workspace(tmp_path))
    output = result["outputs"]["alpha-001/CP-1.md"]
    rows = result["handoffs"][output["sha256"]][1]["blocks"][0]["rows"]
    assert [row["cells"] for row in rows] == [["Revenue", "0"], ["Debt", "not stated"]]
    assert output["sha256"] == hashlib.sha256(CP1.encode()).hexdigest()
    assert output["href"] == f"/files/runs/alpha-001/CP-1.md?sha256={output['sha256']}"
    assert "alpha-001/CP-1-instructions.md" not in result["outputs"]
    assert list(result["inputs"]) == ["alpha-001/CP-1-selected-input.md"]
    assert result["inputs"]["alpha-001/CP-1-selected-input.md"]["href"].startswith(
        "/files/runs/alpha-001/"
    )
    assert result["runs"]["alpha-001"]["modules"]["CP-4A"]["outputs"] == ["alpha-001/CP-4A.md"]


def test_delivered_handoffs_of_a_launcher_run_are_its_outputs(tmp_path):
    result = store.workspace_store(tmp_path, workspace(tmp_path))
    output = result["outputs"]["launched/deliveries/abc/CP-0.md"]
    assert output["source"] == "deliveries/abc/CP-0.md"
    assert output["run"] == "launched" and output["module"] == "CP-0"
    assert output["href"].startswith("/files/runs/launched/deliveries/abc/CP-0.md?sha256=")


def test_a_handoff_that_cannot_be_structured_stays_readable_and_is_flagged(tmp_path):
    result = store.workspace_store(tmp_path, workspace(tmp_path))
    output = result["outputs"]["alpha-001/CP-2.md"]
    assert "Body before" in output["parseError"]
    block = result["handoffs"][output["sha256"]][0]["blocks"][0]
    assert block["type"] == "text" and block["text"].startswith("Body before any heading")
    assert "## Later" in block["text"]
    assert any("alpha-001/CP-2.md" in issue for issue in result["issues"])


def test_reports_trace_handoffs_by_hash_and_name_what_has_no_match(tmp_path):
    result = store.workspace_store(tmp_path, workspace(tmp_path))
    reports = {report["id"]: report for report in result["reports"]}
    assert list(reports) == ["alpha-report", "abc"]
    alpha = reports["alpha-report"]
    assert alpha["label"] == "Alpha annual" and alpha["issuer"] == "Alpha Holdings"
    assert alpha["href"] == "/files/deliverables/alpha-report/report.html?sha256=r&embedded=1"
    assert alpha["download"] == "/files/deliverables/alpha-report/report.html?sha256=r&download=1"
    assert alpha["build"] is None and alpha["modelPublished"] is False
    traced = {row["module"]: row for row in alpha["builtFrom"]}
    assert traced["CP-1"]["run"] == "alpha-001" and traced["CP-1"]["source"] == "alpha-001/CP-1.md"
    assert traced["CP-1"]["output"] is True
    assert traced["CP-9"]["run"] is None
    assert {f["name"] for f in alpha["files"]} == {"CP-1.md", "CP-9.md", "report.html", "view.json"}
    beta = reports["abc"]
    assert beta["label"] == "Beta Group · as of 30 June 2025" and beta["issuer"] == "Beta Group"
    assert beta["builtFrom"][0]["run"] == "launched"


def _report_with_view(tmp_path, **declared):
    catalogue = workspace(tmp_path)
    view_path = tmp_path / "deliverables/alpha-report/view.json"
    view = json.loads(view_path.read_text(encoding="utf-8"))
    view.update(declared)
    view_path.write_text(json.dumps(view), encoding="utf-8")
    record = view_path.with_name("delivery.json")
    listed = json.loads(record.read_text(encoding="utf-8"))
    listed["files"]["view.json"] = hashlib.sha256(
        view_path.read_bytes()
    ).hexdigest()  # As verified.
    record.write_text(json.dumps(listed), encoding="utf-8")
    reports = {r["id"]: r for r in store.workspace_store(tmp_path, catalogue)["reports"]}
    return reports["alpha-report"]


@pytest.mark.parametrize(
    ("declared", "mode", "qualification"),
    [
        ({"mode": "accepted", "analytical_qualification": "qualified"}, "accepted", "qualified"),
        ({"mode": "candidate", "analytical_qualification": "partial"}, "candidate", "partial"),
        ({"analytical_qualification": "unrun"}, None, "unrun"),
        ({"mode": "candidate", "analytical_qualification": "mystery"}, "candidate", "mystery"),
        ({"mode": "candidate"}, "candidate", None),
        ({}, None, None),
    ],
)
def test_a_report_carries_the_mode_and_qualification_it_declares(
    tmp_path, declared, mode, qualification
):
    report = _report_with_view(tmp_path, **declared)
    assert report["mode"] == mode
    assert report["qualification"] == qualification


def test_the_latest_curated_build_is_labelled_latest_build():
    assert store.CURATED_REPORTS["tdg-fy2024-snapshot-7"][1] == "Latest build"
    assert store.CURATED_REPORTS["tdg-fy2024-snapshot"][1] == "Superseded"
    assert "Latest" not in {status for _, status in store.CURATED_REPORTS.values()}


def test_a_curated_pin_that_no_longer_matches_is_dropped_not_fatal(tmp_path):
    catalogue = {
        "issues": [],
        "real": [
            {"id": "tdg-002", "name": "TransDigm", "sector": "", "period": "", "artifacts": []}
        ],
    }
    put(tmp_path, "runs/tdg-002/CP-1-attempt-2.md", "# Changed\n\nNo curated heading here.\n")
    result = store.workspace_store(tmp_path, catalogue)
    assert "CP-1" not in result["pins"]
    assert "tdg-002/CP-1-attempt-2.md" in result["outputs"]
    assert any("CP-1" in issue and "pin" in issue for issue in result["issues"])
    run = result["runs"]["tdg-002"]
    assert (run["issuer"], run["run"]) == ("TransDigm Group", "TDG-002")  # Curated reading label.


def test_empty_workspace_and_unsafe_folder_names(tmp_path):
    empty = store.workspace_store(tmp_path, {"issues": [], "real": []})
    assert (empty["runs"], empty["outputs"], empty["reports"], empty["pins"]) == ({}, {}, [], {})
    assert isinstance(empty["visuals"], list)
    unsafe = store.workspace_store(
        tmp_path,
        {
            "issues": [],
            "real": [{"id": 'bad"name', "name": "x", "sector": "", "period": "", "artifacts": []}],
        },
    )
    assert unsafe["runs"] == {} and any('bad"name' in issue for issue in unsafe["issues"])


def test_a_web_run_gets_a_short_label_and_keeps_its_folder_key(tmp_path):
    folder = "web-" + "e8" * 16
    put(
        tmp_path,
        f"runs/{folder}/workflow.json",
        json.dumps({"run": {"issuer_name": "Beta Group", "as_of": "2025-06-30"}}),
    )
    catalogue = {
        "issues": [],
        "real": [
            {"id": folder, "name": folder, "sector": "Unclassified", "period": "", "artifacts": []}
        ],
    }
    run = store.workspace_store(tmp_path, catalogue)["runs"][folder]
    assert run["run"] == "WEB-E8E8E8E8" and run["folder"] == folder


def test_one_unreadable_run_or_report_does_not_take_the_library_down(tmp_path):
    catalogue = workspace(tmp_path)
    locked = tmp_path / "runs/alpha-001/CP-4A.md"
    locked.chmod(0)
    (tmp_path / "runs/launched/deliveries/abc/view.json").write_text("{}")
    try:
        result = store.workspace_store(tmp_path, catalogue)
    finally:
        locked.chmod(0o600)
    assert list(result["runs"]) == ["empty-001", "launched"]
    assert any(issue.startswith("alpha-001:") for issue in result["issues"])
    assert result["reports"][0]["id"] == "alpha-report" and [
        r["id"] for r in result["reports"]
    ] == ["alpha-report"]
    assert any("deliveries/abc" in issue for issue in result["issues"])


def plain_run(folder: str) -> dict:
    return {"issues": [], "real": [{"id": folder, "name": folder, "artifacts": []}]}


def test_files_that_are_not_handoffs_do_not_take_the_library_down(tmp_path):
    put(tmp_path, "runs/odd/CP-0.md", BETA)
    put(tmp_path, "runs/odd/CP-notes.md", "# Someone's notes\n")
    (tmp_path / "runs/odd/CP-7.md").mkdir()
    result = store.workspace_store(tmp_path, plain_run("odd"))
    assert list(result["outputs"]) == ["odd/CP-0.md"] and result["issues"] == []


def test_a_link_out_of_the_run_is_not_read(tmp_path):
    put(tmp_path, "private.md", "# Private\n\nNot part of any run.\n")
    put(tmp_path, "runs/linked/CP-0.md", BETA)
    (tmp_path / "runs/linked/CP-1.md").symlink_to(tmp_path / "private.md")
    result = store.workspace_store(tmp_path, plain_run("linked"))
    assert list(result["outputs"]) == ["linked/CP-0.md"]


def test_runs_carry_the_recorded_workflow_and_as_of_and_none_when_unrecorded(tmp_path):
    runs = store.workspace_store(tmp_path, workspace(tmp_path))["runs"]
    assert (runs["launched"]["pathway"], runs["launched"]["asOf"]) == (
        "credit_snapshot",
        "2025-06-30",
    )
    assert (runs["alpha-001"]["pathway"], runs["alpha-001"]["asOf"]) == (None, None)


def test_a_malformed_run_manifest_falls_back_to_the_catalogue(tmp_path):
    for number, manifest in enumerate(
        ('{"run": null}', '{"run": "x"}', "[]", '{"run": {"issuer_name": 7}}')
    ):
        folder = f"odd-{number}"
        put(tmp_path, f"runs/{folder}/workflow.json", manifest)
        run = store.workspace_store(tmp_path, plain_run(folder))["runs"][folder]
        assert run["issuer"] == folder and run["period"] == "Period not recorded"
        assert run["pathway"] is None and run["asOf"] is None


def test_two_different_deliveries_of_a_module_can_be_told_apart(tmp_path):
    put(tmp_path, "runs/twice/deliveries/aaaaaaaaaaaa/CP-0.md", BETA)
    put(tmp_path, "runs/twice/deliveries/bbbbbbbbbbbb/CP-0.md", BETA + "\nRepaired.\n")
    result = store.workspace_store(tmp_path, plain_run("twice"))
    labels = sorted(output["label"] for output in result["outputs"].values())
    assert labels == ["CP-0 · delivery aaaaaaaa", "CP-0 · delivery bbbbbbbb"]
    assert result["runs"]["twice"]["modules"]["CP-0"]["default"] is None


def test_the_library_reads_a_workspace_in_its_own_small_process(tmp_path):
    """Every page load runs this, so it must not import the engine; Windows pays for each import."""
    text = (
        "# CP-0\n\n## Findings\n\nNet debt ≥ 0 at Şişli − a Windows code page cannot print these.\n"
    )
    put(tmp_path, "runs/own/CP-0.md", text)
    script = ROOT / "apps/issuer-library/engine/store.py"
    probe = (
        "import runpy,sys;sys.argv=[sys.argv[1],sys.argv[2]];"
        "runpy.run_path(sys.argv[0],run_name='__main__');"
        "sys.stderr.write(' '.join(m for m in sys.modules "
        "if m.split('.')[0] in ('deploy_workflow','deploy_vii','pydantic')))"
    )
    done = subprocess.run(
        [sys.executable, "-I", "-B", "-X", "utf8", "-c", probe, str(script), str(tmp_path)],
        input=json.dumps(plain_run("own")).encode(),
        capture_output=True,
        check=True,
    )
    assert done.stderr == b""
    sent = json.loads(done.stdout.decode("utf-8"))
    output = sent["outputs"]["own/CP-0.md"]
    assert sent["handoffs"][output["sha256"]][1]["blocks"][0]["text"].startswith(
        "Net debt ≥ 0 at Şişli −"
    )


def test_one_run_that_breaks_the_parser_is_reported_and_the_rest_stay(tmp_path, monkeypatch):
    put(tmp_path, "runs/good/CP-0.md", BETA)
    put(tmp_path, "runs/bad/CP-0.md", BETA)
    real = store.output_label

    def label(module, path, siblings):
        if path.parent.name == "bad":
            raise IndexError("an unforeseen file name")
        return real(module, path, siblings)

    monkeypatch.setattr(store, "output_label", label)
    catalogue = {"issues": [], "real": [*plain_run("good")["real"], *plain_run("bad")["real"]]}
    result = store.workspace_store(tmp_path, catalogue)
    assert list(result["runs"]) == ["good"]
    assert any(issue.startswith("bad: could not be read") for issue in result["issues"])


def test_windows_case_blind_matching_adds_no_odd_handoffs(tmp_path, monkeypatch):
    put(tmp_path, "runs/case/CP-0.md", BETA)
    put(tmp_path, "runs/case/CP-1.MD", BETA + "Upper case suffix.\n")
    put(tmp_path, "runs/case/cp-2.md", BETA + "Lower case name.\n")

    def case_blind(self, pattern):
        if "/" in pattern:
            return iter(())
        return (p for p in self.iterdir() if fnmatch.fnmatchcase(p.name.lower(), pattern.lower()))

    monkeypatch.setattr(Path, "glob", case_blind)
    result = store.workspace_store(tmp_path, plain_run("case"))
    assert list(result["outputs"]) == ["case/CP-0.md"] and result["issues"] == []


READER_FIXTURE = ROOT / "apps/issuer-library/designs/reader-fixture/CP-1.md"


def reader_sections(text=None):
    return store.parse_source(READER_FIXTURE.read_text() if text is None else text)


def test_reader_fields_read_the_synthetic_handoff():
    fields = store.reader_fields(reader_sections())
    summary = fields["summary"]
    assert summary["bottomLine"] == (
        "Total debt / EBITDA fell from 4.20x to 3.60x while liquidity held above 275."
    )
    assert summary["confidence"] == "Medium"
    assert summary["limitation"] == "The maturity schedule has no FY2027 figure."
    assert summary["line"] == 17
    assert [(f["finding"], f["impact"], f["confidence"]) for f in summary["findings"]] == [
        (
            "Leverage fell over the two years.",
            "More debt capacity before a covenant test.",
            "Medium",
        ),
        (
            "Liquidity held. <img src=x onerror=alert(document.domain)>",
            "No near-term funding gap is shown.",
            "Low",
        ),
    ]
    assert [f["line"] for f in summary["findings"]] == [21, 22]
    assert fields["charts"] == [
        {"title": "Leverage", "unit": "x", "table": 26, "columns": [1, 2]},
        {"title": "Interest cover", "unit": "x", "table": 33, "columns": [1]},
        {"title": "Liquidity", "unit": "US$m", "table": 40, "columns": [1, 2]},
        {"title": "Debt maturities", "unit": "US$m", "table": 47, "columns": [1]},
    ]
    assert fields["issue"] is None


def test_the_fixture_passes_the_launcher_reader_check():
    sys.path.insert(0, str(ROOT / "src"))
    from deploy_workflow.reader_summary import reader_issues

    assert reader_issues(READER_FIXTURE.read_text()) == ()


def test_a_handoff_without_a_reader_section_has_no_issue():
    assert store.reader_fields(reader_sections(CP1)) == {
        "summary": None,
        "charts": [],
        "issue": None,
    }


@pytest.mark.parametrize(
    ("old", "new", "named"),
    [
        (
            "| Bottom line | Confidence | Main limitation |",
            "| Conclusion | Confidence | Limit |",
            "Reader summary",
        ),
        (
            "| Finding | Creditor impact | Confidence |",
            "| Item | Effect | Confidence |",
            "Reader summary",
        ),
        ("| Period | Debt maturing |", "| Year | Debt maturing |", "Chart data: debt maturities"),
    ],
)
def test_a_malformed_section_is_named_and_the_handoff_still_parses(old, new, named):
    fields = store.reader_fields(reader_sections(READER_FIXTURE.read_text().replace(old, new)))
    assert named in fields["issue"]
    if "Chart" in named:
        assert fields["summary"] is not None and len(fields["charts"]) == 3
    else:
        assert fields["summary"] is None and len(fields["charts"]) == 4


def test_a_malformed_reader_section_reaches_the_workspace_issues(tmp_path):
    folder = tmp_path / "runs/web-1"
    folder.mkdir(parents=True)
    broken = READER_FIXTURE.read_text().replace("| Bottom line |", "| Conclusion |")
    (folder / "CP-1.md").write_text(broken)
    catalogue = {
        "issues": [],
        "real": [{"id": "web-1", "name": "web-1", "sector": "", "period": "", "artifacts": []}],
    }
    result = store.workspace_store(tmp_path, catalogue)
    assert any("web-1/CP-1.md" in issue and "Reader summary" in issue for issue in result["issues"])
    output = result["outputs"]["web-1/CP-1.md"]
    assert output["summary"] is None
    sections = result["handoffs"][output["sha256"]]
    assert any(s["heading"] == "Chart data: leverage" for s in sections)


def many_runs(root: Path, count: int) -> dict:
    for number in range(count):
        put(root, f"runs/copy-{number}/CP-1.md", CP1)
    real = [{"id": f"copy-{n}", "name": f"copy-{n}", "artifacts": []} for n in range(count)]
    return {"issues": [], "real": real}


def test_identical_handoff_bytes_in_many_runs_are_sent_once(tmp_path):
    one = store.workspace_store(tmp_path / "one", many_runs(tmp_path / "one", 1))
    three = store.workspace_store(tmp_path / "three", many_runs(tmp_path / "three", 3))
    digest = hashlib.sha256(CP1.encode()).hexdigest()
    assert list(three["handoffs"]) == [digest]
    assert sorted(three["outputs"]) == ["copy-0/CP-1.md", "copy-1/CP-1.md", "copy-2/CP-1.md"]
    assert all("sections" not in record for record in three["outputs"].values())
    assert all(record["sha256"] == digest for record in three["outputs"].values())
    assert three["handoffs"][digest][1]["blocks"][0]["rows"][0]["cells"] == ["Revenue", "0"]
    assert len(json.dumps(three)) < 1.5 * len(json.dumps(one))


def test_a_shared_unparseable_handoff_is_parsed_once_and_flagged_in_each_run(tmp_path):
    bad = "Body before any heading\n\n## Later\n\nText\n"
    for name in ("x-1", "x-2"):
        put(tmp_path, f"runs/{name}/CP-2.md", bad)
    real = [{"id": n, "name": n, "artifacts": []} for n in ("x-1", "x-2")]
    result = store.workspace_store(tmp_path, {"issues": [], "real": real})
    assert len(result["handoffs"]) == 1
    for name in ("x-1", "x-2"):
        assert "Body before" in result["outputs"][f"{name}/CP-2.md"]["parseError"]
        assert any(f"{name}/CP-2.md" in issue for issue in result["issues"])


# Issuer identity: expected keys, headings and terms are written here, not computed by the store.
def view_delivery(root: Path, folder: str, run_id: str, issuer_id: str | None, name: str) -> dict:
    """A deliverable whose view.json names its run and issuer; returns its catalogue artifact."""
    run = {"run_id": run_id, "issuer_name": name, "as_of": "2025-06-30"}
    if issuer_id is not None:
        run["issuer_id"] = issuer_id
    files = {
        "report.html": put(root, f"{folder}/report.html", "<html>r</html>"),
        "view.json": put(root, f"{folder}/view.json", json.dumps({"run": run})),
    }
    put(root, f"{folder}/delivery.json", json.dumps({"files": files}))
    href = f"/files/{folder}/report.html?sha256=x"
    return {
        "folder": folder,
        "label": folder,
        "state": "final",
        "available": True,
        "href": href,
    }


def identity_catalogue(root: Path, runs: dict, deliveries: list) -> dict:
    """runs: folder -> (catalogue name or None for the folder name, catalogue issuer or None,
    manifest or None)."""
    real = []
    for folder, (name, issuer, manifest) in runs.items():
        put(root, f"runs/{folder}/CP-0.md", "# CP-0\n\n## Request\n\nText.\n")
        if manifest is not None:
            put(root, f"runs/{folder}/workflow.json", json.dumps({"run": manifest}))
        real.append(
            {
                "id": folder,
                "name": name or folder,
                "issuer": issuer or "Unclassified",
                "sector": "",
                "period": "",
                "artifacts": [],
            }
        )
    for artifact in deliveries:
        pseudo = {"id": f"delivery:{Path(artifact['folder']).name}", "name": "x", "sector": ""}
        real.append({**pseudo, "period": "", "artifacts": [artifact]})
    return {"issues": [], "real": real}


def identities(tmp_path, runs, deliveries=()):
    result = store.workspace_store(tmp_path, identity_catalogue(tmp_path, runs, list(deliveries)))
    return result, result["runs"]


def test_agreeing_deliveries_name_an_otherwise_unrecorded_run(tmp_path):
    first = view_delivery(tmp_path, "deliverables/d1", "plain-001", "DLT", "Delta Corp")
    second = view_delivery(tmp_path, "deliverables/d2", "plain-001", "dlt", "Delta Corp")
    result, runs = identities(tmp_path, {"plain-001": (None, None, None)}, [first, second])
    run = runs["plain-001"]
    assert (run["issuer"], run["title"]) == ("Delta Corp", "Delta Corp")
    assert (run["issuerKey"], run["issuerHeading"]) == ("id:dlt", "Delta Corp")
    assert run["issuerTerms"] == ["DLT", "Delta Corp"]
    assert not any("different issuers" in issue for issue in result["issues"])


def test_disagreeing_deliveries_leave_the_run_unrecorded_and_say_so(tmp_path):
    one = view_delivery(tmp_path, "deliverables/d1", "plain-001", "AAA", "Alpha Corp")
    other = view_delivery(tmp_path, "deliverables/d2", "plain-001", "BBB", "Beta Corp")
    result, runs = identities(tmp_path, {"plain-001": (None, None, None)}, [one, other])
    run = runs["plain-001"]
    assert (run["issuer"], run["issuerKey"], run["issuerHeading"], run["issuerTerms"]) == (
        "plain-001",
        None,
        None,
        [],
    )
    assert (
        "runs/plain-001: deliverables name different issuers; issuer left unrecorded"
        in result["issues"]
    )


def test_deliveries_that_agree_on_the_id_but_not_the_name_disagree(tmp_path):
    one = view_delivery(tmp_path, "deliverables/d1", "plain-001", "AAA", "Alpha Corp")
    other = view_delivery(tmp_path, "deliverables/d2", "plain-001", "AAA", "Alpha Corporation")
    result, runs = identities(tmp_path, {"plain-001": (None, None, None)}, [one, other])
    assert runs["plain-001"]["issuerKey"] is None
    assert any("different issuers" in issue for issue in result["issues"])


def test_an_unavailable_delivery_names_nobody(tmp_path):
    gone = {
        **view_delivery(tmp_path, "deliverables/d1", "plain-001", "AAA", "Alpha"),
        "available": False,
    }
    result, runs = identities(tmp_path, {"plain-001": (None, None, None)}, [gone])
    assert runs["plain-001"]["issuerKey"] is None and runs["plain-001"]["issuer"] == "plain-001"
    assert not any("different issuers" in issue for issue in result["issues"])


def test_a_delivery_for_another_run_names_nobody(tmp_path):
    other = view_delivery(tmp_path, "deliverables/d1", "someone-else", "AAA", "Alpha")
    _, runs = identities(tmp_path, {"plain-001": (None, None, None)}, [other])
    assert runs["plain-001"]["issuerKey"] is None


def test_a_recorded_name_outranks_a_delivery(tmp_path):
    delivered = view_delivery(tmp_path, "deliverables/d1", "named-001", "ZZZ", "Delivered Name")
    manifest = {"issuer_name": "Manifest Name", "issuer_id": "MAN"}
    _, runs = identities(tmp_path, {"named-001": (None, None, manifest)}, [delivered])
    assert (runs["named-001"]["issuer"], runs["named-001"]["issuerKey"]) == (
        "Manifest Name",
        "id:man",
    )


def test_the_catalogue_name_counts_only_when_it_differs_from_the_folder(tmp_path):
    seeded = {"seed-001": ("Seed Co", "SEED", None), "bare-001": (None, "BARE", None)}
    _, runs = identities(tmp_path, seeded)
    assert (runs["seed-001"]["issuer"], runs["seed-001"]["issuerKey"]) == ("Seed Co", "id:seed")
    assert (runs["bare-001"]["issuer"], runs["bare-001"]["issuerKey"]) == ("bare-001", None)


def test_ids_that_differ_only_in_case_join_runs_under_the_most_frequent_name(tmp_path):
    spec = {
        "a-001": (None, None, {"issuer_name": "Xyz Corporation", "issuer_id": "XYZ"}),
        "b-001": (None, None, {"issuer_name": "Xyz Corp", "issuer_id": "xyz"}),
        "c-001": (None, None, {"issuer_name": "Xyz Corp", "issuer_id": "Xyz"}),
    }
    _, runs = identities(tmp_path, spec)
    assert {run["issuerKey"] for run in runs.values()} == {"id:xyz"}
    assert {run["issuerHeading"] for run in runs.values()} == {"Xyz Corp"}
    assert runs["a-001"]["issuerTerms"] == ["XYZ", "Xyz", "Xyz Corp", "Xyz Corporation", "xyz"]
    assert runs["a-001"]["issuer"] == "Xyz Corporation"


def test_an_exact_recorded_name_joins_runs_without_ids_and_transitively(tmp_path):
    spec = {
        "a-001": (None, None, {"issuer_name": "Same Name"}),
        "b-001": (None, None, {"issuer_name": "Same Name", "issuer_id": "SN"}),
        "c-001": (None, None, {"issuer_name": "Other Name", "issuer_id": "sn"}),
        "d-001": (None, None, {"issuer_name": "same name"}),
    }
    _, runs = identities(tmp_path, spec)
    assert {runs[k]["issuerKey"] for k in ("a-001", "b-001", "c-001")} == {"id:sn"}
    assert runs["d-001"]["issuerKey"] == "name:same name"
    assert runs["d-001"]["issuerTerms"] == ["same name"]


def test_a_group_without_an_id_is_keyed_by_its_heading(tmp_path):
    spec = {"a-001": (None, None, {"issuer_name": "No Id Inc"})}
    _, runs = identities(tmp_path, spec)
    assert (runs["a-001"]["issuerKey"], runs["a-001"]["issuerHeading"]) == (
        "name:No Id Inc",
        "No Id Inc",
    )


def test_a_tied_heading_goes_to_the_alphabetically_first_name(tmp_path):
    spec = {
        "a-001": (None, None, {"issuer_name": "beta Co", "issuer_id": "K"}),
        "b-001": (None, None, {"issuer_name": "Alpha Co", "issuer_id": "K"}),
        "c-001": (None, None, {"issuer_name": "Alpha co", "issuer_id": "K"}),
    }
    _, runs = identities(tmp_path, spec)
    assert {run["issuerHeading"] for run in runs.values()} == {"Alpha Co"}


def test_a_curated_name_comes_first_and_an_unrecorded_run_shares_no_group(tmp_path):
    spec = {
        "tdg-002": (None, "TDG", {"issuer_name": "Manifest Loses", "issuer_id": "TDG"}),
        "blank-001": (None, None, None),
        "blank-002": (None, None, None),
    }
    _, runs = identities(tmp_path, spec)
    assert (runs["tdg-002"]["issuer"], runs["tdg-002"]["issuerKey"]) == (
        "TransDigm Group",
        "id:tdg",
    )
    for folder in ("blank-001", "blank-002"):
        assert [runs[folder][f] for f in ("issuerKey", "issuerHeading", "issuerTerms")] == [
            None,
            None,
            [],
        ]


def test_a_report_takes_the_key_of_the_group_holding_its_issuer_id(tmp_path):
    spec = {"a-001": (None, None, {"issuer_name": "Alpha Co", "issuer_id": "ALP"})}
    held = view_delivery(tmp_path, "deliverables/held", "elsewhere", "alp", "Alpha Co")
    loose = view_delivery(tmp_path, "deliverables/loose", "elsewhere", "NEW", "New Co")
    anonymous = view_delivery(tmp_path, "deliverables/anon", "elsewhere", None, "Nameless")
    result, _ = identities(tmp_path, spec, [held, loose, anonymous])
    keys = {report["id"]: report["issuerKey"] for report in result["reports"]}
    assert keys == {"held": "id:alp", "loose": "id:new", "anon": None}


# Published models: expected values are written here, not computed by the store.
FORECAST = (
    "# CP-2G\n\n## Findings\n\n### T2H.3 — Assumption Register\n\n"
    "Every row applies to the group;\nrates are decimals.\n\n"
    "| ID | Driver | Rationale |\n|---|---|---|\n| G | Growth 0.05 | Analyst judgment |\n"
    "| M | Margin 0.5 | Held |\n"
)


def model_delivery(root, folder, forecast=FORECAST, exact=None, **options):
    """A model deliverable (model.html, no report.html); returns its catalogue artifact.

    options: scope, sources, previous (the previous directory) and extra (more files by name).
    """
    scope = options.pop("scope", "Scope.")
    sources, previous, extra = (options.pop(k, None) for k in ("sources", "previous", "extra"))
    assert not options, options
    files = {
        "model.html": put(root, f"{folder}/model.html", "<html>model</html>"),
        "view.json": put(
            root,
            f"{folder}/view.json",
            json.dumps(
                {
                    "run": {
                        "run_id": "alpha-001",
                        "issuer_id": "ALP",
                        "issuer_name": "Alpha Holdings",
                        "as_of": "2025-06-30",
                    },
                    "mode": "candidate",
                    "analytical_qualification": "partial",
                }
            ),
        ),
    }
    if forecast is not None:
        files["forecast.md"] = put(root, f"{folder}/forecast.md", forecast)
    if exact is not None:
        files["forecast_exact.json"] = put(
            root,
            f"{folder}/forecast_exact.json",
            exact if isinstance(exact, str) else json.dumps(exact),
        )
    for name, text in (extra or {}).items():
        files[name] = put(root, f"{folder}/{name}", text)
    record = {
        "scope": scope,
        "files": files,
        "sources": sources or {},
        "input_contract": "Six headings.",
        "presentation_repair": None,
        "previous_directory": previous,
    }
    put(root, f"{folder}/delivery.json", json.dumps(record))
    return {
        "folder": folder,
        "kind": "model",
        "label": folder,
        "state": "candidate",
        "available": True,
        "href": f"/files/{folder}/model.html?sha256=m",
    }


def models_of(root, *artifacts, edit=None):
    catalogue = workspace(root)
    if edit:
        edit()  # After the workspace is written, before the store reads it.
    catalogue["real"].append(
        {"id": "delivery:m", "name": "x", "sector": "", "period": "", "artifacts": list(artifacts)}
    )
    return store.workspace_store(root, catalogue)


def test_a_model_is_listed_with_its_register_sources_and_not_as_a_report(tmp_path):
    cp1 = hashlib.sha256(CP1.encode()).hexdigest()
    artifact = model_delivery(
        tmp_path,
        "deliverables/m-2",
        sources={
            "annual": {"path": "runs/alpha-001/CP-1.md", "sha256": cp1},
            "other": {"path": "runs/alpha-001/CP-4A.md", "sha256": "0" * 64},
            "gone": {"path": "runs/alpha-001/missing.md", "sha256": "1" * 64},
        },
        previous="deliverables/m-1",
    )
    result = models_of(tmp_path, artifact)
    assert [r["id"] for r in result["reports"]] == ["alpha-report", "abc"]
    (model,) = result["models"]
    assert model["id"] == "m-2" and model["previous"] == "m-1"
    assert (model["mode"], model["qualification"]) == ("candidate", "partial")
    assert model["runId"] == "alpha-001" and model["issuerKey"] == "id:alp"
    assert model["scope"] == "Scope." and model["inputContract"] == "Six headings."
    assert model["revisionNote"] is None
    assert model["href"] == "/files/deliverables/m-2/model.html?sha256=m&embedded=1"
    assert model["download"] == "/files/deliverables/m-2/model.html?sha256=m&download=1"
    assert {f["name"] for f in model["files"]} == {"model.html", "view.json", "forecast.md"}
    assert model["register"] == {
        "heading": "T2H.3 — Assumption Register",
        "intro": "Every row applies to the group;\nrates are decimals.",
        "headers": ["ID", "Driver", "Rationale"],
        "rows": [["G", "Growth 0.05", "Analyst judgment"], ["M", "Margin 0.5", "Held"]],
    }
    by_role = {row["role"]: row for row in model["sources"]}
    assert [row["role"] for row in model["sources"]] == ["annual", "other", "gone"]
    assert by_role["annual"] == {
        "role": "annual",
        "path": "runs/alpha-001/CP-1.md",
        "sha256": cp1,
        "changed": False,
        "run": "alpha-001",
        "output": "alpha-001/CP-1.md",
    }
    assert (by_role["other"]["changed"], by_role["other"]["run"]) == (True, None)
    assert by_role["other"]["output"] is None
    assert (by_role["gone"]["changed"], by_role["gone"]["output"]) == (True, None)


def test_a_named_run_without_an_id_takes_its_own_deliverables_id(tmp_path):
    put(tmp_path, "runs/alpha-001/CP-1.md", CP1)
    own = model_delivery(tmp_path, "runs/alpha-001/deliveries/own")  # view.json: issuer_id ALP
    catalogue = {
        "issues": [],
        "real": [
            {
                "id": "alpha-001",
                "name": "Alpha Holdings",
                "issuer": "Unclassified",
                "sector": "",
                "period": "",
                "artifacts": [own],
            }
        ],
    }
    result = store.workspace_store(tmp_path, catalogue)
    run = result["runs"]["alpha-001"]
    (model,) = result["models"]
    assert run["issuerKey"] == "id:alp"
    assert model["issuerKey"] == "id:alp"
    assert model["runId"] == "alpha-001"


def test_the_runs_own_delivery_is_kept_over_a_same_named_model_in_either_order(tmp_path):
    own = model_delivery(tmp_path, "runs/alpha-001/deliveries/m-1")
    other = model_delivery(tmp_path, "deliverables/m-1")
    for artifacts in ((other, own), (own, other)):
        result = models_of(tmp_path, *artifacts)
        (model,) = result["models"]
        assert model["href"].startswith("/files/runs/alpha-001/deliveries/m-1/")
        assert (
            "deliverables/m-1: another published model has the same name m-1; "
            "runs/alpha-001/deliveries/m-1 is shown"
        ) in result["issues"]


def test_with_no_own_delivery_the_first_path_is_kept_and_the_other_named(tmp_path):
    first = model_delivery(tmp_path, "deliverables/m-1")
    second = model_delivery(tmp_path, "runs/beta-001/deliveries/m-1")
    for artifacts in ((second, first), (first, second)):
        result = models_of(tmp_path, *artifacts)
        (model,) = result["models"]
        assert model["href"].startswith("/files/deliverables/m-1/")
        assert (
            "runs/beta-001/deliveries/m-1: another published model has the same name m-1; "
            "deliverables/m-1 is shown"
        ) in result["issues"]


def test_the_same_folder_listed_twice_is_one_model_and_no_issue(tmp_path):
    artifact = model_delivery(tmp_path, "deliverables/m-1")
    result = models_of(tmp_path, artifact, artifact)
    assert len(result["models"]) == 1
    assert not any("same name" in i for i in result["issues"])


def test_a_model_without_a_register_section_has_none(tmp_path):
    artifact = model_delivery(
        tmp_path, "deliverables/m-1", forecast="# CP-2G\n\n## Findings\n\nx\n"
    )
    assert models_of(tmp_path, artifact)["models"][0]["register"] is None
    bare = model_delivery(tmp_path, "deliverables/m-0", forecast=None)
    assert {m["id"]: m for m in models_of(tmp_path, artifact, bare)["models"]}["m-0"][
        "register"
    ] is None


def test_a_changed_source_is_flagged_and_the_model_stays_listed(tmp_path):
    cp1 = hashlib.sha256(CP1.encode()).hexdigest()
    artifact = model_delivery(
        tmp_path,
        "deliverables/m-1",
        sources={"annual": {"path": "runs/alpha-001/CP-1.md", "sha256": cp1}},
    )
    (model,) = models_of(
        tmp_path,
        artifact,
        edit=lambda: (tmp_path / "runs/alpha-001/CP-1.md").write_text(CP1 + "x", encoding="utf-8"),
    )["models"]
    (source,) = model["sources"]
    assert source["changed"] is True and source["run"] is None and source["output"] is None


def test_hostile_text_in_a_model_stays_a_string(tmp_path):
    hostile = "<img src=x onerror=alert(1)>"
    artifact = model_delivery(tmp_path, "deliverables/m-1", scope=hostile)
    (model,) = models_of(tmp_path, artifact)["models"]
    assert model["scope"] == hostile


def test_an_unreadable_model_is_reported_and_the_others_stay(tmp_path):
    good = model_delivery(tmp_path, "deliverables/m-1")
    bad = model_delivery(tmp_path, "deliverables/m-2")
    (tmp_path / "deliverables/m-2/view.json").write_text("{", encoding="utf-8")
    result = models_of(tmp_path, good, bad)
    assert [m["id"] for m in result["models"]] == ["m-1"]
    assert any(i.startswith("deliverables/m-2: could not be read") for i in result["issues"])


@pytest.mark.parametrize(
    ("iso", "shown"),
    [
        ("2024-12-31", "31 December 2024"),
        ("2025-05-01", "1 May 2025"),
        ("2024-02-29", "29 February 2024"),
        ("2023-02-29", "2023-02-29"),
        ("2024-02-30", "2024-02-30"),
        ("0000-01-01", "0000-01-01"),
        ("2024-13-01", "2024-13-01"),
        ("2024-1-05", "2024-1-05"),
        (" 2024-12-31", " 2024-12-31"),
        ("2024-12-31x", "2024-12-31x"),
        ("05/08/2023", "05/08/2023"),
        ("2024-12-31T00:00", "2024-12-31T00:00"),
        ("", ""),
    ],
)
def test_display_date_reads_only_a_valid_calendar_date(iso, shown):
    assert store.display_date(iso) == shown


def test_a_model_with_untyped_fields_keeps_only_strings(tmp_path):
    artifact = model_delivery(tmp_path, "deliverables/m-1")
    record = json.loads((tmp_path / "deliverables/m-1/delivery.json").read_text(encoding="utf-8"))
    record.update(scope=5, input_contract=["x"], presentation_repair={"a": 1})
    record["sources"] = {
        "num": {"path": "runs/alpha-001/CP-1.md", "sha256": 5},
        "badhex": {"path": "runs/alpha-001/CP-1.md", "sha256": "A" * 64},
        "short": {"path": "runs/alpha-001/CP-1.md", "sha256": "a" * 63},
        "path": {"path": 7, "sha256": "a" * 64},
        "whole": "not an object",
    }
    (tmp_path / "deliverables/m-1/delivery.json").write_text(json.dumps(record), encoding="utf-8")
    result = models_of(tmp_path, artifact)
    (model,) = result["models"]
    assert (model["scope"], model["inputContract"], model["revisionNote"]) == (None, None, None)
    for row in model["sources"]:
        assert (row["sha256"], row["changed"]) == (None, None), row
        assert row["path"] is None or isinstance(row["path"], str)
    for role in ("num", "badhex", "short", "path", "whole"):
        assert f"deliverables/m-1: source {role} has an invalid path or hash" in result["issues"]


def test_source_paths_outside_the_workspace_are_never_opened(tmp_path, monkeypatch):
    root = tmp_path / "ws"
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.txt"
    secret.write_text("secret", encoding="utf-8")
    digest = hashlib.sha256(b"secret").hexdigest()
    (root / "runs/alpha-001").mkdir(parents=True)
    (root / "runs/alpha-001/link.md").symlink_to(secret)
    (root / "runs/escape").symlink_to(outside, target_is_directory=True)
    artifact = model_delivery(root, "deliverables/m-1")
    record = json.loads((root / "deliverables/m-1/delivery.json").read_text(encoding="utf-8"))
    record["sources"] = {
        "absolute": {"path": str(secret), "sha256": digest},
        "dotdot": {"path": "runs/alpha-001/../../../outside/secret.txt", "sha256": digest},
        "link": {"path": "runs/alpha-001/link.md", "sha256": digest},
        "dirlink": {"path": "runs/escape/secret.txt", "sha256": digest},
        "outside_runs": {"path": "deliverables/m-1/view.json", "sha256": digest},
        "backslash": {"path": "runs\\alpha-001\\x.md", "sha256": digest},
    }
    (root / "deliverables/m-1/delivery.json").write_text(json.dumps(record), encoding="utf-8")
    opened = []
    real = store.sha256
    monkeypatch.setattr(store, "sha256", lambda p: opened.append(p) or real(p))
    result = models_of(root, artifact)
    (model,) = result["models"]
    assert [(r["sha256"], r["changed"]) for r in model["sources"]] == [(None, None)] * 6
    assert not [p for p in opened if "secret" in str(p) or p.name in {"link.md", "x.md"}]
    assert len([i for i in result["issues"] if "has an invalid path or hash" in i]) == 6


# The cash flow model: expected strings are written here, not computed by the store.
REQUEST = (
    "# CP-2G\n\n## Request\n\nTest paths. Amounts in EUR\nbillions; consolidated.\n\n"
    "## Findings\n\nUSD millions.\n"
)
HOSTILE = "<img src=x onerror=alert(1)>"
ANSWER_KEY = json.loads(
    (ROOT / "apps/issuer-library/designs/forecast-answer-key.json").read_text(encoding="utf-8")
)["cashflow"]


def amount(value, reason=None):
    return {"amount": value, "reason": reason}


def forecast_year(revenue, ebitda, **more):
    year = {
        "year": 2026,
        "planning_start": "2025-10-01",
        "planning_end": "2026-09-30",
        "revenue": amount(revenue),
        "ebitda": amount(ebitda),
        "interest": amount("40"),
        "capex": amount("44"),
        "total_leverage": amount("0.125"),
        "coverage": amount("2"),
        "fcf_to_debt": amount("0.12345"),
        "undrawn": amount(None, "No facility"),
    }
    year.update(more)
    return year


def exact_record(**more):
    record = {
        "base": {},
        "outputs": {
            "REFERENCE": {"years": [forecast_year("1188", "891")]},
            "DOWNSIDE": {"years": [forecast_year("1100", "594")]},
            "UPSIDE": {"years": [forecast_year("9999", "9999")]},
        },
        "scope_limits": ["First <b>limit</b>", "Second limit"],
    }
    record["outputs"]["DOWNSIDE"]["years"][0].pop("interest")
    record.update(more)
    return record


def value(key, amount_text, reason=None):
    return {key: {"amount": amount_text, "reason": reason}}


def calculation_record(**changes):
    fy2024 = {
        "revenue": "1000", "cogs": "400", "gross_profit": "600", "opex_magnitude": "150",
        "ebit_reported": "450", "cash_flow_DA": "50", "operating_ebitda": "500",
        "issuer_ordinary_ebitda": "520", "issuer_as_defined": "540", "interest_cash": "100",
        "tax_cash": "30", "capex_signed": "-40", "cash": "300", "carrying_debt": "2000",
        "net_carrying_debt": "1700", "gross_carrying_multiple": "3.7037",
        "net_carrying_multiple": "3.1481", "issuer_earnings_cash_interest": "5.4",
    }  # fmt: skip
    fy2025 = {**fy2024, "revenue": "1100", "issuer_as_defined": "594", "capex_signed": "-44"}
    values = {
        "FY2024": {k: {"amount": v, "reason": None} for k, v in fy2024.items()},
        "FY2025": {k: {"amount": v, "reason": None} for k, v in fy2025.items()},
    }
    values["FY2025"]["issuer_ordinary_ebitda"] = amount(None, "NOT_SOURCED")
    values["FY2025"]["carrying_debt"] = amount(None, "COMPONENT_MISSING")
    values["FY2025"]["tax_cash"] = amount(None, HOSTILE)
    del values["FY2025"]["cash"]
    record = {"annual_periods": ["FY2024", "FY2025"], "values": values}
    record.update(changes)
    return record


QUARTER_HEAD = (
    "| Source row | Label | 2025-10-01–2025-12-31 | 2024-10-01-2024-12-31 "
    "| 2025-01-01–2025-03-31 |\n"
    "|---|---|---|---|---|\n"
)
QUARTER_MD = (
    "# Quarter\n\nIntro with | a pipe that is not a table.\n\n### Income statement\n"
    + QUARTER_HEAD
    + "| 1 | NET SALES | 200 | 100 | 150 |\n"
    "| 2 | COST OF SALES | 80 | 50 | abc |\n"
    "| 3 | GROSS PROFIT | 120 | 50 | 90 |\n"
    "| 4 | SELLING AND ADMINISTRATIVE EXPENSES | 10 | 5 | — |\n"
    "| 5 | AMORTIZATION OF INTANGIBLE ASSETS | 2 | 1 |  |\n"
    "| 6 | INCOME FROM OPERATIONS | (30) | 44 | 85 |\n\n"
    "### Segment revenue\n" + QUARTER_HEAD + "| 1 | Total <b>Alpha</b> | 120 | 60 | 90 |\n"
    "| 2 | Total Beta | 80 | 40 | 60 |\n"
    "| 3 | Net Sales | 200 | 100 | 150 |\n\n"
    "### Segment bridge\n"
    + QUARTER_HEAD
    + "| 1 | Total Company EBITDA As Defined | 100 | 80 | 80 |\n"
    "| 2 | Depreciation and amortization expense | 7 | 6 | 5 |\n"
    "| 3 | Interest expense-net | 1 | 1 | 1 |\n"
    "| 4 | Acquisition costs | 3 | 2 |  |\n"
    "| 5 | Other, net | (4) | — | 1 |\n"
    "| 6 | Quarter only item | 9 | 8 | 7 |\n"
    "| 7 | Income from continuing operations before income taxes | 99 | 99 | 99 |\n\n"
    "### Issuer bridge\n"
    + QUARTER_HEAD
    + "| 1 | Depreciation and amortization expense | 7 | 6 | 5 |\n"
    "| 2 | EBITDA | 105 | 82 | 70 |\n"
)
ANNUAL_HEAD = "| Reported line | FY2025 | FY2024 |\n|---|---:|---:|\n"
ANNUAL_MD = (
    "# Annual\n\n### Period register\n\n| Period | Type | Start | End |\n|---|---|---|---|\n"
    "| FY2024 | Historical duration | 2023-10-01 | 2024-09-30 |\n"
    "| FY2025 | Historical duration | 2024-10-01 | 2025-09-30 |\n\n"
    "### Segments\n\n" + ANNUAL_HEAD + "| Total <b>Alpha</b> | 660 | 600 |\n"
    "| Total Beta | 440 | 400 |\n"
    "| Total Gamma | 1 | 2 |\n"
    "| Net Sales | 1,100 | 1,000 |\n\n"
    "### Bridge\n\n" + ANNUAL_HEAD + "| Total Company EBITDA As Defined | 594 | 540 |\n"
    "| Interest expense-net | 9 | 9 |\n"
    "| Acquisition costs | 20 | 10 |\n"
    "| Other, net | (5) | 5 |\n"
    "| Income from continuing operations before income taxes | 1 | 1 |\n\n"
    "### Debt\n\n| Instrument | Sep 30, 2024 amount / status | Terms |\n|---|---|---|\n"
    "| Trade receivable securitization | Gross 121; carrying 120; commitment 650 | x |\n"
    "| Term loans aggregate | Principal 1,100; carrying 1,000 after costs | x |\n"
    "| Revolving credit facility | Commitment 910; drawn 5 | x |\n"
    "| 6% secured notes due 2030 | Principal 500; carrying 500 | x |\n"
    "| 5% senior subordinated notes due 2029 | Principal 300; carrying 300 | x |\n"
)


def cashflow_files(calculation=None, annual=ANNUAL_MD, quarter=QUARTER_MD):
    files = {
        "calculation.json": json.dumps(calculation or calculation_record()),
        "annual.md": annual,
        "quarter.md": quarter,
    }
    return {name: text for name, text in files.items() if text is not None}


def cashflow_of(tmp_path, forecast=REQUEST, exact=None, extra=None):
    """(cashflow, issues about the four cash flow files) of one synthetic model."""
    artifact = model_delivery(
        tmp_path,
        "deliverables/m-1",
        forecast=forecast,
        exact=exact_record() if exact is None else exact,
        extra=cashflow_files() if extra is None else extra,
    )
    result = models_of(tmp_path, artifact)
    names = ("forecast_exact", "calculation", "annual", "quarter")
    return result["models"][0]["cashflow"], [
        i for i in result["issues"] if any(n in i for n in names)
    ]


def row(cashflow, label):
    return next(r for r in cashflow["rows"] if r["label"] == label)


def shown(cashflow, label):
    return [c["display"] for c in row(cashflow, label)["cells"]]


# Security review L1-L3: model files are read only as bounded regular files; nothing hangs or
# drops a model.
def within(seconds, call):
    """Run call on a thread; a read that blocks forever (a FIFO) fails the test, not hangs it."""
    box = {}
    thread = threading.Thread(target=lambda: box.update(value=call()), daemon=True)
    thread.start()
    thread.join(seconds)
    assert not thread.is_alive(), "the store blocked"
    return box["value"]


def source_model(tmp_path, role, path, prepare):
    root = tmp_path / "ws"
    prepare(root)
    artifact = model_delivery(root, "deliverables/m-1")
    record = json.loads((root / "deliverables/m-1/delivery.json").read_text(encoding="utf-8"))
    record["sources"] = {role: {"path": path, "sha256": "a" * 64}}
    (root / "deliverables/m-1/delivery.json").write_text(json.dumps(record), encoding="utf-8")
    result = within(20, lambda: models_of(root, artifact))
    return result, [m for m in result["models"] if m["id"] == "m-1"]


def test_a_fifo_source_keeps_the_row_without_a_hash_and_is_reported(tmp_path):
    result, (model,) = source_model(
        tmp_path,
        "fifo",
        "runs/alpha-001/pipe",
        lambda root: (
            (root / "runs/alpha-001").mkdir(parents=True) or os.mkfifo(root / "runs/alpha-001/pipe")
        ),
    )
    (row,) = model["sources"]
    assert (row["role"], row["sha256"], row["changed"]) == ("fifo", None, None)
    assert "deliverables/m-1: source fifo is not a readable file" in result["issues"]


def test_a_source_over_64_mib_is_not_read_and_is_reported(tmp_path):
    def big(root):
        (root / "runs/alpha-001").mkdir(parents=True)
        with open(root / "runs/alpha-001/big.bin", "wb") as f:
            f.truncate(store.MODEL_FILE_LIMIT + 1)

    result, (model,) = source_model(tmp_path, "big", "runs/alpha-001/big.bin", big)
    (row,) = model["sources"]
    assert (row["sha256"], row["changed"]) == (None, None)
    assert "deliverables/m-1: source big is not a readable file" in result["issues"]


def test_a_source_path_with_a_nul_byte_is_an_invalid_source_not_a_dropped_model(tmp_path):
    result, (model,) = source_model(tmp_path, "nul", "runs/alpha-001/a\x00b.md", lambda root: None)
    (row,) = model["sources"]
    assert (row["sha256"], row["changed"]) == (None, None)
    assert "deliverables/m-1: source nul has an invalid path or hash" in result["issues"]


def test_forecast_md_through_a_symlink_is_not_read_even_when_its_bytes_match(tmp_path):
    root = tmp_path / "ws"
    artifact = model_delivery(root, "deliverables/m-1")
    outside = tmp_path / "outside.md"
    outside.write_text(FORECAST, encoding="utf-8")
    (root / "deliverables/m-1/forecast.md").unlink()
    (root / "deliverables/m-1/forecast.md").symlink_to(outside)
    result = models_of(root, artifact)
    (model,) = result["models"]
    assert (model["register"], model["cashflow"]) == (None, None)
    assert "deliverables/m-1: forecast.md does not match its delivery record" in result["issues"]


def test_a_forecast_md_whose_hash_changed_is_not_read_and_the_model_stays(tmp_path):
    artifact = model_delivery(tmp_path, "deliverables/m-1")
    (model,) = models_of(
        tmp_path,
        artifact,
        edit=lambda: (tmp_path / "deliverables/m-1/forecast.md").write_text(
            FORECAST + "\nEdited.\n", encoding="utf-8"
        ),
    )["models"]
    assert model["register"] is None and model["cashflow"] is None
    result = models_of(
        tmp_path,
        artifact,
        edit=lambda: (tmp_path / "deliverables/m-1/forecast.md").write_text("x", encoding="utf-8"),
    )
    assert "deliverables/m-1: forecast.md does not match its delivery record" in result["issues"]


def test_forecast_exact_json_must_match_its_listed_hash_and_not_be_a_symlink(tmp_path):
    artifact = model_delivery(tmp_path, "deliverables/m-1", forecast=REQUEST, exact=exact_record())
    path = tmp_path / "deliverables/m-1/forecast_exact.json"
    result = models_of(tmp_path, artifact, edit=lambda: path.write_text("{}", encoding="utf-8"))
    assert result["models"][0]["cashflow"] is None
    assert (
        "deliverables/m-1: forecast_exact.json does not match its delivery record"
        in result["issues"]
    )
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps(exact_record()), encoding="utf-8")
    result = models_of(tmp_path, artifact, edit=lambda: (path.unlink(), path.symlink_to(outside)))
    assert result["models"][0]["cashflow"] is None
    assert (
        "deliverables/m-1: forecast_exact.json does not match its delivery record"
        in result["issues"]
    )


def test_a_model_read_error_names_its_type_and_reason_and_never_the_bytes(tmp_path):
    good = model_delivery(tmp_path, "deliverables/m-1")
    bad = model_delivery(tmp_path, "deliverables/m-2")
    raw = b"\xff\xfe TOPSECRET"
    (tmp_path / "deliverables/m-2/view.json").write_bytes(raw)
    record = tmp_path / "deliverables/m-2/delivery.json"
    listed = json.loads(record.read_text(encoding="utf-8"))
    listed["files"]["view.json"] = hashlib.sha256(
        raw
    ).hexdigest()  # The server verified these bytes.
    record.write_text(json.dumps(listed), encoding="utf-8")
    issues = models_of(tmp_path, good, bad)["issues"]
    (issue,) = [i for i in issues if i.startswith("deliverables/m-2: could not be read")]
    assert "UnicodeDecodeError" in issue and "invalid start byte" in issue
    assert "TOPSECRET" not in issue and "\\x" not in issue and "b'" not in issue


NA = "n.a."
NM = "n.m."
DASH = "—"  # no cell displays this any more
NO_VALUE = "the model's source table has no value for this period"
PRINTED = "printed as — in the source"
QUARTER_LABELS = ["Q1 FY2025 (YTD)", "2025-01-01–2025-03-31", "Q1 FY2026 (YTD)"]


def test_columns_are_quarters_then_fiscal_years_then_base_case_and_downside(tmp_path):
    cashflow, issues = cashflow_of(tmp_path)
    assert issues == []
    assert cashflow["units"] == "EUR billions"
    assert [(c["group"], c["label"]) for c in cashflow["columns"]] == [
        ("Quarter", "Q1 FY2025 (YTD)"),
        ("Quarter", "2025-01-01–2025-03-31"),
        ("Quarter", "Q1 FY2026 (YTD)"),
        ("Fiscal year", "FY2024"),
        ("Fiscal year", "FY2025"),
        ("Base case (reference illustration)", "FY2026E"),
        ("Downside", "FY2026E"),
    ]
    assert [(c["start"], c["end"]) for c in cashflow["columns"]] == [
        ("2024-10-01", "2024-12-31"),
        ("2025-01-01", "2025-03-31"),
        ("2025-10-01", "2025-12-31"),
        (None, None),
        (None, None),
        ("2025-10-01", "2026-09-30"),
        ("2025-10-01", "2026-09-30"),
    ]
    assert list(dict.fromkeys(r["band"] for r in cashflow["rows"])) == ANSWER_KEY["bands"]
    assert cashflow["limits"] == ["First <b>limit</b>", "Second limit"]


def test_a_later_quarter_that_is_not_the_first_is_labelled_by_its_dates(tmp_path):
    cashflow, _ = cashflow_of(tmp_path)
    assert cashflow["columns"][1]["label"] == "2025-01-01–2025-03-31"
    # The forecast's planning_start no longer decides a quarter's label: only the period
    # register does.
    forecast = exact_record()
    for case in forecast["outputs"].values():
        case["years"][0]["planning_start"] = "2025-07-01"
    cashflow, _ = cashflow_of(tmp_path, exact=forecast)
    assert [c["label"] for c in cashflow["columns"][:3]] == QUARTER_LABELS


def test_business_units_come_from_the_total_rows_with_hostile_text_literal(tmp_path):
    cashflow, _ = cashflow_of(tmp_path)
    labels = [r["label"] for r in cashflow["rows"] if r["band"] == "Revenue"]
    assert labels == [
        "<b>Alpha</b>",
        "<b>Alpha</b> YoY growth",
        "Beta",
        "Beta YoY growth",
        "Gamma",
        "Gamma YoY growth",
        "Revenue",
        "Revenue YoY growth",
    ]
    assert shown(cashflow, "<b>Alpha</b>") == ["60", "90", "120", "600", "660", NM, NM]
    assert shown(cashflow, "Beta") == ["40", "60", "80", "400", "440", NM, NM]
    assert shown(cashflow, "Gamma") == [NA, NA, NA, "2", "1", NM, NM]
    assert shown(cashflow, "<b>Alpha</b> YoY growth") == [
        NA, NA, "100.00%", NA, "10.00%", NM, NM,
    ]  # fmt: skip
    assert shown(cashflow, "Gamma YoY growth") == [NA, NA, NA, NA, "-50.00%", NM, NM]


def test_revenue_and_profitability_rows(tmp_path):
    cashflow, _ = cashflow_of(tmp_path)
    assert shown(cashflow, "Revenue") == ["100", "150", "200", "1,000", "1,100", "1,188", "1,100"]
    assert shown(cashflow, "Revenue YoY growth") == [
        NA, NA, "100.00%", NA, "10.00%", "8.00%", "0.00%",
    ]  # fmt: skip
    assert shown(cashflow, "COGS (cost of sales)") == ["50", NA, "80", "400", "400", NM, NM]
    assert shown(cashflow, "Gross profit margin") == [
        "50.00%", "60.00%", "60.00%", "60.00%", "54.55%", NM, NM,
    ]  # fmt: skip
    opex = "Opex (selling and administrative, amortization of intangibles)"
    assert shown(cashflow, opex) == ["6", NA, "12", "150", "150", NM, NM]
    assert shown(cashflow, "EBIT (income from operations)")[:3] == ["44", "85", "(30)"]
    assert shown(cashflow, "EBITDA (EBIT + D&A)") == ["50", "90", "(23)", "500", "500", NM, NM]
    assert shown(cashflow, "Issuer EBITDA (reported)") == ["82", "70", "105", "520", NA, NM, NM]


def test_add_backs_follow_the_annual_labels_then_quarter_only_labels(tmp_path):
    cashflow, _ = cashflow_of(tmp_path)
    labels = [r["label"] for r in cashflow["rows"] if r["band"] == "Add-backs to issuer EBITDA"]
    assert labels == ["Acquisition costs", "Other, net", "Quarter only item"]
    assert shown(cashflow, "Acquisition costs") == ["2", NA, "3", "10", "20", NM, NM]
    assert shown(cashflow, "Other, net") == [NA, "1", "(4)", "5", "(5)", NM, NM]
    assert shown(cashflow, "Quarter only item") == ["8", "7", "9", NA, NA, NM, NM]


def test_adjusted_ebitda_margin_and_growth_use_the_prior_period_of_each_column(tmp_path):
    cashflow, _ = cashflow_of(tmp_path)
    adj = "Adj EBITDA (EBITDA As Defined)"
    assert shown(cashflow, adj) == ["80", "80", "100", "540", "594", "891", "594"]
    assert shown(cashflow, "Adj EBITDA margin") == [
        "80.00%", "53.33%", "50.00%", "54.00%", "54.00%", "75.00%", "54.00%",
    ]  # fmt: skip
    assert shown(cashflow, "Adj EBITDA YoY growth") == [
        NA, NA, "25.00%", NA, "10.00%", "50.00%", "0.00%",
    ]  # fmt: skip


def test_cash_liquidity_debt_and_credit_rows(tmp_path):
    cashflow, _ = cashflow_of(tmp_path)
    assert shown(cashflow, "Cash interest") == [NA, NA, NA, "100", "100", "40", NM]
    assert shown(cashflow, "Cash taxes") == [NA, NA, NA, "30", NA, NM, NM]
    assert shown(cashflow, "Capital expenditure (outflow)") == [NA] * 3 + ["40", "44", "44", "44"]
    assert shown(cashflow, "Closing cash") == [NA] * 3 + ["300", NA, NM, NM]
    assert shown(cashflow, "Undrawn facility") == [NA] * 5 + [NA, NA]
    assert shown(cashflow, "Closing debt (carrying value)") == [NA] * 3 + ["2,000", NA, NM, NM]
    assert shown(cashflow, "Total leverage (debt / Adj EBITDA)") == [
        NA, NA, NA, "3.70x", "3.70x", "0.13x", "0.13x",
    ]  # fmt: skip
    assert shown(cashflow, "Interest coverage (Adj EBITDA / cash interest)") == [
        NA, NA, NA, "5.40x", "5.40x", "2.00x", "2.00x",
    ]  # fmt: skip
    assert shown(cashflow, "Cash proxy / closing debt") == [NA] * 5 + ["12.35%", "12.35%"]
    names = [r["label"] for r in cashflow["rows"]]
    assert "Working capital" not in names


def test_cells_carry_exact_values_and_the_reason_for_every_gap(tmp_path):
    cashflow, _ = cashflow_of(tmp_path)

    def cell(label, index):
        return row(cashflow, label)["cells"][index]

    assert cell("<b>Alpha</b>", 2) == {
        "exact": "120",
        "display": "120",
        "reason": None,
        "status": "value",
    }
    assert cell("EBIT (income from operations)", 2) == {
        "exact": "-30", "display": "(30)", "reason": None, "status": "value",
    }  # fmt: skip
    assert cell("Other, net", 0) == {
        "exact": None, "display": NA, "reason": PRINTED, "status": "na",
    }  # fmt: skip
    assert cell("Acquisition costs", 1) == {
        "exact": None,
        "display": NA,
        "reason": NO_VALUE,
        "status": "na",
    }
    assert cell("COGS (cost of sales)", 1) == {
        "exact": None, "display": NA, "reason": "source cell is not a number", "status": "na",
    }  # fmt: skip
    assert cell("Issuer EBITDA (reported)", 4)["reason"] == "not reported in the source"
    assert (
        cell("Closing debt (carrying value)", 4)["reason"] == "a component is not in the handoffs"
    )
    assert cell("Cash taxes", 4) == {
        "exact": None,
        "display": NA,
        "reason": HOSTILE,
        "status": "na",
    }
    assert cell("Undrawn facility", 5)["reason"] == "No facility"
    assert cell("Capital expenditure (outflow)", 3)["exact"] == "40"
    assert cell("Revenue YoY growth", 0)["reason"] == "prior-year period not in the handoffs"
    assert cell("Revenue YoY growth", 4) == {
        "exact": "0.1",
        "display": "10.00%",
        "reason": None,
        "status": "value",
    }
    assert cell("Adj EBITDA margin", 1)["exact"] == "0.5333333333333333333333333333"
    assert cell("Cash interest", 6) == {
        "exact": None,
        "display": NM,
        "reason": "not modelled in the calculation record",
        "status": "nm",
    }
    assert cell("Cash taxes", 5)["display"] == NM
    gamma = cell("Gamma YoY growth", 2)
    assert (gamma["display"], gamma["reason"]) == (NA, "a component is not in the handoffs")


def test_a_zero_prior_period_gives_no_growth_not_a_crash(tmp_path):
    record = calculation_record()
    record["values"]["FY2024"]["revenue"] = amount("0")
    cashflow, _ = cashflow_of(tmp_path, extra=cashflow_files(record))
    cell = row(cashflow, "Revenue YoY growth")["cells"][4]
    assert (cell["display"], cell["reason"]) == (NA, "a divisor is zero")


def test_senior_secured_leverage_is_the_register_date_year_only(tmp_path):
    cashflow, _ = cashflow_of(tmp_path)
    label = "Senior secured leverage (secured debt / Adj EBITDA)"
    ltm = "needs last-twelve-months Adj EBITDA for this quarter, which is not recorded"
    cells = row(cashflow, label)["cells"]
    assert [c["display"] for c in cells] == [NA, NA, NA, "3.00x", NA, NM, NM]
    assert [c["reason"] for c in cells[:3]] == [ltm] * 3
    assert cells[3]["exact"] == "3"
    assert cells[4]["reason"] == (
        "secured-debt carrying values are recorded only at 30 September 2024"
    )


def test_the_grid_prefers_recorded_derived_rows_and_falls_back_without_them(tmp_path):
    senior = "Senior secured leverage (secured debt / Adj EBITDA)"
    record = calculation_record()
    record["values"]["FY2024"]["revenue_growth"] = amount("0.25")
    record["values"]["FY2024"]["senior_secured_multiple"] = amount(None, "UNCLASSIFIED_ROW")
    cashflow, _ = cashflow_of(tmp_path / "with", extra=cashflow_files(record))
    growth = row(cashflow, "Revenue YoY growth")["cells"][3]
    assert (growth["exact"], growth["display"], growth["status"]) == ("0.25", "25.00%", "value")
    cell = row(cashflow, senior)["cells"][3]
    assert (cell["display"], cell["reason"]) == (
        NA,
        "the debt register has a row that cannot be classified",
    )
    # FY2025 holds no recorded keys, so its cells keep the old derivation.
    assert row(cashflow, "Revenue YoY growth")["cells"][4]["display"] == "10.00%"
    plain, _ = cashflow_of(tmp_path / "without")
    assert row(plain, "Revenue YoY growth")["cells"][3]["reason"] == (
        "prior-year period not in the handoffs"
    )
    assert row(plain, senior)["cells"][3]["display"] == "3.00x"


def test_recorded_derived_reasons_read_in_words(tmp_path):
    senior = "Senior secured leverage (secured debt / Adj EBITDA)"
    expected = {
        "NOT_STATED": "a component is not in the handoffs",
        "ZERO_OR_NEGATIVE_DENOMINATOR": "a divisor is zero or negative",
    }
    for code, words in expected.items():
        record = calculation_record()
        record["values"]["FY2024"]["senior_secured_multiple"] = amount(None, code)
        cashflow, _ = cashflow_of(tmp_path / code, extra=cashflow_files(record))
        cell = row(cashflow, senior)["cells"][3]
        assert (cell["display"], cell["reason"]) == (NA, words)


def test_senior_secured_leverage_needs_every_secured_instrument_carrying_value(tmp_path):
    broken = ANNUAL_MD.replace("Principal 500; carrying 500", "Principal 500")
    cashflow, _ = cashflow_of(tmp_path, extra=cashflow_files(annual=broken))
    cell = row(cashflow, "Senior secured leverage (secured debt / Adj EBITDA)")["cells"][3]
    assert (cell["display"], cell["reason"]) == (NA, "a component is not in the handoffs")


def test_notes_are_the_seven_fixed_lines_and_the_q1_note_needs_a_ytd_column(tmp_path):
    cashflow, _ = cashflow_of(tmp_path)
    assert cashflow["notes"] == ANSWER_KEY["notes"]
    assert len(cashflow["notes"]) == 7
    annual = ANNUAL_MD.replace("2024-09-30", "2024-09-29").replace("2025-09-30", "2025-09-29")
    cashflow, _ = cashflow_of(tmp_path, extra=cashflow_files(annual=annual))
    assert cashflow["notes"] == ANSWER_KEY["notes"][1:]


def test_units_are_none_when_the_request_names_none(tmp_path):
    cashflow, _ = cashflow_of(tmp_path, forecast="## Request\n\nNo units.\n")
    assert cashflow["units"] is None


@pytest.mark.parametrize(
    "name", ["forecast_exact.json", "calculation.json", "annual.md", "quarter.md"]
)
def test_each_missing_input_file_gives_no_cash_flow_model_and_its_own_issue(tmp_path, name):
    extra = cashflow_files()
    exact = exact_record()
    if name == "forecast_exact.json":
        exact = None
    else:
        del extra[name]
    artifact = model_delivery(
        tmp_path, "deliverables/m-1", forecast=REQUEST, exact=exact, extra=extra
    )
    result = models_of(tmp_path, artifact)
    assert result["models"][0]["cashflow"] is None
    assert [i for i in result["issues"] if "m-1" in i] == [
        f"deliverables/m-1: {name} is missing or unreadable"
    ]


def test_every_missing_input_file_is_reported_once_each(tmp_path):
    artifact = model_delivery(tmp_path, "deliverables/m-1", forecast=REQUEST)
    issues = [i for i in models_of(tmp_path, artifact)["issues"] if "m-1" in i]
    assert issues == [
        f"deliverables/m-1: {name} is missing or unreadable"
        for name in ("forecast_exact.json", "calculation.json", "annual.md", "quarter.md")
    ]


@pytest.mark.parametrize(
    ("name", "text"),
    [
        ("calculation.json", "{"),
        ("calculation.json", '{"annual_periods": ["FY2024"], "values": {}}'),
        ("calculation.json", '{"annual_periods": "FY2024", "values": {}}'),
        ("annual.md", None),
        ("quarter.md", None),
    ],
)
def test_an_unreadable_calculation_or_handoff_names_that_file(tmp_path, name, text):
    extra = cashflow_files()
    extra[name] = "ok" if text is None else text
    artifact = model_delivery(
        tmp_path, "deliverables/m-1", forecast=REQUEST, exact=exact_record(), extra=extra
    )
    if text is None:
        (tmp_path / "deliverables/m-1" / name).write_bytes(b"\xff\xfe not utf-8")
        delivery_path = tmp_path / "deliverables/m-1/delivery.json"
        record = json.loads(delivery_path.read_text(encoding="utf-8"))
        record["files"][name] = hashlib.sha256(b"\xff\xfe not utf-8").hexdigest()
        delivery_path.write_text(json.dumps(record), encoding="utf-8")
    result = models_of(tmp_path, artifact)
    assert result["models"][0]["cashflow"] is None
    assert [i for i in result["issues"] if "m-1" in i] == [
        f"deliverables/m-1: {name} is missing or unreadable"
    ]


@pytest.mark.parametrize(
    "exact",
    ["{", '{"base": 1}', '{"outputs": {"REFERENCE": {}}, "scope_limits": []}', '{"outputs": 1}'],
)
def test_an_invalid_forecast_record_gives_no_cash_flow_model_and_an_issue(tmp_path, exact):
    cashflow, issues = cashflow_of(tmp_path, exact=exact)
    assert cashflow is None
    assert issues == ["deliverables/m-1: forecast_exact.json is missing or unreadable"]


def test_a_non_numeric_amount_is_unreadable_not_shown(tmp_path):
    record = exact_record()
    record["outputs"]["REFERENCE"]["years"][0]["revenue"] = amount("NaN")
    cashflow, issues = cashflow_of(tmp_path, exact=record)
    assert cashflow is None and issues == [
        "deliverables/m-1: forecast_exact.json is missing or unreadable"
    ]
    calculation = calculation_record()
    calculation["values"]["FY2024"]["revenue"] = amount("1e999999999999")
    cashflow, issues = cashflow_of(tmp_path, extra=cashflow_files(calculation))
    assert cashflow is None and issues == [
        "deliverables/m-1: calculation.json is missing or unreadable"
    ]


def test_handoffs_without_tables_leave_a_grid_of_dashes_not_a_crash(tmp_path):
    cashflow, issues = cashflow_of(
        tmp_path, extra=cashflow_files(annual="No tables.\n", quarter="| a |\n")
    )
    assert issues == []
    assert [c["group"] for c in cashflow["columns"]] == [
        "Fiscal year", "Fiscal year", "Base case (reference illustration)", "Downside",
    ]  # fmt: skip
    assert shown(cashflow, "Revenue") == ["1,000", "1,100", "1,188", "1,100"]
    assert shown(cashflow, "Gross profit") == ["600", "600", NM, NM]
    assert "Q1 is the first quarter" not in " ".join(cashflow["notes"])
    assert [r["label"] for r in cashflow["rows"] if r["band"] == "Add-backs to issuer EBITDA"] == []


@pytest.mark.parametrize(
    ("exact", "kind", "shown"),
    [("-0.004", "multiple", "0.00x"), ("-0.00004", "percent", "0.00%")],
)
def test_a_multiple_or_percent_that_rounds_to_zero_has_no_sign(exact, kind, shown):
    assert store.display_amount(exact, kind) == shown


def test_units_are_read_from_a_request_with_windows_line_endings():
    handoff = (
        "# CP\r\n\r\n## Request\r\n\r\nAmounts in USD\r\nmillions.\r\n\r\n"
        "## Findings\r\n\r\nEUR billions.\r\n"
    )
    assert store.cashflow_units(handoff) == "USD millions"


# Fix round: a stray or hostile file in one delivery never ends the store.
def test_a_stray_oversize_handoff_beside_a_report_is_never_read_and_the_library_stays(tmp_path):
    report = view_delivery(tmp_path, "deliverables/r-1", "alpha-001", "ALP", "Alpha Holdings")
    with open(tmp_path / "deliverables/r-1/CP-0-attempt-1.md", "wb") as f:
        f.truncate(store.MODEL_FILE_LIMIT + 1)
    catalogue = identity_catalogue(tmp_path, {"alpha-001": (None, None, None)}, [report])
    result = store.workspace_store(tmp_path, catalogue)
    assert [r["id"] for r in result["reports"]] == ["r-1"]
    assert result["reports"][0]["builtFrom"] == []
    # Built from the verified delivery.json listing, so a file it does not list is never opened.
    assert [i for i in result["issues"] if "CP-0-attempt-1.md" in i] == []


def test_deeply_nested_json_in_a_model_is_an_issue_not_a_crash(tmp_path):
    artifact = model_delivery(
        tmp_path, "deliverables/m-1", forecast=REQUEST, exact="[" * 20000, extra=cashflow_files()
    )
    result = models_of(tmp_path, artifact)
    assert result["models"][0]["cashflow"] is None
    assert "deliverables/m-1: forecast_exact.json is missing or unreadable" in result["issues"]
    artifact = model_delivery(tmp_path, "deliverables/m-2")
    (tmp_path / "deliverables/m-2/view.json").write_text("[" * 20000, encoding="utf-8")
    result = models_of(tmp_path, artifact)
    assert [m["id"] for m in result["models"]] == []
    assert any(i.startswith("deliverables/m-2: could not be read (") for i in result["issues"])


def test_a_directory_source_is_not_a_readable_file_and_leaks_no_descriptor(tmp_path):
    def prepare(root):
        (root / "runs/alpha-001/adir").mkdir(parents=True)

    before = len(os.listdir("/dev/fd")) if os.path.isdir("/dev/fd") else None
    result, (model,) = source_model(tmp_path, "dir", "runs/alpha-001/adir", prepare)
    assert (model["sources"][0]["sha256"], model["sources"][0]["changed"]) == (None, None)
    assert "deliverables/m-1: source dir is not a readable file" in result["issues"]
    if before is not None:
        assert len(os.listdir("/dev/fd")) <= before + 1


def test_a_files_list_in_a_delivery_is_an_issue_not_a_crash(tmp_path):
    artifact = model_delivery(tmp_path, "deliverables/m-1")
    record = json.loads((tmp_path / "deliverables/m-1/delivery.json").read_text(encoding="utf-8"))
    record["files"] = ["model.html"]
    (tmp_path / "deliverables/m-1/delivery.json").write_text(json.dumps(record), encoding="utf-8")
    result = models_of(tmp_path, artifact)
    assert result["models"] == []
    assert (
        "deliverables/m-1: could not be read (TypeError: files is not an object)"
        in result["issues"]
    )


# Fix round 1 (review of Task 12).
@pytest.mark.parametrize(
    "entry",
    [
        5,
        {"reason": None},
        {"amount": 5, "reason": None},
        {"amount": "1", "reason": 5},
        {"amount": "1"},
    ],
)
def test_a_calculation_entry_that_is_not_amount_and_reason_names_calculation_json(tmp_path, entry):
    record = calculation_record()
    record["values"]["FY2024"]["revenue"] = entry
    cashflow, issues = cashflow_of(tmp_path, extra=cashflow_files(record))
    assert cashflow is None
    assert issues == ["deliverables/m-1: calculation.json is missing or unreadable"]


@pytest.mark.parametrize("entry", [5, {"reason": None}, {"amount": "1", "reason": 5}])
def test_a_forecast_entry_that_is_not_amount_and_reason_names_forecast_exact_json(tmp_path, entry):
    record = exact_record()
    record["outputs"]["DOWNSIDE"]["years"][0]["revenue"] = entry
    cashflow, issues = cashflow_of(tmp_path, exact=record)
    assert cashflow is None
    assert issues == ["deliverables/m-1: forecast_exact.json is missing or unreadable"]


def test_one_derived_value_too_large_to_show_is_one_n_a_cell_not_a_lost_grid(tmp_path):
    record = calculation_record()
    record["values"]["FY2024"]["revenue"] = amount("1E-190")
    record["values"]["FY2025"]["revenue"] = amount("1E+190")
    cashflow, issues = cashflow_of(tmp_path, extra=cashflow_files(record))
    assert issues == []
    cell = row(cashflow, "Revenue YoY growth")["cells"][4]
    assert (cell["display"], cell["exact"], cell["reason"]) == (
        NA,
        None,
        "the value cannot be displayed",
    )
    assert shown(cashflow, "Revenue")[3] == "0"


@pytest.mark.parametrize("name", ["calculation.json", "annual.md", "quarter.md"])
def test_a_changed_input_file_is_not_read_and_is_named(tmp_path, name):
    artifact = model_delivery(
        tmp_path,
        "deliverables/m-1",
        forecast=REQUEST,
        exact=exact_record(),
        extra=cashflow_files(),
    )
    path = tmp_path / "deliverables/m-1" / name
    result = models_of(tmp_path, artifact, edit=lambda: path.write_text("x", encoding="utf-8"))
    assert result["models"][0]["cashflow"] is None
    assert [i for i in result["issues"] if "m-1" in i] == [
        f"deliverables/m-1: {name} does not match its delivery record"
    ]


def test_a_quarter_starting_on_29_february_has_no_prior_year_quarter(tmp_path):
    quarter = QUARTER_MD.replace("2025-01-01–2025-03-31", "2024-02-29–2024-05-31")
    cashflow, issues = cashflow_of(tmp_path, extra=cashflow_files(quarter=quarter))
    assert issues == []
    assert cashflow["columns"][0]["label"] == "2024-02-29–2024-05-31"
    cell = row(cashflow, "Revenue YoY growth")["cells"][0]
    assert (cell["display"], cell["reason"]) == (NA, "prior-year period not in the handoffs")


def test_a_total_row_in_the_debt_register_is_a_subtotal_and_is_never_summed(tmp_path):
    annual = ANNUAL_MD.replace(
        "| 5% senior",
        "| Total senior secured notes | Subtotal; carrying 500 | x |\n| 5% senior",
    )
    cashflow, _ = cashflow_of(tmp_path, extra=cashflow_files(annual=annual))
    cell = row(cashflow, "Senior secured leverage (secured debt / Adj EBITDA)")["cells"][3]
    assert (cell["display"], cell["exact"]) == ("3.00x", "3")


def test_a_linked_delivery_folder_leads_out_of_the_run_and_is_not_read(tmp_path):
    """Expected: the outside folder's CP-9.md (and its file link CP-8.md) are never listed;
    the run keeps exactly CP-0 at its root and the real delivery's CP-1; nothing leaks."""
    put(tmp_path, "private/CP-9.md", "# CP-9\n\n## Findings\n\nSECRET-OUTSIDE.\n")
    put(tmp_path, "runs/linked/CP-0.md", BETA)
    put(tmp_path, "runs/linked/deliveries/real/CP-1.md", CP1)
    (tmp_path / "runs/linked/deliveries/link").symlink_to(tmp_path / "private")
    # A link to a folder inside the same run is refused as well: it is a link, not a delivery.
    (tmp_path / "runs/linked/deliveries/twin").symlink_to(tmp_path / "runs/linked/deliveries/real")
    result = store.workspace_store(tmp_path, plain_run("linked"))
    assert sorted(result["outputs"]) == ["linked/CP-0.md", "linked/deliveries/real/CP-1.md"]
    assert "SECRET-OUTSIDE" not in json.dumps(result)
    assert result["issues"] == []


def report_catalogue(*folders: str) -> dict:
    artifacts = [
        {
            "folder": folder,
            "label": Path(folder).name,
            "available": True,
            "href": f"/files/{folder}",
        }
        for folder in folders
    ]
    return {"issues": [], "real": [{"id": "delivery:x", "name": "x", "artifacts": artifacts}]}


def test_built_from_is_the_verified_manifest_and_one_odd_entry_loses_nothing(tmp_path):
    """Expected: the first report lists exactly CP-1 (the manifest's only handoff), with the
    manifest's hash; the stray CP-2.md copy, the CP-notes.md directory and a CP-3.md that is a
    directory are not "built from" anything. The second report is listed as well, and the third,
    whose delivery.json lacks report.html, is reported in Settings alone."""
    delivery(tmp_path, "deliverables/first", "Alpha", {"CP-1.md": CP1})
    put(tmp_path, "deliverables/first/CP-2.md", "# CP-2\n\nNot in delivery.json.\n")
    (tmp_path / "deliverables/first/CP-notes.md").mkdir()
    (tmp_path / "deliverables/first/CP-3.md").mkdir()
    delivery(tmp_path, "deliverables/second", "Beta", {"CP-1.md": CP1})
    delivery(tmp_path, "deliverables/third", "Gamma", {"CP-1.md": CP1})
    put(tmp_path, "deliverables/third/delivery.json", json.dumps({"files": {"CP-1.md": "ab"}}))
    names = ("deliverables/first", "deliverables/second", "deliverables/third")
    result = store.workspace_store(tmp_path, report_catalogue(*names))
    assert [r["id"] for r in result["reports"]] == ["first", "second"]
    expected = hashlib.sha256(CP1.encode()).hexdigest()
    first = result["reports"][0]["builtFrom"]
    assert [(row["module"], row["sha256"], row["source"]) for row in first] == [
        ("CP-1", expected, "CP-1.md")
    ]
    assert [issue.split(":")[0] for issue in result["issues"]] == ["deliverables/third"]


def test_unusual_handoff_names_are_labelled_one_by_one_and_hide_no_run(tmp_path):
    """Expected labels, derived from the rule "one optional '-' after the module code; an empty
    remainder is labelled by the file name": CP-1x -> 'X', CP-1-.md -> its own name,
    CP-1(1) -> '(1)', and the bracketed attempts are counted literally (2 of them, not 0)."""
    names = [
        "CP-0.md",
        "CP-1.md",
        "CP-1x.md",
        "CP-1-.md",
        "CP-1(1).md",
        "CP-1-a(-attempt-1.md",
        "CP-1-[draft]-attempt-1.md",
        "CP-1-[draft]-attempt-2.md",
    ]
    for name in names:
        put(tmp_path, f"runs/odd/{name}", f"# {name}\n\n## Findings\n\n{name} text {len(name)}.\n")
    result = store.workspace_store(tmp_path, plain_run("odd"))
    assert result["issues"] == [] and list(result["runs"]) == ["odd"]
    labels = {oid.split("/", 1)[1]: output["label"] for oid, output in result["outputs"].items()}
    assert labels == {
        "CP-0.md": "CP-0",
        "CP-1.md": "CP-1",
        "CP-1x.md": "X",
        "CP-1-.md": "CP-1-.md",
        "CP-1(1).md": "(1)",
        "CP-1-a(-attempt-1.md": "A( · attempt 1 of 1",
        "CP-1-[draft]-attempt-1.md": "[draft] · attempt 1 of 2",
        "CP-1-[draft]-attempt-2.md": "[draft] · attempt 2 of 2",
    }


def test_a_folder_named_like_a_route_key_does_not_replace_the_retained_case(tmp_path):
    """Expected: the curated route key frontier-2020 keeps folder frontier-2020-001 (module CP-1);
    the new CLI run in runs/frontier-2020 is not shown and Settings says why."""
    put(tmp_path, "runs/frontier-2020-001/CP-1.md", CP1)
    put(tmp_path, "runs/frontier-2020/CP-2.md", "# CP-2\n\nNew run.\n")
    catalogue = {
        "issues": [],
        "real": [
            {"id": "frontier-2020-001", "name": "Frontier"},
            {"id": "frontier-2020", "name": "Frontier new"},
        ],
    }
    result = store.workspace_store(tmp_path, catalogue)
    assert {k: (v["folder"], list(v["modules"])) for k, v in result["runs"].items()} == {
        "frontier-2020": ("frontier-2020-001", ["CP-1"])
    }
    assert [i for i in result["issues"] if i.startswith("frontier-2020:")] != []


def test_a_curated_report_label_needs_the_curated_issuer_in_view_json(tmp_path):
    """Expected: the folder name alone does not make a Ford Otosan delivery a TransDigm build;
    it keeps its recorded issuer and a label built from view.json (as of 30 June 2025), no status.
    A build recorded as TransDigm Group Incorporated keeps build 6's hand-written label."""
    delivery(tmp_path, "deliverables/tdg-fy2024-snapshot-7", "Ford Otosan", {"CP-1.md": CP1})
    delivery(
        tmp_path,
        "deliverables/tdg-fy2024-snapshot-6",
        "TransDigm Group Incorporated",
        {"CP-1.md": CP1},
    )
    names = ("deliverables/tdg-fy2024-snapshot-7", "deliverables/tdg-fy2024-snapshot-6")
    reports = {
        r["id"]: r for r in store.workspace_store(tmp_path, report_catalogue(*names))["reports"]
    }
    ford, transdigm = reports["tdg-fy2024-snapshot-7"], reports["tdg-fy2024-snapshot-6"]
    assert (ford["issuer"], ford["label"], ford["status"], ford["build"]) == (
        "Ford Otosan",
        "Ford Otosan · as of 30 June 2025",
        None,
        None,
    )
    assert (transdigm["issuer"], transdigm["label"], transdigm["build"]) == (
        "TransDigm Group",
        "Peer comparison · exact fiscal dates added",
        6,
    )


def test_request_files_are_inputs_not_saved_outputs_and_the_output_stays_the_default(tmp_path):
    """Expected: CP-3C has one saved output (the consumer handoff), which is its default; the
    request sent to the module and a repair request are kept as inputs, never as outputs."""
    put(tmp_path, "runs/asked/CP-3C-consumer.md", "# CP-3C\n\n## Findings\n\nConsumed.\n")
    put(tmp_path, "runs/asked/CP-3C-request.md", "# CP-3C — consume the handoff\n")
    put(tmp_path, "runs/asked/CP-2D-attempt-1.md", "# CP-2D\n\n## Findings\n\nFirst.\n")
    put(tmp_path, "runs/asked/CP-2D-repair-request.md", "# CP-2D — repair\n")
    result = store.workspace_store(tmp_path, plain_run("asked"))
    modules = result["runs"]["asked"]["modules"]
    assert modules["CP-3C"]["outputs"] == ["asked/CP-3C-consumer.md"]
    assert modules["CP-3C"]["default"] == "asked/CP-3C-consumer.md"
    assert modules["CP-3C"]["inputs"] == ["asked/CP-3C-request.md"]
    assert modules["CP-2D"]["outputs"] == ["asked/CP-2D-attempt-1.md"]
    assert sorted(result["inputs"]) == ["asked/CP-2D-repair-request.md", "asked/CP-3C-request.md"]
    assert sorted(result["outputs"]) == ["asked/CP-2D-attempt-1.md", "asked/CP-3C-consumer.md"]


def compared_workspace(root: Path, repaired_issuer: str) -> dict:
    shutil.copytree(ROOT / "runs/tdg-run-comparison-001", root / "runs/tdg-run-comparison-001")
    folders = {
        "tdg-fy2024-snapshot-2": "TransDigm Group Incorporated",
        "tdg-fy2024-snapshot-6": "TransDigm Group Incorporated",
        "tdg-fy2024-snapshot-7": repaired_issuer,
    }
    for name, issuer in folders.items():
        delivery(root, f"deliverables/{name}", issuer, {"CP-1.md": CP1})
    catalogue = report_catalogue(*(f"deliverables/{name}" for name in folders))
    catalogue["real"].append({"id": "tdg-run-comparison-001", "name": "Comparison"})
    return catalogue


def test_the_cp8_comparison_pin_needs_the_curated_builds_not_same_named_folders(tmp_path):
    """Expected: with builds 2, 6 and 7 recorded as TransDigm the CP-8 pin is kept; when the
    folder named build 7 records Ford Otosan the comparison is not offered and Settings says so."""
    kept = store.workspace_store(
        tmp_path / "a", compared_workspace(tmp_path / "a", "TransDigm Group")
    )
    assert "CP-8" in kept["pins"] and not any("pin dropped" in i for i in kept["issues"])
    wrong = store.workspace_store(tmp_path / "b", compared_workspace(tmp_path / "b", "Ford Otosan"))
    assert "CP-8" not in wrong["pins"]
    assert any(i.startswith("CP-8: curated pin dropped") for i in wrong["issues"])


def test_other_one_character_separators_label_and_number_outputs_as_before(tmp_path):
    """Hand-derived from "one separator of -, _, . or space; a series shares the name up to
    'attempt-'": CP-1.original -> 'Original', CP-1 (copy) -> '(copy)', the two CP-1_attempt files
    are attempts 1 and 2 of 2, so the default is attempt 2; CP-1x-attempt-1 counts itself
    (1 of 1)."""
    names = [
        "CP-1.original.md",
        "CP-1 (copy).md",
        "CP-1_attempt-1.md",
        "CP-1_attempt-2.md",
        "CP-1x-attempt-1.md",
    ]
    for name in names:
        put(tmp_path, f"runs/sep/{name}", f"# CP-1\n\n## Findings\n\n{name}.\n")
    result = store.workspace_store(tmp_path, plain_run("sep"))
    labels = {oid.split("/", 1)[1]: output["label"] for oid, output in result["outputs"].items()}
    assert labels == {
        "CP-1.original.md": "Original",
        "CP-1 (copy).md": "(copy)",
        "CP-1_attempt-1.md": "Attempt 1 of 2",
        "CP-1_attempt-2.md": "Attempt 2 of 2",
        "CP-1x-attempt-1.md": "X · attempt 1 of 1",
    }
    assert result["runs"]["sep"]["modules"]["CP-1"]["default"] == "sep/CP-1_attempt-2.md"


def test_a_linked_deliveries_folder_and_a_linked_run_folder(tmp_path):
    """Expected: runs/a/deliveries itself linking outside leaks nothing (only a's root CP-0);
    a run folder that is itself a link keeps its own root handoff, as before the fix."""
    put(tmp_path, "private/real/CP-9.md", "# CP-9\n\nSECRET-OUTSIDE.\n")
    put(tmp_path, "runs/a/CP-0.md", BETA)
    (tmp_path / "runs/a/deliveries").symlink_to(tmp_path / "private")
    put(tmp_path, "elsewhere/b/CP-1.md", CP1)
    (tmp_path / "runs/b").symlink_to(tmp_path / "elsewhere/b")
    catalogue = {"issues": [], "real": [{"id": "a", "name": "a"}, {"id": "b", "name": "b"}]}
    result = store.workspace_store(tmp_path, catalogue)
    assert sorted(result["outputs"]) == ["a/CP-0.md", "b/CP-1.md"]
    assert "SECRET-OUTSIDE" not in json.dumps(result)


def test_a_malformed_manifest_files_value_hides_that_report_alone(tmp_path):
    """Expected: delivery.json "files" as a list is that report's Settings issue only; the good
    report lists CP-1 traced to run alpha-001's CP-1.md, and a manifest name in a subfolder
    (sub/CP-2.md) is not a handoff row, as the old top-level glob never saw it either."""
    put(tmp_path, "runs/alpha-001/CP-1.md", CP1)
    delivery(tmp_path, "deliverables/good", "Alpha", {"CP-1.md": CP1, "sub/CP-2.md": "# CP-2\n"})
    delivery(tmp_path, "deliverables/bad", "Alpha", {"CP-1.md": CP1})
    put(tmp_path, "deliverables/bad/delivery.json", json.dumps({"files": ["CP-1.md"]}))
    catalogue = report_catalogue("deliverables/good", "deliverables/bad")
    catalogue["real"].append({"id": "alpha-001", "name": "Alpha"})
    result = store.workspace_store(tmp_path, catalogue)
    assert [r["id"] for r in result["reports"]] == ["good"]
    assert [(b["module"], b["run"], b["source"]) for b in result["reports"][0]["builtFrom"]] == [
        ("CP-1", "alpha-001", "alpha-001/CP-1.md")
    ]
    assert [i.split(":")[0] for i in result["issues"]] == ["deliverables/bad"]


def test_a_curated_report_name_inside_a_run_is_not_a_curated_build(tmp_path):
    """Expected: a TransDigm delivery kept at runs/r/deliveries/tdg-fy2024-snapshot-7 is not
    build 7: no build number, no "Latest", its recorded issuer and a view.json label."""
    folder = "runs/r/deliveries/tdg-fy2024-snapshot-7"
    delivery(tmp_path, folder, "TransDigm Group Incorporated", {"CP-1.md": CP1})
    report = store.workspace_store(tmp_path, report_catalogue(folder))["reports"][0]
    assert (report["build"], report["status"], report["issuer"], report["label"]) == (
        None,
        None,
        "TransDigm Group Incorporated",
        "TransDigm Group Incorporated · as of 30 June 2025",
    )


@pytest.mark.parametrize("curated_first", [True, False])
def test_the_route_key_rule_does_not_depend_on_catalogue_order(tmp_path, curated_first):
    """Expected either way: key frontier-2020 holds frontier-2020-001 and the same-named folder
    is reported; with the retained folder absent, runs/frontier-2020 is shown under its name."""
    put(tmp_path, "runs/frontier-2020-001/CP-1.md", CP1)
    put(tmp_path, "runs/frontier-2020/CP-2.md", "# CP-2\n\nNew run.\n")
    entries = [{"id": "frontier-2020-001", "name": "F"}, {"id": "frontier-2020", "name": "N"}]
    order = entries if curated_first else entries[::-1]
    result = store.workspace_store(tmp_path, {"issues": [], "real": order})
    assert result["runs"]["frontier-2020"]["folder"] == "frontier-2020-001"
    assert sum(i.startswith("frontier-2020:") for i in result["issues"]) == 1
    alone = store.workspace_store(tmp_path, {"issues": [], "real": [entries[1]]})
    assert alone["runs"]["frontier-2020"]["folder"] == "frontier-2020"
    assert alone["issues"] == []


def test_a_name_that_merely_contains_request_stays_an_output(tmp_path):
    """Expected: CP-1-requested-changes.md is a saved output; CP-1-request.md is an input."""
    put(tmp_path, "runs/q/CP-1-requested-changes.md", "# CP-1\n\n## Findings\n\nChanged.\n")
    put(tmp_path, "runs/q/CP-1-request.md", "# CP-1 — request\n")
    module = store.workspace_store(tmp_path, plain_run("q"))["runs"]["q"]["modules"]["CP-1"]
    assert (module["outputs"], module["inputs"]) == (
        ["q/CP-1-requested-changes.md"],
        ["q/CP-1-request.md"],
    )


def test_a_byte_order_mark_does_not_hide_the_first_heading(tmp_path):
    # Expected by hand: the BOM is not text, so the BOM copy parses exactly like the plain fixture
    # (its reader summary at line 17 and four chart tables), while the hash stays that of the bytes.
    raw = READER_FIXTURE.read_bytes()
    with_bom = b"\xef\xbb\xbf" + raw
    assert store.structured(with_bom, strict=True) == store.structured(raw, strict=True)
    put(tmp_path, "runs/bom-001/CP-1.md", "")
    (tmp_path / "runs/bom-001/CP-1.md").write_bytes(with_bom)
    result = store.workspace_store(tmp_path, {"real": [{"id": "bom-001", "name": "Bom"}]})
    output = result["outputs"]["bom-001/CP-1.md"]
    assert "parseError" not in output
    assert output["summary"]["line"] == 17
    assert len(output["charts"]) == 4
    assert output["sha256"] == hashlib.sha256(with_bom).hexdigest()
    # A file holding only a BOM reads as an empty file does: no sections and no parse error.
    assert store.structured(b"\xef\xbb\xbf", strict=False) == ([], None)


def test_each_handoff_is_read_once_per_page_load(tmp_path, monkeypatch):
    # Expected by hand from workspace(): five handoffs under runs/ are listed (the instructions file
    # is skipped by name and never opened); each is read exactly once, and its hash is of that read.
    catalogue = workspace(tmp_path)
    reads: dict[str, int] = {}
    original = Path.read_bytes
    chunked = store.regular_chunks

    def count(path: Path) -> None:
        name = Path(path).relative_to(tmp_path).as_posix()
        reads[name] = reads.get(name, 0) + 1

    def counting(path: Path) -> bytes:
        count(path)
        return original(path)

    def counting_chunks(path: Path, *args: Any, **kwargs: Any) -> Iterator[bytes]:
        count(path)  # The bounded reader every handoff goes through.
        return chunked(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", counting)
    monkeypatch.setattr(store, "regular_chunks", counting_chunks)
    result = store.workspace_store(tmp_path, catalogue)
    assert {name: count for name, count in reads.items() if name.endswith(".md")} == {
        "runs/alpha-001/CP-1.md": 1,
        "runs/alpha-001/CP-1-selected-input.md": 1,
        "runs/alpha-001/CP-2.md": 1,
        "runs/alpha-001/CP-4A.md": 1,
        "runs/launched/deliveries/abc/CP-0.md": 1,
    }
    assert (
        result["outputs"]["alpha-001/CP-1.md"]["sha256"] == hashlib.sha256(CP1.encode()).hexdigest()
    )
    assert result["outputs"]["launched/deliveries/abc/CP-0.md"]["sha256"] == (
        hashlib.sha256(BETA.encode()).hexdigest()
    )


# Task 14: limits, Q1/YTD labelling, adjacent-year growth, debt classification, layout errors,
# row kinds, cell status and column ytd. Expected strings are written here, not computed by the
# store.
def quarter_table_head(*periods):
    return f"| Source row | Label | {' | '.join(periods)} |\n|{'---|' * (len(periods) + 2)}\n"


def with_quarter_columns(*periods):
    return QUARTER_MD.replace(QUARTER_HEAD, quarter_table_head(*periods))


def limit_issue(file, what, found, limit):
    return (
        f"deliverables/m-1: {file} exceeds the cash flow model's limits ({what}, {found} > {limit})"
    )


def cashflow_issue_texts(tmp_path, exact=None, extra=None):
    artifact = model_delivery(
        tmp_path,
        "deliverables/m-1",
        forecast=REQUEST,
        exact=exact_record() if exact is None else exact,
        extra=cashflow_files() if extra is None else extra,
    )
    result = models_of(tmp_path, artifact)
    return result["models"][0]["cashflow"], [i for i in result["issues"] if "m-1" in i]


def quarters_of(count):
    return [
        f"{2000 + n // 4}-{n % 4 * 3 + 1:02d}-01–{2000 + n // 4}-{n % 4 * 3 + 1:02d}-28"
        for n in range(count)
    ]


def test_forty_quarter_columns_are_read_and_forty_one_are_refused(tmp_path):
    cashflow, issues = cashflow_issue_texts(
        tmp_path, extra=cashflow_files(quarter=with_quarter_columns(*quarters_of(40)))
    )
    assert issues == [] and len([c for c in cashflow["columns"] if c["group"] == "Quarter"]) == 40
    cashflow, issues = cashflow_issue_texts(
        tmp_path, extra=cashflow_files(quarter=with_quarter_columns(*quarters_of(41)))
    )
    assert cashflow is None
    assert issues == [limit_issue("quarter.md", "quarter columns", 41, 40)]


def test_twenty_one_forecast_years_in_a_case_are_refused(tmp_path):
    exact = exact_record()
    exact["outputs"]["REFERENCE"]["years"] = [
        forecast_year("1", "1", year=2026 + n) for n in range(21)
    ]
    cashflow, issues = cashflow_issue_texts(tmp_path, exact=exact)
    assert cashflow is None
    assert issues == [limit_issue("forecast_exact.json", "forecast years in REFERENCE", 21, 20)]
    exact["outputs"]["REFERENCE"]["years"].pop()
    cashflow, issues = cashflow_issue_texts(tmp_path, exact=exact)
    assert issues == [] and len(cashflow["columns"]) == 3 + 2 + 20 + 1


def test_more_than_200_business_units_or_add_backs_are_refused(tmp_path):
    units = "".join(f"| Total Unit {n} | 1 | 1 |\n" for n in range(201))
    annual = ANNUAL_MD.replace("| Net Sales | 1,100", units + "| Net Sales | 1,100")
    cashflow, issues = cashflow_issue_texts(tmp_path, extra=cashflow_files(annual=annual))
    assert cashflow is None
    assert issues == [limit_issue("annual.md", "business-unit rows", 204, 200)]
    backs = "".join(f"| Back {n} | 1 | 1 |\n" for n in range(201))
    annual = ANNUAL_MD.replace("| Acquisition costs | 20", backs + "| Acquisition costs | 20")
    cashflow, issues = cashflow_issue_texts(tmp_path, extra=cashflow_files(annual=annual))
    assert cashflow is None
    assert issues == [limit_issue("annual.md", "add-back rows", 203, 200)]


def test_a_table_of_more_than_2000_rows_is_refused_before_any_cell_is_built(tmp_path):
    rows = "".join(f"| Row {n} | 1 | 1 |\n" for n in range(2001))
    annual = ANNUAL_MD + "\n### Long\n\n" + ANNUAL_HEAD + rows
    cashflow, issues = cashflow_issue_texts(tmp_path, extra=cashflow_files(annual=annual))
    assert cashflow is None
    assert issues == [limit_issue("annual.md", "table rows", 2001, 2000)]
    quarter = (
        QUARTER_MD + "\n" + QUARTER_HEAD + "".join(f"| {n} | Row | 1 |\n" for n in range(2001))
    )
    cashflow, issues = cashflow_issue_texts(tmp_path, extra=cashflow_files(quarter=quarter))
    assert issues == [limit_issue("quarter.md", "table rows", 2001, 2000)]


def test_thousands_of_repeated_business_unit_labels_collapse_to_the_distinct_set(tmp_path):
    units = "".join("| Total Same | 1 | 1 |\n" for _ in range(1900))
    annual = ANNUAL_MD.replace("| Net Sales | 1,100", units + "| Net Sales | 1,100")
    cashflow, issues = cashflow_of(tmp_path, extra=cashflow_files(annual=annual))
    assert issues == []
    labels = [
        r["label"]
        for r in cashflow["rows"]
        if r["band"] == "Revenue" and "growth" not in r["label"]
    ]
    assert labels.count("Same") == 1 and len(labels) == 5  # four units + Revenue
    many = "".join(f"| Total U{n} | 1 | 1 |\n" for n in range(1900))
    annual = ANNUAL_MD.replace("| Net Sales | 1,100", many + "| Net Sales | 1,100")
    cashflow, issues = cashflow_issue_texts(tmp_path, extra=cashflow_files(annual=annual))
    assert cashflow is None and "business-unit rows, 1903 > 200" in issues[0]


def test_one_q1_per_fiscal_year_and_growth_needs_a_prior_of_similar_length(tmp_path):
    quarter = with_quarter_columns(
        "2024-10-01–2024-12-31", "2025-10-01–2025-11-30", "2025-10-01–2025-12-31"
    )
    cashflow, _ = cashflow_of(tmp_path, extra=cashflow_files(quarter=quarter))
    assert columns_of(cashflow) == [
        ("Q1 FY2025 (YTD)", True),
        ("2025-10-01–2025-11-30", False),
        ("Q1 FY2026 (YTD)", True),
    ]
    growth = row(cashflow, "Revenue YoY growth")["cells"]
    assert growth[1]["reason"] == "prior-year period not in the handoffs"
    quarter = with_quarter_columns("2024-10-01–2024-12-31", "2025-10-01–2026-01-08")
    cashflow, _ = cashflow_of(tmp_path, extra=cashflow_files(quarter=quarter))
    cell = row(cashflow, "Revenue YoY growth")["cells"][1]
    assert (cell["display"], cell["reason"]) == (NA, "the prior-year period has a different length")


def test_a_reversed_span_is_not_a_quarter(tmp_path):
    quarter = with_quarter_columns("2025-10-01–2025-09-15")
    cashflow, _ = cashflow_of(tmp_path, extra=cashflow_files(quarter=quarter))
    assert columns_of(cashflow) == [("2025-10-01–2025-09-15", False)]


def test_a_repeated_debt_register_label_makes_leverage_na(tmp_path):
    annual = ANNUAL_MD.replace(
        "| 5% senior",
        "| 6% secured notes due 2030 | Principal 200; carrying 200 | x |\n| 5% senior",
    )
    cashflow, _ = cashflow_of(tmp_path, extra=cashflow_files(annual=annual))
    cell = row(cashflow, "Senior secured leverage (secured debt / Adj EBITDA)")["cells"][3]
    assert (cell["display"], cell["reason"]) == (
        NA,
        "the debt register repeats a row label: 6% secured notes due 2030",
    )


YTD_REGISTER = (
    "| FY2023 | Historical duration | 2022-12-27 | 2024-01-01 |\n"
    "| FY2024 | Historical duration | 2023-10-01 | 2024-09-30 |\n"
)


def columns_of(cashflow):
    return [(c["label"], c["ytd"]) for c in cashflow["columns"] if c["group"] == "Quarter"]


def test_a_year_to_date_column_longer_than_a_quarter_is_not_labelled_q1(tmp_path):
    quarter = with_quarter_columns(
        "2025-10-01–2025-12-31", "2024-10-01–2024-12-31", "2025-10-01–2026-03-31"
    )
    cashflow, issues = cashflow_of(tmp_path, extra=cashflow_files(quarter=quarter))
    assert issues == []
    assert columns_of(cashflow) == [
        ("Q1 FY2025 (YTD)", True),
        ("Q1 FY2026 (YTD)", True),
        ("2025-10-01–2026-03-31", False),
    ]
    growth = row(cashflow, "Revenue YoY growth")["cells"]
    assert [(c["display"], c["reason"]) for c in growth[:3]] == [
        (NA, "prior-year period not in the handoffs"),
        ("100.00%", None),
        (NA, "prior-year period not in the handoffs"),
    ]


def test_a_quarter_is_q1_only_after_a_fiscal_year_end_in_the_register(tmp_path):
    # Starts 1 January but no fiscal year is recorded as ending on 31 December: dates, not Q1.
    quarter = with_quarter_columns("2025-01-01–2025-03-31", "2024-10-01–2024-12-31")
    cashflow, _ = cashflow_of(tmp_path, extra=cashflow_files(quarter=quarter))
    assert columns_of(cashflow) == [("Q1 FY2025 (YTD)", True), ("2025-01-01–2025-03-31", False)]
    # A 52/53-week year ending 1 January 2024 makes the quarter starting 2 January Q1 of FY2024.
    annual = ANNUAL_MD.replace(
        "| FY2024 | Historical duration | 2023-10-01 | 2024-09-30 |\n", YTD_REGISTER
    )
    quarter = with_quarter_columns("2024-01-02–2024-03-30")
    cashflow, _ = cashflow_of(tmp_path, extra=cashflow_files(annual=annual, quarter=quarter))
    assert columns_of(cashflow) == [("Q1 FY2024 (YTD)", True)]


def test_the_q1_prior_is_the_previous_fiscal_years_q1_and_other_quarters_have_none(tmp_path):
    cashflow, _ = cashflow_of(tmp_path)
    growth = row(cashflow, "Revenue YoY growth")["cells"]
    assert [c["display"] for c in growth[:3]] == [NA, NA, "100.00%"]
    assert [c["ytd"] for c in cashflow["columns"]] == [True, False, True] + [False] * 4


def test_growth_is_computed_only_between_adjacent_years(tmp_path):
    calculation = calculation_record()
    calculation["values"] = {
        "FY2023": calculation["values"]["FY2024"],
        "FY2025": calculation["values"]["FY2025"],
    }
    calculation["annual_periods"] = ["FY2023", "FY2025"]
    cashflow, _ = cashflow_of(tmp_path, extra=cashflow_files(calculation))
    cells = row(cashflow, "Revenue YoY growth")["cells"]
    labels = [c["label"] for c in cashflow["columns"]]
    assert (cells[labels.index("FY2025")]["display"], cells[labels.index("FY2025")]["reason"]) == (
        NA,
        "prior-year period not in the handoffs",
    )
    # The first forecast year follows FY2025 only when it is FY2026E.
    assert cells[labels.index("FY2026E")]["display"] == "8.00%"
    exact = exact_record()
    for case in ("REFERENCE", "DOWNSIDE"):
        exact["outputs"][case]["years"] = [
            forecast_year("1188", "891", year=2027),
            forecast_year("1300", "891", year=2028),
            forecast_year("1400", "891", year=2030),
        ]
    cashflow, _ = cashflow_of(tmp_path, exact=exact)
    labels = [c["label"] for c in cashflow["columns"]]
    cells = row(cashflow, "Revenue YoY growth")["cells"]
    base = labels.index("FY2027E")
    assert [cells[base + n]["display"] for n in range(3)] == [NA, "9.43%", NA]
    assert (
        cells[base]["reason"]
        == cells[base + 2]["reason"]
        == "prior-year period not in the handoffs"
    )


def test_debt_register_labels_match_case_insensitively(tmp_path):
    annual = ANNUAL_MD.replace("6% secured notes due 2030", "6% Secured Notes due 2030")
    annual = annual.replace("5% senior subordinated", "5% Senior SUBORDINATED")
    annual = annual.replace("| Term loans aggregate |", "| TERM LOANS Aggregate |")
    cashflow, _ = cashflow_of(tmp_path, extra=cashflow_files(annual=annual))
    cell = row(cashflow, "Senior secured leverage (secured debt / Adj EBITDA)")["cells"][3]
    assert (cell["display"], cell["exact"]) == ("3.00x", "3")


def test_a_register_row_with_a_carrying_value_that_is_not_classified_makes_leverage_na(tmp_path):
    annual = ANNUAL_MD.replace("Commitment 910; drawn 5", "Commitment 910; carrying 5")
    cashflow, _ = cashflow_of(tmp_path, extra=cashflow_files(annual=annual))
    cell = row(cashflow, "Senior secured leverage (secured debt / Adj EBITDA)")["cells"][3]
    assert (cell["display"], cell["reason"]) == (
        NA,
        "the debt register has a row that cannot be classified: Revolving credit facility",
    )
    annual = ANNUAL_MD.replace(
        "| 5% senior", "| TOTAL notes | Subtotal; carrying 800 | x |\n| 5% senior"
    )
    cashflow, _ = cashflow_of(tmp_path, extra=cashflow_files(annual=annual))
    cell = row(cashflow, "Senior secured leverage (secured debt / Adj EBITDA)")["cells"][3]
    assert cell["display"] == "3.00x"


def test_a_layout_failure_names_its_cause_and_input_failures_keep_their_file(tmp_path, monkeypatch):
    early = store.RowSpec(
        "early", "X", "Early margin", "percent", *store.every(("margin", "later"))
    )
    monkeypatch.setattr(store, "TAIL_ROWS", (early, *store.TAIL_ROWS))
    cashflow, issues = cashflow_issue_texts(tmp_path)
    assert cashflow is None
    assert issues == [
        "deliverables/m-1: the cash flow model could not be laid out (KeyError: 'later')"
    ]
    monkeypatch.undo()
    cashflow, issues = cashflow_issue_texts(tmp_path, exact="{")
    assert issues == ["deliverables/m-1: forecast_exact.json is missing or unreadable"]


def test_a_table_cell_keeps_its_rows_kind():
    table = {"rows": {"Margin": ["Margin", "0.25"], "A": ["A", "1"], "B": ["B", "0.5"]}}
    table["periods"] = {("fy", "FY2024"): 1}
    column = {"period": ("fy", "FY2024")}
    inputs = store.CashflowInputs({"t": table}, None, {}, {})
    cell = store.CellContext(inputs, column, 0, {}, "percent")
    assert store.op_table(cell, "t", "Margin")["display"] == "25.00%"
    summed = store.op_table_sum(cell, "t", "A", "B")
    assert summed["display"] == "150.00%"


def test_every_cell_carries_a_status_that_matches_what_it_shows(tmp_path):
    cashflow, _ = cashflow_of(tmp_path)
    expected = {NA: "na", NM: "nm"}
    seen = set()
    for line in cashflow["rows"]:
        for cell in line["cells"]:
            assert cell["display"] != DASH
            assert cell["status"] == expected.get(cell["display"], "value")
            seen.add(cell["status"])
    assert seen == {"value", "na", "nm"}


def test_a_source_cell_printed_as_a_dash_is_n_a_with_its_reason(tmp_path):
    cashflow, _ = cashflow_of(tmp_path)
    cell = row(cashflow, "Other, net")["cells"][0]
    assert (cell["status"], cell["display"], cell["reason"]) == ("na", NA, PRINTED)


def test_every_other_gap_is_n_a_with_the_source_table_has_no_value_reason(tmp_path):
    cashflow, _ = cashflow_of(tmp_path)
    blank = row(cashflow, "Acquisition costs")["cells"][1]  # an empty source cell
    quarter_only = row(cashflow, "Quarter only item")["cells"][3]  # no fiscal-year column entry
    history_none = row(cashflow, "Model cash from operations")["cells"][0]  # no history spec
    for cell in (blank, quarter_only, history_none):
        assert (cell["status"], cell["display"], cell["reason"]) == ("na", NA, NO_VALUE)


def test_every_row_states_its_kind_and_the_eleven_totals_are_marked(tmp_path):
    cashflow, _ = cashflow_of(tmp_path)
    kinds = {line["label"]: line["kind"] for line in cashflow["rows"]}
    assert set(kinds.values()) == {"money", "percent", "multiple"}
    assert kinds["Revenue"] == "money"
    assert kinds["Gross profit margin"] == "percent"
    assert kinds["Revenue YoY growth"] == "percent"
    assert kinds["Total leverage (debt / Adj EBITDA)"] == "multiple"
    assert kinds["Interest coverage (Adj EBITDA / cash interest)"] == "multiple"
    assert kinds["Cash proxy / closing debt"] == "percent"
    totals = [line["label"] for line in cashflow["rows"] if line["total"]]
    assert totals == [
        "Revenue",
        "Gross profit",
        "EBIT (income from operations)",
        "EBITDA (EBIT + D&A)",
        "Adj EBITDA (EBITDA As Defined)",
        "Model cash from operations",
        "Cash proxy (not issuer free cash flow)",
        "Closing cash",
        "Accessible liquidity",
        "Closing debt (carrying value)",
        "Net debt (all modelled cash deducted)",
    ]
    assert not any(line["total"] for line in cashflow["rows"] if line["label"].endswith("growth"))


def test_the_ltm_reason_names_the_quarter_and_says_it_is_not_recorded():
    assert store.LTM_NEEDED == (
        "needs last-twelve-months Adj EBITDA for this quarter, which is not recorded"
    )


def test_the_handoff_labels_the_reader_matches_are_one_mapping():
    assert store.CASHFLOW_LABELS["revenue"] == "NET SALES"
    assert store.CASHFLOW_LABELS["adjusted_ebitda"] == "Total Company EBITDA As Defined"
    assert store.CASHFLOW_LABELS["secured_securitization"] == "Trade receivable securitization"
    assert store.CASHFLOW_LABELS["secured_term_loans"] == "Term loans aggregate"


def lone_report_catalogue(folder: str) -> dict:
    artifact = {
        "folder": folder,
        "available": True,
        "kind": "report",
        "label": Path(folder).name,
        "href": f"/files/{folder}/report.html?sha256=x",
    }
    return {"real": [{"id": "delivery:r", "artifacts": [artifact]}]}


def report_folder(root: Path, view: bytes, delivery_tail: bytes = b"") -> str:
    folder = root / "deliverables/r-1"
    folder.mkdir(parents=True)
    (folder / "view.json").write_bytes(view)
    (folder / "report.html").write_bytes(b"<p>r</p>")
    files = {
        n: hashlib.sha256((folder / n).read_bytes()).hexdigest()
        for n in ("view.json", "report.html")
    }
    body = json.dumps({"files": files}).encode()
    (folder / "delivery.json").write_bytes(
        body[:-1] + delivery_tail + b"}" if delivery_tail else body
    )
    return "deliverables/r-1"


RUN_VIEW = {"run": {"run_id": "r1", "issuer_id": "A", "issuer_name": "A", "as_of": "2025-06-30"}}


def test_a_report_read_error_names_its_type_and_reason_never_the_file_bytes(tmp_path):
    secret = "PRIVATE-NOTE-" + "x" * 2000
    view = json.dumps({**RUN_VIEW, "note": secret}).encode("cp1252")
    view = view.replace(b"x" * 10, b"\xe9" * 10, 1)
    folder = report_folder(tmp_path, view)
    reports, issues = store.catalogue_reports(tmp_path, lone_report_catalogue(folder), {}, {})
    assert reports == [] and len(issues) == 1
    assert issues[0].startswith(f"{folder}: could not be read (UnicodeDecodeError:")
    assert "PRIVATE-NOTE" not in issues[0] and len(issues[0]) < 300


def test_a_non_utf8_report_delivery_json_does_not_copy_its_bytes(tmp_path):
    folder = report_folder(
        tmp_path, json.dumps(RUN_VIEW).encode(), b', "scope": "\xff MARKER ' + b"y" * 2000 + b'"'
    )
    _, issues = store.catalogue_reports(tmp_path, lone_report_catalogue(folder), {}, {})
    assert len(issues) == 1 and "MARKER" not in issues[0] and len(issues[0]) < 300


def test_a_report_view_json_nested_too_deep_is_an_issue_not_a_crash(tmp_path):
    deep = json.dumps(RUN_VIEW)[:-1] + ',"x":' + "[" * 9998 + "]" * 9998 + "}"
    folder = report_folder(tmp_path, deep.encode())
    reports, issues = store.catalogue_reports(tmp_path, lone_report_catalogue(folder), {}, {})
    assert reports == [] and [i.split(" (")[0] for i in issues] == [f"{folder}: could not be read"]
    assert "RecursionError" in issues[0]


def test_a_run_workflow_json_nested_too_deep_records_nothing(tmp_path):
    run = tmp_path / "runs/r1"
    run.mkdir(parents=True)
    (run / "workflow.json").write_text("[" * 20000 + "]" * 20000)
    issues: list[str] = []
    assert store.recorded_run(run, issues) == {}
    assert len(issues) == 1 and issues[0].startswith(
        "r1: workflow.json could not be read (RecursionError:"
    )
    assert "[[[" not in issues[0]


def test_a_model_delivery_json_that_is_a_link_is_not_followed(tmp_path):
    artifact = model_delivery(tmp_path, "deliverables/m-1")
    real = tmp_path / "deliverables/m-1/delivery.json"
    outside = tmp_path.parent / f"{tmp_path.name}-outside.json"
    outside.write_text(real.read_text(encoding="utf-8"), encoding="utf-8")
    real.unlink()
    real.symlink_to(outside)
    result = models_of(tmp_path, artifact)
    assert result["models"] == []
    assert any(i.startswith("deliverables/m-1: could not be read") for i in result["issues"])


def test_a_model_delivery_json_that_is_a_fifo_does_not_block_the_store(tmp_path):
    artifact = model_delivery(tmp_path, "deliverables/m-1")
    real = tmp_path / "deliverables/m-1/delivery.json"
    real.unlink()
    os.mkfifo(real)
    result = models_of(tmp_path, artifact)
    assert result["models"] == []
    assert any(i.startswith("deliverables/m-1: could not be read") for i in result["issues"])


def test_a_model_view_json_that_is_a_link_is_not_read(tmp_path):
    artifact = model_delivery(tmp_path, "deliverables/m-1")
    view = tmp_path / "deliverables/m-1/view.json"
    outside = tmp_path.parent / f"{tmp_path.name}-view.json"
    outside.write_text(view.read_text(encoding="utf-8"), encoding="utf-8")
    view.unlink()
    view.symlink_to(outside)
    result = models_of(tmp_path, artifact)
    assert result["models"] == []
    assert any(i.startswith("deliverables/m-1: could not be read") for i in result["issues"])


def test_the_debt_register_repeat_check_ignores_case(tmp_path):
    annual = ANNUAL_MD.replace(
        "| 5% senior",
        "| Secured notes | Principal 200; carrying 200 | x |\n"
        "| SECURED NOTES | Principal 200; carrying 200 | x |\n| 5% senior",
    )
    cashflow, _ = cashflow_of(tmp_path, extra=cashflow_files(annual=annual))
    cell = row(cashflow, "Senior secured leverage (secured debt / Adj EBITDA)")["cells"][3]
    assert (cell["display"], cell["reason"]) == (
        NA,
        "the debt register repeats a row label: SECURED NOTES",
    )


def lone_identity_catalogue(folder: str) -> dict:
    artifact = {"folder": folder, "available": True, "kind": "model"}
    return {"real": [{"id": "r1", "artifacts": [artifact]}]}


def test_a_delivery_identity_is_not_read_from_a_linked_or_fifo_view_json(tmp_path):
    artifact = model_delivery(tmp_path, "deliverables/m-1")
    catalogue = lone_identity_catalogue(artifact["folder"])
    assert [i["issuer_name"] for i in store.delivery_identities(tmp_path, catalogue)] == [
        "Alpha Holdings"
    ]
    view = tmp_path / "deliverables/m-1/view.json"
    outside = tmp_path.parent / f"{tmp_path.name}-identity.json"
    outside.write_text(view.read_text(encoding="utf-8"), encoding="utf-8")
    view.unlink()
    view.symlink_to(outside)
    assert store.delivery_identities(tmp_path, catalogue) == []
    view.unlink()
    os.mkfifo(view)
    assert store.delivery_identities(tmp_path, catalogue) == []


def test_a_workflow_json_that_is_a_fifo_or_link_is_a_named_issue(tmp_path):
    run = tmp_path / "runs/r1"
    run.mkdir(parents=True)
    os.mkfifo(run / "workflow.json")
    issues: list[str] = []
    assert store.recorded_run(run, issues) == {}
    assert issues == ["r1: workflow.json could not be read (UnreadableFile: not a regular file)"]
    (run / "workflow.json").unlink()
    outside = tmp_path / "outside.json"
    outside.write_text('{"run": {"issuer_name": "Elsewhere"}}', encoding="utf-8")
    (run / "workflow.json").symlink_to(outside)
    issues = []
    assert store.recorded_run(run, issues) == {}
    assert issues == ["r1: workflow.json could not be read (UnreadableFile: a link)"]


def test_a_report_view_json_that_is_a_link_is_not_read(tmp_path):
    folder = report_folder(tmp_path, json.dumps(RUN_VIEW).encode())
    view = tmp_path / folder / "view.json"
    outside = tmp_path.parent / f"{tmp_path.name}-report-view.json"
    outside.write_bytes(view.read_bytes())
    view.unlink()
    view.symlink_to(outside)
    reports, issues = store.catalogue_reports(tmp_path, lone_report_catalogue(folder), {}, {})
    assert reports == [] and len(issues) == 1
    assert issues[0].startswith(f"{folder}: could not be read (UnreadableFile:")


def test_a_run_level_failure_names_its_type_and_reason_not_a_repr(tmp_path, monkeypatch):
    put(tmp_path, "runs/r1/CP-0.md", "# CP-0\n\nText.\n")

    def broken(*args, **kwargs):
        raise ValueError("PRIVATE-BYTES " * 40)

    monkeypatch.setattr(store, "collect_runs", broken)
    result = store.workspace_store(tmp_path, plain_run("r1"))
    (issue,) = [i for i in result["issues"] if "could not be read" in i]
    assert "(ValueError: " in issue and "ValueError('" not in issue and len(issue) < 200


# Task 17: a workspace cash flow budget, no issuer-ID bridging, the own-model check read bounded.
def cell_count(cashflow):
    return len(cashflow["rows"]) * len(cashflow["columns"])


def three_cashflow_models(tmp_path):
    return [
        model_delivery(
            tmp_path,
            f"deliverables/{name}",
            forecast=REQUEST,
            exact=exact_record(),
            extra=cashflow_files(),
        )
        for name in ("m-3", "m-1", "m-2")
    ]


def test_the_cash_flow_budget_is_250000_cells():
    assert store.CASHFLOW_CELL_BUDGET == 250_000


def test_models_past_the_workspace_cell_budget_get_no_grid_in_delivery_path_order(
    tmp_path, monkeypatch
):
    artifacts = three_cashflow_models(tmp_path)
    (one,) = models_of(tmp_path, artifacts[1])["models"]
    cells = cell_count(one["cashflow"])
    monkeypatch.setattr(store, "CASHFLOW_CELL_BUDGET", cells * 2 + 1)
    result = models_of(tmp_path, *artifacts)  # the catalogue lists m-3 first
    by_id = {m["id"]: m for m in result["models"]}
    assert [m["id"] for m in result["models"]] == ["m-3", "m-1", "m-2"]
    assert by_id["m-1"]["cashflow"] is not None and by_id["m-2"]["cashflow"] is not None
    assert by_id["m-3"]["cashflow"] is None
    assert (
        result["issues"].count(
            "deliverables/m-3: the cash flow model is not shown; the workspace's cash flow "
            f"models exceed {store.CASHFLOW_CELL_BUDGET:,} cells"
        )
        == 1
    )
    assert not [i for i in result["issues"] if "deliverables/m-1" in i or "deliverables/m-2" in i]


def test_each_model_manifest_is_read_once_per_load(tmp_path, monkeypatch):
    artifacts = [
        model_delivery(tmp_path, f"deliverables/{name}", forecast=REQUEST, exact=exact_record())
        for name in ("m-1", "m-2")
    ]
    reads: list[str] = []
    real = store.delivery_json

    def counted(folder):
        reads.append(folder.name)
        return real(folder)

    monkeypatch.setattr(store, "delivery_json", counted)
    result = models_of(tmp_path, *artifacts)
    assert [m["id"] for m in result["models"]] == ["m-1", "m-2"]
    assert sorted(n for n in reads if n.startswith("m-")) == ["m-1", "m-2"]


def test_a_grid_over_the_budget_is_not_computed(tmp_path, monkeypatch):
    artifact = model_delivery(
        tmp_path, "deliverables/m-1", forecast=REQUEST, exact=exact_record(), extra=cashflow_files()
    )
    computed: list[int] = []
    real = store.spec_cell

    def counted(*args, **kwargs):
        computed.append(1)
        return real(*args, **kwargs)

    monkeypatch.setattr(store, "spec_cell", counted)
    monkeypatch.setattr(store, "CASHFLOW_CELL_BUDGET", 1)
    result = models_of(tmp_path, artifact)
    (model,) = result["models"]
    assert model["cashflow"] is None
    assert computed == []
    assert (
        "deliverables/m-1: the cash flow model is not shown; the workspace's cash flow "
        "models exceed 1 cells"
    ) in result["issues"]


def test_a_spec_on_a_column_with_no_record_is_a_layout_error_not_a_dash(tmp_path, monkeypatch):
    early = store.RowSpec("early", "X", "Early", "money", ("key", "revenue"), None, None)
    monkeypatch.setattr(store, "TAIL_ROWS", (early, *store.TAIL_ROWS))
    cashflow, issues = cashflow_issue_texts(tmp_path)
    assert cashflow is None
    (issue,) = issues
    assert issue.startswith("deliverables/m-1: the cash flow model could not be laid out (")


def test_different_issuer_ids_are_never_joined_through_a_shared_name(tmp_path):
    spec = {
        "a-001": (None, None, {"issuer_name": "Alpha Holdings", "issuer_id": "ALP"}),
        "b-001": (None, None, {"issuer_name": "Alpha Holdings", "issuer_id": "BET"}),
        "c-001": (None, None, {"issuer_name": "Alpha Holdings"}),
    }
    result, runs = identities(tmp_path, spec)
    assert runs["a-001"]["issuerKey"] == "id:alp"
    assert runs["b-001"]["issuerKey"] == "id:bet"
    assert runs["c-001"]["issuerKey"] == "name:Alpha Holdings"
    assert (
        result["issues"].count(
            "issuer name Alpha Holdings is recorded with different issuer IDs: ALP, BET"
        )
        == 1
    )


def test_a_name_carried_by_one_id_still_joins_runs_without_an_id(tmp_path):
    spec = {
        "a-001": (None, None, {"issuer_name": "Alpha Holdings", "issuer_id": "ALP"}),
        "b-001": (None, None, {"issuer_name": "Alpha Holdings", "issuer_id": "alp"}),
        "c-001": (None, None, {"issuer_name": "Alpha Holdings"}),
    }
    result, runs = identities(tmp_path, spec)
    assert {r["issuerKey"] for r in runs.values()} == {"id:alp"}
    assert not [i for i in result["issues"] if "different issuer IDs" in i]


def test_the_runs_own_model_check_reads_view_json_bounded(tmp_path):
    folder = "runs/r1/deliveries/m-1"
    (tmp_path / folder).mkdir(parents=True)
    (tmp_path / folder / "model.html").write_text("<html>m</html>")
    (tmp_path / folder / "delivery.json").write_text(
        json.dumps({"files": {"model.html": "0" * 64, "view.json": "0" * 64}})
    )
    os.mkfifo(tmp_path / folder / "view.json")
    artifact = {"folder": folder, "kind": "model", "available": True, "href": "/x"}
    catalogue = {"real": [{"id": "r1", "name": "r1", "artifacts": [artifact]}], "issues": []}
    shown, _ = within(10, lambda: store.shown_models(tmp_path, catalogue))
    assert shown == {folder}


# Task 17 rider batch: budget order, label length.
def test_a_model_some_run_shows_is_laid_out_before_models_no_run_shows(tmp_path, monkeypatch):
    unlinked = [
        model_delivery(
            tmp_path,
            f"deliverables/z-{k}",
            forecast=REQUEST,
            exact=exact_record(),
            extra=cashflow_files(),
        )
        for k in range(2)
    ]
    for artifact in unlinked:  # these two name no run of the workspace
        folder = tmp_path / artifact["folder"]
        view = json.loads((folder / "view.json").read_text(encoding="utf-8"))
        view["run"].update(run_id="nobody", issuer_id="BET")
        digest = put(tmp_path, f"{artifact['folder']}/view.json", json.dumps(view))
        record = json.loads((folder / "delivery.json").read_text(encoding="utf-8"))
        record["files"]["view.json"] = digest
        (folder / "delivery.json").write_text(json.dumps(record), encoding="utf-8")
    own = model_delivery(
        tmp_path,
        "runs/alpha-001/deliveries/own",
        forecast=REQUEST,
        exact=exact_record(),
        extra=cashflow_files(),
    )

    def record_issuer():
        manifest = {"issuer_name": "Alpha Holdings", "issuer_id": "ALP"}
        put(tmp_path, "runs/alpha-001/workflow.json", json.dumps({"run": manifest}))

    (one,) = models_of(tmp_path, own, edit=record_issuer)["models"]
    monkeypatch.setattr(store, "CASHFLOW_CELL_BUDGET", cell_count(one["cashflow"]) + 1)
    result = models_of(tmp_path, *unlinked, own, edit=record_issuer)
    grids = {m["id"]: m["cashflow"] is not None for m in result["models"]}
    assert grids == {"z-0": False, "z-1": False, "own": True}
    for name in ("z-0", "z-1"):
        assert any(
            i.startswith(f"deliverables/{name}: the cash flow model is not shown")
            for i in result["issues"]
        )


def test_a_long_unit_or_add_back_label_is_cut_to_200_characters_but_still_reads_its_values(
    tmp_path,
):
    unit = "U" * 300
    annual = ANNUAL_MD.replace("Total Gamma", f"Total {unit}")
    cashflow, _ = cashflow_of(tmp_path, extra=cashflow_files(annual=annual))
    labels = [r["label"] for r in cashflow["rows"] if r["label"].startswith("UU")]
    assert labels == ["U" * 200, "U" * 200 + " YoY growth"]
    cells = row(cashflow, "U" * 200)["cells"]
    assert any(c["status"] != "gap" for c in cells)


# Task 18: whole-branch review fixes.
DEBT_HEAD = "| Instrument | Sep 30, 2024 amount / status | Terms |\n|---|---|---|\n"
DEBT_ROWS = (
    "| Trade receivable securitization | Gross 121; carrying 120; commitment 650 | x |\n"
    "| Term loans aggregate | Principal 1,100; carrying 1,000 after costs | x |\n"
    "| 6% secured notes due 2030 | Principal 500; carrying 500 | x |\n"
)


def secured_of(extra):
    tables = store.markdown_tables("### Debt\n\n" + DEBT_HEAD + DEBT_ROWS + extra, "annual.md")
    return store.secured_debt(tables)


@pytest.mark.parametrize(
    "extra",
    ["|  |  |  |\n|  |  |  |\n", "| Of which | see note | x |\n| Of which | see note | x |\n"],
)
def test_a_repeated_debt_label_without_a_value_does_not_void_secured_leverage(extra):
    found = secured_of(extra)
    assert found is not None and found[1] == 1620 and found[2] is None


def test_a_repeated_debt_label_that_drops_a_carrying_value_still_voids_it():
    found = secured_of("| 6% secured notes due 2030 | carrying 250 | x |\n")
    assert found is not None and found[1] is None
    assert found[2] == "the debt register repeats a row label: 6% secured notes due 2030"
    found = secured_of("| Of which | see note | x |\n| Of which | carrying 5 | x |\n")
    assert found is not None and found[2] == "the debt register repeats a row label: Of which"


def test_an_escaped_pipe_does_not_split_a_register_cell():
    escaped = DEBT_ROWS.replace(
        "Principal 1,100; carrying 1,000", r"Principal 1,100 \| carrying 1,000"
    )
    tables = store.markdown_tables("### Debt\n\n" + DEBT_HEAD + escaped, "annual.md")
    found = store.secured_debt(tables)
    assert found is not None and found[1] == 1620  # 120 + 1,000 + 500, by hand


@pytest.mark.parametrize(
    "label",
    [
        "Secured notes subtotal",
        "Subtotal secured notes",
        "Secured notes, total",
        "Term loans, total",
        "**Total secured notes**",
        "_Total secured notes_",
    ],
)
def test_a_subtotal_labelled_register_row_is_not_summed(label):
    found = secured_of(f"| {label} | carrying 600 | x |\n")
    assert found is not None and found[1] == 1620 and found[2] is None


def test_an_emphasised_register_label_is_classified_by_its_words():
    found = secured_of("| **6.5% secured notes due 2031** | carrying 100 | x |\n")
    assert found is not None and found[1] == 1720
    found = secured_of("| **Term loans aggregate** | carrying 7 | x |\n")
    assert found is not None and found[1] is None
    assert found[2] == "the debt register repeats a row label: **Term loans aggregate**"


@pytest.mark.parametrize(
    "extra",
    [
        "<!-- reviewer note -->\n| 7% secured notes due 2033 | carrying 100 | x |\n",
        (
            "<!-- restated\n| 7% secured notes due 2033 | carrying 50 | x |\n-->\n"
            "| 7% secured notes due 2034 | carrying 100 | x |\n"
        ),
        (
            "| 7% secured notes due 2033 | carrying 50 | x |<!-- restated\n"
            "| 7% secured notes due 2033 | carrying 1 | x |\n-->\n"
            "| 7% secured notes due 2034 | carrying 100 | x |\n"
        ),
    ],
)
def test_a_register_interrupted_by_a_comment_gives_no_total_naming_its_table(extra):
    found = secured_of(extra)
    assert found is not None and found[1] is None
    assert found[2] == (
        "the debt register (Sep 30, 2024 amount / status) is interrupted by a comment"
    )


def test_the_budget_goes_first_to_a_model_a_run_lists_through_its_sources(tmp_path, monkeypatch):
    def record_issuer():
        manifest = {"issuer_name": "Alpha Holdings", "issuer_id": "ALP"}
        put(tmp_path, "runs/alpha-001/workflow.json", json.dumps({"run": manifest}))

    def retarget(artifact, **fields):
        folder = tmp_path / artifact["folder"]
        view = json.loads((folder / "view.json").read_text(encoding="utf-8"))
        view["run"].update(fields)
        digest = put(tmp_path, f"{artifact['folder']}/view.json", json.dumps(view))
        record = json.loads((folder / "delivery.json").read_text(encoding="utf-8"))
        record["files"]["view.json"] = digest
        (folder / "delivery.json").write_text(json.dumps(record), encoding="utf-8")

    def make(name, **options):
        return model_delivery(
            tmp_path,
            f"deliverables/{name}",
            forecast=REQUEST,
            exact=exact_record(),
            extra=cashflow_files(),
            **options,
        )

    unlinked = [make(f"a-{k}") for k in range(2)]
    for artifact in unlinked:
        retarget(artifact, run_id="nobody", issuer_id="BET")
    workspace(tmp_path)
    digest = hashlib.sha256((tmp_path / "runs/alpha-001/CP-1.md").read_bytes()).hexdigest()
    sourced = make("z", sources={"forecast": {"path": "runs/alpha-001/CP-1.md", "sha256": digest}})
    retarget(sourced, run_id="nobody", issuer_id="ALP")
    (one,) = models_of(tmp_path, sourced, edit=record_issuer)["models"]
    assert one["sources"][0]["run"] == "alpha-001"
    monkeypatch.setattr(store, "CASHFLOW_CELL_BUDGET", cell_count(one["cashflow"]) + 1)
    result = models_of(tmp_path, *unlinked, sourced, edit=record_issuer)
    grids = {m["id"]: m["cashflow"] is not None for m in result["models"]}
    assert grids == {"a-0": False, "a-1": False, "z": True}


def test_the_id_conflict_issue_reads_the_same_for_every_run_order():
    import itertools

    recorded = {
        "r1": ("Alpha", "bet"),
        "r2": ("Alpha", "BET"),
        "r3": ("Alpha", "ALP"),
        "r4": ("Alpha", "Zed"),
    }
    texts = set()
    for order in itertools.permutations(recorded.items()):
        issues: list[str] = []
        store.issuer_groups(dict(order), issues)
        texts.add(tuple(issues))
    assert texts == {("issuer name Alpha is recorded with different issuer IDs: ALP, bet, Zed",)}


def named_run_with_deliveries(tmp_path, *views):
    own = [
        view_delivery(tmp_path, f"deliverables/d{n}", "alpha-001", issuer_id, name)
        for n, (issuer_id, name) in enumerate(views)
    ]
    catalogue = identity_catalogue(tmp_path, {"alpha-001": ("Alpha Holdings", None, None)}, own)
    result = store.workspace_store(tmp_path, catalogue)
    return result, result["runs"]["alpha-001"]


def test_a_named_run_takes_the_id_its_deliverables_agree_on_whatever_they_call_it(tmp_path):
    result, run = named_run_with_deliveries(
        tmp_path, ("ALP", "Alpha Holdings"), ("alp", "Alpha Holdings Ltd")
    )
    assert run["issuerKey"] == "id:alp"
    assert any("Alpha Holdings Ltd" in i and "'Alpha Holdings'" in i for i in result["issues"])


def test_a_named_run_whose_deliverables_name_different_ids_takes_none_and_says_so(tmp_path):
    result, run = named_run_with_deliveries(tmp_path, ("ALP", "Alpha Holdings"), ("BET", "Beta"))
    assert run["issuerKey"] == "name:Alpha Holdings"
    assert (
        "runs/alpha-001: deliverables name different issuers; no issuer ID taken"
        in (result["issues"])
    )


def test_a_deliverable_name_equal_after_case_and_spacing_raises_no_issue(tmp_path):
    result, run = named_run_with_deliveries(tmp_path, ("ALP", "  alpha   HOLDINGS "))
    assert run["issuerKey"] == "id:alp"
    assert not any(i.startswith("runs/alpha-001") for i in result["issues"])


def test_named_run_id_says_no_id_recorded_when_no_deliverable_has_one() -> None:
    delivered = [{"issuer_id": None, "issuer_name": "Zeta Corp"}]
    run_id, issue = store.named_run_id("Alpha Holdings", None, delivered)
    assert run_id is None
    assert (
        issue
        == "deliverables name the issuer 'Zeta Corp', not 'Alpha Holdings'; no issuer ID recorded"
    )


def test_named_run_id_keeps_the_id_when_the_names_differ() -> None:
    delivered = [{"issuer_id": "ZET", "issuer_name": "Zeta Corp"}]
    run_id, issue = store.named_run_id("Alpha Holdings", None, delivered)
    assert run_id == "ZET"
    assert issue == "deliverables name the issuer 'Zeta Corp', not 'Alpha Holdings'; issuer ID kept"


# Recorded quarter values (Task 9): hand-written expectations, windows as the bridge prints them.
LTM_ROW = "LTM Adj EBITDA (As Defined)"
SENIOR_ROW = "Senior secured leverage (secured debt / Adj EBITDA)"
TOTAL_ROW = "Total leverage (debt / Adj EBITDA)"
LTM_NEEDED_TEXT = "needs last-twelve-months Adj EBITDA for this quarter, which is not recorded"
AFTER_DEBT_TEXT = "needs quarter-end total carrying debt, which the model does not derive"
AFTER_SENIOR_TEXT = (
    "needs quarter-end senior secured carrying debt, which the model does not derive"
)


def quarter_record(quarters):
    return calculation_record(quarters=quarters)


def test_ltm_adj_ebitda_and_quarter_end_leverage_show_where_the_record_holds_them(tmp_path):
    record = quarter_record(
        {
            "2025-10-01–2025-12-31": {
                "ltm_adj_ebitda": amount("4322"),
                "senior_secured_multiple": amount("4.6719"),
            },
            "2024-10-01-2024-12-31": {"ltm_adj_ebitda": amount("100")},  # hyphen as printed
        }
    )
    cashflow, issues = cashflow_of(tmp_path, extra=cashflow_files(record))
    assert issues == []
    assert shown(cashflow, LTM_ROW) == ["100", NA, "4,322", "540", "594", NM, NM]
    assert shown(cashflow, SENIOR_ROW) == [NA, NA, "4.67x", "3.00x", NA, NM, NM]
    assert row(cashflow, SENIOR_ROW)["cells"][2]["exact"] == "4.6719"
    total = row(cashflow, TOTAL_ROW)["cells"]
    assert [(c["display"], c["reason"]) for c in total[:3]] == [
        (NA, AFTER_DEBT_TEXT),
        (NA, LTM_NEEDED_TEXT),
        (NA, AFTER_DEBT_TEXT),
    ]


def test_without_quarter_values_the_ltm_row_is_not_available_and_leverage_names_why(tmp_path):
    cashflow, _ = cashflow_of(tmp_path)
    assert shown(cashflow, LTM_ROW) == [NA, NA, NA, "540", "594", NM, NM]
    for label in (SENIOR_ROW, TOTAL_ROW):
        assert [c["reason"] for c in row(cashflow, label)["cells"][:3]] == [LTM_NEEDED_TEXT] * 3


def test_a_recorded_ltm_without_a_recorded_leverage_says_the_debt_total_is_missing(tmp_path):
    record = quarter_record({"2025-10-01–2025-12-31": {"ltm_adj_ebitda": amount("4322")}})
    cashflow, _ = cashflow_of(tmp_path, extra=cashflow_files(record))
    for label, text in ((SENIOR_ROW, AFTER_SENIOR_TEXT), (TOTAL_ROW, AFTER_DEBT_TEXT)):
        cell = row(cashflow, label)["cells"][2]
        assert (cell["display"], cell["reason"]) == (NA, text)
    other = row(cashflow, TOTAL_ROW)["cells"][0]
    assert other["reason"] == LTM_NEEDED_TEXT


def test_a_missing_window_reads_with_the_note_the_delivery_recorded(tmp_path):
    note = "the LTM spans 373 days, outside 364-371"
    record = quarter_record(
        {
            "2025-10-01–2025-12-31": {
                "ltm_adj_ebitda": {"amount": None, "reason": "WINDOW_MISSING", "note": note}
            }
        }
    )
    cashflow, _ = cashflow_of(tmp_path, extra=cashflow_files(record))
    cell = row(cashflow, LTM_ROW)["cells"][2]
    assert cell["reason"] == (
        "last-twelve-months Adj EBITDA cannot be built from the handoffs: " + note
    )


def test_quarter_reasons_read_in_words(tmp_path):
    expected = {
        "WINDOW_MISSING": "last-twelve-months Adj EBITDA cannot be built from the handoffs",
        "UNCLASSIFIED_ROW": "the debt register has a row that cannot be classified",
        "REGISTER_DATE_DIFFERS": "secured-debt carrying values are recorded at another date",
        "COMPONENT_MISSING": "a component is not in the handoffs",
        "NOT_STATED": "a component is not in the handoffs",
        "NOT_SOURCED": "not reported in the source",
        "ZERO_OR_NEGATIVE_DENOMINATOR": "a divisor is zero or negative",
    }
    for code, words in expected.items():
        record = quarter_record(
            {
                "2025-10-01–2025-12-31": {
                    "ltm_adj_ebitda": amount(None, code),
                    "senior_secured_multiple": amount(None, code),
                }
            }
        )
        cashflow, _ = cashflow_of(tmp_path / code, extra=cashflow_files(record))
        for label in (LTM_ROW, SENIOR_ROW):
            cell = row(cashflow, label)["cells"][2]
            assert (cell["display"], cell["reason"]) == (NA, words), (code, label)


def test_a_malformed_quarters_entry_is_reported_like_a_malformed_value_entry(tmp_path):
    for bad in ({"2025-10-01–2025-12-31": {"ltm_adj_ebitda": "4322"}}, ["not", "a", "dict"]):
        cashflow, issues = cashflow_of(
            tmp_path / str(len(str(bad))), extra=cashflow_files(quarter_record(bad))
        )
        assert cashflow is None
        assert issues == ["deliverables/m-1: calculation.json is missing or unreadable"]


# Fix round 1: the same label, hidden-text and row rules as delivery.
@pytest.mark.parametrize(
    "label",
    [
        "***Total secured notes***",
        "**_Total secured notes_**",
        "Secured notes (total)",
        "Secured notes total:",
        "Secured notes, total.",
        "**Total** secured notes",
        "Secured notes  total",
    ],
)
def test_a_subtotal_is_skipped_whatever_its_emphasis_or_punctuation(label):
    found = secured_of(f"| {label} | carrying 600 | x |\n")
    assert found is not None and found[1] == 1620 and found[2] is None


def test_a_total_inside_a_label_is_unclassified_and_a_totalizer_is_not_a_total():
    found = secured_of("| Secured total notes | carrying 50 | x |\n")
    assert found is not None and found[1] is None
    assert found[2] == "the debt register has a row that cannot be classified: Secured total notes"
    found = secured_of("| Totalizer secured notes due 2031 | carrying 50 | x |\n")
    assert found is not None and found[1] == 1670  # 120 + 1,000 + 500 + 50


@pytest.mark.parametrize("space", ["  ", " "])
def test_labels_that_differ_only_in_inner_spacing_are_one_repeated_label(space):
    found = secured_of(f"| 6%{space}secured notes due 2030 | carrying 5 | x |\n")
    assert found is not None and found[1] is None
    assert found[2].startswith("the debt register repeats a row label")


def test_a_code_span_comment_marker_is_text_not_a_comment():
    found = secured_of("| 7% secured notes due 2033 | carrying 100; tag `<!--` | x |\n")
    assert found is not None and found[1] == 1720 and found[2] is None


HIDDEN_HEAD = "| Instrument | Sep 30, 2024 amount / status | Note |\n|---|---|---|\n"
HIDDEN_DRAFT = (
    HIDDEN_HEAD + "| Trade receivable securitization | carrying 1 | x |\n"
    "| Term loans aggregate | carrying 2 | x |\n"
)


@pytest.mark.parametrize("wrap", [("<!--\n", "-->\n"), ("```\n", "```\n")])
def test_a_commented_or_fenced_draft_register_is_never_read(wrap):
    tables = store.markdown_tables(
        wrap[0] + HIDDEN_DRAFT + wrap[1] + "\n### Debt\n\n" + HIDDEN_HEAD + DEBT_ROWS, "annual.md"
    )
    found = store.secured_debt(tables)
    assert found is not None and found[1] == 1620


def test_a_row_indented_up_to_three_spaces_is_a_row_and_four_splits_the_table():
    found = secured_of("   | 7% secured notes due 2033 | carrying 100 | x |\n")
    assert found is not None and found[1] == 1720
    found = secured_of("    | 7% secured notes due 2033 | carrying 100 | x |\n")
    assert found is not None and found[1] is None  # code under the rows: a split, never a partial


@pytest.mark.parametrize(
    "gap",
    ["\n<!-- note -->\n", "\n<!-- a\n\nb -->\n", "\n", "\t", "", "<!-- note --> ", "---\n"]
    + ["<!-->\n", "<!--->\n", "<!-- note --> see PDF\n"],
)
def test_a_register_split_by_a_blank_line_or_hidden_text_gives_no_total(gap):
    row = "| 7% secured notes due 2033 | carrying 100 | x |\n"
    extra = {"\t": "\t" + row, "": row[1:]}.get(gap, gap + row)
    found = secured_of(extra + "\nAmounts in USD millions.\n")  # text after it, as in a handoff
    assert found is not None and found[1] is None
    words = "interrupted by a comment" if "<!--" in gap else "split by a blank line or a comment"
    assert found[2] == f"the debt register (Sep 30, 2024 amount / status) is {words}"


def test_a_table_after_hidden_text_is_its_own_table_and_a_plural_total_is_a_subtotal():
    text = (
        "| Label | FY2024 | FY2023 |\n|---|---|---|\n| Total X | 4,300 | 3,900 |\n<!-- c -->\n"
        "| Label | FY2023 | FY2022 |\n|---|---|---|\n| Gain on sale | 30 | 25 |\n"
    )
    table = store.table_holding(store.markdown_tables(text, "annual.md"), "Gain on sale")
    assert store.table_cell(table, "Gain on sale", ("fy", "FY2024"))["exact"] is None  # absent
    assert store.table_cell(table, "Gain on sale", ("fy", "FY2023"))["exact"] == "30"
    assert secured_of("| Totals, secured notes | carrying 600 | x |\n")[1] == 1620


COVENANTS = (  # an unrelated dated table, split, above the register
    "### Covenants\n\n| Covenant | Sep 30, 2023 status | Note |\n|---|---|---|\n"
    "| Leverage | 5.0x | ok |\n\n| Coverage | 2.0x | ok |\n\n### Debt\n\n" + DEBT_HEAD
)
SECURITIZATION, _, TERM_ON = DEBT_ROWS.partition("\n")  # the first row; the rest from Term loans
NOTE_2033 = "| 7% secured notes due 2033 | carrying 100 | x |\n"
SPLIT = "split by a blank line or a comment"


@pytest.mark.parametrize(
    ("rows", "words"),
    [
        (SECURITIZATION + "\n<!-- note -->\n" + TERM_ON, "interrupted by a comment"),
        (SECURITIZATION + "\n\n" + TERM_ON, SPLIT),
        (SECURITIZATION + "\n\n" + NOTE_2033 + TERM_ON, SPLIT),
        (NOTE_2033 + "\n| Revolver | Sep 30, 2024: undrawn | x |\n" + DEBT_ROWS, SPLIT),
    ],
)
def test_a_register_whose_term_loans_row_follows_its_split_names_the_split(rows, words):
    found = store.secured_debt(store.markdown_tables(COVENANTS + rows, "annual.md"))
    assert found is not None and (found[0].isoformat(), found[1]) == ("2024-09-30", None)
    assert found[2] == f"the debt register (Sep 30, 2024 amount / status) is {words}"
    assert store.secured_debt(store.markdown_tables(COVENANTS, "annual.md")) is None


ANNUAL_HANDOFF = ROOT / "runs/tdg-002/CP-1-attempt-2.md"
PROSE = "This is reported issuer disclosure, not CP-1 independent compliance verification.\n"
TRANCHES = (
    "\n| Item / ID | Principal Sep 30, 2024 | Terms retained |\n|---|---|---|\n"
    "| Tranche L / TL05 | 1,500 | January 19, 2032 |\n"
)


@pytest.mark.parametrize("newline", ["\r\n", "\r"])
def test_the_store_reads_crlf_and_lone_cr_handoffs_as_it_reads_lf(newline):
    # Hand key: the retained register totals 20020 at 2024-09-30; a later table stays its own.
    lf = ANNUAL_HANDOFF.read_text("utf-8").replace(PROSE, PROSE + TRANCHES, 1)
    assert TRANCHES in lf
    text = lf.replace("\n", newline)
    found = store.secured_debt(store.markdown_tables(text, "annual.md"))
    assert found is not None
    assert (found[0].isoformat(), found[1], found[2]) == ("2024-09-30", 20020, None)
    lf_tables = store.markdown_tables(lf, "annual.md")
    tables = store.markdown_tables(text, "annual.md")
    tranche = next(t for t in tables if t["header"][:1] == ["Item / ID"])
    assert tranche["interrupted"] is None  # its own table, not a continuation of the register
    assert any(t["periods"] for t in tables)
    assert [(t["header"], t["periods"], t["interrupted"]) for t in tables] == [
        (t["header"], t["periods"], t["interrupted"]) for t in lf_tables
    ]


def test_the_grid_of_a_crlf_model_equals_the_lf_grid_cell_for_cell():
    folder = ROOT / "deliverables/tdg-model-1"
    lf = {name: (folder / name).read_bytes() for name in store.CASHFLOW_FILES}
    crlf = {name: body.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n") for name, body in lf.items()}
    handoff = ANNUAL_HANDOFF.read_text("utf-8")
    grid, problem = store.read_cashflow(lf, handoff)
    assert grid is not None and problem is None
    assert store.read_cashflow(crlf, handoff.replace("\n", "\r\n")) == (grid, None)


@pytest.mark.parametrize("separator", ["\x0c", " ", "\x85"])
def test_source_lines_are_physical_lines_whatever_the_text_contains(separator):
    # Answer key: "## Next" is on physical line 3 (newline-only), as the table reader counts.
    text = f"# Title\nText{separator}more text\n## Next\n\n| A |\n| - |\n| x{separator}y |\nTail\n"
    sections = store.parse_source(text)
    assert [(s["heading"], s["line"]) for s in sections] == [("Title", 1), ("Next", 3)]
    table = sections[1]["blocks"][0]
    assert (table["line"], [r["line"] for r in table["rows"]]) == (5, [7])
    assert sections[0]["blocks"][0]["end"] == 2
