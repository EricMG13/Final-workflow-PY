"""Discovery of runs and deliveries in a workspace.

Admission preserves explicit metadata; it does not interpret arbitrary prose
or infer an issuer, period, ratio definition or completion from a filename.
"""

from __future__ import annotations

import functools
import json
import math
import os
import re
from collections.abc import Callable
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
    FileLink,
    Manifest,
    Metric,
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

# A whole number as written: a run of digits, commas and points not joined to a word or another
# number, with a minus sign only where it does not join two words ("FY2020-2021").
NUMERIC_RUN = re.compile(r"(?:(?<![\w.,-])-)?(?<![\w.,])[0-9](?:[0-9.,]*[0-9])?")
# The runs that are one number: commas only as thousands separators, at most one decimal point.
NUMBER = re.compile(r"-?(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?")
DEFAULT_LABELS = {"sector": "Unclassified", "period": "Not established", "workflow": "Unclassified"}
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


def source_numbers(quote: str) -> set[str]:
    """The whole numbers in a source excerpt, thousands separators removed: '3,4' is neither."""
    return {run.replace(",", "") for run in NUMERIC_RUN.findall(quote) if NUMBER.fullmatch(run)}


def verify_sources(root: Path, manifest: Manifest) -> dict[str, Source]:
    verified: dict[str, Source] = {}
    for key, source in manifest.sources.items():
        if not SOURCE_KEY.fullmatch(key):
            raise ValueError("invalid source key")
        verified[key] = verify_source(root, source)
    return verified


def check_run_identity(run: Run, run_id: str) -> None:
    if run.id != run_id or not run.name or not run.issuer:
        raise ValueError("run identity must match folder and include issuer/name")
    if run.date and not calendar_date(run.date):
        raise ValueError("invalid evidence date")


def check_pinned_identity(run: Run, verified: dict[str, Source]) -> None:
    for key in (run.identity_source, run.sector_source):
        if key and key not in verified:
            raise ValueError("missing identity/sector source")
    if not run.identity_source:
        raise ValueError("issuer identity needs a pinned source")
    if run.sector and run.sector != "Unclassified" and not run.sector_source:
        raise ValueError("sector needs a pinned source")


def check_metric(metric: Metric, verified: dict[str, Source]) -> None:
    if metric.provenance not in ("", "cited", "calculated", "synthetic"):
        raise ValueError("metric provenance must be cited, calculated, synthetic or omitted")
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
    if metric.value not in source_numbers(pinned.quote):
        raise ValueError("metric value absent from source excerpt")


def apply_checklist(run: Run, manifest: Manifest, verified: dict[str, Source]) -> None:
    run.completion = None
    run.checkpoints = None
    if manifest.checklist is None:
        return
    counts = assess_checklist(manifest.checklist, verified)
    run.completion = counts.done * 100 // counts.total
    run.checkpoints = counts
    run._delivery_claimed = any(
        item.stage == "delivery" and item.done for item in manifest.checklist.requirements
    )


def publish(root: Path, run: Run, verified: dict[str, Source], cat: Catalogue) -> None:
    """Publish references only after every check succeeds: failed records cannot
    leave admitted files or source labels behind in the aggregate catalogue."""
    run.handoff_href = ""
    if run.handoff:
        if not run.handoff.startswith(f"runs/{run.id}/"):
            raise ValueError("primary handoff must belong to run")
        handoff = digest(read_file(root, run.handoff))
        run.handoff_href = pinned_url(run.handoff, handoff)
        # The pinned link is served even where the file listing does not enumerate it.
        cat._allowed[run.handoff] = handoff
    for key, source in verified.items():
        cat.sources[f"{run.id}.{key}"] = source
        cat._allowed[source.path] = source.sha256
    for metric in run.metrics.values():
        if metric is not None:
            metric.source = f"{run.id}.{metric.source}"
    for rating in run.ratings:
        rating.source = f"{run.id}.{rating.source}"
    if run.identity_source:
        run.identity_source = f"{run.id}.{run.identity_source}"
    if run.sector_source:
        run.sector_source = f"{run.id}.{run.sector_source}"


