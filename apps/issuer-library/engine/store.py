"""The library's store: every retained handoff in a workspace, parsed for reading.

Reads files only. Nothing here runs analysis, calls a provider or changes a workspace.
The server imports this on each page load, so it imports only the standard library.
"""

import csv
import hashlib
import json
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
REPO = HERE if (HERE / "src").is_dir() else HERE.parents[2]
OUTPUT_SKIP = re.compile(r"instructions|prompt|calculations|verification")
INPUT_NAME = re.compile(r"selected-input|peer-inputs|delivery")
HANDOFF_NAME = re.compile(r"CP-[A-Z0-9]+")
AEROSPACE = "Aerospace & defense"
# Reading labels written by hand.
# Route key: (folder under runs/, issuer, title, run label, sector, period).
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
# The curated labels apply to a folder only while its own identity file names the same issuer.
CURATED_ISSUER_IDS = {"TransDigm Group": "TDG", "Ford Otosan": "FROTO"}
CURATED_REPORT_ISSUER = "TransDigm Group"
SAFE_FOLDER = re.compile(r"[\w. -]+")
WEB_RUN = re.compile(r"web-[a-f0-9]{32}")
# What issuer_library.model keeps unescaped in one path segment of a /files link.
SEGMENT_SAFE = "$&+:=@"
# A chart value the app draws as a bar (screen views.js chartNumber), after commas are removed.
CHART_NUMBER = re.compile(r"(?:[-+]?\d+(?:\.\d+)?|\(\d+(?:\.\d+)?\))(?:%|x)?")


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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pinned_url(name: str, digest: str) -> str:
    """A pinned /files link, as issuer_library.model.pinned_url builds it."""
    segments = "/".join(quote(part, safe=SEGMENT_SAFE) for part in name.split("/"))
    return f"/files/{segments}?sha256={digest}"


def names_other_issuer(issuer: str, issuer_id: str, issuer_name: str) -> bool:
    """Whether an identity file names an issuer other than the curated label's.

    The curated issuer id decides when both are known; otherwise the recorded name must be the
    curated name or begin with it ("TransDigm Group Incorporated"). A file naming none agrees.
    """
    known = CURATED_ISSUER_IDS.get(issuer)
    if issuer_id and known:
        return issuer_id.casefold() != known.casefold()
    if not issuer_name:
        return False
    name, curated = issuer_name.casefold(), issuer.casefold()
    return name != curated and not name.startswith(curated + " ")


def locate_quote(
    sections: list[dict[str, Any]], locator: dict[str, Any], owner: str
) -> dict[str, Any]:
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


def output_label(module: str, path: Path, siblings: list[Path]) -> tuple[str, int | None]:
    """Name a saved output from its file; a label never ranks it as accepted or primary."""
    # CP-8b.md has no separator after its code; its stem is still "b", never empty.
    stem = path.stem.removeprefix(module).lstrip("-_. ") or path.stem
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


def default_output(
    folder: str, sources: list[str], pinned: str | None, attempts: dict[str, int | None]
) -> str | None:
    """Pinned file, else the only file, else the highest attempt; unnumbered variants pick none."""
    if pinned:
        return pinned
    if len(sources) == 1:
        return f"{folder}/{sources[0]}"
    numbered = [(number, s) for s in sources if (number := attempts[s]) is not None]
    return f"{folder}/{max(numbered)[1]}" if numbered else None


def locate_row(
    sections: list[dict[str, Any]], locator: dict[str, Any], owner: str
) -> dict[str, Any]:
    """Return the retained table cell that states the output's unit, or fail the build."""
    for row in (row for s in sections for b in s["blocks"] for row in b.get("rows", [])):
        if row["cells"][0] == locator["row"]:
            if locator["unit"] not in row["cells"][1]:
                raise ValueError(
                    f"{owner}: basis row {locator['row']} does not state {locator['unit']}"
                )
            return {"line": row["line"], "text": row["cells"][1], "unit": locator["unit"]}
    raise ValueError(f"{owner}: basis locator no longer matches {locator}")


