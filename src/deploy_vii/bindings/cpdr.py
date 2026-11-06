"""CP-DR deep research -> the Evidence and Limitations rails only (lease D-C, D7, D8).

No Front Page block shows CP-DR and no pathway lists it: the locked questions and recipients
(TDR.1) and the claims with their located evidence (TDR.2) go to Evidence, the answers with their
contrary evidence, uncertainty and downstream use (TDR.3) to Limitations. The labels are the R7
table titles. Slots carry a ``cpdr-`` prefix: a slot is unique across all shipped maps. The
settled head is read by CP-1C and CP-2 (the dossier block in their prompts; CP-1C also reads the
peer pack's TDR.6 figures), not through a Front Page block.
Data only; it reads facts by table id and never imports ``deploy_workflow``.
"""

from deploy_vii.bindings import Binder, BindingMap

MODULE_ID = "CP-DR"


_bind = Binder(MODULE_ID, "cpdr-").bind


CPDR = BindingMap(
    module_id=MODULE_ID,
    entries=(
        _bind("TDR.1", "evidence", "Locked questions and recipients"),
        _bind("TDR.2", "evidence", "Claims and located evidence"),
        _bind("TDR.3", "limitations", "Answers, contrary evidence, uncertainty and downstream use"),
        _bind("TDR.4", "evidence", "Candidate peers"),
        _bind("TDR.5", "evidence", "Provisional alignment observations"),
        _bind("TDR.6", "evidence", "Located peer/transaction figures"),
    ),
)
