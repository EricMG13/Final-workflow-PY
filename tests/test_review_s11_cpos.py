"""S11 review: CP-OS resume, retained reuse, CP-8 repair feedback and adapter release.

Infrastructure regressions with synthetic or retained answers, not model proof.
"""

import hashlib
import json
import ntpath
import posixpath
from datetime import date
from pathlib import Path
from types import MappingProxyType

import pytest

from deploy_vii.contracts import Run
from deploy_workflow.owners import cpos
from deploy_workflow.owners.cpos import HEADINGS, HandoffTask, _handoff, run_handoffs
from deploy_workflow.owners.cpos_launch import pinned_path

RUN = Run(
    run_id="r",
    issuer_id="acme",
    issuer_name="Acme",
    as_of=date(2025, 12, 31),
    case_kind="public",
    pathway="credit_snapshot",
    requested_modules=("CP-2",),
)
ANSWER = ("# CP-2 Acme\n" + "".join(f"## {h}\nx\n" for h in HEADINGS)).encode()


def task() -> HandoffTask:
    return HandoffTask(RUN, "CP-2", b"instr", MappingProxyType({}), MappingProxyType({}), 1, ())


def test_resume_applies_a_corrected_checker_to_the_paid_response(tmp_path):
    calls = []

    def execute(current):
        calls.append(current.attempt)
        return ANSWER

    with pytest.raises(ValueError, match="cpos_module_failed: CP-2: spurious issue"):
        _handoff(task(), tmp_path, execute, lambda t, r: ("spurious issue",), 1)
    raw, path = _handoff(task(), tmp_path, execute, lambda t, r: (), 1)
    assert (raw, calls) == (ANSWER, [1])
    folder = (tmp_path / path).parent
    first = json.loads((folder / "1.review.json").read_bytes())
    assert first["issues"] == ["spurious issue"]  # the original verdict is kept unchanged
    (recheck,) = folder.glob("1.review-*.json")
    assert json.loads(recheck.read_bytes())["issues"] == []
    # A third resume with the same corrected checker adds nothing.
    assert _handoff(task(), tmp_path, execute, lambda t, r: (), 1) == (raw, path)
    assert len(list(folder.glob("1.review*.json"))) == 2


def test_resume_keeps_the_feedback_a_retained_retry_was_sent_with(tmp_path):
    sent = []

    def execute(current):
        sent.append(current.feedback)
        return ANSWER if current.attempt == 2 else ANSWER + b"draft"

    def first_checker(t, raw):
        return ("old wording",) if raw != ANSWER else ()

    raw, path = _handoff(task(), tmp_path, execute, first_checker, 2)
    assert path.endswith("2.response.md") and sent == [(), ("old wording",)]

    def stricter(t, raw):
        return ("new wording",) if raw != ANSWER else ()

    assert _handoff(task(), tmp_path, execute, stricter, 2) == (raw, path)
    assert len(sent) == 2


def test_retained_answer_is_stale_only_against_its_declared_upstream(tmp_path):
    from test_cpos_handoffs import RESPONSES, checked, replay, retained_job

    path = retained_job(tmp_path, ["CP-0", "CP-1A"])
    data = json.loads(path.read_bytes())
    # CP-1A consumed only CP-0 (its catalog requirement); CP-1 also runs earlier.
    data["retained_handoffs"]["CP-1A"]["upstream"] = {
        "CP-0": hashlib.sha256(RESPONSES["CP-0"]).hexdigest()
    }
    path.write_text(json.dumps(data))
    seen = {}

    def check(t, raw):
        seen[t.module_id] = list(t.handoffs)
        return checked(t, raw)

    report = run_handoffs(path, tmp_path / "state", execute=replay, check=check)
    assert report.exists()
    assert seen["CP-1A"] == ["CP-0"] and seen["CP-2"] == ["CP-0", "CP-1", "CP-1A"]
    data["retained_handoffs"]["CP-1A"]["upstream"]["CP-0"] = "0" * 64
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match=r"cpos_retained_stale: CP-1A: .*changed \['CP-0'\]"):
        run_handoffs(path, tmp_path / "state2", execute=replay, check=checked)


def test_any_cp8_publication_refusal_is_repair_feedback(tmp_path):
    from test_cpos_comparison import RESPONSE, check, job

    path = job(tmp_path)
    data = json.loads(path.read_bytes())
    data["max_attempts"] = 2
    path.write_text(json.dumps(data))
    broken = RESPONSE.replace(b"| Values | Synthetic prior observation |", b"| Values |", 1)
    answers = [broken, RESPONSE]
    report = cpos.run_comparison(
        path, tmp_path / "state", execute=lambda t: answers[t.attempt - 1], check=check
    )
    assert (report.parent / "CP-8.md").read_bytes() == RESPONSE
    (second,) = (tmp_path / "state").glob("requests/CP-8/*/2.request.json")
    assert json.loads(second.read_bytes())["feedback"] == [
        "Markdown table row does not match its header"
    ]


def live_comparison(tmp_path, monkeypatch, outcome):
    from test_cpos_comparison import job

    path = job(tmp_path)
    data = json.loads(path.read_bytes())
    data.update(execution="live-provider", provider_cap_usd="10", max_attempts=1)
    path.write_text(json.dumps(data))
    monkeypatch.setattr(cpos, "live_adapter_for", lambda *a: object())
    monkeypatch.setattr("deploy_workflow.model.handoff.HandoffExecutor", lambda *a, **k: None)
    monkeypatch.setattr(cpos, "run_comparison", outcome)

    def release(adapter):
        raise OSError("close failed")

    monkeypatch.setattr(cpos, "_release", release)
    return cpos.run_live_comparison(path, tmp_path / "state", ruling=Path("r"), check=lambda *a: ())


def test_live_comparison_release_failure_does_not_mask_the_stop(tmp_path, monkeypatch):
    def stop(*args, **kwargs):
        raise ValueError("cp8_issuer: both deliveries must identify the selected issuer")

    with pytest.raises(ValueError, match="cp8_issuer") as stopped:
        live_comparison(tmp_path, monkeypatch, stop)
    assert stopped.value.__notes__ == ["adapter release also failed: close failed"]
    assert "adapter release also failed: close failed" in str(stopped.value)


def test_live_comparison_release_failure_keeps_the_finished_result(tmp_path, monkeypatch):
    with pytest.warns(RuntimeWarning, match="adapter release failed: close failed"):
        report = live_comparison(tmp_path, monkeypatch, lambda *a, **k: tmp_path / "report.html")
    assert report == tmp_path / "report.html"


@pytest.mark.parametrize(
    "path,directory,module,expected",
    [
        (r"D:\issuers\acme\10-K.pdf", r"C:\Final\runs\acme", ntpath, r"D:\issuers\acme\10-K.pdf"),
        (
            r"C:\issuers\acme\10-K.pdf",
            r"c:\Final\runs\acme",
            ntpath,
            r"..\..\..\issuers\acme\10-K.pdf",
        ),
        ("/data/acme/10-K.pdf", "/home/runs/acme", posixpath, "../../../data/acme/10-K.pdf"),
    ],
)
def test_sources_on_another_drive_are_pinned_absolute(path, directory, module, expected):
    assert pinned_path(path, directory, module) == expected
