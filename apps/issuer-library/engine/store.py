"""The library's store: every retained handoff in a workspace, parsed for reading.

Reads files only. Nothing here runs analysis, calls a provider or changes a workspace.
The server imports this on each page load, so it imports only the standard library.
"""

import csv
import datetime
import decimal
import hashlib
import json
import os
import re
import stat
import sys
from collections import Counter
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path, PurePosixPath
from typing import Any, NamedTuple, NotRequired, TypedDict
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
REPO = HERE if (HERE / "src").is_dir() else HERE.parents[2]
OUTPUT_SKIP = re.compile(r"instructions|prompt|calculations|verification")
INPUT_NAME = re.compile(r"selected-input|peer-inputs|delivery|-request\.md")
HANDOFF_NAME = re.compile(r"CP-[A-Z0-9]+")
OUTPUT_SEPARATORS = ("-", "_", ".", " ")
AEROSPACE = "Aerospace & defense"
# Reading labels written by hand. Route key: (folder under runs/, issuer, title, run label, sector, period).
CURATED_RUNS: dict[str, tuple[str, ...]] = {
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
    "tdg-fy2024-snapshot-7": ("Repairs from the deliverable comparison", "Latest build"),
}
SAFE_FOLDER = re.compile(r"[\w. -]+")
MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)


def display_date(iso: Any) -> Any:
    """`31 December 2024` for a valid YYYY-MM-DD calendar date; any other text unchanged."""
    if not isinstance(iso, str) or not ISO_DATE.fullmatch(iso):
        return iso
    try:
        day = datetime.date.fromisoformat(iso)
    except ValueError:
        return iso
    return f"{day.day} {MONTHS[day.month - 1]} {day.year}"


WEB_RUN = re.compile(r"web-[a-f0-9]{32}")


READER_TABLES = [
    ["Bottom line", "Confidence", "Main limitation"],
    ["Finding", "Creditor impact", "Confidence"],
]
CHART_PREFIX = "Chart data: "
CHART_LAST_COLUMNS = ["Reporting unit", "Basis and limitation"]


def physical_lines(text: str) -> list[str]:
    """The text's lines split on newlines only (`\\r\\n` and a lone `\\r` count as one), as
    delivery's `physical_lines` does, so a "line N" citation is the line a reader opens."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if not lines[-1]:
        lines.pop()
    return lines


EQUITY_HEADERS = [
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


def equity_block(lines: list[str], i: int) -> tuple[dict[str, Any], int]:
    """The retained equity statement at `lines[i]` (the ```text fence): a delimited
    transcription, not prose. Its explicitly supplied column order governs this table."""
    start = i + 1
    rows = []
    i += 1
    while i < len(lines) and lines[i] != "```":
        label, values = lines[i].split(":", 1)
        row = [label] + [c.strip() for c in values.split("|")]
        if len(row) != len(EQUITY_HEADERS):
            raise ValueError(f"Malformed equity transcription at {i + 1}")
        rows.append({"line": i + 1, "cells": row})
        i += 1
    if i == len(lines):
        raise ValueError("Unclosed equity transcription")
    block = {
        "type": "table",
        "line": start,
        "headers": list(EQUITY_HEADERS),
        "rows": rows,
        "financial": True,
    }
    return block, i + 1


def source_table_cells(value: str) -> list[str]:
    return [c.strip() for c in re.split(r"(?<!\\)\|", value.strip().strip("|"))]


def table_block(lines: list[str], i: int) -> tuple[dict[str, Any], int]:
    """The pipe table whose header is `lines[i]`; the separator row follows it."""
    start = i + 1
    headers = source_table_cells(lines[i])
    i += 2
    rows = []
    while i < len(lines) and lines[i].startswith("|"):
        row = source_table_cells(lines[i])
        if len(row) != len(headers):
            raise ValueError(f"Malformed table at line {i + 1}")
        rows.append({"line": i + 1, "cells": row})
        i += 1
    return {"type": "table", "line": start, "headers": headers, "rows": rows}, i


def text_block(lines: list[str], i: int) -> tuple[dict[str, Any], int]:
    """The paragraph starting at `lines[i]`, up to a blank line or the next structure."""
    start = i + 1
    parts = [lines[i]]
    i += 1
    while (
        i < len(lines)
        and lines[i].strip()
        and not lines[i].startswith(("#", "|", "- ", "<!-- table-id:"))
        and not re.match(r"\d+\. ", lines[i])
    ):
        parts.append(lines[i])
        i += 1
    return {"type": "text", "line": start, "end": i, "text": "\n".join(parts)}, i


def parse_source(text: str) -> list[dict[str, Any]]:
    """Keep every nonblank body line in one typed block with its source locator."""
    lines = physical_lines(text)
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    i = 0
    while i < len(lines):
        line = lines[i]
        heading = re.match(r"^(#{1,4}) (.+)$", line)
        if heading:
            current = {"heading": heading[2], "level": len(heading[1]), "line": i + 1, "blocks": []}
            sections.append(current)
            i += 1
        elif not line.strip() or re.fullmatch(r"<!-- table-id: [\w.-]+ -->", line):
            # Blank, or a transport identifier preserved in the downloadable original.
            i += 1
        elif current is None:
            raise ValueError("Body before first heading")
        else:
            if line == "```text" and current["heading"].startswith("T4.4 —"):
                block, i = equity_block(lines, i)
            elif (
                line.startswith("|")
                and i + 1 < len(lines)
                and re.fullmatch(r"\|[\s:|\-]+\|", lines[i + 1])
            ):
                block, i = table_block(lines, i)
            else:
                block, i = text_block(lines, i)
            current["blocks"].append(block)
    return sections


# The one size limit for a delivered or uploaded file in this language. The Go server states the
# same 64 MiB as `maxFileBytes` (model.go); change the two together.
MODEL_FILE_LIMIT = 64 * 1024 * 1024
CHUNK = 1024 * 1024


class UnreadableFile(OSError):
    """A path that is not a plain, bounded file: absent is OSError; this is everything else."""


def regular_chunks(
    path: str | Path, follow: bool = True, limit: int = MODEL_FILE_LIMIT
) -> Iterator[bytes]:
    """The bytes of a regular file of at most `limit` bytes, in chunks.

    The kind and size are read from the open descriptor, so a path swapped for a FIFO after a
    check is still refused; the open never blocks on a FIFO.
    """
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0)
    if not follow:
        flags |= getattr(os, "O_NOFOLLOW", 0)
        if Path(path).is_symlink():
            raise UnreadableFile("a link")
    try:
        descriptor = os.open(path, flags)
    except ValueError as error:  # An embedded NUL.
        raise UnreadableFile("an invalid path") from error
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise UnreadableFile("not a regular file")
        if info.st_size > limit:
            raise UnreadableFile("over the size limit")
        handle = os.fdopen(descriptor, "rb")
    except BaseException:
        os.close(descriptor)
        raise
    with handle:
        total = 0
        while chunk := handle.read(CHUNK):
            total += len(chunk)
            if total > limit:
                raise UnreadableFile("over the size limit")
            yield chunk


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    for chunk in regular_chunks(path):
        digest.update(chunk)
    return digest.hexdigest()


def listed_bytes(folder: Path, delivery: dict[str, Any], name: str) -> bytes | None:
    """The bytes of folder/name when a plain file (no link) with the sha256 delivery.json lists."""
    try:
        data = b"".join(regular_chunks(folder / name, follow=False))
    except (OSError, UnreadableFile):
        return None
    return data if hashlib.sha256(data).hexdigest() == delivery["files"][name] else None


def describe(error: BaseException) -> str:
    """An error as its type and a short reason; never the repr, which can hold file bytes."""
    if isinstance(error, UnicodeDecodeError):
        return f"UnicodeDecodeError: {error.reason}"
    return f"{type(error).__name__}: {str(error)[:80]}"


def delivery_json(folder: Path) -> dict[str, Any]:
    """folder/delivery.json read bounded and without following a link; raises when unreadable."""
    loaded: dict[str, Any] = json.loads(
        b"".join(regular_chunks(folder / "delivery.json", follow=False)).decode("utf-8")
    )
    return loaded


def listed_view(folder: Path, delivery: dict[str, Any]) -> dict[str, Any]:
    """folder/view.json when a plain file with the hash delivery.json lists; raises otherwise."""
    if not isinstance(delivery.get("files"), dict):
        raise TypeError("files is not an object")
    raw = listed_bytes(folder, delivery, "view.json")
    if raw is None:
        raise UnreadableFile("view.json is not the plain file its delivery record lists")
    view: dict[str, Any] = json.loads(raw.decode("utf-8"))
    return view


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


def output_label(module: str, path: Path, siblings: list[Path]) -> tuple[str, int | None]:
    """Name a saved output from its file; a label never ranks it as accepted or primary."""
    rest = path.name.removeprefix(module).removesuffix(".md")
    # At most one separator follows the module code; a name with nothing else is its own label.
    stem = (rest[1:] if rest[:1] in OUTPUT_SEPARATORS else rest) or (path.name if rest else module)
    attempt = re.fullmatch(r"(?:(.+)-)?attempt-(\d+)", stem)
    if not attempt:
        repeated = sum(s.name == path.name for s in siblings) > 1
        delivered = repeated and path.parent.parent.name == "deliveries"
        return stem[0].upper() + stem[1:] + (
            f" · delivery {path.parent.name[:8]}" if delivered else ""
        ), None
    # Siblings in the same series share the file name up to "attempt-", taken literally.
    head = re.escape(path.name.removesuffix(f"attempt-{attempt[2]}.md"))
    total = sum(bool(re.fullmatch(rf"{head}attempt-\d+\.md", s.name)) for s in siblings)
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


def sections_of(text: str) -> list[dict[str, Any]]:
    """parse_source, typed as a list of section dicts."""
    sections: list[dict[str, Any]] = parse_source(text)
    return sections


def structured(raw: bytes, strict: bool) -> tuple[list[dict[str, Any]], str | None]:
    """Typed blocks. In the app a handoff the parser refuses stays readable as one flagged block.

    A UTF-8 byte-order mark, which Windows editors often write, is not part of the first heading.
    """
    try:
        return sections_of(raw.decode("utf-8-sig")), None
    except ValueError as error:
        if strict:
            raise
        text = raw.decode("utf-8-sig", "replace")
        block = {"type": "text", "line": 1, "end": text.count("\n") + 1, "text": text}
        return [{"heading": "Unstructured handoff", "level": 1, "line": 1, "blocks": [block]}], str(
            error
        )


def linked(folder: Path) -> bool:
    """A symbolic link or Windows junction: either can lead a folder out of its run."""
    return folder.is_symlink() or folder.is_junction()


class Handoff(NamedTuple):
    """One handoff file as read once: the parsed text and every hash shown come from these bytes."""

    module: str
    raw: bytes
    sha256: str


def handoff_files(run_dir: Path) -> dict[Path, Handoff]:
    """Handoffs at the run root, then those the launcher delivered; each distinct file once."""
    found: dict[Path, Handoff] = {}
    seen: set[str] = set()
    base = run_dir.resolve()
    for path in [*sorted(run_dir.glob("CP-*.md")), *sorted(run_dir.glob("deliveries/*/CP-*.md"))]:
        # The server serves regular files only, so a link out of the run is not a handoff either:
        # not a linked file, not a linked or junctioned delivery folder, nothing resolving outside.
        if (
            # Windows matches these patterns regardless of case; the names here do not.
            (match := HANDOFF_NAME.match(path.name))
            and path.name.endswith(".md")
            and not OUTPUT_SKIP.search(path.name)
            and path.is_file()
            and not path.is_symlink()
            and (path.parent == run_dir or not linked(path.parent))
            and path.resolve().is_relative_to(base)
        ):
            # Bounded: a handoff over the server's read cap raises; the run is hidden and reported.
            raw = b"".join(regular_chunks(path))
            digest = hashlib.sha256(raw).hexdigest()
            if digest not in seen:
                seen.add(digest)
                found[path] = Handoff(match[0], raw, digest)
    return found


