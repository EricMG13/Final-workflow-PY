"""CP-2 fundamental credit synthesis -> Key findings, Strengths and weaknesses, rails.

FP 01's ``key-findings`` (owner CP-2, numbered, pinned) shows the Python-numbered key findings,
one line per finding. ``strengths-weaknesses`` (owner "CP-2 · CP-6") gets CP-2's side: the
thesis, the strengths and the weaknesses, each a ``Binding.section`` column with the row's own
label. The Front Page tables hold one text per row (a prose block shows one line per bound
fact); the full r14 registers, with category, basis and limitation columns, go to Evidence and
the gaps ledger to Limitations, as ``bindings/cp1a.py`` does. Slots carry a ``cp2-`` prefix: a
slot is unique across all shipped maps. Now in ``SHIPPED_MAPS`` since task 8.6.
"""

from deploy_vii.bindings import Binder, BindingMap
from deploy_vii.business_context import CP1_REFERENCES
from deploy_vii.cp2_synthesis import KEY_FINDINGS, MODULE_ID, STRENGTHS, THESIS, WEAKNESSES

_bind = Binder(MODULE_ID, "cp2-", hyphenate=True).bind


CP2 = BindingMap(
    module_id=MODULE_ID,
    entries=(
        _bind(KEY_FINDINGS, "key-findings", "Key findings"),
        _bind(THESIS, "strengths-weaknesses", "Thesis", section="thesis"),
        _bind(STRENGTHS, "strengths-weaknesses", "Strengths", section="strengths"),
        _bind(WEAKNESSES, "strengths-weaknesses", "Weaknesses", section="weaknesses"),
        # Evidence.
        _bind("T2.1", "evidence", "Credit assessment"),
        _bind("T2.7", "evidence", "Thesis, strengths and weaknesses"),
        _bind("T2.10", "evidence", "Key findings register"),
        _bind("T2.11", "evidence", "Key credit risks"),
        _bind(CP1_REFERENCES, "evidence", "CP-1 facts referenced in CP-2 text"),
        # Limitations.
        _bind("T2.12", "limitations", "CP-2 gaps ledger"),
    ),
)
