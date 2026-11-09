"""Shared fixtures: the one real browser the Issuer Library front-end checks drive."""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

import pytest
from issuer_library_browser import Screen, catalogue_reply, design_store, open_app


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


@pytest.fixture(scope="module")
def design() -> tuple[dict[str, Any], dict[str, Any]]:
    return design_store()


@pytest.fixture
def fixture(browser: Any, design: tuple[dict[str, Any], dict[str, Any]]) -> Iterator[Any]:
    """Open the curated design fixture at a route; every page must end without errors."""
    opened: list[Screen] = []

    def factory(
        hash_route: str = "CP-1/performance", viewport: tuple[int, int] = (1280, 600)
    ) -> Screen:
        screen = open_app(
            browser,
            hash_route,
            design[0],
            {"models": [], **design[1]},
            api={"/api/catalogue": catalogue_reply(design[0])},
            viewport=viewport,
        )
        opened.append(screen)
        return screen

    yield factory
    for screen in opened:
        assert screen.errors == []
        screen.close()