def admit_run(root: Path, manifest: Manifest, run_id: str, cat: Catalogue) -> Run:
    run = manifest.run.model_copy(deep=True)
    check_run_identity(run, run_id)
    verified = verify_sources(root, manifest)
    check_pinned_identity(run, verified)
    for metric in run.metrics.values():
        if metric is not None:
            check_metric(metric, verified)
    for rating in run.ratings:
        if rating.source not in verified:
            raise ValueError("rating requires pinned source")
    apply_checklist(run, manifest, verified)
    for field, default in DEFAULT_LABELS.items():
        if not getattr(run, field):
            setattr(run, field, default)
    publish(root, run, verified, cat)
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


def verify_delivery(root: Path, folder: str) -> tuple[Artifact, DeliveryView, dict[str, str]]:
    artifact = Artifact(
        folder=folder, label=os.path.basename(folder), state="candidate", relationship="direct"
    )
    view = DeliveryView()
    files: dict[str, str] = {}
    try:
        record = read_json(root, f"{folder}/delivery.json", DeliveryRecord)
    except (OSError, ValueError) as error:
        artifact.issue = describe(error)
        return artifact, view, files
    if not record.files.get("report.html") or not record.files.get("view.json"):
        artifact.issue = "Delivery manifest requires report.html and view.json"
        return artifact, view, files
    for name, sha256 in record.files.items():
        if not local_path(name):
            artifact.issue = "Invalid delivery path"
            return artifact, view, files
        try:
            raw = read_file(root, f"{folder}/{name}")
        except (OSError, ValueError):
            raw = None
        if raw is None or digest(raw) != sha256:
            artifact.issue = f"Missing or changed delivery file: {name}"
            return artifact, view, files
        if name == "view.json":
            try:
                view = DeliveryView.model_validate_json(raw)
            except ValueError:
                artifact.issue = "Invalid delivery identity"
                return artifact, view, files
        files[f"{folder}/{name}"] = sha256
    if not view.run.issuer_id or not view.run.issuer_name or not view.run.run_id:
        artifact.issue = "Missing delivery issuer/run identity"
        return artifact, view, files
    if not calendar_date(view.run.as_of):
        artifact.issue = "Invalid delivery evidence date"
        return artifact, view, files
    artifact.available = True
    artifact.href = pinned_url(f"{folder}/report.html", record.files["report.html"])
    if view.mode:
        artifact.state = view.mode
    return artifact, view, files


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


def library_manifest(root: Path, folder: str) -> Manifest:
    manifest = read_json(root, f"{folder}/library.json", Manifest)
    if manifest.schema_ != MANIFEST_SCHEMA:
        raise ValueError("unsupported run manifest schema")
    return manifest


def admit_folder(root: Path, folder: str, seeds: Catalogue, cat: Catalogue) -> Run:
    """The folder's own library.json, else its legacy summary, else an unclassified run."""
    run_id = os.path.basename(folder)
    seed = next((run for run in seeds.real if run.id == run_id), None)
    load: Callable[[], Manifest]
    if os.path.lexists(root / folder / "library.json"):
        gap, load = "Run metadata rejected", functools.partial(library_manifest, root, folder)
    elif seed is not None:
        # Legacy summaries remain useful only when their exact pinned files survive.
        gap, load = "Legacy summary unavailable", functools.partial(seed_manifest, seed, seeds)
    else:
        return blank_run(run_id)
    try:
        return admit_run(root, load(), run_id, cat)
    except (OSError, ValueError) as error:
        run = blank_run(run_id)
        run.gaps.append(f"{gap}: {describe(error)}")
        cat.issues.append(f"{folder}: {describe(error)}")
        return run


def recorded_identity(root: Path, folder: str) -> tuple[str, str]:
    """The launcher's (run_id, issuer_id) from the run's workflow.json, or blanks without one."""
    try:
        recorded = json.loads(read_file(root, f"{folder}/workflow.json"))["run"]
    except (OSError, ValueError, KeyError, TypeError):
        return "", ""
    if not isinstance(recorded, dict):
        return "", ""
    run_id, issuer_id = recorded.get("run_id"), recorded.get("issuer_id")
    return (
        run_id if isinstance(run_id, str) else "",
        issuer_id if isinstance(issuer_id, str) else "",
    )


