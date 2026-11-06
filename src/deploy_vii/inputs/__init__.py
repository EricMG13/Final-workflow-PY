"""User-supplied input files and their self-checks.

`KINDS` maps each input kind to its validator; a new kind is one entry here. The predecessor's
`deploy-vii validate-input` CLI (`deploy_vii.__main__`) is not part of this import
(docs/reuse/manifest.json, excluded_python_modules): call the validators directly.
"""

from collections.abc import Callable, Mapping
from pathlib import Path

from deploy_vii.inputs.portfolio import validate_portfolio
from deploy_vii.inputs.rv_quotes import ValidationReport, validate_rv_quotes

KINDS: Mapping[str, Callable[[Path], ValidationReport]] = {
    "rv": validate_rv_quotes,
    "portfolio": validate_portfolio,
}
