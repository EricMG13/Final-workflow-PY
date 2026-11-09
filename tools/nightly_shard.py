"""Pytest plugin for the nightly shards (``-p tools.nightly_shard``). Standard library only."""

from __future__ import annotations

import os
from typing import Any

SHARD_ENV = "NIGHTLY_SHARD"  # "<shard>/<shards>", set by tools/nightly_tests.py


def pytest_collection_modifyitems(config: Any, items: list[Any]) -> None:
    """Pytest hook (``-p tools.nightly_shard``): keep every ``shards``-th collected test.

    Every shard collects the same suite in the same order, so the slices cover each test once.
    Splitting tests rather than files spreads a file of slow end-to-end tests over every shard.
    """
    shard, shards = (int(part) for part in os.environ[SHARD_ENV].split("/"))
    config.hook.pytest_deselected(
        items=[item for n, item in enumerate(items) if n % shards != shard]
    )
    items[:] = items[shard::shards]
