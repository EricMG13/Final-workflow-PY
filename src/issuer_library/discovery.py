"""Discovery of runs and deliveries in a workspace.

Admission preserves explicit metadata; it does not interpret arbitrary prose
or infer an issuer, period, ratio definition or completion from a filename.
"""

from __future__ import annotations

import math
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from pydantic import ValidationError

from .model import (
    Artifact,
    Catalogue,
    Checklist,
    Counts,
    DeliveryRecord,
    DeliveryView,
    Facility,
    FileLink,
    LaunchedWorkflow,
    Manifest,
    Metric,
    RecordedIdentity,
    Run,
    Source,
    blank_run,
    digest,
    file_url,
    folders,
    local_path,
    pinned_url,
    read_file,
    read_json,
)

# One number in full: an optional leading minus, digits with thousands commas grouping exactly
# three digits, and an optional decimal part.
WHOLE_NUMBER = re.compile(r"-?(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?")
LEADING_GROUP = re.compile(r"-?[0-9]{1,3}")
TRAILING_GROUP = re.compile(r"[0-9]{3}(?:[^0-9]|\Z)")
DASHES = "-\u2010\u2011\u2012\u2013\u2014\u2212"
SPACES = " \u00a0\u2009\u202f"
EXPONENT_GAPS = ("e", "E", "e+", "E+")
SOURCE_KEY = re.compile(r"[a-zA-Z0-9_-]+")
CALENDAR_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
DATA_ROOTS = ("runs/", "data/", "deliverables/")
STAGES = ("sources", "analysis", "verification", "downstream", "delivery")
LISTED = {".md", ".txt", ".pdf", ".html", ".htm", ".json", ".csv", ".xlsx"}
RUN_FILE_LIMIT = 5000
MANIFEST_SCHEMA = "issuer-library-run/1"


def describe(error: Exception) -> str:
    """One line for a discovery notice; a validation error names each field."""
    if isinstance(error, ValidationError):
        return "; ".join(
            f"{'.'.join(str(part) for part in item['loc']) or 'document'}: {item['msg']}"
            for item in error.errors()
        )
    return str(error)


