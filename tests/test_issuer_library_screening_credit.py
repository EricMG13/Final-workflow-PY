"""Library credit and market screening ports.

apps/issuer-library/web/screening-credit.test.cjs at final-workflow d877d8ce (plan-4c) evaluated
screening.js in a bare vm context. Here the real page loads screening.js and its LibraryLogic
global is called through js(); the expected values are read from the same answer-key files under
tests/fixtures/library-credit/ and every fixture row becomes its own case, as in the Node suite.
Synthetic data only. Marked browser: real browser proof.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from issuer_library_browser import Screen, js, open_app

pytestmark = pytest.mark.browser

KEYS = Path(__file__).parent / "fixtures" / "library-credit"


def load(name: str) -> Any:
    return json.loads((KEYS / name).read_text(encoding="utf-8"))


REAL = load("screening-catalogue.json")["real"]
SCALE_KEY = load("rating-scale.json")
ISSUER_CASE = load("issuer-case-cases.json")


@pytest.fixture
def screen(browser: Any) -> Iterator[Screen]:
    opened = open_app(browser, "W-Library/cases")
    yield opened
    assert opened.errors == []
    opened.close()


def logic(screen: Screen, expression: str, **data: Any) -> Any:
    """Evaluate an expression over LibraryLogic in the page; each datum is bound by name.

    The result is passed through JSON in the page, as the Node suite's plain() did.
    """
    bound = "".join(f"const {k}={json.dumps(v)};" for k, v in data.items())
    return js(
        screen,
        f"const L=LibraryLogic;{bound}"
        f"const out=({expression});return out===undefined?null:JSON.parse(JSON.stringify(out));",
    )


def ids(rows: list[dict[str, Any]]) -> list[str]:
    return [r["id"] for r in rows]


def test_code_scale_has_the_answer_key_rows_in_order(screen: Screen) -> None:
    expected = [
        f"{row['sp_fitch']}/{row['moodys']}" if row["moodys"] else row["sp_fitch"]
        for row in SCALE_KEY["scale"]
    ]
    assert logic(screen, "L.scale") == expected


@pytest.mark.parametrize(
    "item", SCALE_KEY["placement_cases"], ids=lambda i: f"placement of {json.dumps(i['text'])}"
)
def test_placement(screen: Screen, item: dict[str, Any]) -> None:
    place = logic(screen, "L.ratingPlace(text)", text=item["text"])
    if item.get("off_scale"):
        assert place is None
        return
    assert place["rank"] == item["rank"]
    assert place["placesAs"] == item["places_as"]


@pytest.mark.parametrize(
    "item", SCALE_KEY["lowest_cases"], ids=lambda i: f"lowest rating: {i['name']}"
)
def test_lowest_rating(screen: Screen, item: dict[str, Any]) -> None:
    lowest = logic(
        screen, "L.lowestRating({ratings}, scope)", ratings=item["ratings"], scope=item["scope"]
    )
    assert (lowest["label"] if lowest else None) == item["lowest"]

    def below(threshold: str) -> bool:
        run = {
            "id": "x",
            "issuer": "X",
            "date": "2024-01-01",
            "artifacts": [],
            "metrics": {},
            "ratings": item["ratings"],
        }
        filters = {"runs": "any", "ratingScope": item["scope"], "ratingBelow": threshold}
        return len(logic(screen, "L.filterRuns([run], filters)", run=run, filters=filters)) == 1

    for m in item["matches"]:
        assert below(m["threshold"]), m["threshold"]
    for m in item["does_not_match"]:
        assert not below(m["threshold"]), m["threshold"]


@pytest.mark.parametrize(
    "item", load("filter-cases.json"), ids=lambda i: f"filter case: {i['name']}"
)
def test_filter_case(screen: Screen, item: dict[str, Any]) -> None:
    got = logic(screen, "L.filterRuns(real, filters)", real=REAL, filters=item["filters"])
    assert sorted(ids(got)) == item["expected_ids"]
    assert logic(screen, "L.coverage(real, filters)", real=REAL, filters=item["filters"]) == (
        item.get("coverage") or {}
    )


@pytest.mark.parametrize("item", load("sort-cases.json"), ids=lambda i: f"sort case: {i['name']}")
def test_sort_case(screen: Screen, item: dict[str, Any]) -> None:
    got = logic(
        screen,
        "L.sortRuns(L.filterRuns(real, filters), key, direction)",
        real=REAL,
        filters=item["filters"],
        key=item["key"],
        direction=item["direction"],
    )
    assert ids(got) == item["expected_ids"]


@pytest.mark.parametrize(
    "item", ISSUER_CASE["cases"], ids=lambda i: f"issuer case folding: {i['name']}"
)
def test_issuer_case_folding(screen: Screen, item: dict[str, Any]) -> None:
    runs = [r for r in ISSUER_CASE["runs"] if not item.get("only") or r["id"] in item["only"]]
    got = logic(screen, "L.screened(runs, filters)", runs=runs, filters=item["filters"])
    assert sorted(e["run"]["id"] for e in got) == sorted(item["expected_ids"])
    assert sorted(e["run"]["id"] for e in got if e.get("notScreened")) == sorted(
        item["expected_not_screened"]
    )
