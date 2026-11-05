"""Atomic public progress projection; never contains prompts or credentials."""

import json
import os
import tempfile
from pathlib import Path

from deploy_workflow.platform_io import replace


def progress(directory: Path, module: str, step: str) -> None:
    atomic_json(directory / "progress.json", {"module": module, "step": step})


def atomic_json(target: Path, value: object) -> None:
    directory = target.parent
    fd, name = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream)
        replace(name, target)
    finally:
        Path(name).unlink(missing_ok=True)
