"""The library's store: every retained handoff in a workspace, parsed for reading.

Reads files only. Nothing here runs analysis, calls a provider or changes a workspace.
Every page load runs this as its own process, so it imports only the standard library.
"""

import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
REPO = HERE if (HERE / "src").is_dir() else HERE.parents[2]
OUTPUT_SKIP = re.compile(r"instructions|prompt|calculations|verification")
INPUT_NAME = re.compile(r"selected-input|peer-inputs|delivery")
HANDOFF_NAME = re.compile(r"CP-[A-Z0-9]+")
AEROSPACE = "Aerospace & defense"
# Reading labels written by hand. Route key: (folder under runs/, issuer, title, run label, sector, period).
CURATED_RUNS = {
    "tdg-002": (
        "tdg-002",
        "TransDigm Group",
        "TransDigm Group",
        "TDG-002",
        AEROSPACE,
        "FY2024 historical evidence · later events separately dated",
    ),
    "tdg-003": (
        "tdg-003",
        "TransDigm Group",
        "TransDigm Group",
        "TDG-003",
        AEROSPACE,
        "FY2024 and quarter ended 28 December 2024",
    ),
    "tdg-004": (
        "tdg-004",
        "TransDigm Group",
        "TransDigm Group",
        "TDG-004",
        AEROSPACE,
        "19 September 2024 indenture · 6% secured notes due 2033",
    ),
    "tdg-guidance": (
        "tdg-guidance-001",
        "TransDigm Group",
        "TransDigm Group",
        "TDG-GUIDANCE",
        AEROSPACE,
        "7 November 2024 guidance · FY2025 outlook",
    ),
    "tdg-peers-2024": (
        "tdg-peers-2024-001",
        "TransDigm Group",
        "TransDigm & peers",
        "TDG-PEERS-2024",
        AEROSPACE,
        "Each company’s own FY2024 · unmatched fiscal dates",
    ),
    "tdg-run-comparison": (
        "tdg-run-comparison-001",
        "TransDigm Group",
        "TransDigm Group",
        "TDG-RUN-COMPARISON",
        AEROSPACE,
        "Build 2 compared with build 6 · 30 September 2024 financial base",
    ),
    "ford-otosan-2024": (
        "ford-otosan-2024-001",
        "Ford Otosan",
        "Ford Otosan",
        "FORD-OTOSAN-2024",
        "Automotive",
        "11 April 2024 · historical case",
    ),
    "frontier-2020": (
        "frontier-2020-001",
        "Frontier",
        "Frontier",
        "FRONTIER-2020",
        "Telecommunications",
        "29 June 2020 disclosure · historical case",
    ),
}
# Build history recorded in README.md and VERIFICATION.md; builds 4-6 matched by diff.
CURATED_REPORTS = {
    "tdg-fy2024-snapshot": ("Initial snapshot · failed date presentation", "Superseded"),
    "tdg-fy2024-snapshot-2": ("Annual snapshot · reviewed", None),
    "tdg-fy2024-snapshot-3": ("Integrated · macro/ESG and conditional forecast", None),
    "tdg-fy2024-snapshot-4": ("Peer comparison · first delivery, gap rows dropped", None),
    "tdg-fy2024-snapshot-5": ("Peer comparison · gap boundary repaired", None),
    "tdg-fy2024-snapshot-6": ("Peer comparison · exact fiscal dates added", None),
    "tdg-fy2024-snapshot-7": ("CP-8 repairs applied", "Latest"),
}
SAFE_FOLDER = re.compile(r"[\w. -]+")
WEB_RUN = re.compile(r"web-[a-f0-9]{32}")


READER_TABLES = [
    ["Bottom line", "Confidence", "Main limitation"],
    ["Finding", "Creditor impact", "Confidence"],
]
CHART_PREFIX = "Chart data: "
CHART_LAST_COLUMNS = ["Reporting unit", "Basis and limitation"]


