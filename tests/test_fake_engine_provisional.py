"""The rehearsal fake engine writes the frozen key's Task 10 register for CP-4 and the Provisional
sentence for its consumers. Expected texts come from tests/fixtures/primary-provisional/
rehearsal-key.json; each answer also goes through the real checker (no server)."""

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest
from test_cpos_provisional import instructions_of, new_categories, prepared_for
from test_fake_engine_pro_forma import PLAIN

from deploy_vii.cp4_legal import DRAFT_LIMITATION
from deploy_workflow.owners.cpos import HandoffTask, _checked_handoff
from deploy_workflow.owners.cpos_launch import (
    CONSUMER_SENTENCE,
    CONSUMERS,
    OPENING,
    PROVISIONAL_PARAGRAPH,
    checker,
)

ROOT = Path(__file__).resolve().parents[1]
KEY = json.loads(
    (ROOT / "tests/fixtures/primary-provisional/rehearsal-key.json").read_text(encoding="utf-8")
)
MODULES = ["CP-0", "CP-1", "CP-1A", "CP-1D", "CP-2", "CP-4", "CP-3", "CP-5", "CP-6"]
CELL = "| A fake engine finding only. | Low | Fake data. |"
VIEW = "A fake engine view only.\n\n"
UPSTREAM = {"CP-1": b"# upstream"}


def filled(text: str | None) -> str:
    return (text or "").replace("{DRAFT_LIMITATION}", DRAFT_LIMITATION)


