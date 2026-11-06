"""Helpers the owner cores share.

`is_blank` is the one blank-text predicate for analyst text (LEAD round 12 B10); the predicate
itself is `deploy_vii.prose.is_blank`, and this module keeps its public name for the owner cores
(`from deploy_workflow.owners.blank import is_blank`). `one_per_page` is the derived-fact
citation rule of Stage 2 round 3, which cp1c, cp2g, cp2h and cp4c each held a copy of.
`with_rules` and `parse_submission` are the bodies several owners carry as identical private
copies (`_with_rules`; `_parsed` in cp1d, cp2a, cp2d and cp2g); they are offered here under new
names for a later consolidation, and no owner calls them yet.
"""

from collections.abc import Callable, Sequence

from pydantic import BaseModel, ValidationError

from deploy_vii.contracts import Citation
from deploy_vii.execution import Attempt, StepValidation
from deploy_vii.live.schema import exact_json, json_object
from deploy_vii.preparation import PreparedPack
from deploy_vii.prose import is_blank
from deploy_vii.readiness import shape_issues

__all__ = ["is_blank", "one_per_page", "parse_submission", "with_rules"]

NOT_BOUNDED = "(root): not a bounded JSON object"


def one_per_page(citations: Sequence[Citation]) -> tuple[Citation, ...]:
    """One Citation per (source, locator), quoting the first input quote with that locator, in
    input order; a locator such as ``page 3, table 2`` is its own entry. No quote is invented."""
    first: dict[tuple[str, str], Citation] = {}
    for citation in citations:
        first.setdefault((citation.source_id, citation.locator), citation)
    return tuple(first.values())


def with_rules(
    validate: Callable[[PreparedPack, Attempt], StepValidation],
    rules: Callable[[str], tuple[str, ...]],
    payload: str,
) -> Callable[[PreparedPack, Attempt], StepValidation]:
    """`validate`, then the tool-use rule issues of the retained payload appended (the order the
    verifier rebuilds: validator issues, then the journaled rules), each issue once."""

    def run(pack: PreparedPack, attempt: Attempt) -> StepValidation:
        outcome = validate(pack, attempt)
        found = rules(payload)
        if not found:
            return outcome
        return StepValidation(
            output=outcome.output, issues=tuple(dict.fromkeys((*outcome.issues, *found)))
        )

    return run


def parse_submission[Submission: BaseModel](
    model: type[Submission], payload: str
) -> tuple[Submission | None, tuple[str, ...]]:
    """The submission, or its shape issues (protocol section 6: model text is read only through
    `json_object`). The schema validates the bounded document's exact re-serialisation, never the
    raw text; text `json_object` refuses keeps Pydantic's own shape issue and is refused even if
    Pydantic would parse it."""
    document = json_object(payload)
    try:
        if document is None:
            model.model_validate_json(payload)  # for its shape issue only
            return None, (NOT_BOUNDED,)
        return model.model_validate_json(exact_json(document)), ()
    except ValidationError as error:
        return None, shape_issues(error)