class Handoffs:
    """Each distinct handoff parsed once, by digest, however many runs hold the same bytes."""

    def __init__(self, strict: bool) -> None:
        self.strict = strict
        self.parsed: dict[str, tuple[list[dict[str, Any]], str | None]] = {}

    def read(self, digest: str, raw: bytes) -> tuple[list[dict[str, Any]], str | None]:
        """The sections and parse problem of these bytes; the problem is each output's to report."""
        if digest not in self.parsed:
            self.parsed[digest] = structured(raw, self.strict)
        return self.parsed[digest]


def collect_runs(
    root: Path,
    shown: dict[str, tuple[str, ...]],
    catalog: dict[str, Any],
    link: Callable[[str, str, str], str],
    handoffs: Handoffs,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, list[dict[str, Any]]],
    dict[str, str],
    list[str],
]:
    """Parse every saved output of every shown run; each file keeps its own identity.

    The parsed sections are not in the records: they stay in `handoffs` by digest, so a handoff
    saved in many runs is parsed once and held once. A caller that sends the records sends
    `handoffs.parsed` beside them. Pass one `Handoffs` across calls to share it.
    """
    strict = handoffs.strict
    runs: dict[str, Any] = {}
    outputs: dict[str, Any] = {}
    inputs: dict[str, Any] = {}
    sources: dict[str, list[dict[str, Any]]] = {}
    pins: dict[str, str] = {}
    issues: list[str] = []
    for key, (folder, issuer, title, label, sector, period) in shown.items():
        run_dir = root / "runs" / folder

        # The default binds this run's folder.
        def relative(path: Path, base: Path = run_dir) -> str:
            return path.relative_to(base).as_posix()

        grouped: dict[str, dict[str, list[Path]]] = {}
        read = handoff_files(run_dir)
        for path, handoff in read.items():
            kind = "inputs" if INPUT_NAME.search(path.name) else "outputs"
            grouped.setdefault(handoff.module, {"outputs": [], "inputs": []})[kind].append(path)
            sources.setdefault(handoff.sha256, []).append(
                {"run": key, "source": f"{folder}/{relative(path)}", "output": kind == "outputs"}
            )
        modules: dict[str, Any] = {}
        first: str | None = None
        for module, files in grouped.items():
            config = catalog.get(module, {})
            pinned: str | None = None
            labels = {
                relative(f): output_label(module, f, files["outputs"]) for f in files["outputs"]
            }
            for path in files["outputs"]:
                name = relative(path)
                output_id = f"{folder}/{name}"
                digest = read[path].sha256
                sections, problem = handoffs.read(digest, read[path].raw)
                record: dict[str, Any] = {
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
                }
                record.update(reader_fields(sections))  # type: ignore[no-untyped-call]  # legacy untyped parser
                if record["issue"]:
                    issues.append(f"{output_id}: {record['issue']}")
                if problem:
                    record["parseError"] = problem
                    issues.append(f"{output_id}: shown unstructured ({problem})")
                if config.get("path") == output_id:
                    try:
                        record.update(pinned_fields(sections, config, module))  # type: ignore[no-untyped-call]  # legacy untyped parser
                        pins[module] = pinned = output_id
                        first = first or module
                    except (ValueError, KeyError, IndexError) as error:
                        if strict:
                            raise
                        issues.append(f"{module}: curated pin dropped: {error}")
                outputs[output_id] = record
            for path in files["inputs"]:
                name = relative(path)
                digest = read[path].sha256
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
                "default": default_output(  # type: ignore[no-untyped-call]  # legacy untyped helper
                    folder, sources_here, pinned, {s: labels[s][1] for s in sources_here}
                )
                if sources_here
                else None,
            }
        with_outputs = [module for module in modules if modules[module]["outputs"]]
        recorded = recorded_run(run_dir, issues)
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


