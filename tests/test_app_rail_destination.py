"""The rail destination for each route, from the real ``destOf`` in app.js, run under node."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1] / "src/deploy_vii/assets/app.js"
HARNESS = """
const modules = {"CP-1": {module_id: "CP-1"}, "CP-2": {module_id: "CP-2"}};
const moduleFor = (route) => modules[route];
%s
console.log(JSON.stringify(%s.map(route => [route, destOf(route)])));
"""


def destinations(source: str, routes: list[str], setup: str = "") -> dict[str, str | None]:
    found = re.search(r"  const destOf = \(route\) => \{.*?\n  \};\n", source, re.DOTALL)
    assert found, "destOf not found in app.js"
    script = HARNESS % (setup + found.group(0), json.dumps(routes))
    run = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    return dict(json.loads(run.stdout))


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_model_routes_light_the_model_rail_entry_and_the_others_are_unchanged() -> None:
    got = destinations(
        APP.read_text(encoding="utf-8"),
        ["CP-1", "CP-MODEL", "CP-2", "front", "analysis", "FIT", "evidence", "limitations", "x"],
    )
    assert got == {
        "CP-1": "model",
        "CP-MODEL": "model",  # model.html's rail link is #CP-MODEL
        "CP-2": "analysis",
        "front": "front",
        "analysis": "analysis",
        "FIT": "fit",
        "evidence": "evidence",
        "limitations": "limits",
        "x": None,
    }


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_cp_model_lights_model_whether_or_not_the_page_lists_it_as_a_module() -> None:
    """report.html lists CP-MODEL among its modules (its page is reached from the Model
    destination); model.html's patched rail link may name it without a module entry."""
    source = APP.read_text(encoding="utf-8")
    listed = 'modules["CP-MODEL"] = {module_id: "CP-MODEL"};\n'
    got = destinations(source, ["CP-MODEL", "CP-2"], setup=listed)
    assert got == {"CP-MODEL": "model", "CP-2": "analysis"}
    assert source.count('["model", "Model", "#CP-1"]') == 1  # the delivery patches need one
