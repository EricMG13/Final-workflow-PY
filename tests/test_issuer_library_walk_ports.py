"""The browser walk takes OS-assigned ports, not ones CI's outgoing connections can hold."""

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
        port = bc.free_port()
        assert port not in OLD_PORTS
        server = bc.serve(workspace, port, ROOT / "apps/issuer-library/engine")
        assert port in bc.SESSIONS
        assert bc.LOGS[port].exists()
    finally:
        if server is not None:
            server.terminate()
            server.wait(timeout=10)
        for probe in held:
            probe.close()
