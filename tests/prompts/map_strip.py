"""Undo the CP1H-R23.16 schema change in the financials composed message: the model is shown
``FinancialMapSubmission`` (the canonical submission plus ``unit_maps``), while ``spec.schema``
stays ``FinancialSubmission``. The last line of the message is the offered schema; putting the
canonical schema's text back there gives the message the digests pinned before the change."""

import json

from deploy_vii.live.schema import strict_schema
from deploy_workflow.owner_workflow import OWNER_SPECS
from deploy_workflow.prompts.tools import offered_schema


def _text(schema: object) -> str:
    return json.dumps(schema, sort_keys=True, separators=(",", ":"))


def undo_unit_maps(step_id: str, text: str) -> str:
    """Put the canonical financials schema back in a composed message (financials only)."""
    if step_id != "financials":
        return text
    spec = next(s for o in OWNER_SPECS.values() for s in o.steps if s.step_id == "financials")
    offered = _text(offered_schema(spec))
    assert text.count(offered) == 1, step_id
    return text.replace(offered, _text(strict_schema(spec.schema)))