def pinned_fields(
    sections: list[dict[str, Any]], config: dict[str, Any], module: str
) -> dict[str, Any]:
    """Curated fields of a pinned output; a locator that no longer matches fails the build."""
    fields: dict[str, Any] = {
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


def _reader_summary(section: dict[str, Any]) -> dict[str, Any] | None:
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


def chart_number(cell: str) -> bool:
    return bool(CHART_NUMBER.fullmatch(re.sub(r"\*\*|`", "", cell).strip().replace(",", "")))


def _chart_unit(rows: list[dict[str, Any]], columns: list[int]) -> str | None:
    """The one Reporting unit of the rows holding a drawn number; None when they differ or none do.

    A 'Not supplied' row names the unit of a value that is absent, not of the bars drawn.
    """
    units = {
        row["cells"][-2] for row in rows if any(chart_number(row["cells"][c]) for c in columns)
    }
    return units.pop() if len(units) == 1 else None


def _chart_table(section: dict[str, Any]) -> dict[str, Any] | None:
    """What the app needs to draw the section's table, or None when it is not the fixed shape."""
    tables = [b for b in section["blocks"] if b["type"] == "table"]
    if len(tables) != 1 or not tables[0]["rows"]:
        return None
    table = tables[0]
    headers = table["headers"]
    if len(headers) < 4 or headers[0] != "Period" or headers[-2:] != CHART_LAST_COLUMNS:
        return None
    columns = list(range(1, len(headers) - 2))
    return {
        "title": section["heading"].removeprefix(CHART_PREFIX).capitalize(),
        "unit": _chart_unit(table["rows"], columns),
        "table": table["line"],
        "columns": columns,
    }


def reader_fields(sections: list[dict[str, Any]]) -> dict[str, Any]:
    """A handoff's reader section and chart tables; a malformed one is named, the handoff reads."""
    summary: dict[str, Any] | None = None
    charts: list[dict[str, Any]] = []
    problems: list[str] = []
    for section in sections:
        heading = section["heading"]
        if heading == "Reader summary":
            summary = _reader_summary(section)
            if summary is None:
                problems.append("Reader summary is not in its two tables")
        elif heading.startswith(CHART_PREFIX):
            chart = _chart_table(section)
            if chart is None:
                problems.append(f"{heading} is not in its fixed table")
            elif chart["unit"] is None:
                problems.append(f"{heading} has a mixed or missing reporting unit for its numbers")
            else:
                charts.append(chart)
    return {"summary": summary, "charts": charts, "issue": "; ".join(problems) or None}


def structured(raw: bytes, strict: bool) -> tuple[list[dict[str, Any]], str | None]:
    """Typed blocks. In the app a handoff the parser refuses stays readable as one flagged block."""
    try:
        sections: list[dict[str, Any]] = parse_source(raw.decode("utf-8"))  # type: ignore[no-untyped-call]
        return sections, None
    except ValueError as error:
        if strict:
            raise
        text = raw.decode("utf-8", "replace")
        block = {"type": "text", "line": 1, "end": text.count("\n") + 1, "text": text}
        return [{"heading": "Unstructured handoff", "level": 1, "line": 1, "blocks": [block]}], str(
            error
        )


def is_handoff(path: Path) -> bool:
    # Windows matches the glob patterns regardless of case; the names here do not.
    # The server serves regular files only, so a link out of the run is not a handoff either.
    return bool(
        HANDOFF_NAME.match(path.name)
        and path.name.endswith(".md")
        and not OUTPUT_SKIP.search(path.name)
        and path.is_file()
        and not path.is_symlink()
    )


def module_of(path: Path) -> str:
    match = HANDOFF_NAME.match(path.name)
    if match is None:
        raise ValueError(f"not a handoff name: {path.name}")
    return match[0]


def handoff_files(run_dir: Path) -> list[tuple[Path, str]]:
    """Handoffs at the run root, then those the launcher delivered, each with its SHA-256.

    Every root handoff is its own output, whatever its bytes. A delivered copy is dropped when the
    same module's bytes are already listed: a repeated delivery is one file.
    """
    found: list[tuple[Path, str]] = []
    seen: set[tuple[str, str]] = set()
    for path in [*sorted(run_dir.glob("CP-*.md")), *sorted(run_dir.glob("deliveries/*/CP-*.md"))]:
        if not is_handoff(path):
            continue
        digest = sha256(path)
        key = (module_of(path), digest)
        if path.parent != run_dir and key in seen:
            continue
        seen.add(key)
        found.append((path, digest))
    return found


Handoffs = dict[str, dict[str, list[tuple[Path, str]]]]


def group_handoffs(files: list[tuple[Path, str]]) -> Handoffs:
    grouped: Handoffs = {}
    for path, digest in files:
        kind = "inputs" if INPUT_NAME.search(path.name) else "outputs"
        grouped.setdefault(module_of(path), {"outputs": [], "inputs": []})[kind].append(
            (path, digest)
        )
    return grouped


Link = Callable[[str, str, str], str]


@dataclass(frozen=True)
class RunScope:
    """One shown run while its files are collected."""

    key: str
    folder: str
    run_dir: Path
    case: str
    period: str
    link: Link
    strict: bool

    def relative(self, path: Path) -> str:
        return path.relative_to(self.run_dir).as_posix()

    def file_name(self, name: str) -> str:
        return f"{self.folder}--{name.replace('/', '--')}"


@dataclass
class Collected:
    runs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    inputs: dict[str, Any] = field(default_factory=dict)
    sources: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    pins: dict[str, str] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)