def parse_source(text):
    """Keep every nonblank body line in one typed block with its source locator."""
    lines = text.splitlines()
    sections = []
    current = None
    i = 0
    while i < len(lines):
        line = lines[i]
        heading = re.match(r"^(#{1,4}) (.+)$", line)
        if heading:
            current = {"heading": heading[2], "level": len(heading[1]), "line": i + 1, "blocks": []}
            sections.append(current)
            i += 1
            continue
        if not line.strip():
            i += 1
            continue
        if re.fullmatch(r"<!-- table-id: [\w.-]+ -->", line):
            # A transport identifier, preserved in the downloadable original.
            i += 1
            continue
        if current is None:
            raise ValueError("Body before first heading")
        start = i + 1
        if line == "```text" and current["heading"].startswith("T4.4 —"):
            # The retained equity statement is a delimited transcription, not
            # prose. Its explicitly supplied column order governs this table.
            headers = [
                "Reported equity movement",
                "Common shares (individual)",
                "Common stock par",
                "APIC",
                "Accumulated deficit",
                "Accumulated other comprehensive loss",
                "Treasury shares (individual)",
                "Treasury stock value",
                "Noncontrolling interests",
                "Total",
            ]
            rows = []
            i += 1
            while i < len(lines) and lines[i] != "```":
                label, values = lines[i].split(":", 1)
                row = [label] + [c.strip() for c in values.split("|")]
                if len(row) != len(headers):
                    raise ValueError(f"Malformed equity transcription at {i + 1}")
                rows.append({"line": i + 1, "cells": row})
                i += 1
            if i == len(lines):
                raise ValueError("Unclosed equity transcription")
            current["blocks"].append(
                {
                    "type": "table",
                    "line": start,
                    "headers": headers,
                    "rows": rows,
                    "financial": True,
                }
            )
            i += 1
        elif (
            line.startswith("|")
            and i + 1 < len(lines)
            and re.fullmatch(r"\|[\s:|\-]+\|", lines[i + 1])
        ):

            def cells(value):
                return [c.strip() for c in re.split(r"(?<!\\)\|", value.strip().strip("|"))]

            headers = cells(line)
            i += 2
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                row = cells(lines[i])
                if len(row) != len(headers):
                    raise ValueError(f"Malformed table at line {i + 1}")
                rows.append({"line": i + 1, "cells": row})
                i += 1
            current["blocks"].append(
                {"type": "table", "line": start, "headers": headers, "rows": rows}
            )
        else:
            parts = [line]
            i += 1
            while (
                i < len(lines)
                and lines[i].strip()
                and not lines[i].startswith(("#", "|", "- ", "<!-- table-id:"))
                and not re.match(r"\d+\. ", lines[i])
            ):
                parts.append(lines[i])
                i += 1
            current["blocks"].append(
                {"type": "text", "line": start, "end": i, "text": "\n".join(parts)}
            )
    return sections


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def locate_quote(sections, locator, owner):
    """Return a block's opening sentences verbatim, or fail the build."""
    for section in sections:
        if not section["heading"].startswith(locator["heading"]):
            continue
        for block in section["blocks"]:
            flat = re.sub(
                r"\s+", " ", block.get("text", "").replace("**", "").replace("`", "")
            ).strip()
            if flat.startswith(locator["startsWith"]):
                ends = [m.end() for m in re.finditer(r"[.!?](?:\*\*)?(?=\s|$)", block["text"])]
                text = block["text"][: ends[locator["sentences"] - 1]]
                if text.count("**") % 2:
                    raise ValueError(f"{owner}: quote {locator} cuts through bold text")
                return {"line": block["line"], "text": text}
    raise ValueError(f"{owner}: quote locator no longer matches {locator}")


def output_label(module, path, siblings):
    """Name a saved output from its file; a label never ranks it as accepted or primary."""
    stem = module if path.name == f"{module}.md" else path.name[len(module) + 1 : -3]
    attempt = re.fullmatch(r"(?:(.+)-)?attempt-(\d+)", stem)
    if not attempt:
        repeated = sum(s.name == path.name for s in siblings) > 1
        delivered = repeated and path.parent.parent.name == "deliveries"
        return stem[0].upper() + stem[1:] + (
            f" · delivery {path.parent.name[:8]}" if delivered else ""
        ), None
    prefix = f"{attempt[1]}-" if attempt[1] else ""
    total = sum(bool(re.fullmatch(rf"{module}-{prefix}attempt-\d+\.md", s.name)) for s in siblings)
    counted = f"attempt {attempt[2]} of {total}"
    return (f"{attempt[1].capitalize()} · {counted}" if attempt[1] else counted.capitalize()), int(
        attempt[2]
    )


def default_output(folder, sources, pinned, attempts):
    """Pinned file, else the only file, else the highest attempt; unnumbered variants pick none."""
    if pinned:
        return pinned
    if len(sources) == 1:
        return f"{folder}/{sources[0]}"
    numbered = [(attempts[s], s) for s in sources if attempts[s] is not None]
    return f"{folder}/{max(numbered)[1]}" if numbered else None