def built_from(
    files: dict[str, str], sources: dict[str, list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    """Each handoff the verified delivery lists, traced to the run files holding the same bytes.

    The names and hashes are delivery.json's, which the server verified; a handoff-looking file
    beside the report that the delivery does not list was not verified and is not "built from".
    """
    rows = []
    for name, digest in sorted(files.items()):
        match = HANDOFF_NAME.match(name)
        if not match or not name.endswith(".md"):
            continue
        matches = sources.get(digest) or [{"run": None, "source": name, "output": False}]
        rows += [{"module": match[0], "sha256": digest, **found} for found in matches]
    return rows


def report_record(
    root: Path,
    folder: str,
    artifact: dict[str, Any],
    sources: dict[str, list[dict[str, Any]]],
    keys: dict[str, str],
) -> dict[str, Any]:
    """One verified deliverable as the app shows it; raises when its delivery cannot be read."""
    name = Path(folder).name
    delivery = delivery_json(root / folder)
    view = listed_view(root / folder, delivery)
    identity = view["run"]
    issuer_name, as_of = identity["issuer_name"], identity["as_of"]
    issuer_key = report_issuer_key(keys, identity.get("issuer_id"))
    files = {str(n): str(h) for n, h in delivery["files"].items()}
    mode, qualification = view.get("mode"), view.get("analytical_qualification")
    # The hand-written labels describe the TransDigm builds under deliverables/; a folder of that
    # name elsewhere or for another issuer keeps the issuer its own view.json records.
    curated = (
        folder == f"deliverables/{name}"
        and name in CURATED_REPORTS
        and str(issuer_name).startswith("TransDigm Group")
    )
    issuer = "TransDigm Group" if curated else issuer_name
    if curated:
        label, status = CURATED_REPORTS[name]
    else:
        label = (
            artifact["label"]
            if artifact["label"] != name
            else f"{issuer} · as of {display_date(as_of)}"
        )
        status = "Superseded" if artifact.get("state") == "superseded" else None
    return {
        "id": name,
        "build": list(CURATED_REPORTS).index(name) + 1 if curated else None,
        "label": label,
        "status": status,
        "mode": mode if isinstance(mode, str) else None,
        "qualification": qualification if isinstance(qualification, str) else None,
        "issuer": issuer,
        "issuerKey": issuer_key,
        "sha256": files["report.html"],
        "scope": delivery.get("scope"),
        "modelPublished": delivery.get("cp_model_published", False),
        "href": artifact["href"] + "&embedded=1",
        "download": artifact["href"] + "&download=1",
        "files": [
            {"name": n, "href": f"/files/{quote(f'{folder}/{n}')}?sha256={h}&download=1"}
            for n, h in sorted(files.items())
        ],
        "builtFrom": built_from(files, sources),
    }


def catalogue_reports(
    root: Path,
    catalogue: dict[str, Any],
    sources: dict[str, list[dict[str, Any]]],
    keys: dict[str, str],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Deliverables the server verified, each once, with what it was built from.

    `keys` maps issuer IDs to group keys.
    """
    reports, seen, issues = [], set(), []
    for run in catalogue["real"]:
        for artifact in run.get("artifacts") or []:
            folder = artifact["folder"]
            name = Path(folder).name
            if (
                not artifact.get("available")
                or artifact.get("kind", "report") != "report"
                or name in seen
            ):
                continue
            seen.add(name)
            # Documented fail-open: reported in Settings; the other deliverables stay readable.
            try:
                reports.append(report_record(root, folder, artifact, sources, keys))
            except (
                OSError,
                ValueError,
                KeyError,
                TypeError,
                AttributeError,
                RecursionError,
                MemoryError,
            ) as error:
                issues.append(f"{folder}: could not be read ({describe(error)})")
    return reports, issues


def register_of(sections: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The section whose heading names an assumption register: heading, intro, table rows."""
    for section in sections:
        if "assumption register" not in section["heading"].casefold():
            continue
        text = next((b["text"] for b in section["blocks"] if b["type"] == "text"), None)
        table = next((b for b in section["blocks"] if b["type"] == "table"), None)
        return {
            "heading": section["heading"],
            "intro": text,
            "headers": table["headers"] if table else [],
            "rows": [row["cells"] for row in table["rows"]] if table else [],
        }
    return None


def text_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def source_location(root: Path, path: Any) -> Path | None:
    """The file a model source names, only if it is runs/<folder>/<file> inside root."""
    if not isinstance(path, str) or "\\" in path or ":" in path:
        return None
    parts = PurePosixPath(path).parts
    if len(parts) < 3 or parts[0] != "runs" or PurePosixPath(path).is_absolute():
        return None
    if ".." in parts:
        return None
    try:
        resolved = (root / path).resolve()
    except (ValueError, OSError):  # An embedded NUL or an unresolvable path is an invalid source.
        return None
    return resolved if resolved.is_relative_to(root.resolve()) else None


def model_sources(
    root: Path,
    delivery: dict[str, Any],
    outputs: dict[str, Any],
    folder: str | None = None,
    issues: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Each source a model declares, whether its file has the declared bytes, and the output.

    A source whose path is not a confined runs/<folder>/<file> or whose hash is not 64 lowercase hex
    keeps its row with sha256 and changed null; its file is never opened. A source that is not a
    regular file of at most 64 MiB is likewise kept with nulls and named in the issues; an absent
    file stays "changed". The issues are appended to `issues`, prefixed with `folder`.
    """
    rows: list[dict[str, Any]] = []
    issues = [] if issues is None else issues
    declared_sources = delivery.get("sources")
    for role, source in (declared_sources if isinstance(declared_sources, dict) else {}).items():
        source = source if isinstance(source, dict) else {}
        path, declared = source.get("path"), source.get("sha256")
        location = source_location(root, path)
        valid = (
            location is not None
            and isinstance(declared, str)
            and re.fullmatch(r"[0-9a-f]{64}", declared) is not None
        )
        row = {
            "role": role,
            "path": path if isinstance(path, str) else None,
            "sha256": declared if valid else None,
            "changed": None,
            "run": None,
            "output": None,
        }
        if location is not None and valid:
            try:
                row["changed"] = sha256(location) != declared
            except UnreadableFile:
                row["sha256"] = None
                issues.append(f"{folder}: source {role} is not a readable file")
            except OSError:
                row["changed"] = True
            held = outputs.get(str(path).removeprefix("runs/"))
            match = held if held and held["sha256"] == declared else None
            if match and row["sha256"] is not None:
                row["run"], row["output"] = match["run"], match["id"]
        else:
            issues.append(f"{folder}: source {role} has an invalid path or hash")
        rows.append(row)
    return rows


CASHFLOW_FILES = ("forecast_exact.json", "calculation.json", "annual.md", "quarter.md")
# The CP-1 handoff table labels the cash flow reader matches, exactly as the handoffs print them
# (TDG wording). To read another issuer's handoffs, add or change its labels here; nothing else in
# the reader names a handoff label. Matching is exact and case-sensitive except the debt register,
# which is matched case-insensitively (see secured_debt).
CASHFLOW_LABELS = {
    "revenue": "NET SALES",
    "cogs": "COST OF SALES",
    "gross_profit": "GROSS PROFIT",
    "selling_admin": "SELLING AND ADMINISTRATIVE EXPENSES",
    "amortization": "AMORTIZATION OF INTANGIBLE ASSETS",
    "operating_income": "INCOME FROM OPERATIONS",
    "segment_revenue": "Net Sales",
    "total_prefix": "Total",
    "da": "Depreciation and amortization expense",
    "issuer_ebitda": "EBITDA",
    "adjusted_ebitda": "Total Company EBITDA As Defined",
    "interest_net": "Interest expense-net",
    "pretax_income": "Income from continuing operations before income taxes",
    "secured_securitization": "Trade receivable securitization",
    "secured_term_loans": "Term loans aggregate",
    "secured_notes": "secured notes",
    "unsecured_notes": "subordinated",
    "unsecured": "unsecured",
    "label_header": "Label",
    "period_header": "Period",
    "period_end_header": "End",
}
# Inputs beyond these are refused before any cell is built (see CashflowLimit).
QUARTER_COLUMN_LIMIT = 40
FORECAST_YEAR_LIMIT = 20
FISCAL_YEAR_LIMIT = 20
UNIT_ROW_LIMIT = 200
ADD_BACK_ROW_LIMIT = 200
TABLE_ROW_LIMIT = 2000
QUARTER_DAYS = 100
QUARTER_LENGTH_SLACK = 7
FORECAST_CASES = (("REFERENCE", "Base case (reference illustration)"), ("DOWNSIDE", "Downside"))
NO_VALUE = "the model's source table has no value for this period"
PRINTED_DASH = "printed as \u2014 in the source"
PRIOR_MISSING = "prior-year period not in the handoffs"
COMPONENT_MISSING = "a component is not in the handoffs"
REASON_PHRASES = {
    "NOT_SOURCED": "not reported in the source",
    "NOT_STATED": COMPONENT_MISSING,
    "ZERO_OR_NEGATIVE_DENOMINATOR": "a divisor is zero or negative",
    "COMPONENT_MISSING": COMPONENT_MISSING,
    "PRIOR_PERIOD_MISSING": PRIOR_MISSING,
    "REGISTER_DATE_DIFFERS": "secured-debt carrying values are recorded at another date",
    "UNCLASSIFIED_ROW": "the debt register has a row that cannot be classified",
    "WINDOW_MISSING": "last-twelve-months Adj EBITDA cannot be built from the handoffs",
}
LTM_NEEDED = "needs last-twelve-months Adj EBITDA for this quarter, which is not recorded"
DEBT_TOTAL_NEEDED = "needs quarter-end total carrying debt, which the model does not derive"
DEBT_SENIOR_NEEDED = (
    "needs quarter-end senior secured carrying debt, which the model does not derive"
)
MONTHS_SHORT = {name[:3]: number for number, name in enumerate(MONTHS, 1)}
Q1_NOTE = "Q1 is the first quarter of the fiscal year, so it is also the year to date."
CASHFLOW_NOTES = (
    Q1_NOTE,
    "Pro forma: no pro forma period is recorded in the handoffs.",
    (
        "Base case is the model's reference case: a conditional illustration, not an "
        "evidence-supported central issuer forecast. The upside case stays in the calculation "
        "record and the published model."
    ),
    "n.m. \u2014 not modelled: the calculation record does not project this line.",
    (
        "EBITDA (EBIT + D&A) differs from the issuer's reported EBITDA, which also deducts "
        "refinancing costs and includes other income or expense."
    ),
    (
        "Adj EBITDA is the issuer's EBITDA As Defined, a non-GAAP measure; in the forecast it is "
        "the model's earnings on that basis, not issuer guidance."
    ),
    (
        "Leverage uses carrying debt including securitization; senior secured debt is the term "
        "loans, secured notes and securitization at carrying value. Ratios are shown for fiscal "
        "years only."
    ),
)
QUARTER_HEADER = re.compile(r"(\d{4}-\d{2}-\d{2})[–-](\d{4}-\d{2}-\d{2})", re.ASCII)
FISCAL_HEADER = re.compile(r"FY\d{4}", re.ASCII)
TABLE_NUMBER = re.compile(r"(\()?((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)(\))?", re.ASCII)
SEPARATOR_CELL = re.compile(r":?-+:?")
CARRYING = re.compile(r"carrying\s+(\d[\d,]*(?:\.\d+)?)", re.ASCII)
REGISTER_DATE = re.compile(r"\b([A-Z][a-z]{2}) (\d{1,2}), (\d{4})\b", re.ASCII)


class Cell(TypedDict):
    """One grid cell. `status` is value, na (not available, with a reason) or nm (not modelled)."""

    exact: str | None
    display: str
    reason: str | None
    status: str


PeriodKey = tuple[str, ...]
Span = tuple[str, ...]  # (start, end) ISO dates of a quarter column
SecuredDebt = tuple[datetime.date, decimal.Decimal | None, str | None]
Spec = tuple[Any, ...]  # (operation name, *its arguments); see CELL_OPS
RowKey = str | tuple[str, str]
Forecast = list[tuple[str, list[dict[str, Any]]]]  # (case name, that case's years)
Fiscal = list[tuple[str, dict[str, Any]]]  # (fiscal year label, its values)


class Table(TypedDict):
    """A Markdown table: its header, rows by first-found label, and column index by period."""

    header: list[str]
    rows: dict[str, list[str]]
    periods: dict[PeriodKey, int]
    repeated: str | None
    interrupted: str | None


class Column(TypedDict):
    """A grid column; `prior` is the index of its prior-year column."""

    label: str
    group: str
    kind: str
    record: dict[str, Any] | None
    start: str | None
    end: str | None
    period: PeriodKey | None
    prior: int | None
    ytd: bool
    length_differs: NotRequired[bool]


def display_amount(exact: str, kind: str) -> str:
    """An exact decimal string as the reader sees it: half-up, money in brackets when negative."""
    with decimal.localcontext(decimal.Context(prec=200)) as context:
        value = decimal.Decimal(exact)
        if not value.is_finite():
            raise ValueError(f"not a finite decimal: {exact!r}")
        if kind in ("percent", "multiple"):
            scaled = value * 100 if kind == "percent" else value
            two = scaled.quantize(decimal.Decimal("0.01"), decimal.ROUND_HALF_UP, context)
            if two == 0:
                two = abs(two)  # a negative that rounds to zero is not shown as -0.00
            return f"{two:,.2f}{'%' if kind == 'percent' else 'x'}"
        rounded = value.quantize(decimal.Decimal(1), decimal.ROUND_HALF_UP, context)
        if rounded == 0:
            return "0"  # a negative that rounds to zero is not shown as -0 or in brackets
        return f"({-rounded:,})" if rounded < 0 else f"{rounded:,}"


def cashflow_units(handoff: str) -> str | None:
    """The first '<ISO currency> millions|billions|thousands' phrase of the Request section."""
    request = re.search(
        r"^## Request[ \t]*\r?\n(.*?)(?=^## |\Z)", handoff, re.MULTILINE | re.DOTALL
    )
    phrase = (
        re.search(r"\b[A-Z]{3}\s+(?:millions|billions|thousands)\b", request.group(1))
        if request
        else None
    )
    return re.sub(r"\s+", " ", phrase.group(0)) if phrase else None


class CashflowBudget(Exception):
    """A grid larger than the cells left in the workspace's budget; raised before any cell."""


class CashflowLimit(Exception):
    """A cash flow input larger than the reader accepts; names the file and what was too large."""

    def __init__(self, file: str, what: str, found: int, limit: int) -> None:
        super().__init__(f"{file} exceeds the cash flow model's limits ({what}, {found} > {limit})")


def grid_cell(
    exact: str | None, display: str, reason: str | None = None, status: str = "value"
) -> Cell:
    return {"exact": exact, "display": display, "reason": reason, "status": status}


def amount_cell(exact: str, kind: str) -> Cell:
    return grid_cell(exact, display_amount(exact, kind))


def absent_cell() -> Cell:
    return unavailable_cell(NO_VALUE)


def unavailable_cell(reason: str | None) -> Cell:
    return grid_cell(None, "n.a.", reason, "na")


def not_modelled_cell() -> Cell:
    return grid_cell(None, "n.m.", "not modelled in the calculation record", "nm")


def held_cell(held: dict[str, Any], kind: str, negate: bool = False) -> Cell:
    """A calculation record's {amount, reason}; an amount of null is n.a. with its reason."""
    exact = held["amount"]
    if exact is None:
        reason, note = held.get("reason"), held.get("note")
        words = REASON_PHRASES.get(reason, reason) if isinstance(reason, str) else None
        if reason == "WINDOW_MISSING" and isinstance(note, str) and note:
            words = f"{words}: {note[:LABEL_LIMIT]}"  # the cause the delivery recorded
        return unavailable_cell(words)
    if negate:
        value = decimal.Decimal(exact).copy_negate()
        exact = "0" if value == 0 else str(value)
    return amount_cell(exact, kind)


def checked_entries(record: dict[str, Any], skip: tuple[str, ...] = ()) -> None:
    """Every entry of a calculation record but `skip` is {amount: text|null, reason: text|null}."""
    for key, held in record.items():
        if key in skip:
            continue
        if not isinstance(held, dict) or not {"amount", "reason"} <= held.keys():
            raise TypeError(f"{key} is not an amount and a reason")
        exact, reason = held["amount"], held["reason"]
        if not (reason is None or isinstance(reason, str)):
            raise TypeError(f"the reason of {key} is not text")
        if exact is None:
            continue
        if not isinstance(exact, str) or len(exact) > 200:
            raise ValueError("an amount is not a decimal string")
        display_amount(exact, "money")  # a non-finite or out-of-range amount raises here
        display_amount(exact, "percent")


def source_cell(text: str, kind: str) -> Cell:
    """A Markdown table cell as the handoff printed it."""
    if text == "":
        return absent_cell()
    if text == "\u2014":
        return unavailable_cell(PRINTED_DASH)
    found = TABLE_NUMBER.fullmatch(text) if len(text) <= 40 else None
    if found is None or bool(found.group(1)) != bool(found.group(3)):
        return unavailable_cell("source cell is not a number")
    digits = found.group(2).replace(",", "")
    negative = found.group(1) and decimal.Decimal(digits) != 0
    return amount_cell(f"-{digits}" if negative else digits, kind)


def table_cells(line: str) -> list[str]:
    """The cells of a table row; an escaped pipe (backslash, pipe) is text inside a cell."""
    inner = line.strip().removeprefix("|").removesuffix("|")
    return [cell.strip().replace("\\|", "|") for cell in re.split(r"(?<!\\)\|", inner)]


MARKS = re.compile(r"[*_()]")
TOTAL_AT_EDGE = re.compile(r"(?:(?:sub)?totals?\b.*|.*\b(?:sub)?totals?)")
TOTAL_WORD = re.compile(r"\b(?:sub)?totals?\b")
SEPARATOR = re.compile(r"[ \t]*(?=[^-]*-)(?=.*\|)[ \t:|-]+")
TABLE_ROW = re.compile(r" {0,3}(\|.*?)\s*")
CODE_SPAN = re.compile(r"(`+).+?\1")
FENCE_LINE = re.compile(r"[ \t]*(?:`{3,}|~{3,})")
HEADING_START = re.compile(r" {0,3}(#{1,6})(?:[ \t]|$)")


def plain_label(label: str) -> str:
    """A register row label as classified, delivery's `_plain` written again: emphasis marks and
    parentheses removed, whitespace runs one space, trailing `:` and `.` stripped, casefolded."""
    text = " ".join(MARKS.sub("", label).split())
    return text.rstrip(":.").strip().casefold()


def total_kind(low: str) -> str | None:
    """`edge` when the whole word total or subtotal starts or ends the plain label (a subtotal),
    `inner` when it sits elsewhere (a row that cannot be classified), else None."""
    if TOTAL_AT_EDGE.fullmatch(low):
        return "edge"
    return "inner" if TOTAL_WORD.search(low) else None


def table_row(line: str) -> str | None:
    """The row text of a line that starts with '|' after at most three spaces (four is code),
    without trailing whitespace; None for any other line."""
    found = TABLE_ROW.fullmatch(line)
    return None if found is None else found[1]


def inline_comments(line: str) -> tuple[str, bool]:
    """`line` without its complete HTML comments, and whether one is still open at its end.
    Code spans are blanked before looking for `<!--`; `<!-->` and `<!--->` are whole comments."""
    kept = ""
    while True:
        masked = CODE_SPAN.sub(lambda m: "x" * len(m[0]), line)
        opener = masked.find("<!--")
        if opener < 0:
            return kept + line, False
        if masked.startswith(">", opener + 4):
            end = opener + 5
        elif masked.startswith("->", opener + 4):
            end = opener + 6
        elif (closer := masked.find("-->", opener + 4)) >= 0:
            end = closer + 3
        else:
            return kept + line[:opener], True
        kept, line = kept + line[:opener], line[end:]


def shown_lines(lines: list[str]) -> list[str]:
    """The lines as a Markdown viewer shows them (delivery's `_shown` written again): comments
    removed, fenced code blanked, line numbers kept. A comment never closed hides the rest."""
    shown, fenced, opened = [], False, False
    for line in lines:
        if opened:
            end = line.find("-->")
            text, opened = ("", True) if end < 0 else inline_comments(line[end + 3 :])
            shown.append(text)
            continue
        found = HEADING_START.match(line)
        fenced = fenced and not (found and len(found[1]) == 2)
        toggled = FENCE_LINE.match(line) is not None
        fenced ^= toggled
        if fenced or toggled:
            shown.append("")
            continue
        text, opened = inline_comments(line)
        shown.append(text)
    return shown


def period_key(header: str) -> PeriodKey | None:
    quarter = QUARTER_HEADER.fullmatch(header)
    if quarter:
        try:
            for part in quarter.groups():
                datetime.date.fromisoformat(part)
        except ValueError:
            return None
        return ("q",) + quarter.groups()
    return ("fy", header) if FISCAL_HEADER.fullmatch(header) else None


def holds_carrying_value(row: list[str]) -> bool:
    return len(row) > 1 and len(row[1]) <= 4000 and CARRYING.search(row[1]) is not None


def markdown_table(lines: list[str], file: str) -> Table:
    """One run of '|' lines: header, optional separator, rows. Rows are found by their label."""
    header = table_cells(lines[0])
    separated = len(lines) > 1 and all(SEPARATOR_CELL.fullmatch(c) for c in table_cells(lines[1]))
    if len(lines) - 1 - separated > TABLE_ROW_LIMIT:
        raise CashflowLimit(file, "table rows", len(lines) - 1 - separated, TABLE_ROW_LIMIT)
    body = [table_cells(line) for line in lines[1 + separated :]]
    label_header = CASHFLOW_LABELS["label_header"]
    label_column = header.index(label_header) if label_header in header else 0
    rows: dict[str, list[str]] = {}
    repeated: str | None = None
    folded: set[str] = set()
    for row in body:
        if label_column < len(row):
            # Case-insensitive, as the debt classification is.
            # A later row of a label already seen is dropped by `rows`: that matters when it holds a
            # carrying value, not for a blank label or a note row.
            label = row[label_column]
            dropped = plain_label(label) in folded and label != ""
            if dropped and repeated is None and holds_carrying_value(row):
                repeated = label
            folded.add(plain_label(label))
            rows.setdefault(row[label_column], row)
    periods: dict[PeriodKey, int] = {}
    for index, name in enumerate(header):
        key = period_key(name)
        if key is not None:
            periods.setdefault(key, index)
    return {
        "header": header,
        "rows": rows,
        "periods": periods,
        "repeated": repeated,
        "interrupted": None,
    }


def markdown_tables(text: str, file: str) -> list[Table]:
    """The tables of a Markdown text as a viewer shows it; `file` names it in a limit error. A table
    is its header and raw rows; `interrupted` when hiding changed one or '|' text outside code
    follows before the next `#` heading without its own separator row (delivery's rule). Rows after
    a split table are never merged: they read under its header, with no period and its problem."""
    tables: list[Table] = []
    raw = physical_lines(text)
    shown = shown_lines(raw)
    at, head, problem = 0, "", None  # the header and problem of a split table
    while at < len(raw):
        if table_row(shown[at]) is None:
            at += 1
            continue
        end = at + 1
        while end < len(raw) and table_row(raw[end]) is not None:
            end += 1
        rows = [row for row in map(table_row, shown[at:end]) if row is not None]
        follows = problem is not None and not SEPARATOR.fullmatch("".join(shown[at + 1 : at + 2]))
        table = markdown_table([head, *rows] if follows else rows, file)
        stop = next((i for i in range(end, len(raw)) if HEADING_START.match(shown[i])), len(raw))
        more = next((i for i in range(end, stop) if "|" in CODE_SPAN.sub("", shown[i])), stop)
        split = more < stop and not SEPARATOR.fullmatch("".join(shown[more + 1 : more + 2]))
        if any(shown[i] != raw[i] for i in range(at, more + 1 if split else end)):
            table["interrupted"] = "interrupted by a comment"
        elif split:
            table["interrupted"] = "split by a blank line or a comment"
        if follows:
            table["periods"], table["interrupted"] = {}, problem
        head, problem = head if follows else rows[0], table["interrupted"] if split else None
        tables.append(table)
        at = end
    return tables


def table_holding(tables: list[Table], label: str) -> Table | None:
    return next((table for table in tables if label in table["rows"]), None)


def table_cell(
    table: Table | None, label: str, period: PeriodKey | None, kind: str = "money"
) -> Cell:
    row = None if table is None else table["rows"].get(label)
    index = None if table is None or period is None else table["periods"].get(period)
    if row is None or index is None or index >= len(row):
        return absent_cell()
    return source_cell(row[index], kind)


def add_back_labels(table: Table | None) -> list[str]:
    """The rows between 'Interest expense-net' and the pre-tax income row of a bridge."""
    start = CASHFLOW_LABELS["interest_net"]
    if table is None or start not in table["rows"]:
        return []
    labels = list(table["rows"])
    labels = labels[labels.index(start) + 1 :]
    end = CASHFLOW_LABELS["pretax_income"]
    labels = labels[: labels.index(end)] if end in labels else labels
    return [label for label in labels if label]


def register_date(text: str) -> datetime.date | None:
    found = REGISTER_DATE.search(text)
    if found is None or found.group(1) not in MONTHS_SHORT:
        return None
    try:
        return datetime.date(int(found.group(3)), MONTHS_SHORT[found.group(1)], int(found.group(2)))
    except ValueError:
        return None


def secured_debt(tables: list[Table]) -> SecuredDebt | None:
    """(register date, secured carrying total, problem) of the annual debt register, or None.

    Labels match case-insensitively. Secured: the securitization, the term loans aggregate, and
    secured notes. Unsecured: subordinated or unsecured notes. Total rows are subtotals. Any other
    row with a `carrying <n>` value cannot be classified: the total is then None and the problem
    names the label. None when the register date or a secured carrying value is missing.
    """
    names = CASHFLOW_LABELS
    anchor = names["secured_term_loans"].casefold()
    debt = next(
        (t for t in tables if any(plain_label(label) == anchor for label in t["rows"])), None
    )
    if debt is None or len(debt["header"]) < 2:
        return None
    when = register_date(debt["header"][1])
    if when is None:
        return None
    required = {names["secured_securitization"].casefold(), names["secured_term_loans"].casefold()}
    secured_notes = re.compile(r"(?<![a-z])" + re.escape(names["secured_notes"]))
    total, incomplete, unclassified = decimal.Decimal(0), False, None
    named: set[str] = set()
    for label, row in debt["rows"].items():
        low = plain_label(label)
        kind = total_kind(low)
        if kind == "edge":
            continue
        unsecured = names["unsecured_notes"] in low or names["unsecured"] in low
        secured = kind is None and (
            low in required or (secured_notes.search(low) and not unsecured)
        )
        carrying = CARRYING.search(row[1]) if len(row) > 1 and len(row[1]) <= 4000 else None
        if not secured:
            if carrying is not None and not unsecured and unclassified is None:
                unclassified = label[:LABEL_LIMIT]
            continue
        if carrying is None:
            incomplete = True
            continue
        total += decimal.Decimal(carrying.group(1).replace(",", ""))
        named.add(low)
    if debt["interrupted"] is not None:
        return (
            when,
            None,
            f"the debt register ({debt['header'][1][:LABEL_LIMIT]}) is {debt['interrupted']}",
        )
    if debt["repeated"] is not None:
        return (
            when,
            None,
            f"the debt register repeats a row label: {debt['repeated'][:LABEL_LIMIT]}",
        )
    if unclassified is not None:
        return (
            when,
            None,
            f"the debt register has a row that cannot be classified: {unclassified}",
        )
    return (when, total, None) if required <= named and not incomplete else None


def fiscal_year_ends(tables: list[Table]) -> dict[str, str]:
    """FY label -> ISO end date from the annual period register (headed Period ... End)."""
    names = CASHFLOW_LABELS
    period_name, end_name = names["period_header"], names["period_end_header"]
    register = next(
        (t for t in tables if period_name in t["header"] and end_name in t["header"]), None
    )
    if register is None:
        return {}
    period, end = register["header"].index(period_name), register["header"].index(end_name)
    return {
        row[period]: row[end]
        for row in register["rows"].values()
        if len(row) > max(period, end) and FISCAL_HEADER.fullmatch(row[period])
    }


def derive(kind: str, operands: list[Cell], compute: Callable[..., decimal.Decimal]) -> Cell:
    """A value from other cells under prec=28; n.m. or a gap in an operand carries through."""
    if any(operand["status"] == "nm" for operand in operands):
        return not_modelled_cell()
    exacts = [operand["exact"] for operand in operands]
    values = [decimal.Decimal(exact) for exact in exacts if exact is not None]
    if len(values) != len(exacts):
        return unavailable_cell(COMPONENT_MISSING)
    try:
        with decimal.localcontext(decimal.Context(prec=28)):
            result = compute(*values)
    except (decimal.DivisionByZero, decimal.InvalidOperation):
        return unavailable_cell("a divisor is zero")
    try:
        return amount_cell("0" if result == 0 else str(result), kind)
    except (ArithmeticError, ValueError):
        return unavailable_cell("the value cannot be displayed")


def forecast_inputs(exact: Any) -> tuple[Forecast, list[str]]:
    """(source years by case, scope limits) of the forecast record; validated here."""
    cases: Forecast = []
    for key, name in FORECAST_CASES:
        if key not in exact["outputs"]:
            continue
        years = exact["outputs"][key]["years"]
        if len(years) > FORECAST_YEAR_LIMIT:
            raise CashflowLimit(
                CASHFLOW_FILES[0], f"forecast years in {key}", len(years), FORECAST_YEAR_LIMIT
            )
        for year in years:
            if not isinstance(year["year"], int):
                raise TypeError("year is not a number")
            checked_entries(year, ("year", "planning_start", "planning_end"))
        cases.append((name, years))
    limits = exact["scope_limits"]
    if not isinstance(limits, list) or not all(isinstance(item, str) for item in limits):
        raise TypeError("scope_limits is not a list of text")
    return cases, limits


def fiscal_inputs(record: Any) -> Fiscal:
    """[(fiscal year label, its values)] in the record's annual_periods order; validated here."""
    labels = record["annual_periods"]
    if not isinstance(labels, list) or not all(isinstance(label, str) for label in labels):
        raise TypeError("annual_periods is not a list of text")
    if len(labels) > FISCAL_YEAR_LIMIT:
        raise CashflowLimit(CASHFLOW_FILES[1], "fiscal years", len(labels), FISCAL_YEAR_LIMIT)
    years: Fiscal = []
    for label in labels:
        values = record["values"][label]
        checked_entries(values)
        years.append((label, values))
    return years


def quarter_inputs(record: Any) -> dict[str, dict[str, Any]]:
    """The record's derived quarter values by window text; absent is empty; validated here."""
    quarters = record.get("quarters", {})
    if not isinstance(quarters, dict):
        raise TypeError("quarters is not a mapping of windows")
    for held in quarters.values():
        if not isinstance(held, dict):
            raise TypeError("a quarter window is not a mapping")
        checked_entries(held)
    return quarters


def span_days(start: str, end: str) -> int:
    return (datetime.date.fromisoformat(end) - datetime.date.fromisoformat(start)).days


def quarter_numbers(quarters: list[Span], ends: dict[str, str] | None) -> list[int | None]:
    """Per quarter, the fiscal year it opens (as Q1) or None.

    A quarter opens fiscal year N+1 when it spans at most QUARTER_DAYS days and starts the day
    after the end the period register records for FY N. Anything else is neither Q1 nor year to
    date.
    """
    openings: dict[datetime.date, int] = {}
    for label, end in (ends or {}).items():
        try:
            day = datetime.date.fromisoformat(end) + datetime.timedelta(days=1)
            openings.setdefault(day, int(label.removeprefix("FY")) + 1)
        except (ValueError, OverflowError):
            continue  # a register row with an unreadable end opens no fiscal year
    numbers: list[int | None] = []
    longest: dict[int, tuple[int, int]] = {}
    for index, (start, end) in enumerate(quarters):
        days = span_days(start, end)
        number = (
            openings.get(datetime.date.fromisoformat(start)) if 0 <= days <= QUARTER_DAYS else None
        )
        numbers.append(number)
        if number is not None and days > longest.get(number, (-1, 0))[0]:
            longest[number] = (days, index)
    # One Q1 per fiscal year: the longest span; the other candidates are plain date ranges.
    return [
        number if number is not None and longest[number][1] == index else None
        for index, number in enumerate(numbers)
    ]


def quarter_columns(quarters: list[Span], ends: dict[str, str] | None) -> list[Column]:
    """One column per quarter; a Q1 (year to date) has the previous year's Q1 as prior."""
    numbers = quarter_numbers(quarters, ends)
    first_quarter: dict[int, int] = {}
    for index, number in enumerate(numbers):
        if number is not None:
            first_quarter.setdefault(number, index)
    columns: list[Column] = []
    for (start, end), number in zip(quarters, numbers, strict=True):
        prior = None if number is None else first_quarter.get(number - 1)
        column = Column(
            label=f"{start}–{end}" if number is None else f"Q1 FY{number} (YTD)",
            group="Quarter",
            kind="q",
            record=None,
            start=start,
            end=end,
            period=("q", start, end),
            prior=prior,
            ytd=number is not None,
        )
        if prior is not None and abs(span_days(start, end) - span_days(*quarters[prior])) > (
            QUARTER_LENGTH_SLACK
        ):
            column["length_differs"] = True
        columns.append(column)
    return columns


def fiscal_columns(columns: list[Column], fiscal: Fiscal) -> dict[str, int]:
    """Append one column per fiscal year; returns each label's column index."""
    fiscal_index: dict[str, int] = {}
    for label, values in fiscal:
        found = FISCAL_HEADER.fullmatch(label)
        columns.append(
            Column(
                label=label,
                group="Fiscal year",
                kind="fy",
                record=values,
                start=None,
                end=None,
                period=("fy", label),
                prior=fiscal_index.get(f"FY{int(label[2:]) - 1}") if found else None,
                ytd=False,
            )
        )
        fiscal_index.setdefault(label, len(columns) - 1)
    return fiscal_index


def forecast_columns(columns: list[Column], cases: Forecast, fiscal_index: dict[str, int]) -> None:
    """Append one column per forecast year of each case."""
    for name, years in cases:
        case_index: dict[int, int] = {}
        for year in years:
            prior = case_index.get(year["year"] - 1)
            if prior is None and not case_index:
                prior = fiscal_index.get(f"FY{year['year'] - 1}")
            columns.append(
                Column(
                    label=f"FY{year['year']}E",
                    group=name,
                    kind="fc",
                    record=year,
                    start=text_or_none(year.get("planning_start")),
                    end=text_or_none(year.get("planning_end")),
                    period=None,
                    prior=prior,
                    ytd=False,
                )
            )
            case_index.setdefault(year["year"], len(columns) - 1)


def cashflow_columns(
    quarters: list[Span], fiscal: Fiscal, cases: Forecast, ends: dict[str, str] | None = None
) -> list[Column]:
    """Quarter, fiscal-year and forecast columns, each with its prior-year column's index.

    The prior of Q1 FY<n> is Q1 FY<n-1>; other quarters have none. The prior of FY<n> is FY<n-1>,
    of the first forecast year the fiscal year before it, of a later forecast year the same case's
    year before it; a prior that is not the adjacent year is None.
    """
    columns = quarter_columns(quarters, ends)
    fiscal_index = fiscal_columns(columns, fiscal)
    forecast_columns(columns, cases, fiscal_index)
    return columns


class CashflowInputs(NamedTuple):
    """What every cell of one model's grid reads: tables, the debt register, fiscal-year ends."""

    tables: dict[str, Table | None]
    secured: SecuredDebt | None
    ends: dict[str, str]
    quarters: dict[str, dict[str, Any]]


class CellContext(NamedTuple):
    """The one argument of a cell operation: inputs, the cell's column, position and row kind."""

    inputs: CashflowInputs
    column: Column
    at: int
    grid: dict[RowKey, list[Cell]]
    kind: str


def add_cells(cells: list[Cell], kind: str = "money") -> Cell:
    return derive(kind, cells, lambda a, b: a + b)


def op_table(c: CellContext, name: str, label: str) -> Cell:
    return table_cell(c.inputs.tables[name], label, c.column["period"], c.kind)


def op_table_sum(c: CellContext, name: str, first: str, second: str) -> Cell:
    table = c.inputs.tables[name]
    cells = [table_cell(table, label, c.column["period"], c.kind) for label in (first, second)]
    return add_cells(cells, c.kind)


def op_key(c: CellContext, key: str, negate: bool = False) -> Cell:
    missing = not_modelled_cell if c.column["kind"] == "fc" else absent_cell
    record = c.column["record"]
    if record is None:
        raise ValueError(f"the {c.column['label']} column holds no record to read {key} from")
    return held_cell(record[key], c.kind, negate) if key in record else missing()


def op_sum(c: CellContext, *rows: RowKey) -> Cell:
    return add_cells([c.grid[row][c.at] for row in rows], c.kind)


def op_growth(c: CellContext, source: RowKey) -> Cell:
    """YoY growth of an earlier row against the same row in the column's prior-year column."""
    current = c.grid[source][c.at]
    if current["status"] == "nm":
        return not_modelled_cell()
    if c.column["prior"] is None:
        return unavailable_cell(PRIOR_MISSING)
    if c.column.get("length_differs"):
        return unavailable_cell("the prior-year period has a different length")
    prior = c.grid[source][c.column["prior"]]
    return derive("percent", [current, prior], lambda a, b: a / b - 1)


def op_margin(c: CellContext, source: RowKey) -> Cell:
    return derive("percent", [c.grid[source][c.at], c.grid["revenue"][c.at]], lambda a, b: a / b)


def op_prefer(c: CellContext, key: str, fallback: Spec) -> Cell:
    """The calculation record's own value for the key when it holds one, else the derivation."""
    record = c.column["record"]
    if record is not None and key in record:
        return held_cell(record[key], c.kind)
    return spec_cell(fallback, c)


def quarter_held(c: CellContext, key: str) -> dict[str, Any] | None:
    """The record's entry for the key in this quarter column's window (either dash), or None."""
    column = c.column
    if column["kind"] != "q" or column["start"] is None or column["end"] is None:
        return None
    for dash in ("\u2013", "-"):
        window = c.inputs.quarters.get(f"{column['start']}{dash}{column['end']}")
        if window is not None and key in window:
            held: dict[str, Any] = window[key]
            return held
    return None


def op_quarter(c: CellContext, key: str, fallback: Spec | None = None) -> Cell:
    """The record's quarter value for this column's window, else the fallback, else n.a."""
    held = quarter_held(c, key)
    if held is not None:
        return held_cell(held, c.kind)
    return spec_cell(fallback, c) if fallback is not None else absent_cell()


def op_needs_ltm(c: CellContext, debt_needed: str = DEBT_TOTAL_NEEDED) -> Cell:
    held = quarter_held(c, "ltm_adj_ebitda")
    return unavailable_cell(LTM_NEEDED if held is None or held["amount"] is None else debt_needed)


def op_senior(c: CellContext) -> Cell:
    """Secured carrying values over Adj EBITDA, for the fiscal year ending on the register date."""
    if c.inputs.secured is None:
        return unavailable_cell(COMPONENT_MISSING)
    when, total, problem = c.inputs.secured
    if c.inputs.ends.get(c.column["label"]) != when.isoformat():
        return unavailable_cell(
            f"secured-debt carrying values are recorded only at {display_date(when.isoformat())}"
        )
    if problem is not None or total is None:
        return unavailable_cell(problem)
    return derive("multiple", [c.grid["adj"][c.at]], lambda a: total / a)


CELL_OPS: dict[str, Callable[..., Cell]] = {
    "table": op_table,
    "table-sum": op_table_sum,
    "key": op_key,
    "sum": op_sum,
    "growth": op_growth,
    "margin": op_margin,
    "ltm": op_needs_ltm,
    "quarter": op_quarter,
    "senior": op_senior,
    "prefer": op_prefer,
}


def spec_cell(spec: Spec | None, cell: CellContext) -> Cell:
    """One cell from its row's spec for the column's kind (None: n.a., or n.m. in forecast)."""
    if spec is None:
        return not_modelled_cell() if cell.column["kind"] == "fc" else absent_cell()
    return CELL_OPS[spec[0]](cell, *spec[1:])


def every(spec: Spec) -> tuple[Spec, Spec, Spec]:
    return (spec, spec, spec)


# Rows the grid shows as totals (the ones a reader adds up to): by row key.
TOTAL_ROWS = frozenset(
    (
        "revenue",
        "gp",
        "ebit",
        "ebitda",
        "adj",
        "cfo",
        "fcf",
        "closing-cash",
        "liquidity",
        "closing-debt",
        "net-debt",
    )
)


class RowSpec(NamedTuple):
    """A grid row as data; a None spec shows n.a. (history) or n.m. (forecast)."""

    key: RowKey
    band: str
    label: str
    kind: str
    quarter: Spec | None
    fiscal: Spec | None
    forecast: Spec | None


# Rows as data: (id, band, label, kind, quarter spec, fiscal-year spec, forecast spec).
INCOME = "Profitability"
HEAD_ROWS = (
    RowSpec(
        "revenue",
        "Revenue",
        "Revenue",
        "money",
        ("table", "income", CASHFLOW_LABELS["revenue"]),
        ("key", "revenue"),
        ("key", "revenue"),
    ),
    RowSpec(
        "revenue-growth",
        "Revenue",
        "Revenue YoY growth",
        "percent",
        ("growth", "revenue"),
        ("prefer", "revenue_growth", ("growth", "revenue")),
        ("growth", "revenue"),
    ),
    RowSpec(
        "cogs",
        INCOME,
        "COGS (cost of sales)",
        "money",
        ("table", "income", CASHFLOW_LABELS["cogs"]),
        ("key", "cogs"),
        None,
    ),
    RowSpec(
        "gp",
        INCOME,
        "Gross profit",
        "money",
        ("table", "income", CASHFLOW_LABELS["gross_profit"]),
        ("key", "gross_profit"),
        None,
    ),
    RowSpec(
        "gp-margin",
        INCOME,
        "Gross profit margin",
        "percent",
        ("margin", "gp"),
        ("prefer", "gross_margin", ("margin", "gp")),
        ("margin", "gp"),
    ),
    RowSpec(
        "opex",
        INCOME,
        "Opex (selling and administrative, amortization of intangibles)",
        "money",
        (
            "table-sum",
            "income",
            CASHFLOW_LABELS["selling_admin"],
            CASHFLOW_LABELS["amortization"],
        ),
        ("key", "opex_magnitude"),
        None,
    ),
    RowSpec(
        "ebit",
        INCOME,
        "EBIT (income from operations)",
        "money",
        ("table", "income", CASHFLOW_LABELS["operating_income"]),
        ("key", "ebit_reported"),
        None,
    ),
    RowSpec(
        "da",
        INCOME,
        "D&A (depreciation and amortization)",
        "money",
        ("table", "bridge", CASHFLOW_LABELS["da"]),
        ("key", "cash_flow_DA"),
        None,
    ),
    RowSpec(
        "ebitda",
        INCOME,
        "EBITDA (EBIT + D&A)",
        "money",
        ("sum", "ebit", "da"),
        ("key", "operating_ebitda"),
        None,
    ),
    RowSpec(
        "issuer",
        INCOME,
        "Issuer EBITDA (reported)",
        "money",
        ("table", "bridge", CASHFLOW_LABELS["issuer_ebitda"]),
        ("key", "issuer_ordinary_ebitda"),
        None,
    ),
)
ADJUSTED = "Adjusted EBITDA"
PROXY = "Earnings to cash proxy"
CASH = "Cash and liquidity"
DEBT = "Debt"
CREDIT = "Credit metrics"
TAIL_ROWS = (
    RowSpec(
        "adj",
        ADJUSTED,
        "Adj EBITDA (EBITDA As Defined)",
        "money",
        ("table", "qdef", CASHFLOW_LABELS["adjusted_ebitda"]),
        ("key", "issuer_as_defined"),
        ("key", "ebitda"),
    ),
    RowSpec(
        "adj-margin",
        ADJUSTED,
        "Adj EBITDA margin",
        "percent",
        ("margin", "adj"),
        ("prefer", "adj_ebitda_margin", ("margin", "adj")),
        ("margin", "adj"),
    ),
    RowSpec(
        "adj-growth",
        ADJUSTED,
        "Adj EBITDA YoY growth",
        "percent",
        ("growth", "adj"),
        ("prefer", "adj_ebitda_growth", ("growth", "adj")),
        ("growth", "adj"),
    ),
    RowSpec(
        "ltm-adj",
        ADJUSTED,
        "LTM Adj EBITDA (As Defined)",
        "money",
        ("quarter", "ltm_adj_ebitda"),
        ("key", "issuer_as_defined"),
        None,
    ),
    RowSpec(
        "interest",
        PROXY,
        "Cash interest",
        "money",
        None,
        ("key", "interest_cash"),
        ("key", "interest"),
    ),
    RowSpec("tax", PROXY, "Cash taxes", "money", None, ("key", "tax_cash"), None),
    RowSpec(
        "tax-wc",
        PROXY,
        "Cash taxes and working capital, combined",
        "money",
        None,
        None,
        ("key", "tax_wc"),
    ),
    RowSpec("cfo", PROXY, "Model cash from operations", "money", None, None, ("key", "cfo")),
    RowSpec(
        "capex",
        PROXY,
        "Capital expenditure (outflow)",
        "money",
        None,
        ("key", "capex_signed", True),
        ("key", "capex"),
    ),
    RowSpec(
        "fcf", PROXY, "Cash proxy (not issuer free cash flow)", "money", None, None, ("key", "fcf")
    ),
    RowSpec("dividends", CASH, "Distributions", "money", None, None, ("key", "dividends")),
    RowSpec("repayment", CASH, "Debt repayment", "money", None, None, ("key", "repayment")),
    RowSpec("opening-cash", CASH, "Opening cash", "money", None, None, ("key", "opening_cash")),
    RowSpec(
        "closing-cash",
        CASH,
        "Closing cash",
        "money",
        None,
        ("key", "cash"),
        ("key", "closing_cash"),
    ),
    RowSpec("undrawn", CASH, "Undrawn facility", "money", None, None, ("key", "undrawn")),
    RowSpec("liquidity", CASH, "Accessible liquidity", "money", None, None, ("key", "liquidity")),
    RowSpec("opening-debt", DEBT, "Opening debt", "money", None, None, ("key", "opening_debt")),
    RowSpec(
        "closing-debt",
        DEBT,
        "Closing debt (carrying value)",
        "money",
        None,
        ("key", "carrying_debt"),
        ("key", "closing_debt"),
    ),
    RowSpec(
        "net-debt",
        DEBT,
        "Net debt (all modelled cash deducted)",
        "money",
        None,
        ("key", "net_carrying_debt"),
        ("key", "net_debt"),
    ),
    RowSpec(
        "senior",
        CREDIT,
        "Senior secured leverage (secured debt / Adj EBITDA)",
        "multiple",
        ("quarter", "senior_secured_multiple", ("ltm", DEBT_SENIOR_NEEDED)),
        ("prefer", "senior_secured_multiple", ("senior",)),
        None,
    ),
    RowSpec(
        "total-leverage",
        CREDIT,
        "Total leverage (debt / Adj EBITDA)",
        "multiple",
        ("ltm",),
        ("key", "gross_carrying_multiple"),
        ("key", "total_leverage"),
    ),
    RowSpec(
        "net-leverage",
        CREDIT,
        "Net leverage (net debt / Adj EBITDA)",
        "multiple",
        ("ltm",),
        ("key", "net_carrying_multiple"),
        ("key", "net_leverage"),
    ),
    RowSpec(
        "coverage",
        CREDIT,
        "Interest coverage (Adj EBITDA / cash interest)",
        "multiple",
        None,
        ("key", "issuer_earnings_cash_interest"),
        ("key", "coverage"),
    ),
    RowSpec(
        "cash-to-debt",
        CREDIT,
        "Cash proxy / closing debt",
        "percent",
        None,
        None,
        ("key", "fcf_to_debt"),
    ),
)


# A free-text label copied from a handoff into the grid is cut to this many characters.
LABEL_LIMIT = 200


def capped(found: Any, what: str, limit: int, file: str) -> None:
    if len(found) > limit:
        raise CashflowLimit(file, what, len(found), limit)


def listed_labels(tables: dict[str, Table | None]) -> list[str]:
    """Business units (rows `Total <unit>`) of the annual, then the quarter, segment table."""
    units: dict[str, None] = {}
    prefix = CASHFLOW_LABELS["total_prefix"] + " "
    for name, file in (("aseg", CASHFLOW_FILES[2]), ("qseg", CASHFLOW_FILES[3])):
        table = tables[name]
        for label in () if table is None else table["rows"]:
            if label.startswith(prefix) and label.removeprefix(prefix):
                units.setdefault(label.removeprefix(prefix))
        capped(units, "business-unit rows", UNIT_ROW_LIMIT, file)
    return list(units)


def listed_add_backs(tables: dict[str, Table | None]) -> list[str]:
    """The annual add-back labels in order, then any quarter-only label."""
    labels = dict.fromkeys(add_back_labels(tables["adef"]))
    capped(labels, "add-back rows", ADD_BACK_ROW_LIMIT, CASHFLOW_FILES[2])
    labels.update(dict.fromkeys(add_back_labels(tables["qdef"])))
    capped(labels, "add-back rows", ADD_BACK_ROW_LIMIT, CASHFLOW_FILES[3])
    return list(labels)


def cashflow_rows(tables: dict[str, Table | None]) -> list[RowSpec]:
    """The grid's rows in presentation order: units, the fixed head, add-backs, the fixed tail."""
    rows: list[RowSpec] = []
    for unit in listed_labels(tables):
        total = f"{CASHFLOW_LABELS['total_prefix']} {unit}"
        rows.append(
            RowSpec(
                ("unit", unit),
                "Revenue",
                unit[:LABEL_LIMIT],
                "money",
                ("table", "qseg", total),
                ("table", "aseg", total),
                None,
            )
        )
        rows.append(
            RowSpec(
                ("growth", unit),
                "Revenue",
                f"{unit[:LABEL_LIMIT]} YoY growth",
                "percent",
                *every(("growth", ("unit", unit))),
            )
        )
    rows.extend(HEAD_ROWS)
    for label in listed_add_backs(tables):
        rows.append(
            RowSpec(
                ("add-back", label),
                "Add-backs to issuer EBITDA",
                label[:LABEL_LIMIT],
                "money",
                ("table", "qdef", label),
                ("table", "adef", label),
                None,
            )
        )
    return rows + list(TAIL_ROWS)


def cashflow_of(
    forecast: tuple[Forecast, list[str]],
    recorded: tuple[Fiscal, dict[str, dict[str, Any]]],
    statements: tuple[list[Table], list[Table]],
    handoff: str | None,
    budget: int,
) -> dict[str, Any]:
    """History from the parsed annual and quarter tables and the forecast record, as a grid.

    Raises CashflowBudget, before computing any cell, when rows x columns passes `budget`.
    """
    cases, limits = forecast
    fiscal, quarters = recorded
    annual, quarter = statements
    names = CASHFLOW_LABELS
    tables: dict[str, Table | None] = {
        "income": table_holding(quarter, names["cogs"]),
        "qseg": table_holding(quarter, names["segment_revenue"]),
        "aseg": table_holding(annual, names["segment_revenue"]),
        "bridge": table_holding(quarter, names["issuer_ebitda"]),
        "qdef": table_holding(quarter, names["adjusted_ebitda"]),
        "adef": table_holding(annual, names["adjusted_ebitda"]),
    }
    ends = fiscal_year_ends(annual)
    inputs = CashflowInputs(tables, secured_debt(annual), ends, quarters)
    income = tables["income"]
    periods = sorted({key[1:] for key in income["periods"] if key[0] == "q"}) if income else []
    capped(periods, "quarter columns", QUARTER_COLUMN_LIMIT, CASHFLOW_FILES[3])
    layout = [RowSpec._make(spec) for spec in cashflow_rows(tables)]  # a plain 7-tuple row works
    columns = cashflow_columns(periods, fiscal, cases, ends)
    if len(layout) * len(columns) > budget:
        raise CashflowBudget(
            "the cash flow model is not shown; the workspace's cash flow models exceed "
            f"{CASHFLOW_CELL_BUDGET:,} cells"
        )
    grid: dict[RowKey, list[Cell]] = {}
    rows = []
    for spec in layout:
        pick = {"q": spec.quarter, "fy": spec.fiscal, "fc": spec.forecast}
        grid[spec.key] = [
            spec_cell(pick[column["kind"]], CellContext(inputs, column, index, grid, spec.kind))
            for index, column in enumerate(columns)
        ]
        rows.append(
            {
                "band": spec.band,
                "label": spec.label,
                "kind": spec.kind,
                "total": spec.key in TOTAL_ROWS,
                "cells": grid[spec.key],
            }
        )
    year_to_date = any(column["ytd"] for column in columns)
    return {
        "units": cashflow_units(handoff) if handoff is not None else None,
        "columns": [
            {
                "label": column["label"],
                "group": column["group"],
                "start": column["start"],
                "end": column["end"],
                "ytd": column["ytd"],
            }
            for column in columns
        ],
        "rows": rows,
        "notes": [note for note in CASHFLOW_NOTES if year_to_date or note != Q1_NOTE],
        "limits": limits,
    }


# Across every model of one page load; a model whose grid would pass it is listed without a grid.
CASHFLOW_CELL_BUDGET = 250_000

# Errors a malformed input file or layout can raise; each is reported, never ends the store.
CASHFLOW_ERRORS = (
    OSError,
    ValueError,
    KeyError,
    TypeError,
    AttributeError,
    IndexError,
    ArithmeticError,
    RecursionError,
    MemoryError,
)


def read_cashflow(
    files: dict[str, bytes], handoff: str | None, budget: int | None = None
) -> tuple[dict[str, Any] | None, tuple[str, str] | None]:
    """(grid, None), or (None, (kind, text)).

    Kind "file" (text: the input that cannot be read), "limit" (text: the limit message, or the
    budget message when the grid passes `budget`, which no cell was computed for) or "layout"
    (text: describe(error) of the failure while laying out). `budget` is the cells left to this
    grid; None means the whole CASHFLOW_CELL_BUDGET, read when called.

    Documented fail-open: an input the reader cannot read or lay out leaves the model listed with
    no grid and a Workspace issue naming the file or the cause. A model too large to parse
    (MemoryError) or nested too deep (RecursionError) is reported the same way, not allowed to end
    the store.
    """
    stage = CASHFLOW_FILES[0]
    try:
        forecast = forecast_inputs(json.loads(files[stage].decode("utf-8")))
        stage = CASHFLOW_FILES[1]
        record = json.loads(files[stage].decode("utf-8"))
        fiscal = fiscal_inputs(record)
        quarter_values = quarter_inputs(record)
        stage = CASHFLOW_FILES[2]
        annual = markdown_tables(files[stage].decode("utf-8"), stage)
        stage = CASHFLOW_FILES[3]
        quarter = markdown_tables(files[stage].decode("utf-8"), stage)
    except CashflowLimit as error:
        return None, ("limit", str(error))
    except CASHFLOW_ERRORS:
        return None, ("file", stage)
    try:
        left = CASHFLOW_CELL_BUDGET if budget is None else budget
        recorded = (fiscal, quarter_values)
        return cashflow_of(forecast, recorded, (annual, quarter), handoff, left), None
    except (CashflowLimit, CashflowBudget) as error:
        return None, ("limit", str(error))
    except CASHFLOW_ERRORS as error:
        return None, ("layout", describe(error))


class GridAsk(NamedTuple):
    """What a model's grid is built from besides its files: its handoff text and its cell budget
    (None: the whole CASHFLOW_CELL_BUDGET)."""

    handoff: str | None
    budget: int | None


def cashflow_or_issues(
    folder: str,
    files: dict[str, Any],
    inputs: dict[str, bytes | None],
    ask: GridAsk,
    issues: list[str],
) -> dict[str, Any] | None:
    """The model's cash flow grid, or None with one issue for each of the four unusable files."""
    present: dict[str, bytes] = {}
    for name in CASHFLOW_FILES:
        data = inputs[name]
        if data is not None:
            present[name] = data
            continue
        what = "does not match its delivery record" if name in files else "is missing or unreadable"
        issues.append(f"{folder}: {name} {what}")
    if len(present) != len(CASHFLOW_FILES):
        return None
    cashflow, problem = read_cashflow(present, ask.handoff, ask.budget)
    if problem is not None:
        kind, text = problem
        issues.append(
            {
                "file": f"{folder}: {text} is missing or unreadable",
                "limit": f"{folder}: {text}",
                "layout": f"{folder}: the cash flow model could not be laid out ({text})",
            }[kind]
        )
    return cashflow


MANIFEST_ERRORS = (
    OSError,
    ValueError,
    KeyError,
    TypeError,
    AttributeError,
    RecursionError,
    MemoryError,
)

Manifests = dict[str, "tuple[dict[str, Any], dict[str, Any]] | str"]


def model_manifests(root: Path, folders: Iterable[str]) -> Manifests:
    """Each folder's (delivery.json, listed view.json), read once, or describe(error) when it
    cannot be read. Documented fail-open: a folder that cannot be read is reported by its readers
    (a Workspace issue or no identity), never ends the store."""
    found: Manifests = {}
    for folder in folders:
        if folder in found:
            continue
        try:
            delivery = delivery_json(root / folder)
            found[folder] = (delivery, listed_view(root / folder, delivery))
        except MANIFEST_ERRORS as error:
            found[folder] = describe(error)
    return found


def available_folders(catalogue: dict[str, Any]) -> list[str]:
    """Every available artifact folder of the catalogue, once, in catalogue order."""
    return list(
        dict.fromkeys(
            artifact["folder"]
            for run in catalogue["real"]
            for artifact in run.get("artifacts") or []
            if artifact.get("available")
        )
    )


def shown_models(
    root: Path, catalogue: dict[str, Any], manifests: Manifests | None = None
) -> tuple[set[str], list[str]]:
    """The one available model folder shown per name (the route id), and the issues for the others.

    A folder is listed once however many runs list it. When folders share a name, the run's own
    delivery (runs/<run_id>/deliveries/<name>, its view.json recording that run) is kept, else the
    first by path; each dropped folder is named in an issue that says which one is shown. Only the
    kept folder is read in full. `manifests` are the folders' model_manifests, read when omitted.
    """
    manifests = (
        model_manifests(root, available_folders(catalogue)) if manifests is None else manifests
    )
    by_name: dict[str, list[str]] = {}
    for run in catalogue["real"]:
        for artifact in run.get("artifacts") or []:
            folder = artifact["folder"]
            if artifact.get("available") and artifact.get("kind") == "model":
                names = by_name.setdefault(Path(folder).name, [])
                if folder not in names:
                    names.append(folder)

    def own(folder: str) -> bool:
        parts = PurePosixPath(folder).parts
        if len(parts) != 4 or parts[0] != "runs" or parts[2] != "deliveries":
            return False
        # Documented fail-open: an unreadable view.json means "not known to be the run's own"; the
        # model read in catalogue_models reports the same failure as a Workspace issue.
        manifest = manifests.get(folder)
        if not isinstance(manifest, tuple):
            return False
        try:
            recorded = manifest[1]["run"]["run_id"]
        except MANIFEST_ERRORS:
            return False
        return bool(recorded == parts[1])

    shown: set[str] = set()
    issues: list[str] = []
    for name, folders in by_name.items():
        kept = next((f for f in folders if own(f)), None) or min(folders)
        shown.add(kept)
        issues.extend(
            f"{f}: another published model has the same name {name}; {kept} is shown"
            for f in sorted(folders)
            if f != kept
        )
    return shown, issues


SourcesOf = Callable[[str, dict[str, Any]], tuple[list[dict[str, Any]], list[str]]]


class ModelReads(NamedTuple):
    """What reading a model needs beyond its folder: the root, the issuer keys and the once-per-
    load sources of a model (see catalogue_models)."""

    root: Path
    keys: dict[str, str]
    sources_of: SourcesOf


def read_model(
    reads: ModelReads,
    artifact: dict[str, Any],
    manifest: tuple[dict[str, Any], dict[str, Any]] | str,
    issues: list[str],
    budget: int | None = None,
) -> dict[str, Any] | None:
    """One published model with its grid, or None with an issue when its record cannot be read.

    `manifest` is the model_manifests entry; `reads.sources_of(folder, delivery)` gives the
    model's (source rows, their issues); `budget` is the grid cells left (see read_cashflow).
    """
    root, keys, sources_of = reads
    folder = artifact["folder"]
    if isinstance(manifest, str):
        issues.append(f"{folder}: could not be read ({manifest})")
        return None
    delivery, view = manifest
    # Documented fail-open: reported in Settings; the other models stay readable. A model too
    # large to parse (MemoryError) is reported the same way, never ends the store.
    try:
        identity = view["run"]
        run_id = identity["run_id"]
        issuer_key = report_issuer_key(keys, identity.get("issuer_id"))
        sources, source_issues = sources_of(folder, delivery)
        issues.extend(source_issues)
        register = handoff_text = None
        files = delivery["files"]
        if "forecast.md" in files:
            handoff = listed_bytes(root / folder, delivery, "forecast.md")
            if handoff is None:
                issues.append(f"{folder}: forecast.md does not match its delivery record")
            else:
                handoff_text = handoff.decode("utf-8")
                register = register_of(sections_of(handoff_text))
        inputs = {
            name: listed_bytes(root / folder, delivery, name) if name in files else None
            for name in CASHFLOW_FILES
        }
        previous = delivery.get("previous_directory")
    except MANIFEST_ERRORS as error:
        issues.append(f"{folder}: could not be read ({describe(error)})")
        return None
    cashflow = cashflow_or_issues(folder, files, inputs, GridAsk(handoff_text, budget), issues)
    mode, qualification = view.get("mode"), view.get("analytical_qualification")
    return {
        "id": Path(folder).name,
        "issuerKey": issuer_key,
        "mode": mode if isinstance(mode, str) else None,
        "qualification": qualification if isinstance(qualification, str) else None,
        "runId": run_id if isinstance(run_id, str) else None,
        "scope": text_or_none(delivery.get("scope")),
        "inputContract": text_or_none(delivery.get("input_contract")),
        "revisionNote": text_or_none(delivery.get("presentation_repair")),
        "previous": Path(previous).name if isinstance(previous, str) else None,
        "href": artifact["href"] + "&embedded=1",
        "download": artifact["href"] + "&download=1",
        "files": [
            {"name": n, "href": f"/files/{quote(f'{folder}/{n}')}?sha256={h}&download=1"}
            for n, h in sorted(files.items())
        ],
        "sources": sources,
        "register": register,
        "cashflow": cashflow,
    }


def run_shows(
    artifact: dict[str, Any],
    manifest: tuple[dict[str, Any], dict[str, Any]] | str,
    keys: dict[str, str],
    sources_of: SourcesOf,
    runs: dict[str, dict[str, Any]],
) -> bool:
    """Whether a run's Forecast lists this model: the same issuer key and the run named by the
    model's run_id or by one of its sources (the rule of views.js runModels)."""
    folder = artifact["folder"]
    # Documented fail-open: a record that cannot be read is not shown by a run; read_model reports
    # the same failure as a Workspace issue.
    if isinstance(manifest, str):
        return False
    delivery, view = manifest
    try:
        identity = view["run"]
        key = report_issuer_key(keys, identity.get("issuer_id"))
        if key is None:
            return False
        held = {route for route, run in runs.items() if run["issuerKey"] == key}
        if any(runs[route]["folder"] == identity["run_id"] for route in held):
            return True
        return any(row["run"] in held for row in sources_of(folder, delivery)[0])
    except MANIFEST_ERRORS:
        return False


class WorkspaceReads(NamedTuple):
    """What the store has read before the models: outputs, issuer keys, runs, model manifests."""

    outputs: dict[str, Any]
    keys: dict[str, str]
    runs: dict[str, dict[str, Any]]
    manifests: Manifests


def catalogue_models(
    root: Path,
    catalogue: dict[str, Any],
    prior: WorkspaceReads,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Published models the server verified, each once, with why and from what they were built.

    The models share one budget of CASHFLOW_CELL_BUDGET grid cells. Models some run shows
    (runs: the store's runs) are laid out first, then the rest, each in delivery path
    order; a model whose grid would pass the budget is listed without one, with an issue and
    without computing any of its cells. Each folder's manifest (`prior.manifests`) and each
    model's sources are read once.
    """
    outputs, keys, runs, manifests = prior
    shown, issues = shown_models(root, catalogue, manifests)
    held: dict[str, tuple[list[dict[str, Any]], list[str]] | Exception] = {}

    def sources_of(folder: str, delivery: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
        if folder not in held:
            found: list[str] = []
            try:
                held[folder] = (model_sources(root, delivery, outputs, folder, found), found)
            except MANIFEST_ERRORS as error:
                held[folder] = error
        result = held[folder]
        if isinstance(result, Exception):
            raise result
        return result

    listed: list[dict[str, Any]] = []
    done: set[str] = set()
    for run in catalogue["real"]:
        for artifact in run.get("artifacts") or []:
            folder = artifact["folder"]
            model = artifact.get("available") and artifact.get("kind") == "model"
            if model and folder in shown and folder not in done:
                done.add(folder)
                listed.append(artifact)
    built: dict[int, dict[str, Any]] = {}
    cells = 0
    reads = ModelReads(root, keys, sources_of)
    unshown = {
        i
        for i, artifact in enumerate(listed)
        if not run_shows(artifact, manifests[artifact["folder"]], keys, sources_of, runs)
    }
    for position in sorted(range(len(listed)), key=lambda i: (i in unshown, listed[i]["folder"])):
        artifact = listed[position]
        model = read_model(
            reads, artifact, manifests[artifact["folder"]], issues, CASHFLOW_CELL_BUDGET - cells
        )
        if model is None:
            continue
        grid = model["cashflow"]
        if grid is not None:
            cells += len(grid["rows"]) * len(grid["columns"])
        built[position] = model
    return [built[position] for position in sorted(built)], issues


def visual_catalogue() -> list[dict[str, str]]:
    with (REPO / "docs/visualisations/catalogue.csv").open(encoding="utf-8-sig") as source:
        return list(csv.DictReader(source))


def recorded_run(run_dir: Path, issues: list[str] | None = None) -> dict[str, str]:
    """The text fields of the launcher's own manifest; a run without a readable one records none.

    Documented fail-open: a manifest that cannot be read records nothing and, when `issues` is
    given, is named there by type and reason (never its bytes). A run with no manifest is normal.
    """
    try:
        raw = b"".join(regular_chunks(run_dir / "workflow.json", follow=False))
        manifest = json.loads(raw.decode("utf-8"))
        return {key: value for key, value in manifest["run"].items() if isinstance(value, str)}
    except FileNotFoundError:
        return {}
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        RecursionError,
        MemoryError,
    ) as error:
        if issues is not None:
            issues.append(f"{run_dir.name}: workflow.json could not be read ({describe(error)})")
        return {}


def delivery_identities(
    root: Path, catalogue: dict[str, Any], manifests: Manifests | None = None
) -> list[dict[str, Any]]:
    """What each available (hash-verified) deliverable says about its own run and issuer.

    A deliverable whose view.json cannot be read is skipped here; catalogue_reports names it in
    Workspace issues, so the failure is reported once and no run takes an identity from it.
    `manifests` are the folders' model_manifests, read when omitted.
    """
    manifests = (
        model_manifests(root, available_folders(catalogue)) if manifests is None else manifests
    )
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    for run in catalogue["real"]:
        for artifact in run.get("artifacts") or []:
            folder = artifact["folder"]
            if not artifact.get("available") or folder in seen:
                continue
            seen.add(folder)
            manifest = manifests.get(folder)
            if not isinstance(manifest, tuple):
                continue
            try:
                identity = manifest[1]["run"]
                run_id, name = identity["run_id"], identity["issuer_name"]
                issuer_id = identity.get("issuer_id") or None
            except MANIFEST_ERRORS:
                continue
            if isinstance(run_id, str) and isinstance(name, str) and name:
                valid_id = issuer_id if isinstance(issuer_id, str) else None
                found.append(
                    {"folder": folder, "run_id": run_id, "issuer_id": valid_id, "issuer_name": name}
                )
    return sorted(found, key=lambda item: item["folder"])


def squeezed(text: str) -> str:
    """A name compared as a reader reads it: case and runs of spaces do not count."""
    return " ".join(text.split()).casefold()


def named_run_id(
    name: str, issuer_id: str | None, delivered: list[dict[str, Any]]
) -> tuple[str | None, str | None]:
    """A named run's ID and the issue to report, from what its deliverables say.

    Deliverables agree when their case-folded IDs agree, whatever they call the issuer. If they
    disagree, the ID the run has stays and the disagreement is reported. If they agree on an ID
    but call the issuer something other than the run's name, the ID is taken and the names are
    reported.
    """
    if len({(item["issuer_id"] or "").casefold() for item in delivered}) > 1:
        return issuer_id, "deliverables name different issuers; no issuer ID taken"
    if not delivered:
        return issuer_id, None
    others = sorted(
        {
            item["issuer_name"]
            for item in delivered
            if squeezed(item["issuer_name"]) != squeezed(name)
        }
    )
    taken = issuer_id or delivered[0]["issuer_id"]
    issue = (
        f"deliverables name the issuer {', '.join(repr(o) for o in others)}, not {name!r}; "
        + ("issuer ID kept" if taken else "no issuer ID recorded")
        if others
        else None
    )
    return taken, issue


def recorded_identity(
    run_dir: Path, run: dict[str, Any], curated_name: str | None, delivered: list[dict[str, Any]]
) -> tuple[str | None, str | None, str | None]:
    """A run's recorded issuer (name, ID) and, if its deliverables disagree, the issue to report.

    Name: curated, else the launcher manifest, else a catalogue name unlike the folder, else what
    its deliverables agree on. ID: manifest, else the catalogue's issuer, else the deliverables'.
    """
    manifest = recorded_run(run_dir)
    name = (
        curated_name
        or manifest.get("issuer_name")
        or (run["name"] if run["name"] != run["id"] else None)
    )
    seeded = run.get("issuer")
    issuer_id = manifest.get("issuer_id") or (seeded if seeded != "Unclassified" else None)
    said: dict[tuple[str, Any], dict[str, Any]] = {}
    # In folder order, so the first deliverable's spelling of the ID is kept.
    for item in delivered:
        said.setdefault(((item["issuer_id"] or "").casefold(), item["issuer_name"]), item)
    if name:
        return name, *named_run_id(name, issuer_id, delivered)
    if len(said) > 1:
        return None, issuer_id, "deliverables name different issuers; issuer left unrecorded"
    if said:
        (agreed,) = said.values()
        return agreed["issuer_name"], issuer_id or agreed["issuer_id"], None
    return None, issuer_id, None


def ids_by_name(named: dict[str, tuple[str, str | None]]) -> dict[str, dict[str, str]]:
    """Each recorded name's IDs as recorded, by case-folded ID."""
    carried: dict[str, dict[str, str]] = {}
    for _, (name, issuer_id) in sorted(named.items()):  # run-path order, not insertion order
        if issuer_id:
            carried.setdefault(name, {}).setdefault(issuer_id.casefold(), issuer_id)
    return carried


def issuer_groups(
    recorded: dict[str, tuple[str | None, str | None]], issues: list[str] | None = None
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """Group runs by issuer. recorded maps run key to (name or None, ID or None).

    Runs with a name join when they share a case-folded ID. A name joins runs without an ID to the
    one ID that carries it; two different IDs are never joined through a name. A name carried by
    several IDs leaves its runs without an ID in a group of their own and, when `issues` is given,
    adds one issue naming the IDs. Returns the identity fields of every run and a map from each
    case-folded ID to its group's key.
    """
    named = {key: (name, issuer_id) for key, (name, issuer_id) in recorded.items() if name}
    carried = ids_by_name(named)
    if issues is not None:
        issues.extend(
            f"issuer name {name} is recorded with different issuer IDs: "
            + ", ".join(sorted(ids.values(), key=lambda i: (i.casefold(), i)))
            for name, ids in sorted(carried.items())
            if len(ids) > 1
        )
    parent = {key: key for key in named}

    def root_of(key: str) -> str:
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    first: dict[tuple[str, str], str] = {}
    for key, (name, issuer_id) in named.items():
        # An ID joins its runs; a run without an ID joins its name's one ID, else other such runs.
        if issuer_id:
            token = ("id", issuer_id.casefold())
        else:
            holders = carried.get(name, {})
            token = ("id", next(iter(holders))) if len(holders) == 1 else ("name", name)
        parent[root_of(key)] = root_of(first.setdefault(token, key))
    members: dict[str, list[str]] = {}
    for key in named:
        members.setdefault(root_of(key), []).append(key)
    fields: dict[str, dict[str, Any]] = {
        key: {"issuerKey": None, "issuerHeading": None, "issuerTerms": []} for key in recorded
    }
    keys: dict[str, str] = {}
    for group in members.values():
        names = Counter(named[key][0] for key in group)
        heading = min(names, key=lambda name: (-names[name], name.casefold(), name))
        ids = {known for key in group if (known := named[key][1])}
        folded = {issuer_id.casefold() for issuer_id in ids}
        group_key = f"id:{min(folded)}" if folded else f"name:{heading}"
        keys |= dict.fromkeys(folded, group_key)
        for key in group:
            fields[key] = {
                "issuerKey": group_key,
                "issuerHeading": heading,
                "issuerTerms": sorted({*names, *ids}),
            }
    return fields, keys


def report_issuer_key(keys: dict[str, str], issuer_id: Any) -> str | None:
    """The key of the group holding a report's issuer ID, or one built from that ID alone."""
    if not isinstance(issuer_id, str) or not issuer_id:
        return None
    return keys.get(issuer_id.casefold(), f"id:{issuer_id.casefold()}")


def run_row(root: Path, run: dict[str, Any], name: str | None = None) -> tuple[str, ...]:
    """Labels for a run with no curated ones: the launcher's own manifest, else the catalogue."""
    folder = run["id"]
    identity = recorded_run(root / "runs" / folder)
    issuer = name or identity.get("issuer_name") or run["name"]
    period = (
        f"As of {display_date(identity['as_of'])}"
        if identity.get("as_of")
        else run.get("period") or "Period not recorded"
    )
    # A web run's folder is 32 hex characters; eight are enough to tell runs apart on screen.
    label = folder.upper()[:12] if WEB_RUN.fullmatch(folder) else folder.upper()
    return (folder, issuer, issuer, label, run.get("sector") or "Unclassified", period)


def shown_runs(
    root: Path, catalogue: dict[str, Any], issues: list[str], manifests: Manifests | None = None
) -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[str | None, str | None]]]:
    """The runs to show by route key, and each one's recorded (issuer name, issuer ID).

    A folder that cannot be linked or that takes a retained case's route key is named in `issues`.
    """
    curated = {row[0]: (key, row) for key, row in CURATED_RUNS.items()}
    shown: dict[str, tuple[str, ...]] = {}
    recorded: dict[str, tuple[str | None, str | None]] = {}
    delivered: dict[str, list[dict[str, Any]]] = {}
    for item in delivery_identities(root, catalogue, manifests):
        delivered.setdefault(item["run_id"], []).append(item)
    route_keys = {curated[run["id"]][0] for run in catalogue["real"] if run["id"] in curated}
    for run in catalogue["real"]:
        folder = run["id"]
        if folder.startswith("delivery:"):
            continue
        if not SAFE_FOLDER.fullmatch(folder):
            issues.append(f"{folder}: folder name cannot be linked; rename it to show this run")
            continue
        if folder in route_keys and folder not in curated:
            # The route key names the retained case in links and pins: never replace it.
            issues.append(f"{folder}: name is a retained case's route key; rename it to show it")
            continue
        key, row = curated.get(folder) or (folder, None)
        name, issuer_id, problem = recorded_identity(
            root / "runs" / folder, run, row[1] if row else None, delivered.get(folder, [])
        )
        if problem:
            issues.append(f"runs/{folder}: {problem}")
        shown[key] = row or run_row(root, run, name)
        recorded[key] = (name, issuer_id)
    return shown, recorded


def workspace_store(root: str | Path, catalogue: dict[str, Any]) -> dict[str, Any]:
    """Everything the app reads. A curated pin that stopped matching is dropped, not fatal."""
    root = Path(root)
    catalog = json.loads((HERE / "catalog.json").read_text(encoding="utf-8"))
    issues = list(catalogue.get("issues") or [])
    manifests = model_manifests(root, available_folders(catalogue))
    shown, recorded = shown_runs(root, catalogue, issues, manifests)

    def link(folder: str, relative: str, digest: str) -> str:
        return f"/files/{quote(f'runs/{folder}/{relative}')}?sha256={digest}"

    runs: dict[str, Any] = {}
    outputs: dict[str, Any] = {}
    inputs: dict[str, Any] = {}
    sources: dict[str, list[dict[str, Any]]] = {}
    pins: dict[str, Any] = {}
    handoffs = Handoffs(strict=False)
    found: list[str] = []
    for key, row in shown.items():
        # Documented fail-open: one run that cannot be read is hidden and reported in Settings.
        try:
            part = collect_runs(root, {key: row}, catalog, link, handoffs)
        except Exception as error:  # noqa: BLE001
            found.append(f"{row[0]}: could not be read ({describe(error)})")
            continue
        runs |= part[0]
        outputs |= part[1]
        inputs |= part[2]
        for digest, matches in part[3].items():
            sources.setdefault(digest, []).extend(matches)
        pins |= part[4]
        found += part[5]
    fields, keys = issuer_groups({key: recorded[key] for key in runs}, found)
    for key, identity in fields.items():
        runs[key].update(identity)
    reports, unread = catalogue_reports(root, catalogue, sources, keys)
    found += unread
    models, unread = catalogue_models(
        root, catalogue, WorkspaceReads(outputs, keys, runs, manifests)
    )
    found += unread
    # A compared deliverable is a curated build, not a folder that merely has its name.
    for module, config in catalog.items():
        compare = config.get("compare")
        if (
            module in pins
            and compare
            and not (
                compare["recheck"] in outputs
                and {compare["prior"], compare["current"], compare["repaired"]}
                <= {r["id"] for r in reports if r["build"]}
            )
        ):
            del pins[module]
            found.append(
                f"{module}: curated pin dropped: a compared deliverable or recheck is missing"
            )
    return {
        "runs": runs,
        "outputs": outputs,
        # Only what an output shown refers to: a run that failed part-way leaves nothing behind.
        "handoffs": {o["sha256"]: handoffs.parsed[o["sha256"]][0] for o in outputs.values()},
        "inputs": inputs,
        "pins": pins,
        "reports": reports,
        "models": models,
        "visuals": visual_catalogue(),
        "issues": issues + found,
    }


if __name__ == "__main__":
    print(json.dumps(workspace_store(Path(sys.argv[1]), json.load(sys.stdin)), ensure_ascii=False))
