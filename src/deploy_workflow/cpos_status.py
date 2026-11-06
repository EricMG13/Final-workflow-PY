"""Atomic public progress projection; never contains prompts or credentials."""

import json
from pathlib import Path

from deploy_workflow.platform_io import atomic_write


def progress(directory: Path, module: str, step: str) -> None:
    atomic_json(directory / "progress.json", {"module": module, "step": step})


def atomic_json(target: Path, value: object) -> None:
    """Replace ``target`` with ``value`` as JSON, durably (``platform_io.atomic_write``)."""
    atomic_write(target, json.dumps(value).encode())