def locate_row(sections, locator, owner):
    """Return the retained table cell that states the output's unit, or fail the build."""
    for row in (row for s in sections for b in s["blocks"] for row in b.get("rows", [])):
        if row["cells"][0] == locator["row"]:
            if locator["unit"] not in row["cells"][1]:
                raise ValueError(
                    f"{owner}: basis row {locator['row']} does not state {locator['unit']}"
                )
            return {"line": row["line"], "text": row["cells"][1], "unit": locator["unit"]}
    raise ValueError(f"{owner}: basis locator no longer matches {locator}")


def pinned_fields(sections, config, module):
    """Curated fields of a pinned output; a locator that no longer matches fails the build."""
    fields = {
        "period": config["period"],
        "scope": config["scope"],
        "compare": config.get("compare"),
    }
    if "call" in config:
        fields["call"] = locate_quote(sections, config["call"], module)
    if "basis" in config:
        fields["basis"] = locate_row(sections, config["basis"], module)
    visual = config.get("visual")
    if visual:
        if not any(
            b["type"] == "table" and b["line"] == visual["table"]
            for s in sections
            for b in s["blocks"]
        ):
            raise ValueError(f"{module}: visual table locator no longer matches")
        quote = visual.get("noteQuote")
        fields["visual"] = (
            {**visual, "quote": locate_quote(sections, quote, module)} if quote else visual
        )
    return fields


def _reader_summary(section):
    """The section's values, or None when it does not hold its two tables."""
    tables = [b for b in section["blocks"] if b["type"] == "table"]
    if [t["headers"] for t in tables] != READER_TABLES:
        return None
    calls, findings = (t["rows"] for t in tables)
    if len(calls) != 1 or not findings or any(len(r["cells"]) != 3 for r in calls + findings):
        return None
    bottom_line, confidence, limitation = calls[0]["cells"]
    return {
        "bottomLine": bottom_line,
        "confidence": confidence,
        "limitation": limitation,
        "line": calls[0]["line"],
        "findings": [
            {
                "finding": r["cells"][0],
                "impact": r["cells"][1],
                "confidence": r["cells"][2],
                "line": r["line"],
            }
            for r in findings
        ],
    }


def _chart_table(section):
    """What the app needs to draw the section's table, or None when it is not the fixed shape."""
    tables = [b for b in section["blocks"] if b["type"] == "table"]
    if len(tables) != 1 or not tables[0]["rows"]:
        return None
    table = tables[0]
    headers = table["headers"]
    if len(headers) < 4 or headers[0] != "Period" or headers[-2:] != CHART_LAST_COLUMNS:
        return None
    return {
        "title": section["heading"].removeprefix(CHART_PREFIX).capitalize(),
        "unit": table["rows"][0]["cells"][-2],
        "table": table["line"],
        "columns": list(range(1, len(headers) - 2)),
    }


def reader_fields(sections):
    """A handoff's reader section and chart tables. A malformed one is named; the handoff still reads."""
    summary, charts, problems = None, [], []
    for section in sections:
        heading = section["heading"]
        if heading == "Reader summary":
            summary = _reader_summary(section)
            if summary is None:
                problems.append("Reader summary is not in its two tables")
        elif heading.startswith(CHART_PREFIX):
            chart = _chart_table(section)
            if chart:
                charts.append(chart)
            else:
                problems.append(f"{heading} is not in its fixed table")
    return {"summary": summary, "charts": charts, "issue": "; ".join(problems) or None}


def structured(raw, strict):
    """Typed blocks. In the app a handoff the parser refuses stays readable as one flagged block."""
    try:
        return parse_source(raw.decode("utf-8")), None
    except ValueError as error:
        if strict:
            raise
        text = raw.decode("utf-8", "replace")
        block = {"type": "text", "line": 1, "end": text.count("\n") + 1, "text": text}
        return [{"heading": "Unstructured handoff", "level": 1, "line": 1, "blocks": [block]}], str(
            error
        )


def handoff_files(run_dir):
    """Handoffs at the run root, then those the launcher delivered; a repeated delivery is one file."""
    paths, seen = [], set()
    for path in [*sorted(run_dir.glob("CP-*.md")), *sorted(run_dir.glob("deliveries/*/CP-*.md"))]:
        # The server serves regular files only, so a link out of the run is not a handoff either.
        if (
            # Windows matches these patterns regardless of case; the names here do not.
            HANDOFF_NAME.match(path.name)
            and path.name.endswith(".md")
            and not OUTPUT_SKIP.search(path.name)
            and path.is_file()
            and not path.is_symlink()
            and sha256(path) not in seen
        ):
            seen.add(sha256(path))
            paths.append(path)
    return paths


