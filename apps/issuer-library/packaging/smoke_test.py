"""Exercise the launcher over loopback, without a browser or providers.

With no argument it starts the repository's own server (the uv environment, PYTHONPATH=src).
With a package folder it starts that package's pinned runtime, as the Windows launcher does.
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from deploy_workflow.model.adapter import KEY_VARIABLES

workspace = ROOT
environment = os.environ.copy()
# Every provider key the adapters read: the smoke run never pays.
for key in KEY_VARIABLES.values():
    environment.pop(key, None)
if len(sys.argv) > 1:
    package = Path(sys.argv[1]).resolve()
    launcher = [
        str(package / "engine/runtime/python.exe"),
        "-I",
        "-B",
        "-X",
        "utf8",
        "-m",
        "issuer_library",
    ]
    context = (package / "engine/smoke-context.json").read_bytes()
else:
    launcher = [sys.executable, "-B", "-X", "utf8", "-m", "issuer_library"]
    environment["PYTHONPATH"] = str(ROOT / "src")
    context = (ROOT / "cases/context/research-minimal.json").read_bytes()
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
with tempfile.TemporaryDirectory(prefix="issuer-library-smoke-") as temporary:
    state = Path(temporary) / "state"
    other = Path(temporary) / "workspace-émetteur"
    other.mkdir()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    address = f"http://127.0.0.1:{port}"
    arguments = [*launcher, "--state-dir", str(state), "--port", str(port), "--no-browser"]

    def request(endpoint, payload=None, content_type="application/json"):
        headers = {}
        raw = None
        if payload is not None:
            raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            headers = {"Content-Type": content_type, "X-Issuer-Library": "1", "Origin": address}
        with opener.open(
            urllib.request.Request(address + endpoint, raw, headers), timeout=10
        ) as response:
            body = response.read()
            return json.loads(body) if "json" in response.headers["Content-Type"] else body

    def ready(process):
        for _ in range(100):
            if process.poll() is not None:
                raise AssertionError("Launcher exited before serving")
            try:
                request("/health")
                return
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.1)
        raise AssertionError("Launcher did not become ready")

    process = subprocess.Popen(
        arguments + ["--workspace", str(workspace)], env=environment, stdout=subprocess.DEVNULL
    )
    try:
        ready(process)
        catalogue = request("/api/catalogue")
        # The HTML Model deliveries hold no report, which the library does not present yet.
        assert sorted(issue.split(":")[0] for issue in catalogue["issues"]) == [
            f"deliverables/tdg-model-{n}" for n in (1, 2, 3)
        ]
        runs = {row["id"] for row in catalogue["real"] if not row["id"].startswith("delivery:")}
        assert runs == {path.name for path in (workspace / "runs").iterdir() if path.is_dir()}
        reports = {
            a["href"] for row in catalogue["real"] for a in row["artifacts"] if a["available"]
        }
        assert len(reports) == len(list(workspace.glob("deliverables/*/report.html"))) + len(
            list(workspace.glob("runs/*/deliveries/*/report.html"))
        )
        for report in reports:
            assert b"<html" in request(report).lower()
        store = request("/api/workspace")
        assert "tdg-002" in store["runs"] and len(store["reports"]) == len(reports)
        subprocess.run(arguments, timeout=5, check=True, env=environment)
        request("/api/settings", {"workspace": str(other)})
        boundary = "IssuerLibraryOfflineSmoke"
        parts = []
        for name, raw in [
            ("context", context),
            ("config", b"sol-medium"),
            ("cap_usd", b"10.00"),
            ("source_paths", b'["annual.txt"]'),
        ]:
            parts.append(
                f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
                + raw
                + b"\r\n"
            )
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="sources"; filename="source.txt"\r\nContent-Type: text/plain\r\n\r\nSynthetic offline source. No issuer analysis.\r\n--{boundary}--\r\n'.encode()
        )
        review = request(
            "/api/runs/review", b"".join(parts), "multipart/form-data; boundary=" + boundary
        )
        assert review["ok"] and not review["provider_ready"], review
        draft = other / "intake" / review["id"]
        assert (draft / "review.json").exists()
        assert list((other / "runs").iterdir()) == [], "Offline review created a run"
        try:
            request(
                "/api/runs/start",
                {"id": review["id"], "review_id": review["review_id"], "confirm": True},
            )
        except urllib.error.HTTPError as error:
            assert error.code == 409
        else:
            raise AssertionError("Unconfigured provider passed the Start gate")
        assert not (draft / "start.claim").exists()
        added = other / "runs/automatically-discovered"
        added.mkdir(parents=True)
        (added / "CP-0.md").write_text("Synthetic discovery smoke fixture.\n", encoding="utf-8")
        for _ in range(38):
            catalogue = request("/api/catalogue")
            if any(row["id"] == "automatically-discovered" for row in catalogue["real"]):
                break
            time.sleep(1)
        else:
            raise AssertionError("Periodic discovery did not find new run")
        assert catalogue["real"][0]["completion"] is None
        request("/api/quit", {})
        assert process.wait(timeout=5) == 0
        process = subprocess.Popen(arguments, env=environment, stdout=subprocess.DEVNULL)
        ready(process)
        assert request("/api/catalogue")["workspace"] == str(other)
        request("/api/quit", {})
        assert process.wait(timeout=5) == 0
        print(
            "PASS: launch, retained reports, workspace store, repeat launch, Unicode workspace, offline "
            "CP-OS context/source/budget review and unavailable-provider Start gate, automatic discovery, "
            "settings persistence, shutdown and restart; no browser acceptance implied."
        )
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
