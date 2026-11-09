"""Catalogue records and the workspace file rules. A manifest is admitted only as its producer wrote it."""

from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path
from typing import Any
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

# The one size limit for a delivered or uploaded file. The store states the same 64 MiB as
# MODEL_FILE_LIMIT (engine/store.py); change the two together.
MAX_FILE = 64 << 20
# What url.PathEscape keeps in one path segment.
SEGMENT_SAFE = "$&+:=@"


class Record(BaseModel):
    """JSON as a typed record: exact types, unknown keys ignored, missing keys at their zero value."""

    model_config = ConfigDict(strict=True, extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def _null_is_absent(cls, value: Any) -> Any:
        """JSON null leaves a field at its zero value, as a Go struct reads it."""
        if isinstance(value, dict):
            return {key: item for key, item in value.items() if item is not None}
        return value


class Source(Record):
    path: str = ""
    sha256: str = ""
    line: int = 0
    quote: str = ""
    href: str = ""


class Metric(Record):
    value: str = ""
    unit: str = ""
    period: str = ""
    basis: str = ""
    source: str = ""
    provenance: str = ""


class FacilityQuote(Record):
    kind: str = ""
    terms: dict[str, Metric | None] = {}


class Facility(Record):
    facility_id: str = ""
    terms: dict[str, Metric | None] = {}
    quotes: list[FacilityQuote] = []


class Rating(Record):
    label: str = ""
    agency: str = ""
    scope: str = ""
    date: str = ""
    source: str = ""


class Counts(Record):
    done: int = 0
    total: int = 0


class Artifact(Record):
    folder: str = ""
    kind: str = ""
    label: str = ""
    state: str = ""
    relationship: str = ""
    available: bool = False
    href: str = ""
    issue: str = ""


class FileLink(Record):
    name: str = ""
    href: str = ""


class Run(Record):
    id: str = ""
    issuer: str = ""
    name: str = ""
    title: str = ""
    workflow: str = ""
    sector: str = ""
    date: str = ""
    period: str = ""
    period_kind: str = ""
    currency: str = ""
    summary: str = ""
    gaps: list[str] = []
    metrics: dict[str, Metric | None] = {}
    completion: int | None = None
    checkpoints: Counts | None = None
    ratings: list[Rating] = []
    classification: str = ""
    classification_source: str = ""
    private_side: bool = False
    private_side_source: str = ""
    facilities: list[Facility] = []
    identity_source: str = ""
    sector_source: str = ""
    handoff: str = ""
    handoff_href: str = ""
    artifacts: list[Artifact] = []
    files: list[FileLink] = []
    _delivery_claimed: bool = PrivateAttr(default=False)


class Catalogue(Record):
    real: list[Run] = []
    illustrative: list[Run] = []
    sources: dict[str, Source] = {}
    built_at: str = ""
    issues: list[str] = []
    workspace: str = ""
    live: bool = False
    policy_locked: bool = False
    _allowed: dict[str, str] = PrivateAttr(default_factory=dict)


class Requirement(Record):
    id: str = ""
    stage: str = ""
    done: bool = False
    evidence: list[str] = []


class Checklist(Record):
    scope: str = ""
    requirements: list[Requirement] = []


class Manifest(Record):
    schema_: str = Field("", alias="schema")
    run: Run = Run()
    sources: dict[str, Source] = {}
    checklist: Checklist | None = None


class DeliveryRun(Record):
    run_id: str = ""
    issuer_id: str = ""
    issuer_name: str = ""
    as_of: str = ""
    pathway: str = ""


class DeliveryView(Record):
    run: DeliveryRun = DeliveryRun()
    mode: str = ""


class RecordedIdentity(Record):
    run_id: str = ""
    issuer_id: str = ""


class LaunchedWorkflow(Record):
    """The launcher's workflow.json: only the identity it recorded for the run."""

    run: RecordedIdentity = RecordedIdentity()


class DeliveryRecord(Record):
    files: dict[str, str] = {}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def local_path(name: str) -> bool:
    """Slash-separated relative paths on every OS; Windows streams and device
    paths must never become alternate spellings of admitted workspace files."""
    if name == "." or any(character in name for character in "\\:\x00"):
        return False
    return all(part not in ("", ".", "..") for part in name.split("/"))


def read_file(root: Path, name: str) -> bytes:
    """The bytes of one workspace file: a regular file under root, at most 64 MiB, never a link."""
    if not local_path(name):
        raise ValueError(f"invalid relative path: {name}")
    path = root / name
    try:
        # Reject links, devices and FIFOs before opening (a FIFO could otherwise block).
        if not stat.S_ISREG(os.lstat(path).st_mode):
            raise ValueError(f"not a regular file: {name}")
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"path leaves the workspace: {name}")
        with open(path, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FILE:
                raise ValueError(f"not a regular file within 64 MiB: {name}")
            raw = stream.read(MAX_FILE + 1)
    except OSError as error:
        raise OSError(f"cannot read {name}: {error.strerror or error}") from error
    if len(raw) > MAX_FILE:
        raise ValueError(f"file grew beyond 64 MiB: {name}")
    return raw


def read_json[T: Record](root: Path, name: str, record: type[T]) -> T:
    return record.model_validate_json(read_file(root, name))


def file_url(name: str) -> str:
    return "/files/" + "/".join(quote(part, safe=SEGMENT_SAFE) for part in name.split("/"))


def pinned_url(name: str, sha256: str) -> str:
    return f"{file_url(name)}?sha256={sha256}"


def blank_run(run_id: str) -> Run:
    return Run(
        id=run_id,
        issuer="Unclassified",
        name=run_id,
        title="Discovered run",
        workflow="Unclassified",
        sector="Unclassified",
        period="Not established",
        period_kind="Unclassified",
        summary="This folder has been discovered. Structured issuer and screening metadata "
        "have not been supplied.",
    )


def folders(root: Path, parent: str) -> list[str]:
    """The visible subfolders of parent as slash paths, in name order; a missing parent holds none."""
    directory = root / parent
    try:
        with os.scandir(directory) as entries:
            found = sorted(entries, key=lambda entry: entry.name)
    except FileNotFoundError:
        return []
    if not directory.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"{parent} leaves the workspace")
    return [
        f"{parent}/{entry.name}"
        for entry in found
        if entry.is_dir(follow_symlinks=False) and not entry.name.startswith(".")
    ]
