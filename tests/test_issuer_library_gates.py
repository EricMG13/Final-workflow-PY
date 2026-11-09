"""The Issuer Library's gate scripts pass no provider key to what they start. Dummy values only."""

import importlib.util
from pathlib import Path

import pytest

from deploy_workflow.model.adapter import KEY_VARIABLES
from deploy_workflow.model.redact import KEY_ENV_NAMES

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps/issuer-library"
spec = importlib.util.spec_from_file_location("library_validate", APP / "validate.py")
validate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate)


def test_the_redactor_list_names_every_provider_key() -> None:
    # The gates strip KEY_ENV_NAMES, so it must hold every key a provider config can read.
    assert set(KEY_VARIABLES.values()) <= set(KEY_ENV_NAMES)


def test_validate_strips_every_provider_key_from_the_gate_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Expected by hand: the four KEY_VARIABLES names plus GH_TOKEN and GITHUB_TOKEN, all removed;
    # an unrelated variable passes through.
    names = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "OPENROUTER_API_KEY",
        "COPILOT_GITHUB_TOKEN",
        "GH_TOKEN",
        "GITHUB_TOKEN",
    ]
    for name in names:
        monkeypatch.setenv(name, "dummy-not-a-key")
    monkeypatch.setenv("ISSUER_LIBRARY_UNRELATED", "kept")
    env = validate.clean_env()
    assert [name for name in names if name in env] == []
    assert env["ISSUER_LIBRARY_UNRELATED"] == "kept"
    assert set(validate.KEYS) == set(KEY_ENV_NAMES)


@pytest.mark.parametrize("script", ["designs/browser_check.py", "packaging/smoke_test.py"])
def test_the_browser_and_smoke_checks_read_the_same_list(script: str) -> None:
    # Both start a process at import (a browser or the launcher), so their source is checked: the
    # strip list comes from redact.py, and no hand-kept tuple of key names remains.
    source = (APP / script).read_text(encoding="utf-8")
    assert 'src/deploy_workflow/model/redact.py"' in source.replace("'", '"')
    assert "KEY_ENV_NAMES" in source
    assert "'OPENROUTER_API_KEY'" not in source and '"OPENROUTER_API_KEY"' not in source


def test_the_nightly_runner_strips_the_same_keys() -> None:
    # tools/nightly_tests.py keeps its own copy of the list; it must not drift from the Redactor's.
    from tools import nightly_tests

    assert set(nightly_tests.KEYS) == set(KEY_ENV_NAMES)


def test_report_prints_every_fail_line(capsys: pytest.CaptureFixture[str]) -> None:
    validate.report("x", False, "FAIL early\n" + "ok\n" * 60)
    assert "FAIL early" in capsys.readouterr().out
