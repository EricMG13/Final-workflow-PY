"""Build the browser test fixture from the curated retained outputs; strict, so a stale pin fails.

This is test data for tests/test_issuer_library_design.py, not a product and not an analysis
run. The app itself reads a workspace through engine/store.py.
"""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "engine"))
from store import CURATED_REPORTS, CURATED_RUNS, built_from, collect_runs, sha256, visual_catalogue

OUT = ROOT / "artifacts/issuer-library/design-fixture"


def prepare_reports(sources):
    """Keep original bytes, trace each handoff to its run file by hash, and add the app's presentation."""
    reports = []
    web = HERE.parent / "web"
    adapter = (web / "report-adapter.js").read_text()
    adapter_css = (web / "report-adapter.css").read_text() + (web / "brand.css").read_text()
    for number, folder in enumerate(
        sorted((ROOT / "deliverables").glob("tdg-fy2024-snapshot*")), 1
    ):
        original = folder / "report.html"
        if not original.exists():
            continue
        destination = OUT / "reports" / folder.name
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, destination / "original.html")
        html = original.read_text(encoding="utf-8")
        html = html.replace(
            "</body>", f"<style>{adapter_css}</style><script>{adapter}</script></body>", 1
        )
        (destination / "preview.html").write_text(html, encoding="utf-8")
        delivery = json.loads((folder / "delivery.json").read_text())
        rows = built_from(folder, sources)
        for row in rows:
            if row["run"] is None:
                raise ValueError(f"{folder.name}: {row['source']} matches no shown run file")
        modules = [row["module"] for row in rows]
        if len(set(modules)) != len(modules):
            raise ValueError(f"{folder.name}: a handoff matches several shown run files")
        label, status = CURATED_REPORTS[folder.name]
        reports.append(
            {
                "id": folder.name,
                "build": number,
                "label": label,
                "status": status,
                "issuer": "TransDigm Group",
                "sha256": sha256(original),
                "scope": delivery["scope"],
                "modelPublished": delivery["cp_model_published"],
                "href": f"reports/{folder.name}/preview.html",
                "download": f"reports/{folder.name}/original.html",
                "files": [],
                "builtFrom": rows,
            }
        )
    return reports


def build():
    shutil.rmtree(OUT, ignore_errors=True)
    (OUT / "sources").mkdir(parents=True)
    catalog = json.loads((HERE.parent / "engine/catalog.json").read_text())
    runs, outputs, inputs, sources, pins, _ = collect_runs(
        ROOT,
        CURATED_RUNS,
        catalog,
        lambda folder, relative, _: f"sources/{folder}--{relative.replace('/', '--')}",
    )
    missing = [module for module, config in catalog.items() if module not in pins]
    if missing:
        raise ValueError(f"pinned outputs were not found: {missing}")
    for record in [*outputs.values(), *inputs.values()]:
        folder = record["file"].split("--")[0]
        shutil.copyfile(ROOT / "runs" / folder / record["source"], OUT / "sources" / record["file"])
    store = {"runs": runs, "outputs": outputs, "inputs": inputs, "pins": pins}
    (OUT / "data.js").write_text(
        "window.DESIGN_DATA = "
        + json.dumps(store, ensure_ascii=False).replace("<", "\\u003c")
        + ";\n",
        encoding="utf-8",
    )
    reports = prepare_reports(sources)
    for module, config in catalog.items():
        compare = config.get("compare")
        if compare:
            cited = {
                compare["prior"]: config["path"],
                compare["current"]: config["path"],
                compare["repaired"]: compare["recheck"],
            }
            for report, handoff in cited.items():
                if (
                    next(r["sha256"] for r in reports if r["id"] == report)
                    not in (ROOT / "runs" / handoff).read_text()
                ):
                    raise ValueError(
                        f"{module}: {handoff} does not cite the report hash of {report}"
                    )
    workspace = {"reports": reports, "visuals": visual_catalogue()}
    (OUT / "workspace-data.js").write_text(
        "window.DESIGN_WORKSPACE = "
        + json.dumps(workspace, ensure_ascii=False).replace("<", "\\u003c")
        + ";\n",
        encoding="utf-8",
    )
    print(
        f"Built {OUT}: {len(runs)} runs, {len(outputs)} saved outputs, {len(inputs)} inputs, {len(reports)} reports."
    )


if __name__ == "__main__":
    build()