def output_record(
    scope: RunScope, module: str, path: Path, digest: str, label: str
) -> dict[str, Any]:
    name = scope.relative(path)
    sections, problem = structured(path.read_bytes(), scope.strict)
    record: dict[str, Any] = {
        "id": f"{scope.folder}/{name}",
        "run": scope.key,
        "module": module,
        "source": name,
        "file": scope.file_name(name),
        "href": scope.link(scope.folder, name, digest),
        "label": label,
        "sha256": digest,
        "case": scope.case,
        "period": scope.period,
        "scope": "Retained module output",
        "firstHeading": None,
        "sections": sections,
    }
    record.update(reader_fields(sections))
    if problem:
        record["parseError"] = problem
    return record


def pin_output(record: dict[str, Any], config: dict[str, Any], strict: bool) -> str | None:
    """Apply a curated pin's fields. A locator that stopped matching fails a strict build;
    in the app it drops the pin, and the returned issue says why."""
    module = record["module"]
    try:
        record.update(pinned_fields(record["sections"], config, module))
    except (ValueError, KeyError, IndexError) as error:
        if strict:
            raise
        return f"{module}: curated pin dropped: {error}"
    return None


def collect_module(
    scope: RunScope,
    module: str,
    files: dict[str, list[tuple[Path, str]]],
    found: Collected,
    config: dict[str, Any],
) -> tuple[dict[str, Any], str | None]:
    """The module's outputs and inputs recorded in found; its entry, and its pinned output."""
    paths = [path for path, _ in files["outputs"]]
    labels = {scope.relative(path): output_label(module, path, paths) for path in paths}
    pinned = None
    for path, digest in files["outputs"]:
        record = output_record(scope, module, path, digest, labels[scope.relative(path)][0])
        record["firstHeading"] = config.get("firstHeading")
        output_id = record["id"]
        if record["issue"]:
            found.issues.append(f"{output_id}: {record['issue']}")
        if "parseError" in record:
            found.issues.append(f"{output_id}: shown unstructured ({record['parseError']})")
        if config.get("path") == output_id:
            if dropped := pin_output(record, config, scope.strict):
                found.issues.append(dropped)
            else:
                found.pins[module] = pinned = output_id
        found.outputs[output_id] = record
    for path, digest in files["inputs"]:
        name = scope.relative(path)
        found.inputs[f"{scope.folder}/{name}"] = {
            "module": module,
            "run": scope.key,
            "source": name,
            "file": scope.file_name(name),
            "href": scope.link(scope.folder, name, digest),
            "sha256": digest,
        }
    names = [scope.relative(path) for path in paths]
    entry = {
        "outputs": [f"{scope.folder}/{name}" for name in names],
        "inputs": [f"{scope.folder}/{scope.relative(path)}" for path, _ in files["inputs"]],
        "default": default_output(
            scope.folder, names, pinned, {name: labels[name][1] for name in names}
        )
        if names
        else None,
    }
    return entry, pinned