def collect_runs(root, shown, catalog, link, strict=True):
    """Parse every saved output of every shown run; each file keeps its own identity."""
    runs, outputs, inputs, sources, pins, issues = {}, {}, {}, {}, {}, []
    for key, (folder, issuer, title, label, sector, period) in shown.items():
        run_dir = root / "runs" / folder

        def relative(path, base=run_dir):  # The default binds this run's folder.
            return path.relative_to(base).as_posix()

        grouped = {}
        for path in handoff_files(run_dir):
            kind = "inputs" if INPUT_NAME.search(path.name) else "outputs"
            grouped.setdefault(HANDOFF_NAME.match(path.name)[0], {"outputs": [], "inputs": []})[
                kind
            ].append(path)
            sources.setdefault(sha256(path), []).append(
                {"run": key, "source": f"{folder}/{relative(path)}", "output": kind == "outputs"}
            )
        modules = {}
        first = None
        for module, files in grouped.items():
            config = catalog.get(module, {})
            pinned = None
            labels = {
                relative(f): output_label(module, f, files["outputs"]) for f in files["outputs"]
            }
            for path in files["outputs"]:
                name = relative(path)
                output_id = f"{folder}/{name}"
                digest = sha256(path)
                sections, problem = structured(path.read_bytes(), strict)
                record = {
                    "id": output_id,
                    "run": key,
                    "module": module,
                    "source": name,
                    "file": f"{folder}--{name.replace('/', '--')}",
                    "href": link(folder, name, digest),
                    "label": labels[name][0],
                    "sha256": digest,
                    "case": f"{title} · {label}",
                    "period": period,
                    "scope": "Retained module output",
                    "firstHeading": config.get("firstHeading"),
                    "sections": sections,
                }
                record.update(reader_fields(sections))
                if record["issue"]:
                    issues.append(f"{output_id}: {record['issue']}")
                if problem:
                    record["parseError"] = problem
                    issues.append(f"{output_id}: shown unstructured ({problem})")
                if config.get("path") == output_id:
                    try:
                        record.update(pinned_fields(sections, config, module))
                        pins[module] = pinned = output_id
                        first = first or module
                    except (ValueError, KeyError, IndexError) as error:
                        if strict:
                            raise
                        issues.append(f"{module}: curated pin dropped: {error}")
                outputs[output_id] = record
            for path in files["inputs"]:
                name = relative(path)
                digest = sha256(path)
                inputs[f"{folder}/{name}"] = {
                    "module": module,
                    "run": key,
                    "source": name,
                    "file": f"{folder}--{name.replace('/', '--')}",
                    "href": link(folder, name, digest),
                    "sha256": digest,
                }
            sources_here = [relative(f) for f in files["outputs"]]
            modules[module] = {
                "outputs": [f"{folder}/{s}" for s in sources_here],
                "inputs": [f"{folder}/{relative(f)}" for f in files["inputs"]],
                "default": default_output(
                    folder, sources_here, pinned, {s: labels[s][1] for s in sources_here}
                )
                if sources_here
                else None,
            }
        with_outputs = [module for module in modules if modules[module]["outputs"]]
        recorded = recorded_run(run_dir)
        runs[key] = {
            "folder": folder,
            "issuer": issuer,
            "title": title,
            "run": label,
            "sector": sector,
            "period": period,
            "pathway": recorded.get("pathway") or None,
            "asOf": recorded.get("as_of") or None,
            "first": first or (with_outputs[0] if with_outputs else "W-Overview"),
            "modules": modules,
        }
    return runs, outputs, inputs, sources, pins, issues


def built_from(folder, sources):
    """Each handoff beside a report, traced to the run files holding the same bytes, or named as unmatched."""
    rows = []
    for path in sorted(folder.glob("CP-*.md")):
        digest = sha256(path)
        match = HANDOFF_NAME.match(path.name)
        if not match:
            continue
        module = match[0]
        matches = sources.get(digest) or [{"run": None, "source": path.name, "output": False}]
        rows += [{"module": module, "sha256": digest, **match} for match in matches]
    return rows


