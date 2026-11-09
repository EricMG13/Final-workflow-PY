"""Start the library on a stable loopback port and open its one-time launch link."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
import time
import urllib.request
import zlib
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import uvicorn

from . import quit as quitting
from .desktop import open_browser, platform_locations, show_error
from .launch import launch_link
from .model import digest
from .server import APPLICATION, Application

log = logging.getLogger("issuer_library")


def running_instance(address: str, instance: str) -> bool:
    """Whether this user's library already answers at the address."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    # A simultaneous launch may have bound the port but not started serving yet.
    for _ in range(5):
        try:
            with opener.open(f"{address}/health", timeout=2) as response:
                health = json.loads(response.read(4096))
        except (OSError, ValueError):
            health = None
        if (
            isinstance(health, dict)
            and health.get("application") == APPLICATION
            and health.get("instance") == instance
        ):
            return True
        time.sleep(0.2)
    return False


def rotate_log(path: Path) -> None:
    try:
        if path.stat().st_size > 1 << 20:
            os.replace(path, path.with_name("library.log.previous"))
    except OSError:
        pass


def announce(link: str, address: str, browse: bool) -> None:
    """Tell the person how to reach the library: open the launch link, or print it with
    --no-browser. The link (it holds the one-time ticket) never reaches the log."""
    if not browse:
        print("Issuer Library:", link, flush=True)
        return

    def open_link() -> None:
        try:
            open_browser(link)
        except OSError as error:
            log.warning("Open browser: %s", error)
            show_error(
                f"Open this link in your browser within 2 minutes; it works once:\n{link}\n{error}"
            )

    threading.Thread(target=open_link, daemon=True).start()
    print("Issuer Library:", address, flush=True)


def rediscover(app: Application, stopped: Callable[[], bool], every: float) -> None:
    """Rediscover every interval until stopped() or the library quits."""
    while not stopped():
        time.sleep(every)
        if not stopped() and not app.refresh_for_caller():
            return  # The library is quitting; no discovery starts again.


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="issuer-library", description=__doc__)
    parser.add_argument("--workspace", default="", help="Workspace folder (disabled by IT policy)")
    parser.add_argument(
        "--state-dir", default="", help="Override per-user state directory for testing"
    )
    parser.add_argument("--no-browser", action="store_true", help="Start without opening a browser")
    parser.add_argument(
        "--port", type=int, default=0, help="Loopback port; zero selects a stable per-user port"
    )
    arguments = parser.parse_args(argv)
    loc = platform_locations()
    if arguments.state_dir:
        loc = replace(loc, state=Path(os.path.abspath(arguments.state_dir)))
    os.makedirs(loc.state, mode=0o700, exist_ok=True)
    rotate_log(loc.state / "library.log")
    logging.basicConfig(
        filename=loc.state / "library.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    port = arguments.port or 49000 + zlib.crc32(str(loc.state).encode()) % 10000
    if not 1024 <= port <= 65535:
        raise ValueError("port must be between 1024 and 65535")
    host = f"127.0.0.1:{port}"
    address = f"http://{host}"
    try:
        listener = quitting.listen(port)
    except OSError as error:
        if not running_instance(address, digest(str(loc.state).encode())):
            raise ValueError(f"local port is occupied by another application: {error}") from error
        # This user's instance answers. Its session secret is in its memory only, so this launch
        # cannot sign a browser in to it; it asks the instance to quit instead (quit.py).
        listener = quitting.ask_to_quit(loc.state, port)
    quitting.clear_quit_files(loc.state)
    app = Application(loc, arguments.workspace, host)
    server = uvicorn.Server(
        uvicorn.Config(
            app.asgi,
            host="127.0.0.1",
            port=port,
            log_config=None,
            access_log=False,
            lifespan="off",
            timeout_keep_alive=30,
            timeout_graceful_shutdown=3,
            h11_max_incomplete_event_size=16384,
        )
    )

    def stop() -> None:
        server.should_exit = True

    app.stop = stop

    threading.Thread(
        target=rediscover, args=(app, lambda: server.should_exit, 30), daemon=True
    ).start()
    threading.Thread(
        target=quitting.watch_quit_requests,
        args=(app, lambda: server.should_exit, quitting.quit_poll),
        daemon=True,
    ).start()
    announce(
        link=launch_link(host, app.session.ticket()),
        address=address,
        browse=not arguments.no_browser,
    )
    log.info("Listening at %s", address)
    server.run(sockets=[listener])
    return 0


def main() -> int:
    try:
        return run()
    except (OSError, ValueError) as error:
        log.error("%s", error)
        show_error(str(error))
        return 1


if __name__ == "__main__":
    sys.exit(main())
