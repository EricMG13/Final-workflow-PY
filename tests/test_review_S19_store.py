"""S19 review regressions: the store's identities, units, handoff lists and report links.

Expected values are written here by hand; the store reads files only.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "review_store", ROOT / "apps/issuer-library/engine/store.py"
)
assert spec is not None and spec.loader is not None
store = importlib.util.module_from_spec(spec)
spec.loader.exec_module(store)

BODY = "# CP-8\n\n## Findings\n\nA finding.\n"


def put(root: Path, name: str, text: str) -> str:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode()).hexdigest()


def plain(*folders: str, **fields: str) -> dict:
    blank = {"sector": "", "period": "", "artifacts": [], **fields}
    return {"issues": [], "real": [{"id": f, "name": f, **blank} for f in folders]}


CHART = (
    "# CP-1\n\n## Findings\n\n### Chart data: net sales\n\n"
    "| Period | Net sales | Reporting unit | Basis and limitation |\n"
    "| --- | --- | --- | --- |\n"
    "{rows}"
)


def chart(rows: str) -> dict:
    return store.reader_fields(store.parse_source(CHART.format(rows=rows)))


def test_the_chart_unit_comes_from_the_rows_holding_numbers():
    fields = chart(
        "| FY2022 | Not supplied: reported in EUR m | EUR m | Pre-redenomination filing |\n"
        "| FY2023 | 1,200 | US$m | Annual report |\n"
        "| FY2024 | (35) | US$m | Annual report |\n"
    )
    assert fields["charts"] == [{"title": "Net sales", "unit": "US$m", "table": 7, "columns": [1]}]
    assert fields["issue"] is None


def test_a_chart_whose_numbers_disagree_on_unit_is_not_drawn():
    fields = chart(
        "| FY2023 | 1200 | EUR m | Annual report |\n| FY2024 | 1350 | US$m | Annual report |\n"
    )
    assert fields["charts"] == []
    assert fields["issue"] == (
        "Chart data: net sales has a mixed or missing reporting unit for its numbers"
    )


def test_a_chart_with_no_number_at_all_has_no_unit():
    fields = chart("| FY2024 | Not supplied | US$m | Not disclosed |\n")
    assert fields["charts"] == [] and "mixed or missing reporting unit" in fields["issue"]


def test_a_folder_named_like_a_curated_case_keeps_its_own_issuer(tmp_path):
    put(tmp_path, "runs/tdg-003/CP-0.md", "# Acme\n\nAcme FY2030 run.\n")
    put(
        tmp_path,
        "runs/tdg-003/workflow.json",
        json.dumps(
            {"run": {"issuer_name": "Acme Corp", "issuer_id": "ACME", "as_of": "2030-06-30"}}
        ),
    )
    result = store.workspace_store(tmp_path, plain("tdg-003"))
    run = result["runs"]["tdg-003"]
    assert {k: run[k] for k in ("issuer", "title", "run", "sector", "period", "asOf")} == {
        "issuer": "Acme Corp",
        "title": "Acme Corp",
        "run": "TDG-003",
        "sector": "Unclassified",
        "period": "As of 2030-06-30",
        "asOf": "2030-06-30",
    }
    assert (
        "tdg-003: curated TransDigm Group labels not applied; its workflow.json names Acme Corp"
        in result["issues"]
    )


def test_a_curated_folder_whose_files_agree_keeps_the_curated_labels(tmp_path):
    put(tmp_path, "runs/tdg-003/CP-0.md", "# TDG\n\nRequest.\n")
    put(
        tmp_path,
        "runs/tdg-003/workflow.json",
        json.dumps({"run": {"issuer_name": "TransDigm Group Incorporated", "issuer_id": "tdg"}}),
    )
    catalogue = plain("tdg-003", issuer="TDG")
    result = store.workspace_store(tmp_path, catalogue)
    run = result["runs"]["tdg-003"]
    assert (run["issuer"], run["sector"]) == ("TransDigm Group", "Aerospace & defense")
    assert not [issue for issue in result["issues"] if "labels not applied" in issue]


def test_the_admitted_catalogue_issuer_also_decides(tmp_path):
    put(tmp_path, "runs/ford-otosan-2024-001/CP-0.md", "# Run\n\nRequest.\n")
    catalogue = plain("ford-otosan-2024-001")
    catalogue["real"][0] |= {"issuer": "ACME", "name": "Acme Corp"}
    result = store.workspace_store(tmp_path, catalogue)
    assert "ford-otosan-2024-001" in result["runs"]
    assert result["runs"]["ford-otosan-2024-001"]["issuer"] == "Acme Corp"
    assert any("the library admitted it as Acme Corp" in issue for issue in result["issues"])


def test_an_uncurated_folder_on_a_curated_route_is_reported_not_silently_dropped(tmp_path):
    put(tmp_path, "runs/tdg-guidance/CP-1.md", BODY)
    put(tmp_path, "runs/tdg-guidance-001/CP-2.md", BODY + "curated\n")
    for order in (("tdg-guidance", "tdg-guidance-001"), ("tdg-guidance-001", "tdg-guidance")):
        result = store.workspace_store(tmp_path, plain(*order))
        assert {key: run["folder"] for key, run in result["runs"].items()} == {
            "tdg-guidance": "tdg-guidance-001"
        }
        assert (
            "tdg-guidance: not shown; its folder name is the route of the curated run "
            "tdg-guidance-001; rename the folder to show this run"
        ) in result["issues"], order


def test_distinct_modules_with_identical_bytes_are_both_kept(tmp_path):
    body = "# Not applicable\n\nNo applicable source for this module.\n"
    put(tmp_path, "runs/case-x/CP-3.md", body)
    put(tmp_path, "runs/case-x/CP-4.md", body)
    put(tmp_path, "runs/case-x/deliveries/a/CP-3.md", body)
    put(tmp_path, "runs/case-x/deliveries/b/CP-3.md", body)
    put(tmp_path, "runs/case-x/deliveries/b/CP-5.md", body)
    result = store.workspace_store(tmp_path, plain("case-x"))
    assert sorted(result["outputs"]) == [
        "case-x/CP-3.md",
        "case-x/CP-4.md",
        "case-x/deliveries/b/CP-5.md",
    ]
    digest = hashlib.sha256(body.encode()).hexdigest()
    row = ("case-x", "Case", "Case", "CASE-X", "Unclassified", "Not established")
    sources = store.collect_runs(tmp_path, {"case-x": row}, {}, lambda *_: "", False)[3]
    assert [match["source"] for match in sources[digest]] == [
        "case-x/CP-3.md",
        "case-x/CP-4.md",
        "case-x/deliveries/b/CP-5.md",
    ]


def test_an_odd_handoff_name_gets_a_label_and_the_run_stays(tmp_path):
    put(tmp_path, "runs/case-a/CP-8.md", BODY)
    put(tmp_path, "runs/case-a/CP-8b.md", BODY + "b\n")
    put(tmp_path, "runs/case-a/CP-8.v2.md", BODY + "v2\n")
    result = store.workspace_store(tmp_path, plain("case-a"))
    labels = {key: output["label"] for key, output in result["outputs"].items()}
    assert labels == {"case-a/CP-8.md": "CP-8", "case-a/CP-8.v2.md": "V2", "case-a/CP-8b.md": "B"}
    assert not [issue for issue in result["issues"] if "could not be read" in issue]


def delivery(root: Path, folder: str, view: dict, files: dict[str, str] | None = None) -> str:
    report = put(root, f"{folder}/report.html", "<html>report</html>")
    shown = put(root, f"{folder}/view.json", json.dumps({"run": view}))
    manifest = files if files is not None else {"report.html": report, "view.json": shown}
    put(root, f"{folder}/delivery.json", json.dumps({"files": manifest}))
    return report


def artifact(folder: str, label: str = "") -> dict:
    return {
        "folder": folder,
        "label": label or Path(folder).name,
        "state": "candidate",
        "available": True,
        "href": f"/files/{folder}/report.html?sha256=s",
    }


ACME = {"issuer_id": "ACME", "issuer_name": "Acme", "as_of": "2025-06-30"}
TDG = {"issuer_id": "TDG", "issuer_name": "TransDigm Group Incorporated", "as_of": "2024-09-30"}


def reports_of(root: Path, *artifacts: dict) -> tuple[dict, list[str]]:
    catalogue = {"issues": [], "real": [{"id": "delivery:x", "artifacts": list(artifacts)}]}
    result = store.workspace_store(root, catalogue)
    return {report["id"]: report for report in result["reports"]}, result["issues"]


def test_a_report_named_like_a_curated_build_keeps_its_own_issuer(tmp_path):
    delivery(tmp_path, "deliverables/tdg-fy2024-snapshot-7", ACME)
    delivery(tmp_path, "runs/x/deliveries/tdg-fy2024-snapshot-6", TDG)
    reports, issues = reports_of(
        tmp_path,
        artifact("deliverables/tdg-fy2024-snapshot-7"),
        artifact("runs/x/deliveries/tdg-fy2024-snapshot-6"),
    )
    acme = reports["tdg-fy2024-snapshot-7"]
    assert (acme["issuer"], acme["label"], acme["build"], acme["status"]) == (
        "Acme",
        "Acme · as of 2025-06-30",
        None,
        None,
    )
    assert (
        "deliverables/tdg-fy2024-snapshot-7: curated label not applied; its view.json names Acme"
        in issues
    )
    elsewhere = reports["tdg-fy2024-snapshot-6"]
    assert (elsewhere["build"], elsewhere["issuer"]) == (None, "TransDigm Group Incorporated")


def test_the_curated_build_still_reads_as_curated(tmp_path):
    delivery(tmp_path, "deliverables/tdg-fy2024-snapshot-7", TDG)
    reports, issues = reports_of(tmp_path, artifact("deliverables/tdg-fy2024-snapshot-7"))
    report = reports["tdg-fy2024-snapshot-7"]
    assert (report["issuer"], report["label"], report["build"], report["status"]) == (
        "TransDigm Group",
        "CP-8 repairs applied",
        7,
        "Latest",
    )
    assert not [issue for issue in issues if "label not applied" in issue]


def test_two_deliveries_with_one_folder_name_are_both_listed(tmp_path):
    delivery(tmp_path, "runs/a/deliveries/report-1", ACME)
    delivery(tmp_path, "runs/b/deliveries/report-1", {**ACME, "as_of": "2026-06-30"})
    reports, _ = reports_of(
        tmp_path,
        artifact("runs/a/deliveries/report-1"),
        artifact("runs/b/deliveries/report-1"),
        artifact("runs/a/deliveries/report-1"),
    )
    assert list(reports) == ["report-1", "runs--b--deliveries--report-1"]
    assert reports["runs--b--deliveries--report-1"]["label"] == "Acme · as of 2026-06-30"


def test_a_delivery_manifest_that_lost_its_report_does_not_take_the_store_down(tmp_path):
    delivery(tmp_path, "deliverables/broken", ACME, files={"view.json": "x"})
    delivery(tmp_path, "deliverables/fine", ACME)
    reports, issues = reports_of(
        tmp_path, artifact("deliverables/broken"), artifact("deliverables/fine")
    )
    assert list(reports) == ["fine"]
    assert any(
        issue.startswith("deliverables/broken: could not be read (KeyError") for issue in issues
    )


def test_store_links_are_the_server_s_pinned_urls(tmp_path):
    folder = "runs/a$b+c/deliveries/x@y"
    digest = delivery(tmp_path, folder, ACME)
    reports, _ = reports_of(tmp_path, artifact(folder))
    hrefs = {f["name"]: f["href"] for f in reports["x@y"]["files"]}
    assert hrefs["report.html"] == (
        f"/files/runs/a$b+c/deliveries/x@y/report.html?sha256={digest}&download=1"
    )
    assert store.pinned_url("runs/a b/é#.md", "d") == "/files/runs/a%20b/%C3%A9%23.md?sha256=d"
