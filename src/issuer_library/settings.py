"""Per-user settings, the managed policy file and atomic JSON files."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from deploy_workflow.platform_io import replace


class Config(BaseModel):
    model_config = ConfigDict(strict=True)

    workspace: str = ""


@dataclass(frozen=True)
class Locations:
    state: Path
    documents: Path
    policy: Path | None = None
    defaults: Path | None = None


def load_config(loc: Locations) -> tuple[Config, bool]:
    """The managed policy file (locked), then the per-user file, then the package default
    (not locked), then Documents; a malformed file is an error."""
    for name, locked in (
        (loc.policy, True),
        (loc.state / "settings.json", False),
        (loc.defaults, False),
    ):
        if name is None:
            continue
        try:
            raw = name.read_bytes()
        except FileNotFoundError:
            continue
        try:
            # Windows PowerShell 5.1 writes "UTF8" with a byte order mark; only that one is skipped.
            config = Config.model_validate_json(raw.removeprefix(b"\xef\xbb\xbf"))
        except ValueError as error:
            raise ValueError(f"invalid configuration {name}: {error}") from error
        if not os.path.isabs(config.workspace):
            raise ValueError(f"workspace must be an absolute path in {name}")
        return config, locked
    return Config(workspace=str(loc.documents / "FinalWorkflow")), False


def save_json(name: Path, value: Any) -> None:
    """Write indented JSON through a temporary file beside the target, then replace it."""
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    raw = json.dumps(value, indent=2).encode()
    os.makedirs(name.parent, mode=0o700, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=name.parent, prefix=".library-", suffix=".tmp")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        replace(temporary, name)
    finally:
        Path(temporary).unlink(missing_ok=True)
