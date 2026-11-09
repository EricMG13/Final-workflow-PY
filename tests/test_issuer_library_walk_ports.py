"""The browser walk takes OS-assigned ports, not ones CI's outgoing connections can hold."""

import shutil
import socket
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DESIGNS = ROOT / "apps/issuer-library/designs"
sys.path.insert(0, str(DESIGNS))
import browser_check as bc

OLD_PORTS = range(53901, 53911)


def test_a_walk_server_starts_while_the_old_fixed_ports_are_taken(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(bc, "S", tmp_path)
    monkeypatch.setattr(bc, "PY", sys.executable)
    monkeypatch.setattr(bc, "LOGS", {})
    monkeypatch.setattr(bc, "SESSIONS", {})
    monkeypatch.setattr(bc, "DRAINS", [])
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    held: list[socket.socket] = []
    server = None
    try:
        for p in OLD_PORTS:  # bound, not listening: what an outgoing connection does
            probe = socket.socket()
            try:
                probe.bind(("127.0.0.1", p))
            except OSError:
                probe.close()  # already in use by something else
                continue
            held.append(probe)
        with pytest.raises(SystemExit):  # the premise: a held port stops the server
            bc.serve(workspace, OLD_PORTS[0], ROOT / "apps/issuer-library/engine")
        server, port = bc.serve_free(workspace, ROOT / "apps/issuer-library/engine")
        assert port not in OLD_PORTS
        assert port in bc.SESSIONS
        assert bc.LOGS[port].exists()
    finally:
        if server is not None:
            server.terminate()
            server.wait(timeout=10)
        for probe in held:
            probe.close()


def test_serve_free_retries_on_another_port_when_the_first_is_taken(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(bc, "S", tmp_path)
    monkeypatch.setattr(bc, "PY", sys.executable)
    monkeypatch.setattr(bc, "LOGS", {})
    monkeypatch.setattr(bc, "SESSIONS", {})
    monkeypatch.setattr(bc, "DRAINS", [])
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    picked: list[int] = []
    real = bc.free_port
    taken = socket.socket()  # bound, not listening: another process got there first
    taken.bind(("127.0.0.1", 0))

    def pick() -> int:
        picked.append(taken.getsockname()[1] if not picked else real())
        return picked[-1]

    monkeypatch.setattr(bc, "free_port", pick)
    server = None
    try:
        server, port = bc.serve_free(workspace, ROOT / "apps/issuer-library/engine")
        assert picked[0] == taken.getsockname()[1]
        assert port == picked[1] != picked[0]
        assert port in bc.SESSIONS
    finally:
        if server is not None:
            server.terminate()
            server.wait(timeout=10)
        taken.close()


def test_serve_free_raises_a_failure_that_is_not_a_taken_port(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(bc, "S", tmp_path)
    monkeypatch.setattr(bc, "PY", shutil.which("false") or "false")  # exits 1, names no port
    monkeypatch.setattr(bc, "LOGS", {})
    monkeypatch.setattr(bc, "SESSIONS", {})
    monkeypatch.setattr(bc, "DRAINS", [])
    calls: list[int] = []
    real = bc.free_port
    monkeypatch.setattr(bc, "free_port", lambda: calls.append(1) or real())
    with pytest.raises(SystemExit) as error:
        bc.serve_free(tmp_path, tmp_path)
    assert not isinstance(error.value, bc.PortTaken)
    assert len(calls) == 1