def catalogue_reports(root, catalogue, sources):
    """Deliverables the server verified, each once, with what it was built from."""
    reports, seen, issues = [], set(), []
    for run in catalogue["real"]:
        for artifact in run.get("artifacts") or []:
            folder = artifact["folder"]
            name = Path(folder).name
            if not artifact.get("available") or name in seen:
                continue
            seen.add(name)
            # Documented fail-open: reported in Settings; the other deliverables stay readable.
            try:
                delivery = json.loads((root / folder / "delivery.json").read_text(encoding="utf-8"))
                identity = json.loads((root / folder / "view.json").read_text(encoding="utf-8"))[
                    "run"
                ]
                issuer_name, as_of = identity["issuer_name"], identity["as_of"]
            except (OSError, ValueError, KeyError) as error:
                issues.append(f"{folder}: could not be read ({error!r})")
                continue
            curated = name in CURATED_REPORTS
            issuer = "TransDigm Group" if curated else issuer_name
            default = (
                artifact["label"] if artifact["label"] != name else f"{issuer} · as of {as_of}"
            )
            label, status = CURATED_REPORTS.get(
                name, (default, "Superseded" if artifact.get("state") == "superseded" else None)
            )
            reports.append(
                {
                    "id": name,
                    "build": list(CURATED_REPORTS).index(name) + 1 if curated else None,
                    "label": label,
                    "status": status,
                    "issuer": issuer,
                    "sha256": delivery["files"]["report.html"],
                    "scope": delivery.get("scope"),
                    "modelPublished": delivery.get("cp_model_published", False),
                    "href": artifact["href"] + "&embedded=1",
                    "download": artifact["href"] + "&download=1",
                    "files": [
                        {
                            "name": n,
                            "href": f"/files/{quote(f'{folder}/{n}')}?sha256={h}&download=1",
                        }
                        for n, h in sorted(delivery["files"].items())
                    ],
                    "builtFrom": built_from(root / folder, sources),
                }
            )
    return reports, issues


def visual_catalogue():
    with (REPO / "docs/visualisations/catalogue.csv").open(encoding="utf-8-sig") as source:
        return list(csv.DictReader(source))


def recorded_run(run_dir):
    """The text fields of the launcher's own manifest; a run without a readable one records none."""
    try:
        manifest = json.loads((run_dir / "workflow.json").read_text(encoding="utf-8"))
        return {key: value for key, value in manifest["run"].items() if isinstance(value, str)}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {}


def run_row(root, run):
    """Labels for a run with no curated ones: the launcher's own manifest, else the catalogue."""
    folder = run["id"]
    identity = recorded_run(root / "runs" / folder)
    issuer = identity.get("issuer_name") or run["name"]
    period = (
        f"As of {identity['as_of']}"
        if identity.get("as_of")
        else run.get("period") or "Period not recorded"
    )
    # A web run's folder is 32 hex characters; eight are enough to tell runs apart on screen.
    label = folder.upper()[:12] if WEB_RUN.fullmatch(folder) else folder.upper()
    return (folder, issuer, issuer, label, run.get("sector") or "Unclassified", period)


def workspace_store(root, catalogue):
    """Everything the app reads. A curated pin that stopped matching is dropped and reported, not fatal."""
    root = Path(root)
    catalog = json.loads((HERE / "catalog.json").read_text(encoding="utf-8"))
    curated = {row[0]: (key, row) for key, row in CURATED_RUNS.items()}
    shown, issues = {}, list(catalogue.get("issues") or [])
    for run in catalogue["real"]:
        folder = run["id"]
        if folder.startswith("delivery:"):
            continue
        if not SAFE_FOLDER.fullmatch(folder):
            issues.append(f"{folder}: folder name cannot be linked; rename it to show this run")
            continue
        key, row = curated.get(folder) or (folder, run_row(root, run))
        shown[key] = row

    def link(folder, relative, digest):
        return f"/files/{quote(f'runs/{folder}/{relative}')}?sha256={digest}"

    runs, outputs, inputs, sources, pins, found = {}, {}, {}, {}, {}, []
    for key, row in shown.items():
        # Documented fail-open: one run that cannot be read is hidden and reported in Settings.
        try:
            part = collect_runs(root, {key: row}, catalog, link, strict=False)
        except Exception as error:  # noqa: BLE001
            found.append(f"{row[0]}: could not be read ({error!r})")
            continue
        runs |= part[0]
        outputs |= part[1]
        inputs |= part[2]
        for digest, matches in part[3].items():
            sources.setdefault(digest, []).extend(matches)
        pins |= part[4]
        found += part[5]
    reports, unread = catalogue_reports(root, catalogue, sources)
    found += unread
    for module, config in catalog.items():
        compare = config.get("compare")
        if (
            module in pins
            and compare
            and not (
                compare["recheck"] in outputs
                and {compare["prior"], compare["current"], compare["repaired"]}
                <= {r["id"] for r in reports}
            )
        ):
            del pins[module]
            found.append(
                f"{module}: curated pin dropped: a compared deliverable or recheck is missing"
            )
    return {
        "runs": runs,
        "outputs": outputs,
        "inputs": inputs,
        "pins": pins,
        "reports": reports,
        "visuals": visual_catalogue(),
        "issues": issues + found,
    }


if __name__ == "__main__":
    print(json.dumps(workspace_store(Path(sys.argv[1]), json.load(sys.stdin)), ensure_ascii=False))
