"""S11 review: splitting the delivery adapter into helpers left its output bytes unchanged.

Oracles: (1) a retained CP-OS delivery bundle written by an earlier run, compared byte for byte;
(2) delivery receipts captured from the pre-split adapter on 2026-11-06 for two retained
relative-value layouts (yield chart, chart routes, prose and tables). The receipt hashes every
other file. A deliberate renderer change elsewhere also changes (2); re-capture it then.
"""

import hashlib
import json
from pathlib import Path

import pytest

from deploy_workflow.handoff_delivery import delivery_files

ROOT = Path(__file__).resolve().parents[1]
READER = ROOT / "runs/cpos-launch-cp2-reader-001"


def test_retained_bundle_is_reproduced_byte_for_byte():
    manifest = next(READER.glob("delivery-593bc6819bec*.json"))
    retained = READER / "deliveries"
    files = delivery_files(manifest)
    delivery_id = hashlib.sha256(
        json.dumps(
            {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()},
            sort_keys=True,
        ).encode()
    ).hexdigest()
    bundle = retained / delivery_id
    assert bundle.is_dir()
    assert {p.name for p in bundle.iterdir()} == set(files)
    assert all((bundle / name).read_bytes() == raw for name, raw in files.items())


@pytest.mark.parametrize(
    "manifest,receipt",
    [
        (
            "runs/cpos-sol-remaining-20261105/pathways/relative_value/delivery.json",
            "17a76b45a740eed99419b2c56661dcbeea19d716629ca567b4a191de07706d5d",
        ),
        (
            (
                "runs/cpos-arcc-rv-001/execution/delivery-00f58d875d6ac7b80ff8515b4daee074fb48a79d"
                "ad913874e2088204bf3e8272.json"
            ),
            "0491bd5951ad2c2c0efac847743ed5b43637f30f0e62c43fa33e3bb7bf9a9344",
        ),
    ],
)
def test_split_adapter_keeps_the_pre_split_receipt(manifest, receipt):
    files = delivery_files(ROOT / manifest)
    assert hashlib.sha256(files["delivery.json"]).hexdigest() == receipt
    recorded = json.loads(files["delivery.json"])["files"]
    assert recorded == {
        name: hashlib.sha256(raw).hexdigest()
        for name, raw in files.items()
        if name != "delivery.json"
    }