def foreign_delivery(view: DeliveryView, run: Run, recorded: tuple[str, str]) -> str:
    """Why a delivery inside a run is not that run's, or blank when nothing contradicts it."""
    run_id, issuer_id = recorded
    if run.issuer != "Unclassified" and view.run.issuer_id != run.issuer:
        return "Delivery issuer does not match run"
    if issuer_id and view.run.issuer_id != issuer_id:
        return "Delivery issuer does not match the run's workflow.json"
    if run_id and view.run.run_id != run_id:
        return "Delivery run does not match the run's workflow.json"
    return ""


def attach_run_deliveries(root: Path, folder: str, run: Run, cat: Catalogue) -> None:
    """A launcher run keeps its verified deliveries inside the run; run files stay unverified."""
    try:
        deliveries = folders(root, f"{folder}/deliveries")
    except (OSError, ValueError):
        deliveries = []
    recorded = recorded_identity(root, folder) if deliveries else ("", "")
    for delivered in deliveries:
        artifact, view, files = verify_delivery(root, delivered)
        if artifact.available and (issue := foreign_delivery(view, run, recorded)):
            artifact.available, artifact.href, artifact.issue = False, "", issue
        if not artifact.available:
            cat.issues.append(f"{delivered}: {artifact.issue}")
            continue
        cat._allowed.update(files)
        run.artifacts.append(artifact)


def link_mapped(artifact: Artifact, view: DeliveryView, run: Run, folder: str) -> bool:
    """Refresh the run's own mapping of this delivery folder; whether it now links the delivery."""
    linked = False
    for position, old in enumerate(run.artifacts):
        if old.folder != folder:
            continue
        updated = artifact.model_copy()
        updated.label = old.label
        updated.relationship = old.relationship
        if old.state == "superseded":
            updated.state = old.state
        if artifact.available and view.run.issuer_id != run.issuer:
            updated.available = False
            updated.href = ""
            updated.issue = "Delivery issuer does not match run"
        run.artifacts[position] = updated
        if not artifact.available or updated.available:
            linked = True
    return linked


def unlinked_delivery(folder: str, artifact: Artifact, view: DeliveryView) -> Run:
    run = blank_run(f"delivery:{os.path.basename(folder)}")
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


def link_deliverable(root: Path, folder: str, cat: Catalogue) -> None:
    """A deliverables/ folder joins the runs that map it or name it; otherwise it stands alone."""
    artifact, view, files = verify_delivery(root, folder)
    linked = False
    for run in cat.real:
        linked = link_mapped(artifact, view, run, folder) or linked
        # A matching run identifier is explicit identity; shared issuer alone is not.
        if artifact.available and run.id == view.run.run_id and run.issuer == view.run.issuer_id:
            if not any(item.folder == folder for item in run.artifacts):
                run.artifacts.append(artifact.model_copy())
            linked = True
    if artifact.available:
        cat._allowed.update(files)
    else:
        cat.issues.append(f"{folder}: {artifact.issue}")
    if not linked:
        cat.real.append(unlinked_delivery(folder, artifact, view))


def withhold_unverified_completion(cat: Catalogue) -> None:
    for run in cat.real:
        if not run._delivery_claimed:
            continue
        available = any(
            item.available and item.state != "superseded" and item.relationship != "related"
            for item in run.artifacts
        )
        if not available:
            run.completion = None
            run.checkpoints = None
            run.gaps.append(
                "Checklist delivery checkpoint is unverified: no available direct deliverable."
            )
            cat.issues.append(
                f"{run.id}: completeness withheld until its delivery checkpoint can be verified"
            )


def listed_folders(root: Path, parent: str, cat: Catalogue) -> list[str]:
    try:
        return folders(root, parent)
    except (OSError, ValueError) as error:
        cat.issues.append(str(error))
        return []


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
    for folder in listed_folders(root, "runs", cat):
        run = admit_folder(root, folder, seeds, cat)
        # Delivery availability is always checked afresh, not inherited from a seed.
        for artifact in run.artifacts:
            artifact.available = False
            artifact.href = ""
            artifact.issue = "Delivery folder not found"
        index_run_files(root, folder, cat, run)
        attach_run_deliveries(root, folder, run, cat)
        cat.real.append(run)
    for folder in listed_folders(root, "deliverables", cat):
        link_deliverable(root, folder, cat)
    withhold_unverified_completion(cat)
    cat.real.sort(key=lambda run: (run.name, run.id))
    return cat