@pytest.fixture
def engine(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("CHECK_ROOT", str(ROOT))
    monkeypatch.delenv("FAKE_MALFORMED", raising=False)
    path = ROOT / "apps/issuer-library/designs/fake_engine/bridge.py"
    spec = importlib.util.spec_from_file_location("fake_bridge_provisional", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def prepared(tmp_path: Path) -> Any:
    return prepared_for(tmp_path, "credit_snapshot", "primary", "draft", MODULES)


def fake_text(
    engine: Any, prepared: Any, module: str, handoffs: dict[str, bytes], instructions: str
) -> str:
    context = {
        "module_id": module,
        "sources": {"annual.txt": hashlib.sha256(b"Net sales").hexdigest()},
        "handoffs": {n: {"sha256": hashlib.sha256(r).hexdigest()} for n, r in handoffs.items()},
    }
    routes = [
        {"module_id": r.module_id, "heading": r.heading, "kind": r.kind}
        for r in prepared.plan.layout.routes
    ]
    run = {"issuer_name": prepared.plan.run.issuer_name, "as_of": str(prepared.plan.run.as_of)}
    return str(
        engine.handoff_markdown(context, {"run": run, "layout": {"routes": routes}}, instructions)
    )


def key_placed(plain: str, given: dict[str, Any], headings: list[str]) -> str:
    """The key's placement (its `placement` entries) applied to the fake's plain text."""
    text = plain.replace("Fake data.", filled(given["main_limitation"]))
    if given["routed_sections_text"]:
        for heading in headings:
            head = f"### {heading}\n\n"
            text = text.replace(head, head + filled(given["routed_sections_text"]) + "\n\n")
    if given["findings_text"]:
        text = text.replace(VIEW, VIEW + filled(given["findings_text"]) + "\n\n")
    if given["register"]:
        register = "### Legal document register\n\n" + given["register"] + "\n\n## Calculations"
        text = text.replace("## Calculations", register, 1)
    return text


def issues_of(prepared: Any, module: str, text: str, handoffs: dict[str, bytes]) -> tuple[str, ...]:
    task = HandoffTask(
        prepared.plan.run,
        module,
        instructions_of(prepared, module),
        {"annual.txt": b"Net sales", "context": b"{}"},
        handoffs,
        1,
        (),
    )
    return tuple(_checked_handoff(task, text.encode(), checker(prepared.layout)))


def cp4_headings(prepared: Any) -> list[str]:
    return [r.heading for r in prepared.plan.layout.routes if r.module_id == "CP-4"]


def test_the_prepared_run_carries_the_trigger_texts(prepared: Any) -> None:
    assert PROVISIONAL_PARAGRAPH.encode() in instructions_of(prepared, "CP-4")
    for module in CONSUMERS:
        assert CONSUMER_SENTENCE.encode() in instructions_of(prepared, module)


def test_cp4_writes_the_keys_register_and_passes_the_checker(engine: Any, prepared: Any) -> None:
    instructions = instructions_of(prepared, "CP-4").decode()
    plain = fake_text(engine, prepared, "CP-4", UPSTREAM, "Method.\n\nEnd.")
    text = fake_text(engine, prepared, "CP-4", UPSTREAM, instructions)
    given = KEY["cp4_case"]["text"]
    assert text == key_placed(plain, given, cp4_headings(prepared))
    assert text.count("### Legal document register") == 1
    assert text.count(DRAFT_LIMITATION) == 1
    assert text.count(given["register"]) == 1
    assert issues_of(prepared, "CP-4", text, UPSTREAM) == tuple(
        KEY["cp4_case"]["key_expected"]["issues"]
    )


@pytest.mark.parametrize("module", CONSUMERS)
def test_consumers_write_the_keys_provisional_limitation(
    engine: Any, prepared: Any, module: str
) -> None:
    instructions = instructions_of(prepared, module).decode()
    cp4 = fake_text(engine, prepared, "CP-4", UPSTREAM, instructions_of(prepared, "CP-4").decode())
    handoffs = UPSTREAM | {"CP-4": cp4.encode()}
    plain = fake_text(engine, prepared, module, handoffs, "Method.\n\nEnd.")
    text = fake_text(engine, prepared, module, handoffs, instructions)
    assert text == plain.replace("Fake data.", KEY["consumers"]["text"])
    assert issues_of(prepared, module, text, handoffs) == ()
    assert new_categories(issues_of(prepared, module, plain, handoffs)) == {
        "consumer_provisional_missing"
    }


@pytest.mark.parametrize("module", ["CP-4", "CP-3", "CP-2"])
def test_without_the_trigger_texts_the_old_text_is_unchanged(engine: Any, module: str) -> None:
    routes = (("Sources and uses", "table"), ("A chart", "chart"), ("Some prose", "prose"))
    plan = {
        "run": {"issuer_name": "Issuer", "as_of": "2014-06-30"},
        "layout": {"routes": [{"module_id": module, "heading": h, "kind": k} for h, k in routes]},
    }
    context = {
        "module_id": module,
        "sources": {"a.pdf": "1111"},
        "handoffs": {"CP-1": {"sha256": "2222"}},
    }
    expected = PLAIN.replace("# CP-3", f"# {module}").replace("OPENING", OPENING[module])
    assert engine.handoff_markdown(context, plan, "Method.\n\nEnd.") == expected
    # Neither text reaches a module outside CP-4 and the consumers.
    both = f"Method.\n\n{PROVISIONAL_PARAGRAPH}\n\n{CONSUMER_SENTENCE}\n\nEnd."
    if module == "CP-2":
        assert engine.handoff_markdown(context, plan, both) == expected
    # Each text reaches only its own modules.
    if module == "CP-4":
        assert (
            engine.handoff_markdown(context, plan, f"Method.\n\n{CONSUMER_SENTENCE}\n\n")
            == expected
        )
    if module == "CP-3":
        assert (
            engine.handoff_markdown(context, plan, f"Method.\n\n{PROVISIONAL_PARAGRAPH}\n\n")
            == expected
        )


def test_malformed_cp4_writes_the_keys_rejected_case(
    engine: Any, prepared: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    instructions = instructions_of(prepared, "CP-4").decode()
    plain = fake_text(engine, prepared, "CP-4", UPSTREAM, "Method.\n\nEnd.")
    monkeypatch.setenv("FAKE_MALFORMED", "CP-4")
    text = fake_text(engine, prepared, "CP-4", UPSTREAM, instructions)
    given = KEY["malformed"]["text"]
    assert text == key_placed(plain, given, cp4_headings(prepared))
    assert DRAFT_LIMITATION not in text
    found = issues_of(prepared, "CP-4", text, UPSTREAM)
    assert new_categories(found) == set(KEY["malformed"]["key_expected"]["issues"])
    assert any(i.startswith(KEY["malformed"]["issue_prefix"]) for i in found)
    # Without the paragraph the old text is written even in this mode.
    assert fake_text(engine, prepared, "CP-4", UPSTREAM, "Method.\n\nEnd.") == plain


@pytest.mark.parametrize("env_value", ["CP-2", "CP-4"])
def test_the_variable_holds_one_module_and_changes_no_other(
    engine: Any, prepared: Any, monkeypatch: pytest.MonkeyPatch, env_value: str
) -> None:
    """FAKE_MALFORMED holds one module id (an equality test), so CP-2 and CP-4 are not malformed
    together: each value malforms only its own module; every other module is as without it."""
    clean = {
        m: fake_text(engine, prepared, m, UPSTREAM, instructions_of(prepared, m).decode())
        for m in MODULES
    }
    monkeypatch.setenv("FAKE_MALFORMED", env_value)
    for module in MODULES:
        text = fake_text(
            engine, prepared, module, UPSTREAM, instructions_of(prepared, module).decode()
        )
        assert (text != clean[module]) == (module == env_value)
