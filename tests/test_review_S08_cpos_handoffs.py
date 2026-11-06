"""S08 review regressions for the CP-OS Markdown transport adapter (cpos_handoffs).

Synthetic, offline: a staged O2 case and a retained in-memory module; no provider call."""

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import o2_case
import pytest

from deploy_vii.contracts import Claim, Module, View
from deploy_vii.preparation import load_pack
from deploy_workflow.cpos_handoffs import deliver, retain

ROOT = Path(__file__).resolve().parents[1]


class _Store:
    def __init__(self, run_dir, module):
        self.directory = run_dir / "execution"
        self.module = module

    def read(self):
        head = SimpleNamespace(
            module_id=self.module.module_id, result_sha256=self.module.content_hash()
        )
        return SimpleNamespace(heads=[head])

    def head_module(self, head):
        return self.module


def _store(tmp_path, text="Revenue rose year over year."):
    _, run_dir = o2_case.stage(tmp_path / "case")
    pack = load_pack(run_dir / "pack")
    module = Module(
        run_id=pack.run.run_id, issuer_id=pack.run.issuer_id, as_of=pack.run.as_of,
        module_id="CP-1", status="accepted",
        claims=(Claim(claim_id="c1", text=text, citations=()),),
    )
    return run_dir, _Store(run_dir, module)


def test_a_module_with_a_claim_is_retained_and_delivered(tmp_path):
    run_dir, store = _store(tmp_path)
    handoff = retain(store)["CP-1"].read_text(encoding="utf-8")
    assert "- c1: Revenue rose year over year." in handoff
    deliver(store, run_dir / "delivery")
    view = View.model_validate_json((run_dir / "delivery/view.json").read_bytes())
    claims = next(m for m in view.modules if m.module_id == "CP-1").claims
    assert [(claim.claim_id, claim.text) for claim in claims] == [
        ("c1", "Revenue rose year over year.")
    ]


def test_a_publication_file_cannot_replace_the_delivered_report(tmp_path):
    run_dir, store = _store(tmp_path)
    (run_dir / "publication").mkdir()
    (run_dir / "publication" / "report.html").write_text("other report", encoding="utf-8")
    with pytest.raises(ValueError, match=r"publication file report\.html would replace"):
        deliver(store, run_dir / "delivery")
    assert not (run_dir / "delivery" / "report.html").exists()


def test_a_resumed_delivery_rewrites_the_same_folder(tmp_path):
    run_dir, store = _store(tmp_path)
    (run_dir / "publication").mkdir()
    (run_dir / "publication" / "summary.md").write_text("# Summary\n", encoding="utf-8")
    deliver(store, run_dir / "delivery")
    first = (run_dir / "delivery" / "delivery.json").read_bytes()
    deliver(store, run_dir / "delivery")
    manifest = json.loads((run_dir / "delivery" / "delivery.json").read_bytes())
    assert (run_dir / "delivery" / "delivery.json").read_bytes() == first
    assert "delivery.json" not in manifest["files"]
    assert {"view.json", "report.html", "summary.md"} <= set(manifest["files"])


def test_handoffs_are_read_as_utf8_whatever_the_locale(tmp_path):
    script = (
        "import sys; from pathlib import Path\n"
        "sys.path[:0] = [sys.argv[1] + '/src', sys.argv[1] + '/tests', sys.argv[1]]\n"
        "import test_review_S08_cpos_handoffs as t\n"
        "run_dir, store = t._store(Path(sys.argv[2]), 'Umsatz stieg – Ergebnis über Plan')\n"
        "t.deliver(store, run_dir / 'delivery')\n"
    )
    result = subprocess.run(
        [sys.executable, "-X", "warn_default_encoding", "-W",
         "error::EncodingWarning:deploy_workflow.cpos_handoffs", "-c", script, str(ROOT), str(tmp_path)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr[-2000:]