def collect_runs(
    root: Path,
    shown: dict[str, tuple[str, str, str, str, str, str]],
    catalog: dict[str, Any],
    link: Link,
    strict: bool = True,
) -> tuple[Any, ...]:
    """Parse every saved output of every shown run; each file keeps its own identity."""
    found = Collected()
    for key, (folder, issuer, title, label, sector, period) in shown.items():
        run_dir = root / "runs" / folder
        scope = RunScope(key, folder, run_dir, f"{title} · {label}", period, link, strict)
        files = handoff_files(run_dir)
        for path, digest in files:
            found.sources.setdefault(digest, []).append(
                {
                    "run": key,
                    "source": f"{folder}/{scope.relative(path)}",
                    "output": not INPUT_NAME.search(path.name),
                }
            )
        modules, first = {}, None
        for module, grouped in group_handoffs(files).items():
            modules[module], pinned = collect_module(
                scope, module, grouped, found, catalog.get(module, {})
            )
            first = first or (module if pinned else None)
        with_outputs = [module for module in modules if modules[module]["outputs"]]
        recorded = recorded_run(run_dir)
        found.runs[key] = {
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
    return (found.runs, found.outputs, found.inputs, found.sources, found.pins, found.issues)


def built_from(folder: Path, sources: dict[str, Any]) -> list[dict[str, Any]]:
    """Each handoff beside a report, traced to the run files holding the same bytes, or unmatched."""
    rows: list[dict[str, Any]] = []
    for path in sorted(folder.glob("CP-*.md")):
        digest = sha256(path)
        match = HANDOFF_NAME.match(path.name)
        if not match:
            continue
        module = match[0]
        matches = sources.get(digest) or [{"run": None, "source": path.name, "output": False}]
        rows += [{"module": module, "sha256": digest, **match} for match in matches]
    return rows


def curated_report(folder: str, identity: dict[str, Any]) -> tuple[bool, str]:
    """Whether a delivery takes its curated build label, and the issue when its view.json
    names another issuer. Only the curated deliverables/ folder of that name qualifies."""
    name = Path(folder).name
    if name not in CURATED_REPORTS or folder != f"deliverables/{name}":
        return False, ""
    issuer_id, issuer_name = identity.get("issuer_id") or "", identity.get("issuer_name") or ""
    if names_other_issuer(CURATED_REPORT_ISSUER, issuer_id, issuer_name):
        named = issuer_name or issuer_id
        return False, f"{folder}: curated label not applied; its view.json names {named}"
    return True, ""


def report_record(
    root: Path, artifact: dict[str, Any], report_id: str, sources: dict[str, Any]
) -> tuple[dict[str, Any], str]:
    """One verified delivery as the app lists it, and an issue to report; raises when unreadable."""
    folder = artifact["folder"]
    delivery = json.loads((root / folder / "delivery.json").read_text(encoding="utf-8"))
    identity = json.loads((root / folder / "view.json").read_text(encoding="utf-8"))["run"]
    issuer_name, as_of = identity["issuer_name"], identity["as_of"]
    files: dict[str, str] = delivery["files"]
    name = Path(folder).name
    curated, issue = curated_report(folder, identity)
    issuer = CURATED_REPORT_ISSUER if curated else issuer_name
    default = artifact["label"] if artifact["label"] != name else f"{issuer} · as of {as_of}"
    label, status = (
        CURATED_REPORTS[name]
        if curated
        else (default, "Superseded" if artifact.get("state") == "superseded" else None)
    )
    return {
        "id": report_id,
        "build": list(CURATED_REPORTS).index(name) + 1 if curated else None,
        "label": label,
        "status": status,
        "issuer": issuer,
        "sha256": files["report.html"],
        "scope": delivery.get("scope"),
        "modelPublished": delivery.get("cp_model_published", False),
        "href": artifact["href"] + "&embedded=1",
        "download": artifact["href"] + "&download=1",
        "files": [
            {"name": n, "href": pinned_url(f"{folder}/{n}", h) + "&download=1"}
            for n, h in sorted(files.items())
        ],
        "builtFrom": built_from(root / folder, sources),
    }, issue


def catalogue_reports(
    root: Path, catalogue: dict[str, Any], sources: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[str]]:
    """Deliverables the server verified, each folder once, with what it was built from.

    A report's id is its folder's name; a second folder of the same name is told apart by its path.
    """
    reports: list[dict[str, Any]] = []
    seen: set[str] = set()
    issues: list[str] = []
    for run in catalogue["real"]:
        for artifact in run.get("artifacts") or []:
            folder = artifact["folder"]
            if not artifact.get("available") or folder in seen:
                continue
            seen.add(folder)
            taken = {report["id"] for report in reports}
            name = Path(folder).name
            report_id = name if name not in taken else folder.replace("/", "--")
            # Documented fail-open: reported in Settings; the other deliverables stay readable.
            try:
                report, issue = report_record(root, artifact, report_id, sources)
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
                issues.append(f"{folder}: could not be read ({error!r})")
                continue
            reports.append(report)
            if issue:
                issues.append(issue)
    return reports, issues


def visual_catalogue() -> list[dict[str, str]]:
    with (REPO / "docs/visualisations/catalogue.csv").open(encoding="utf-8-sig") as source:
        return list(csv.DictReader(source))


def recorded_run(run_dir: Path) -> dict[str, str]:
    """The text fields of the launcher's own manifest; a run without a readable one records none."""
    try:
        manifest = json.loads((run_dir / "workflow.json").read_text(encoding="utf-8"))
        return {key: value for key, value in manifest["run"].items() if isinstance(value, str)}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {}


def run_row(root: Path, run: dict[str, Any]) -> tuple[str, str, str, str, str, str]:
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


def curated_conflict(root: Path, run: dict[str, Any], issuer: str) -> str:
    """What names another issuer for a run folder that has a curated label, or blank."""
    recorded = recorded_run(root / "runs" / run["id"])
    named = recorded.get("issuer_name", "")
    if names_other_issuer(issuer, recorded.get("issuer_id", ""), named):
        return f"its workflow.json names {named or recorded.get('issuer_id')}"
    admitted, name = run.get("issuer") or "", run.get("name") or ""
    if admitted and admitted != "Unclassified" and names_other_issuer(issuer, admitted, name):
        return f"the library admitted it as {name or admitted}"
    return ""


Row = tuple[str, str, str, str, str, str]


def route_taken(hidden: str, curated: str) -> str:
    return (
        f"{hidden}: not shown; its folder name is the route of the curated run {curated}; "
        "rename the folder to show this run"
    )


def shown_runs(root: Path, catalogue: dict[str, Any], issues: list[str]) -> dict[str, Row]:
    """Each run's route key and labels: curated ones while the folder agrees, else its own."""
    curated = {row[0]: (key, row) for key, row in CURATED_RUNS.items()}
    shown: dict[str, Row] = {}
    for run in catalogue["real"]:
        folder = run["id"]
        if folder.startswith("delivery:"):
            continue
        if not SAFE_FOLDER.fullmatch(folder):
            issues.append(f"{folder}: folder name cannot be linked; rename it to show this run")
            continue
        key, row = curated.get(folder) or (folder, run_row(root, run))
        if folder in curated and (conflict := curated_conflict(root, run, row[1])):
            issues.append(f"{folder}: curated {row[1]} labels not applied; {conflict}")
            key, row = folder, run_row(root, run)
        if key in shown:
            # Only a curated route can equal another folder's name; the curated run keeps it.
            if key == folder:
                issues.append(route_taken(folder, shown[key][0]))
                continue
            issues.append(route_taken(shown[key][0], folder))
        shown[key] = row
    return shown


def workspace_store(root: Path | str, catalogue: dict[str, Any]) -> dict[str, Any]:
    """Everything the app reads; a curated pin that stopped matching is dropped and reported."""
    root = Path(root)
    catalog = json.loads((HERE / "catalog.json").read_text(encoding="utf-8"))
    issues = list(catalogue.get("issues") or [])
    shown = shown_runs(root, catalogue, issues)

    def link(folder: str, relative: str, digest: str) -> str:
        return pinned_url(f"runs/{folder}/{relative}", digest)

    runs: dict[str, Any] = {}
    outputs: dict[str, Any] = {}
    inputs: dict[str, Any] = {}
    sources: dict[str, list[dict[str, Any]]] = {}
    pins: dict[str, str] = {}
    found: list[str] = []
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
