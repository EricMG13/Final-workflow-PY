"""CP1H-R23: the CP-1 prompt states the search the source_context absence gate requires.

``deploy_vii.live.tools.absence_issues`` refuses an absence claim for a source the step has no
recorded ``search_pack`` for. The statement is in every composed ``source_context`` message,
before ``Rules:``.
"""

__all__ = ["ABSENCE_RULE_ID", "ABSENCE_STATEMENT"]

ABSENCE_RULE_ID = "source_context.absence"
ABSENCE_STATEMENT = (
    "Before you set a source's `event_scan` to `no_events_identified`, run `search_pack` over "
    "that source in this step; reading its pages does not count."
)
