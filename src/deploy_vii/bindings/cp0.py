"""CP-0 source readiness -> header, Evidence and Limitations blocks."""

from deploy_vii.bindings import Binder, BindingMap

_bind = Binder("CP-0").bind


CP0 = BindingMap(
    module_id="CP-0",
    entries=(
        _bind("T1", "header", slot="run-identity"),
        _bind("T2", "evidence", slot="source-inventory"),
        _bind("P3", "evidence", slot="source-classification"),
        _bind("P5", "evidence", slot="preparation"),
        _bind("T3", "evidence", slot="authority"),
        _bind("T6", "evidence", slot="quotations"),
        _bind("T4", "evidence", slot="consumer-readiness"),
        _bind("T8", "evidence", slot="commands"),
        _bind("T5", "limitations", slot="gaps"),
        _bind("T7", "limitations", slot="assertion-scope"),
    ),
)