def calendar_date(value: str) -> bool:
    if not CALENDAR_DATE.fullmatch(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def number_char(char: str) -> bool:
    """A character that can belong to a written number: digits, decimal and group separators,
    dashes and the slash of a date. A run of them is read as a whole, never in fragments."""
    return sign_or_digit(char) or char in ".,'\u2019/"


def is_dash(char: str) -> bool:
    return char in DASHES


def sign_or_digit(char: str) -> bool:
    return "0" <= char <= "9" or is_dash(char)


@dataclass(frozen=True)
class NumberRun:
    start: int
    end: int
    depth: int
    text: str


def number_runs(chars: str) -> list[NumberRun]:
    """Maximal runs of number characters, trailing . and , trimmed, with the parenthesis depth."""
    runs: list[NumberRun] = []
    depth = 0
    i = 0
    while i < len(chars):
        if not number_char(chars[i]):
            if chars[i] == "(":
                depth += 1
            elif chars[i] == ")" and depth > 0:
                depth -= 1
            i += 1
            continue
        start = i
        while i < len(chars) and number_char(chars[i]):
            i += 1
        end = i
        while end > start and chars[end - 1] in ".,":
            end -= 1
        runs.append(NumberRun(start, end, depth, chars[start:end]))
    return runs


def grouped_runs(chars: str, runs: list[NumberRun]) -> set[int]:
    """Indexes of runs that read as space-grouped thousands (1 234) or an exponent (1.2e3)."""
    grouped: set[int] = set()
    for k in range(1, len(runs)):
        before, after = runs[k - 1], runs[k]
        gap = chars[before.end : after.start]
        spaced = (
            len(gap) == 1
            and gap in SPACES
            and LEADING_GROUP.fullmatch(before.text) is not None
            and TRAILING_GROUP.match(after.text) is not None
        )
        exponent = gap in EXPONENT_GAPS and before.text != "" and after.text != ""
        if spaced or exponent:
            grouped.update((k - 1, k))
    return grouped


def accounting_number(chars: str, run: NumberRun, number: str) -> str | None:
    """The value of a number inside parentheses: only the exact form "(x)" stands alone, as -x,
    with no sign inside it and no sign or digit around it."""
    exact = (
        chars[run.start - 1] == "("
        and run.end < len(chars)
        and chars[run.end] == ")"
        and number[0] != "-"
    )
    if not exact:
        return None
    if run.start > 1 and sign_or_digit(chars[run.start - 2]):
        return None
    if run.end + 1 < len(chars) and sign_or_digit(chars[run.end + 1]):
        return None
    return "-" + number


def run_number(chars: str, run: NumberRun) -> str | None:
    """The number a run states, or None when its sign or scale is not known."""
    if WHOLE_NUMBER.fullmatch(run.text) is None:
        return None
    if run.text[0] == "-" and run.start > 0 and chars[run.start - 1].isalpha():
        return None
    # A minus before a currency symbol (-$5) is a sign this reader does not move.
    if (
        run.start > 1
        and unicodedata.category(chars[run.start - 1]) == "Sc"
        and is_dash(chars[run.start - 2])
    ):
        return None
    number = run.text.replace(",", "")
    # The end of a parenthesis opened before the quote: its sign is unknown.
    if run.depth == 0 and run.end < len(chars) and chars[run.end] == ")":
        return None
    if run.depth > 0:
        return accounting_number(chars, run, number)
    return number


def stated_numbers(quote: str) -> list[str]:
    """The numbers a quote states, as decimal strings without thousands commas.

    A maximal run of number characters counts only when all of it is one whole number, so a
    date, range, list or figure in another separator convention states nothing rather than a
    fragment of itself; sentence punctuation after a number is dropped. These also state nothing:
    a minus joined to a word (COVID-19) or placed before a currency symbol (-$5), two runs that
    read as space-grouped thousands (1 234) or as an exponent (1.2e3), and a number closing a
    parenthesis the quote did not open. Inside parentheses only the exact accounting form "(x)"
    has a known sign, -x; any other parenthesised number, or "(x)" next to a dash or digit, is
    not taken.
    """
    runs = number_runs(quote)
    grouped = grouped_runs(quote, runs)
    numbers = (run_number(quote, run) for k, run in enumerate(runs) if k not in grouped)
    return [number for number in numbers if number is not None]


def verify_source(root: Path, source: Source) -> Source:
    if not source.path.startswith(DATA_ROOTS):
        raise ValueError("source is outside workspace data directories")
    raw = read_file(root, source.path)
    if len(source.sha256) != 64 or digest(raw) != source.sha256:
        raise ValueError(f"source hash changed: {source.path}")
    lines = raw.decode("utf-8", "surrogateescape").replace("\r\n", "\n").split("\n")
    if source.line < 1 or source.line > len(lines) or lines[source.line - 1] != source.quote:
        raise ValueError(f"source excerpt changed: {source.path}")
    return source.model_copy(update={"href": pinned_url(source.path, source.sha256)})


def check_metric(metric: Metric, verified: dict[str, Source]) -> None:
    if metric.provenance not in ("", "cited", "calculated", "synthetic", "user"):
        raise ValueError("metric provenance must be cited, calculated, synthetic, user or omitted")
    try:
        value = float(metric.value)
    except ValueError:
        value = math.nan
    pinned = verified.get(metric.source)
    if (
        not math.isfinite(value)
        or pinned is None
        or not metric.unit
        or not metric.period
        or not metric.basis
    ):
        raise ValueError(
            "metric requires finite exact value, unit, period, basis and pinned source"
        )
    if metric.value not in stated_numbers(pinned.quote):
        raise ValueError("metric value absent from source excerpt")


FACILITY_TERM_KEYS = (
    "size_m",
    "tenor_years",
    "talk_spread_bps_low",
    "talk_spread_bps_high",
    "talk_oid_low",
    "talk_oid_high",
    "floor_pct",
    "coupon_pct",
    "margin_bps",
)
QUOTE_TERM_KEYS = ("bid", "ask", "price", "yield_pct", "spread_bps")
GO_ESCAPES = {
    "\a": "\\a",
    "\b": "\\b",
    "\f": "\\f",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
    "\v": "\\v",
    "\\": "\\\\",
    '"': '\\"',
}


def go_quote(text: str) -> str:
    """Go's strconv.Quote (the %q verb): printable runes as they are, the rest escaped.

    Printability follows Python's Unicode tables (15.1 on Python 3.13), while Go 1.26's
    strconv.Quote uses Unicode 15.0, so the 627 code points added in 15.1 (U+2FFC-U+2FFF, U+31EF,
    U+2EBF0-U+2EE5D) print raw here and are escaped in Go. Only the error text differs; such a key
    is rejected either way.
    """
    parts = []
    for char in text:
        code = ord(char)
        if char in GO_ESCAPES:
            parts.append(GO_ESCAPES[char])
        elif char.isprintable():
            parts.append(char)
        elif code < 0x80:
            parts.append(f"\\x{code:02x}")
        elif code < 0x10000:
            parts.append(f"\\u{code:04x}")
        else:
            parts.append(f"\\U{code:08x}")
    return '"' + "".join(parts) + '"'


def facility_metrics(facility: Facility) -> list[Metric]:
    """Every term metric of a facility, its quotes included."""
    found = [metric for metric in facility.terms.values() if metric is not None]
    for quote in facility.quotes:
        found.extend(metric for metric in quote.terms.values() if metric is not None)
    return found


def check_terms(
    terms: dict[str, Metric | None], allowed: tuple[str, ...], verified: dict[str, Source]
) -> None:
    """Only the allowed term keys, each a user-provenance metric passing check_metric."""
    for key in sorted(terms):
        metric = terms[key]
        if key not in allowed:
            raise ValueError(f"facility term {go_quote(key)} is not an allowed term")
        if metric is None or metric.provenance != "user":
            raise ValueError(f"facility term {go_quote(key)} must be a user-entered metric")
        try:
            check_metric(metric, verified)
        except ValueError as error:
            raise ValueError(f"facility term {go_quote(key)}: {error}") from error


def check_quoted_source(name: str, key: str, value: str, verified: dict[str, Source]) -> None:
    """A verified source whose quote holds the value in double quotes."""
    source = verified.get(key)
    if source is None or f'"{value}"' not in source.quote:
        raise ValueError(f"{name} needs a pinned source stating {go_quote(value)}")


def check_facilities(run: Run, verified: dict[str, Source]) -> None:
    seen: set[str] = set()
    for facility in run.facilities:
        if not facility.facility_id or facility.facility_id in seen:
            raise ValueError("facility_id must be non-empty and unique within the run")
        seen.add(facility.facility_id)
        check_terms(facility.terms, FACILITY_TERM_KEYS, verified)
        for quote in facility.quotes:
            if quote.kind not in ("observed", "indicative_talk"):
                raise ValueError("facility quote kind must be observed or indicative_talk")
            check_terms(quote.terms, QUOTE_TERM_KEYS, verified)


def check_credit_keys(run: Run, verified: dict[str, Source]) -> None:
    """Classification, private side and facilities under the same rule as metrics: each is backed
    by an exact value in a pinned quote.
    """
    if not run.classification and run.classification_source:
        raise ValueError("classification_source needs a classification")
    if run.classification:
        if run.classification not in ("investment_grade", "high_yield"):
            raise ValueError("classification must be investment_grade or high_yield")
        check_quoted_source(
            "classification", run.classification_source, run.classification, verified
        )
    if not run.private_side and run.private_side_source:
        raise ValueError("private_side_source needs private_side")
    if run.private_side:
        check_quoted_source("private_side", run.private_side_source, "private", verified)
    check_facilities(run, verified)


def verify_identity(root: Path, manifest: Manifest, run: Run, run_id: str) -> dict[str, Source]:
    """The manifest's pinned sources, verified, after the run's identity checks."""
    if run.id != run_id or not run.name or not run.issuer:
        raise ValueError("run identity must match folder and include issuer/name")
    if run.date and not calendar_date(run.date):
        raise ValueError("invalid evidence date")
    verified: dict[str, Source] = {}
    for key, source in manifest.sources.items():
        if not SOURCE_KEY.fullmatch(key):
            raise ValueError("invalid source key")
        verified[key] = verify_source(root, source)
    for key in (run.identity_source, run.sector_source):
        if key and key not in verified:
            raise ValueError("missing identity/sector source")
    if not run.identity_source:
        raise ValueError("issuer identity needs a pinned source")
    if run.sector and run.sector != "Unclassified" and not run.sector_source:
        raise ValueError("sector needs a pinned source")
    return verified


def apply_defaults(root: Path, run: Run, run_id: str) -> None:
    if not run.sector:
        run.sector = "Unclassified"
    if not run.period:
        run.period = "Not established"
    if not run.workflow:
        run.workflow = "Unclassified"
    if run.handoff:
        if not run.handoff.startswith(f"runs/{run_id}/"):
            raise ValueError("primary handoff must belong to run")
        run.handoff_href = pinned_url(run.handoff, digest(read_file(root, run.handoff)))


def prefix_sources(run: Run, run_id: str) -> None:
    """Qualify every source key the run names with its run id, as the catalogue publishes them."""
    for metric in run.metrics.values():
        if metric is not None:
            metric.source = f"{run_id}.{metric.source}"
    for rating in run.ratings:
        rating.source = f"{run_id}.{rating.source}"
    if run.classification_source:
        run.classification_source = f"{run_id}.{run.classification_source}"
    if run.private_side_source:
        run.private_side_source = f"{run_id}.{run.private_side_source}"
    for facility in run.facilities:
        for metric in facility_metrics(facility):
            metric.source = f"{run_id}.{metric.source}"


def admit_run(root: Path, manifest: Manifest, run_id: str, cat: Catalogue) -> Run:
    run = manifest.run.model_copy(deep=True)
    verified = verify_identity(root, manifest, run, run_id)
    for metric in run.metrics.values():
        if metric is not None:
            check_metric(metric, verified)
    for rating in run.ratings:
        if rating.source not in verified:
            raise ValueError("rating requires pinned source")
        if rating.scope not in ("", "issuer", "facility"):
            raise ValueError("rating scope must be issuer, facility or omitted")
    check_credit_keys(run, verified)
    run.completion = None
    run.checkpoints = None
    if manifest.checklist is not None:
        counts = assess_checklist(manifest.checklist, verified)
        run.completion = counts.done * 100 // counts.total
        run.checkpoints = counts
        run._delivery_claimed = any(
            item.stage == "delivery" and item.done for item in manifest.checklist.requirements
        )
    run.handoff_href = ""
    apply_defaults(root, run, run_id)
    # Publish references only after every check succeeds: failed records cannot
    # leave admitted files or source labels behind in the aggregate catalogue.
    for key, source in verified.items():
        cat.sources[f"{run_id}.{key}"] = source
        cat._allowed[source.path] = source.sha256
    prefix_sources(run, run_id)
    if run.identity_source:
        run.identity_source = f"{run_id}.{run.identity_source}"
    if run.sector_source:
        run.sector_source = f"{run_id}.{run.sector_source}"
    return run


def assess_checklist(checklist: Checklist, sources: dict[str, Source]) -> Counts:
    counts = Counts(total=len(checklist.requirements))
    if not checklist.scope or counts.total == 0:
        raise ValueError("checklist needs scope and required checkpoints")
    stages = dict.fromkeys(STAGES, False)
    seen: set[str] = set()
    for item in checklist.requirements:
        if not item.id or item.id in seen:
            raise ValueError("duplicate or empty checkpoint")
        seen.add(item.id)
        if item.stage not in stages:
            raise ValueError("unknown checkpoint stage")
        stages[item.stage] = True
        if item.done:
            if not item.evidence:
                raise ValueError("completed checkpoint has no evidence")
            for key in item.evidence:
                if key not in sources:
                    raise ValueError("checkpoint evidence not verified")
            counts.done += 1
    if not all(stages.values()):
        raise ValueError(
            "checklist must cover sources, analysis, verification, downstream and delivery"
        )
    return counts


def index_run_files(root: Path, folder: str, cat: Catalogue, run: Run) -> None:
    """List the run's retained files in name order; links and hidden entries are not enumerated."""
    run.files = []
    count = 0

    def walk(relative: str) -> None:
        nonlocal count
        with os.scandir(root / relative) as entries:
            found = sorted(entries, key=lambda entry: entry.name)
        for entry in found:
            name = f"{relative}/{entry.name}"
            if entry.is_dir(follow_symlinks=False):
                if not entry.name.startswith("."):
                    walk(name)
                continue
            if not entry.is_file(follow_symlinks=False) or entry.name.startswith("."):
                continue
            if os.path.splitext(entry.name)[1].lower() not in LISTED:
                continue
            count += 1
            if count > RUN_FILE_LIMIT:
                raise ValueError(f"run file limit ({RUN_FILE_LIMIT}) reached")
            cat._allowed.setdefault(name, "")
            run.files.append(FileLink(name=name.removeprefix(f"{folder}/"), href=file_url(name)))

    try:
        walk(folder)
    except (OSError, ValueError) as error:
        cat.issues.append(f"{folder}: {error}")


def pin_delivery_files(
    root: Path, folder: str, record: DeliveryRecord, view: DeliveryView
) -> tuple[str, DeliveryView, dict[str, str]]:
    """Every file the delivery lists, read and hashed; the first problem as text, else ""."""
    files: dict[str, str] = {}
    for name, sha256 in record.files.items():
        if not local_path(name):
            return "Invalid delivery path", view, files
        try:
            raw = read_file(root, f"{folder}/{name}")
        except (OSError, ValueError):
            raw = None
        if raw is None or digest(raw) != sha256:
            return f"Missing or changed delivery file: {name}", view, files
        if name == "view.json":
            try:
                view = DeliveryView.model_validate_json(raw)
            except ValueError:
                return "Invalid delivery identity", view, files
        files[f"{folder}/{name}"] = sha256
    return "", view, files


def verify_delivery(root: Path, folder: str) -> tuple[Artifact, DeliveryView, dict[str, str]]:
    artifact = Artifact(
        folder=folder, label=os.path.basename(folder), state="candidate", relationship="direct"
    )
    view = DeliveryView()
    try:
        record = read_json(root, f"{folder}/delivery.json", DeliveryRecord)
    except (OSError, ValueError) as error:
        artifact.issue = describe(error)
        return artifact, view, {}
    # A delivery presents either a report or, lacking one, a published model.
    page, artifact.kind = "report.html", "report"
    if not record.files.get(page) and record.files.get("model.html"):
        page, artifact.kind = "model.html", "model"
    if not record.files.get(page) or not record.files.get("view.json"):
        artifact.issue = "Delivery manifest requires report.html and view.json"
        return artifact, view, {}
    artifact.issue, view, files = pin_delivery_files(root, folder, record, view)
    if not artifact.issue and not (view.run.issuer_id and view.run.issuer_name and view.run.run_id):
        artifact.issue = "Missing delivery issuer/run identity"
    elif not artifact.issue and not calendar_date(view.run.as_of):
        artifact.issue = "Invalid delivery evidence date"
    if artifact.issue:
        return artifact, view, files
    artifact.available = True
    artifact.href = pinned_url(f"{folder}/{page}", record.files[page])
    if view.mode:
        artifact.state = view.mode
    return artifact, view, files


def run_delivery_identity_issue(
    root: Path, folder: str, run_id: str, run: Run, view: DeliveryView
) -> str:
    """Check a delivery kept inside runs/<id>/deliveries against that run; "" when it belongs.

    The launcher names the folder web-<hex> but stamps its deliveries with the run identity
    recorded in the run's own workflow.json, so either the folder id or the recorded run id is
    accepted; an issuer recorded by the launcher or admitted from the run manifest must match.
    """
    try:
        recorded = read_json(root, f"{folder}/workflow.json", LaunchedWorkflow).run
    except (OSError, ValueError):
        # Unreadable or malformed: fall back to the folder id alone. Fail closed: a type error
        # rejects the whole record (run_id and issuer_id alike), so none of it may be used.
        recorded = RecordedIdentity()
    if view.run.run_id != run_id and (not recorded.run_id or view.run.run_id != recorded.run_id):
        return "Delivery run identity does not match this run"
    if recorded.issuer_id and view.run.issuer_id != recorded.issuer_id:
        return "Delivery issuer does not match run"
    if run.issuer and run.issuer != "Unclassified" and view.run.issuer_id != run.issuer:
        return "Delivery issuer does not match run"
    return ""


def declared_as(declared: Artifact, artifact: Artifact) -> Artifact:
    """A verified delivery under the label and relationship its run manifest declared.

    A declared superseded state is kept.
    """
    updated = artifact.model_copy()
    updated.label = declared.label
    updated.relationship = declared.relationship
    if declared.state == "superseded":
        updated.state = declared.state
    return updated


def admit_run_deliveries(root: Path, folder: str, run: Run, cat: Catalogue) -> None:
    """A launcher run keeps its verified deliveries inside the run; run files stay unverified."""
    try:
        deliveries = folders(root, f"{folder}/deliveries")
    except (OSError, ValueError):
        deliveries = []
    run_id = os.path.basename(folder)
    for delivered in deliveries:
        artifact, view, files = verify_delivery(root, delivered)
        if artifact.available:
            # A delivery copied in from another run or issuer must not pass for this one.
            issue = run_delivery_identity_issue(root, folder, run_id, run, view)
            if issue:
                artifact.available, artifact.href, artifact.issue = False, "", issue
        if not artifact.available:
            cat.issues.append(f"{delivered}: {artifact.issue}")
            for old in run.artifacts:
                if old.folder == delivered:
                    old.issue = artifact.issue
            continue
        cat._allowed.update(files)
        declared = False
        for position, old in enumerate(run.artifacts):
            if old.folder == delivered:
                run.artifacts[position] = declared_as(old, artifact)
                declared = True
        if not declared:
            run.artifacts.append(artifact)


def link_deliverable(cat: Catalogue, folder: str, artifact: Artifact, view: DeliveryView) -> bool:
    """Attach a deliverables/ folder to the runs that declare it or share its run identity."""
    linked = False
    for run in cat.real:
        for position, old in enumerate(run.artifacts):
            if old.folder != folder:
                continue
            updated = declared_as(old, artifact)
            if artifact.available and view.run.issuer_id != run.issuer:
                updated.available = False
                updated.href = ""
                updated.issue = "Delivery issuer does not match run"
            run.artifacts[position] = updated
            if not artifact.available or updated.available:
                linked = True
        # A matching run identifier is explicit identity; shared issuer alone is not.
        if artifact.available and run.id == view.run.run_id and run.issuer == view.run.issuer_id:
            if not any(item.folder == folder for item in run.artifacts):
                run.artifacts.append(artifact.model_copy())
            linked = True
    return linked


def withhold_unverified_completeness(run: Run, cat: Catalogue) -> None:
    if not run._delivery_claimed:
        return
    # The delivery checkpoint is the report bundle: a published model alone does not complete a run.
    available = any(
        item.available
        and item.kind == "report"
        and item.state != "superseded"
        and item.relationship != "related"
        for item in run.artifacts
    )
    if available:
        return
    run.completion = None
    run.checkpoints = None
    run.gaps.append("Checklist delivery checkpoint is unverified: no available direct report.")
    cat.issues.append(
        f"{run.id}: completeness withheld until its delivery checkpoint can be verified"
    )


def seed_manifest(seed: Run, seeds: Catalogue) -> Manifest:
    """A legacy summary as a manifest; its pinned files must still match exactly."""
    manifest = Manifest(schema=MANIFEST_SCHEMA, run=seed.model_copy(deep=True))
    keys = [
        seed.identity_source,
        seed.sector_source,
        *(metric.source for metric in seed.metrics.values() if metric is not None),
        *(rating.source for rating in seed.ratings),
    ]
    manifest.sources = {key: seeds.sources.get(key, Source()) for key in keys if key}
    return manifest


def unattached_delivery(artifact: Artifact, view: DeliveryView) -> Run:
    run = blank_run(f"delivery:{os.path.basename(artifact.folder)}")
    run.title = "Delivery revision"
    run.workflow = "Delivery"
    run.artifacts = [artifact.model_copy()]
    if artifact.available:
        run.issuer = view.run.issuer_id
        run.name = view.run.issuer_name
        run.date = view.run.as_of
        run.period = view.run.as_of
        run.summary = (
            f"Discovered delivery for {view.run.run_id}. Its relationship to analytical "
            "run folders has not been established; no metrics or completion are inferred."
        )
    return run


def place_deliverable(root: Path, folder: str, cat: Catalogue) -> None:
    """A deliverables/ folder verified, pinned and attached to its runs, else a run of its own."""
    artifact, view, files = verify_delivery(root, folder)
    linked = link_deliverable(cat, folder, artifact, view)
    if artifact.available:
        cat._allowed.update(files)
    else:
        cat.issues.append(f"{folder}: {artifact.issue}")
    if not linked:
        cat.real.append(unattached_delivery(artifact, view))


def discover(workspace: str, seeds: Catalogue) -> Catalogue:
    cat = Catalogue(
        workspace=workspace,
        live=True,
        built_at=datetime.now(UTC).strftime("%d %b %Y, %H:%M:%S UTC"),
    )
    root = Path(workspace)
    if not root.is_dir():
        cat.issues.append(f"Workspace unavailable: {workspace} is not a readable folder")
        return cat
    try:
        run_folders = folders(root, "runs")
    except (OSError, ValueError) as error:
        cat.issues.append(str(error))
        run_folders = []
    # Legacy summaries remain useful only when their exact pinned files survive.
    seed_by_id = {run.id: run for run in seeds.real}
    for folder in run_folders:
        run_id = os.path.basename(folder)
        run = blank_run(run_id)
        if os.path.lexists(root / folder / "library.json"):
            try:
                manifest = read_json(root, f"{folder}/library.json", Manifest)
                if manifest.schema_ != MANIFEST_SCHEMA:
                    raise ValueError("unsupported run manifest schema")
                run = admit_run(root, manifest, run_id, cat)
            except (OSError, ValueError) as error:
                run = blank_run(run_id)
                run.gaps.append(f"Run metadata rejected: {describe(error)}")
                cat.issues.append(f"{folder}: {describe(error)}")
        elif run_id in seed_by_id:
            try:
                run = admit_run(root, seed_manifest(seed_by_id[run_id], seeds), run_id, cat)
            except (OSError, ValueError) as error:
                run = blank_run(run_id)
                run.gaps.append(f"Legacy summary unavailable: {describe(error)}")
                cat.issues.append(f"{folder}: {describe(error)}")
        # Delivery availability is always checked afresh, not inherited from a seed.
        for artifact in run.artifacts:
            artifact.available = False
            artifact.href = ""
            artifact.issue = "Delivery folder not found"
        index_run_files(root, folder, cat, run)
        admit_run_deliveries(root, folder, run, cat)
        cat.real.append(run)
    try:
        delivery_folders = folders(root, "deliverables")
    except (OSError, ValueError) as error:
        cat.issues.append(str(error))
        delivery_folders = []
    for folder in delivery_folders:
        place_deliverable(root, folder, cat)
    for run in cat.real:
        withhold_unverified_completeness(run, cat)
    cat.real.sort(key=lambda run: (run.name, run.id))
    return cat
