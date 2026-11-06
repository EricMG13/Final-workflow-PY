"""The library's store over a hand-written workspace; expected values are written here."""

import fnmatch
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

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
        "As of 2025-06-30",
    )
    assert result["runs"]["empty-001"]["first"] == "W-Overview"
    assert beta["first"] == "CP-0"


def test_outputs_keep_exact_values_identity_and_a_serving_link(tmp_path):
    result = store.workspace_store(tmp_path, workspace(tmp_path))
    output = result["outputs"]["alpha-001/CP-1.md"]
    rows = output["sections"][1]["blocks"][0]["rows"]
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
    block = output["sections"][0]["blocks"][0]
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
    assert beta["label"] == "Beta Group · as of 2025-06-30" and beta["issuer"] == "Beta Group"
    assert beta["builtFrom"][0]["run"] == "launched"


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
        "sys.stderr.write(' '.join(m for m in sys.modules if m.split('.')[0] in ('deploy_workflow','deploy_vii','pydantic')))"
    )
    done = subprocess.run(
        [sys.executable, "-I", "-B", "-X", "utf8", "-c", probe, str(script), str(tmp_path)],
        input=json.dumps(plain_run("own")).encode(),
        capture_output=True,
        check=True,
    )
    assert done.stderr == b""
    output = json.loads(done.stdout.decode("utf-8"))["outputs"]["own/CP-0.md"]
    assert output["sections"][1]["blocks"][0]["text"].startswith("Net debt ≥ 0 at Şişli −")


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
    assert any(s["heading"] == "Chart data: leverage" for s in output["sections"])
