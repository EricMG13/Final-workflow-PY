"""shape_issues keeps a real min-length error beside a failed item (S15 C02).

For a tuple with `min_length`, Pydantic reports `too_short` after item validation with ctx
`actual_length` = the valid items. When items fail that error may only echo them (the input was
long enough) and shape_issues drops it; before the fix it was dropped whenever any item failed,
so a too-short input with one bad item hid the length error from the repair prompt. Expected
texts follow from the inputs: valid items + failed items vs min_length 3.
"""

import json
from typing import Annotated

import pytest
from pydantic import Field, ValidationError

from deploy_vii.contracts import Contract
from deploy_vii.readiness import shape_issues

SHORT = "a: Tuple should have at least 3 items after validation, not {}"


class Item(Contract):
    n: int


class M(Contract):
    a: Annotated[tuple[int, ...], Field(min_length=3)]


class Nested(Contract):
    a: Annotated[tuple[Item, ...], Field(min_length=3)]


def _issues(model: type[Contract], value: object) -> tuple[str, ...]:
    with pytest.raises(ValidationError) as caught:
        model.model_validate_json(json.dumps({"a": value}))
    return shape_issues(caught.value)


def test_a_long_enough_tuple_with_a_bad_item_reports_only_the_item() -> None:
    # 2 valid + 1 failed = 3 items: the length error is an echo
    assert _issues(M, [1, 2, "x"]) == ("a.2: Input should be a valid integer",)


def test_a_short_tuple_with_a_bad_item_reports_both() -> None:
    # 1 valid + 1 failed = 2 < 3: the input really is too short
    assert _issues(M, [1, "x"]) == ("a.1: Input should be a valid integer", SHORT.format(1))


def test_a_short_tuple_of_bad_items_reports_both() -> None:
    # 0 valid + 2 failed = 2 < 3
    assert _issues(M, ["x", "y"]) == (
        "a.0: Input should be a valid integer",
        "a.1: Input should be a valid integer",
        SHORT.format(0),
    )


def test_a_short_tuple_with_no_bad_item_reports_the_length() -> None:
    assert _issues(M, [1]) == (SHORT.format(1),)


def test_several_errors_inside_one_item_count_that_item_once() -> None:
    # item 1 fails on two fields: 1 valid + 1 distinct failed index = 2 < 3, a real error
    issues = _issues(Nested, [{"n": 1}, {"n": "x", "extra": 1}])
    assert issues[-1] == SHORT.format(1)
    assert all(issue.startswith("a.1.") for issue in issues[:-1])
    assert len(issues) == 3
    # 2 valid + 1 failed item with two errors = 3: an echo
    issues = _issues(Nested, [{"n": 1}, {"n": 2}, {"n": "x", "extra": 1}])
    assert len(issues) == 2
    assert all(issue.startswith("a.2.") for issue in issues)
