"""Build the browser test fixture from the curated retained outputs; strict, so a stale pin fails.

This is test data for tests/test_issuer_library_design.py, not a product and not an analysis
run. The app itself reads a workspace through engine/store.py.
"""

import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "engine"))
from store import (
    CURATED_REPORTS,
    CURATED_RUNS,
    Handoffs,
    WorkspaceReads,
    available_folders,
    built_from,
    catalogue_models,
    collect_runs,
    issuer_groups,
    model_manifests,
    recorded_identity,
    report_issuer_key,
    sha256,
    visual_catalogue,
)

OUT = ROOT / "artifacts/issuer-library/design-fixture"


def prepare_reports(
    sources: dict[str, list[dict[str, Any]]], keys: dict[str, str]
) -> list[dict[str, Any]]:
    """Keep original bytes, trace each handoff to its run file by hash, add the presentation."""
    reports: list[dict[str, Any]] = []
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
        view = json.loads((folder / "view.json").read_text(encoding="utf-8"))
        identity = view["run"]
        rows = built_from({str(n): str(h) for n, h in delivery["files"].items()}, sources)
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
                "mode": view.get("mode") if isinstance(view.get("mode"), str) else None,
                "qualification": view.get("analytical_qualification")
                if isinstance(view.get("analytical_qualification"), str)
                else None,
                "issuer": "TransDigm Group",
                "issuerKey": report_issuer_key(keys, identity.get("issuer_id")),
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


def prepare_models(outputs: dict[str, Any], keys: dict[str, str]) -> list[dict[str, Any]]:
    """Published models, read by the app's own catalogue function; each page is copied beside."""
    artifacts: list[dict[str, Any]] = []
    for folder in sorted((ROOT / "deliverables").glob("*/model.html")):
        destination = OUT / "models" / folder.parent.name
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(folder, destination / "model.html")
        artifacts.append(
            {
                "folder": f"deliverables/{folder.parent.name}",
                "kind": "model",
                "available": True,
                "href": f"models/{folder.parent.name}/model.html?sha256={sha256(folder)}",
            }
        )
    catalogue = {"real": [{"artifacts": artifacts}]}
    prior = WorkspaceReads(outputs, keys, {}, model_manifests(ROOT, available_folders(catalogue)))
    models, issues = catalogue_models(ROOT, catalogue, prior)
    if issues:
        raise ValueError(f"models could not be read: {issues}")
    return models


def build() -> None:
    shutil.rmtree(OUT, ignore_errors=True)
    (OUT / "sources").mkdir(parents=True)
    catalog = json.loads((HERE.parent / "engine/catalog.json").read_text())
    handoffs = Handoffs(strict=True)
    runs, outputs, inputs, sources, pins, _ = collect_runs(
        ROOT,
        CURATED_RUNS,
        catalog,
        lambda folder, relative, _: f"sources/{folder}--{relative.replace('/', '--')}",
        handoffs,
    )
    missing = [module for module, config in catalog.items() if module not in pins]
    if missing:
        raise ValueError(f"pinned outputs were not found: {missing}")
    for record in [*outputs.values(), *inputs.values()]:
        folder = record["file"].split("--")[0]
        shutil.copyfile(ROOT / "runs" / folder / record["source"], OUT / "sources" / record["file"])
    # The same identity rules as the app; the seeded catalogue supplies the issuer IDs Go
    # discovery would.
    seeded = json.loads((HERE.parent / "web/legacy-catalog.json").read_text(encoding="utf-8"))
    seeds = {run["id"]: run for run in seeded["real"]}
    recorded = {
        key: recorded_identity(
            ROOT / "runs" / row[0], seeds.get(row[0], {"id": row[0], "name": row[0]}), row[1], []
        )[:2]
        for key, row in CURATED_RUNS.items()
    }
    fields, keys = issuer_groups(recorded)
    for key, identity in fields.items():
        runs[key].update(identity)
    # The shape /api/workspace sends: sections once per handoff, which the page's hydrate() spreads.
    sent = {r["sha256"]: handoffs.parsed[r["sha256"]][0] for r in outputs.values()}
    store = {
        "runs": runs,
        "outputs": outputs,
        "handoffs": sent,
        "inputs": inputs,
        "pins": pins,
    }
    (OUT / "data.js").write_text(
        "window.DESIGN_DATA = "
        + json.dumps(store, ensure_ascii=False).replace("<", "\\u003c")
        + ";\n",
        encoding="utf-8",
    )
    reports = prepare_reports(sources, keys)
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
    workspace = {
        "reports": reports,
        "models": prepare_models(outputs, keys),
        "visuals": visual_catalogue(),
    }
    (OUT / "workspace-data.js").write_text(
        "window.DESIGN_WORKSPACE = "
        + json.dumps(workspace, ensure_ascii=False).replace("<", "\\u003c")
        + ";\n",
        encoding="utf-8",
    )
    print(
        f"Built {OUT}: {len(runs)} runs, {len(outputs)} saved outputs, {len(inputs)} inputs, "
        f"{len(reports)} reports, {len(workspace['models'])} models."
    )


if __name__ == "__main__":
    build()
