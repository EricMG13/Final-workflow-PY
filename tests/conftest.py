"""Shared fixtures: the one real browser the Issuer Library front-end checks drive."""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

import pytest


@pytest.fixture(scope="session")
def browser() -> Iterator[Any]:
    """Chromium through Playwright; ISSUER_LIBRARY_CHROMIUM names the executable when
    Playwright's own download is not installed. Without a browser the proof is skipped."""
    playwright_api = pytest.importorskip("playwright.sync_api")
    with playwright_api.sync_playwright() as playwright:
        executable = os.environ.get("ISSUER_LIBRARY_CHROMIUM") or None
        try:
            instance = playwright.chromium.launch(executable_path=executable)
        except playwright_api.Error as error:
            pytest.skip(f"Chromium is unavailable: {error}")
        yield instance
        instance.close()
