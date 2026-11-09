"""The browser walk fault helpers: crash scan, redaction, HTTP and request verdicts, faults.json."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "library_faults", ROOT / "apps/issuer-library/designs/faults.py"
)
faults = importlib.util.module_from_spec(spec)
spec.loader.exec_module(faults)


def test_crashes_finds_go_panic_python_traceback_and_race() -> None:
    log = (
        "listening on 53901\n"
        "panic: runtime error: index out of range\n"
        "goroutine 1 [running]:\n"
        "ok line\n"
        "Traceback (most recent call last):\n"
        '  File "x.py", line 1\n'
        "WARNING: DATA RACE\n"
    )
    assert len(faults.crashes(log)) == 3
    assert faults.crashes("listening\nGET /health 200\npanic recovered later\n") == []


def test_redact_replaces_every_key_value() -> None:
    assert faults.redact("a sk-abcdef123456 b", ["sk-abcdef123456", ""]) == "a [redacted] b"
    assert faults.redact("a short b", ["short"]) == "a short b"


def test_http_fault() -> None:
    assert faults.http_fault(500, "/api/workspace", frozenset())
    assert faults.http_fault(404, "/x", frozenset())
    assert not faults.http_fault(404, "/x", frozenset({(404, "/x")}))
    assert not faults.http_fault(200, "/x", frozenset())
    assert not faults.http_fault(304, "/x", frozenset())


def test_request_fault() -> None:
    assert not faults.request_fault("net::ERR_ABORTED")
    assert not faults.request_fault("NS_BINDING_ABORTED")
    assert faults.request_fault("net::ERR_CONNECTION_REFUSED")
    assert not faults.request_fault(None)


def test_faults_write_round_trips(tmp_path: Path) -> None:
    found = faults.Faults()
    found.add("chromium", "check", "bad", url="http://x/", artifacts=["a.png"])
    found.add("firefox", "exception", "boom")
    path = tmp_path / "faults.json"
    found.write(path, "offline", 7)
    data = json.loads(path.read_text())
    assert (data["scope"], data["passed"], data["failed"]) == ("offline", 7, 2)
    assert data["faults"][0] == {
        "walk": "chromium",
        "kind": "check",
        "detail": "bad",
        "url": "http://x/",
        "artifacts": ["a.png"],
    }
    assert data["faults"][1]["artifacts"] == []


def test_crashes_finds_a_recovered_handler_panic_after_a_log_timestamp() -> None:
    log = (
        "2026/11/07 12:00:01 listening\n2026/11/07 12:00:02 http: panic serving 127.0.0.1:1: boom\n"
    )
    assert len(faults.crashes(log)) == 1
    assert len(faults.crashes("http: panic serving x\n")) == 1


def test_faults_write_redacts_secrets_in_every_field(tmp_path: Path) -> None:
    found = faults.Faults()
    found.add("w", "exception", "key sk-abcdef123456 leaked", url="http://x/sk-abcdef123456")
    path = tmp_path / "faults.json"
    found.write(path, "scope", 0, secrets=["sk-abcdef123456"])
    assert "sk-abcdef123456" not in path.read_text()
    assert "[redacted]" in path.read_text()
