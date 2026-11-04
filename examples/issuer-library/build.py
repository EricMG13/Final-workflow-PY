"""Build a local screening example from pinned, curated handoff summaries."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import math
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def project_file(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Path outside project: {relative}")
    return path


def relative_link(path: Path, page_dir: Path) -> str:
    return quote(os.path.relpath(path.resolve(), page_dir.resolve()), safe="/")


def verify_artifact(artifact: dict, root: Path, page_dir: Path, issuer: str) -> dict:
    """A missing or changed bundle remains visible without an Open link."""
    result = dict(artifact, available=False, href=None, issue=None)
    try:
        folder = project_file(root, artifact["folder"])
        if not folder.is_relative_to((root / "deliverables").resolve()):
            raise ValueError("Report is outside deliverables")
        record = json.loads((folder / "delivery.json").read_text())
        if not isinstance(record, dict) or not isinstance(record.get("files"), dict):
            raise TypeError("Invalid delivery file manifest")
        if not {"report.html", "view.json"} <= record["files"].keys():
            raise ValueError("Report and identity are not recorded in delivery.json")
        view = None
        for name, digest in record["files"].items():
            path = project_file(folder, name)
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != digest:
                raise ValueError(f"Changed delivery file: {name}")
            if name == "view.json":
                view = json.loads(raw)
        if view["run"]["issuer_id"] != issuer:
            raise ValueError("Delivery issuer does not match the catalogue run")
        result.update(available=True, href=relative_link(folder / "report.html", page_dir))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result["issue"] = str(exc)
    return result


def admit_catalog(data: dict, root: Path, page_dir: Path) -> dict:
    """Check pinned excerpts and numeric transport before publishing a snapshot."""
    result = copy.deepcopy(data)
    for key, source in result["sources"].items():
        path = project_file(root, source["path"])
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != source["sha256"]:
            raise ValueError(f"Changed source: {key}")
        lines = raw.decode().splitlines()
        line = source["line"]
        if (
            not isinstance(line, int)
            or not 1 <= line <= len(lines)
            or lines[line - 1] != source["quote"]
        ):
            raise ValueError(f"Source excerpt differs: {key}")
        source["href"] = relative_link(path, page_dir)
    for dataset in ("real", "illustrative"):
        ids = set()
        for run in result[dataset]:
            if run["id"] in ids:
                raise ValueError(f"Duplicate run: {run['id']}")
            ids.add(run["id"])
            if dataset == "real" and (
                run["completion"] is not None or run["checkpoints"] is not None
            ):
                raise ValueError("Real completeness is unassessed in this example")
            if dataset == "illustrative":
                counts = run["checkpoints"]
                if not 0 <= counts["done"] <= counts["total"] or counts["total"] <= 0:
                    raise ValueError("Invalid illustrative completion counts")
                if run["completion"] != 100 * counts["done"] / counts["total"] or run["artifacts"]:
                    raise ValueError("Illustrative score or report boundary differs")
            for metric in run["metrics"].values():
                if metric is None:
                    continue
                number = float(metric["value"])
                if not math.isfinite(number):
                    raise ValueError("Metric must be finite or missing")
                if dataset == "real":
                    source = result["sources"][metric["source"]]
                    tokens = re.findall(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?", source["quote"])
                    if metric["value"] not in {token.replace(",", "") for token in tokens}:
                        raise ValueError("Metric value absent from its pinned excerpt")
            run["handoff_href"] = (
                relative_link(project_file(root, run["handoff"]), page_dir)
                if run["handoff"]
                else None
            )
            run["artifacts"] = [
                verify_artifact(a, root, page_dir, run["issuer"]) for a in run["artifacts"]
            ]
    return result


def render_page(template: str, data: dict, assets: dict[str, str]) -> str:
    replacements = assets | {
        "DATA": json.dumps(data, ensure_ascii=True, allow_nan=False).replace("<", "\\u003c")
    }
    return re.sub(
        r"/\*(DATA|STYLE|LOGIC|APP|FONTS|LOGO|LICENSE)\*/",
        lambda match: replacements[match[1]],
        template,
    )


def main() -> None:
    data = admit_catalog(json.loads((HERE / "catalog.json").read_text()), ROOT, HERE)
    data["built_at"] = datetime.now(UTC).strftime("%d %b %Y, %H:%M UTC")
    fonts = []
    for family, file, weight in [
        ("Red Hat Display", "RedHatDisplay-SemiBold.woff2", 600),
        ("Red Hat Display", "RedHatDisplay-Bold.woff2", 700),
        ("Red Hat Text", "RedHatText-Regular.woff2", 400),
        ("Red Hat Text", "RedHatText-Medium.woff2", 500),
        ("Red Hat Text", "RedHatText-SemiBold.woff2", 600),
        ("Red Hat Mono", "RedHatMono-Medium.woff2", 500),
        ("Red Hat Mono", "RedHatMono-SemiBold.woff2", 600),
    ]:
        encoded = base64.b64encode(
            (ROOT / "src/deploy_vii/assets/fonts" / file).read_bytes()
        ).decode()
        fonts.append(
            f'@font-face{{font-family:"{family}";font-weight:{weight};font-display:swap;src:url(data:font/woff2;base64,{encoded}) format("woff2")}}'
        )
    assets = {
        name: (HERE / filename).read_text()
        for name, filename in [("STYLE", "style.css"), ("LOGIC", "logic.js"), ("APP", "app.js")]
    }
    shared = ROOT / "src/deploy_vii/assets"
    assets["STYLE"] = (
        (shared / "tokens.css").read_text() + (shared / "app.css").read_text() + assets["STYLE"]
    )
    assets["LOGO"] = (
        "data:image/png;base64,"
        + base64.b64encode(
            (shared / "brand/ssim-logo-stacked-black-trim.png").read_bytes()
        ).decode()
    )
    assets["LICENSE"] = (shared / "fonts/OFL.txt").read_text().replace("--", "—")
    assets["FONTS"] = "\n".join(fonts)
    output = render_page((HERE / "template.html").read_text(), data, assets)
    # Replace only the example's generated page, never a historical delivery.
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=HERE, suffix=".tmp", delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(output)
    try:
        temporary.replace(HERE / "index.html")
    finally:
        temporary.unlink(missing_ok=True)
    print(HERE / "index.html")


if __name__ == "__main__":
    main()
