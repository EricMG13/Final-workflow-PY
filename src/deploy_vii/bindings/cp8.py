"""CP-8 decision ledger and post-mortem -> What changed since the last Report, rails.

FP 01's ``what-changed`` (owner CP-8, prose; its ``report_view._Spec`` exists) shows the rails
table ``cp8.what_changed``: one line per row (the decision, the compared measures, the
attribution, the summary), each Python-resolved. T7.1 to T7.7 go to Evidence and the T7.8 gaps
ledger to Limitations. Data only: no arithmetic, and the module never imports ``deploy_workflow``
(protocol section 6), so the module id and table ids are literals that the CP-8 core's tests pin.
Slots carry a ``cp8-`` prefix: a slot is unique across all shipped maps.
"""

from deploy_vii.bindings import Binder, BindingMap

MODULE_ID = "CP-8"
WHAT_CHANGED = "cp8.what_changed"


_bind = Binder(MODULE_ID, "cp8-", hyphenate=True).bind


CP8 = BindingMap(
    module_id=MODULE_ID,
    entries=(
        _bind(WHAT_CHANGED, "what-changed", "What changed since the last Report"),
        # Evidence.
        _bind("T7.1", "evidence", "Decision record"),
        _bind("T7.2", "evidence", "Thesis register"),
        _bind("T7.3", "evidence", "Realized outcome log"),
        _bind("T7.4", "evidence", "Variance table"),
        _bind("T7.5", "evidence", "Attribution table"),
        _bind("T7.6", "evidence", "Calibration register (advisory)"),
        _bind("T7.7", "evidence", "Track-record dashboard"),
        # Limitations.
        _bind("T7.8", "limitations", "CP-8 gaps ledger"),
    ),
)
