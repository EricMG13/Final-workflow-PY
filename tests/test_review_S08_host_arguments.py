"""S08 review pin: NaN/Infinity tool arguments are refused (bad_arguments, arguments {}) and the
source workflow stays in step with its session. The code-review finding (host.py:1135) did not
reproduce: host._detached already serialises with allow_nan=False. Synthetic pack; offline."""

import json

import pytest
from test_source_workflow import api, make_pack, observe, readiness


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_argument_is_refused_and_later_calls_proceed(tmp_path, value):
    module = api()
    pack = make_pack()
    workflow = module.SourceWorkflow.create(tmp_path / "execution", pack)
    refused = workflow.invoke(
        "read_pages", {"source_id": "identity", "first_page": value, "last_page": 1}
    )
    assert (refused["status"], refused["error_code"], refused["arguments"]) == (
        "refused", "bad_arguments", {}
    )
    json.dumps(refused, allow_nan=False)
    observe(workflow)
    assert workflow.submit_review(readiness(pack))["status"] == "valid"

