"""CP-2E macro, FX and hedging sensitivity -> the Evidence and Limitations rails.

CP-2E has no Front Page block: no pathway lists it and no design reference assigns it one
(`docs/CP2E-OWNER-LEASE.md`, D7). Its deliverables are the module page (the `Module.tables`
layouts T2F.1 to T2F.9) and the two rails. `validate_bindings` still needs every fact of a
restricted module bound exactly once, so each table is bound: T2F.1 to T2F.6 and T2F.8 to
Evidence, T2F.7 and T2F.9 to Limitations. Slots carry a ``cp2e-`` prefix: a slot is unique
across all shipped maps. Data only: no arithmetic, and no import of ``deploy_workflow``.
"""

from deploy_vii.bindings import Binder, BindingMap

MODULE_ID = "CP-2E"


_bind = Binder(MODULE_ID, "cp2e-").bind


CP2E = BindingMap(
    module_id=MODULE_ID,
    entries=(
        _bind("T2F.1", "evidence", "Sourced operands"),
        _bind("T2F.2", "evidence", "Baseline exposure"),
        _bind("T2F.3", "evidence", "Interest rate shock"),
        _bind("T2F.4", "evidence", "Currency shock"),
        _bind("T2F.5", "evidence", "Hedging"),
        _bind("T2F.6", "evidence", "Assessments"),
        _bind("T2F.7", "limitations", "Missing inputs"),
        _bind("T2F.8", "evidence", "Evidence"),
        _bind("T2F.9", "limitations", "Limitations"),
    ),
)
