"""Where the workspace comes from: policy, the user's file, the package default, Documents."""

from __future__ import annotations

import os
import socket
from pathlib import Path
from typing import Any

import pytest

from issuer_library import __main__ as launcher
from issuer_library.settings import Config, Locations, load_config, save_json


def locations(tmp_path: Path, defaults: Path | None = None) -> Locations:
    return Locations(
        state=tmp_path / "state",
        documents=tmp_path / "documents",
        policy=tmp_path / "policy.json",
        defaults=defaults,
    )


def test_package_default_used_only_without_user_setting(tmp_path: Path) -> None:
    defaults = tmp_path / "package" / "default-workspace.json"
    save_json(defaults, {"workspace": str(tmp_path / "shared")})
    loc = locations(tmp_path, defaults)
    assert load_config(loc) == (Config(workspace=str(tmp_path / "shared")), False)
    save_json(loc.state / "settings.json", {"workspace": str(tmp_path / "mine")})
    assert load_config(loc) == (Config(workspace=str(tmp_path / "mine")), False)
    fallback = (Config(workspace=str(tmp_path / "documents" / "FinalWorkflow")), False)
    (loc.state / "settings.json").unlink()
    gone = tmp_path / "nowhere" / "default-workspace.json"
    assert load_config(locations(tmp_path, gone)) == fallback
    assert load_config(locations(tmp_path)) == fallback


def test_package_default_must_be_absolute(tmp_path: Path) -> None:
    defaults = tmp_path / "package" / "default-workspace.json"
    save_json(defaults, {"workspace": "relative"})
    with pytest.raises(ValueError, match="default-workspace.json") as relative:
        load_config(locations(tmp_path, defaults))
    assert str(defaults) in str(relative.value)
    defaults.write_text("{")
    with pytest.raises(ValueError) as malformed:
        load_config(locations(tmp_path, defaults))
    assert str(defaults) in str(malformed.value)


def test_policy_still_wins_and_locks(tmp_path: Path) -> None:
    defaults = tmp_path / "package" / "default-workspace.json"
    save_json(defaults, {"workspace": str(tmp_path / "shared")})
    loc = locations(tmp_path, defaults)
    save_json(loc.state / "settings.json", {"workspace": str(tmp_path / "mine")})
    assert loc.policy is not None
    save_json(loc.policy, {"workspace": str(tmp_path / "managed")})
    assert load_config(loc) == (Config(workspace=str(tmp_path / "managed")), True)


class Reached(Exception):
    pass


@pytest.mark.parametrize("relative", [True, False])
def test_defaults_option_reaches_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, relative: bool
) -> None:
    seen: list[Locations] = []
    opened: list[socket.socket] = []
    real_listen = launcher.quitting.listen

    def listen(port: int) -> socket.socket:
        opened.append(real_listen(port))
        return opened[-1]

    def recorder(loc: Locations, *_: Any) -> None:
        seen.append(loc)
        raise Reached

    monkeypatch.setattr(launcher, "Application", recorder)
    monkeypatch.setattr(launcher.quitting, "listen", listen)
    monkeypatch.chdir(tmp_path)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    name = "package/default-workspace.json" if relative else str(tmp_path / "d.json")
    base = ["--state-dir", str(tmp_path / "state"), "--no-browser"]
    try:
        for extra in (["--port", str(port), "--defaults", name], ["--port", str(port)]):
            with pytest.raises(Reached):
                launcher.run(base + extra)
            opened.pop().close()
    finally:
        for stream in opened:
            stream.close()
    assert seen[0].defaults == Path(os.path.abspath(name))
    assert seen[1].defaults is None
