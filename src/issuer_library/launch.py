"""The per-launch secrets: a one-time ticket in the launch link and the session cookie it buys.

Host, Origin and Sec-Fetch-Site stop browsers and DNS rebinding, but any local process can set
them. So each launch makes two random values held in memory only: a one-time ticket, carried
once in the URL the launcher opens, and a session secret the browser receives as a cookie in
exchange. Neither is written to disk, the log, settings, the index or any response body.
"""

from __future__ import annotations

import secrets
import threading
import time
from collections.abc import Callable

# How long the ticket works after the library is ready: time for a browser to start on a slow
# machine, and a short window for a ticket other local users may read on the opener's command line.
TICKET_LIFETIME = 120.0

# A module variable so tests can move it.
clock: Callable[[], float] = time.monotonic

# The whole answer to a request without the session cookie.
LAUNCHER_ONLY = (
    "Open Credit OS from its launcher. This page is not part of the library's current "
    "session. If the library is already running, start it again: a library with no run or "
    "review in progress quits and the new launch opens a fresh window."
)

# What a second launch reports when the running instance neither quits nor answers its quit
# request: its secret is in its memory only, so this launch cannot sign a browser in to it.
ALREADY_RUNNING = (
    "Credit OS is already running and did not quit for this launch. Quit the running "
    "library (Settings > Quit library, or end Credit OS in Task Manager), then start it "
    "again."
)


def cookie_name(host: str) -> str:
    """Cookies are not kept apart by port, so a second instance must not replace this one's."""
    return "issuer-library-" + host.rpartition(":")[2]


def launch_link(host: str, ticket: str) -> str:
    return f"http://{host}/launch?ticket={ticket}"


class Session:
    """One launch's ticket and session secret, in memory only."""

    def __init__(self, ticket_ttl: float = TICKET_LIFETIME) -> None:
        self._lock = threading.Lock()
        self._ticket = secrets.token_hex(32)
        self.cookie = secrets.token_hex(32)
        self.expires = clock() + ticket_ttl

    def ticket(self) -> str:
        """The unspent ticket; empty once exchanged or found expired."""
        with self._lock:
            if not clock() < self.expires:
                self._ticket = ""
            return self._ticket

    def exchange(self, ticket: str) -> str | None:
        """Spend the ticket once for the session secret; a wrong or late ticket spends nothing."""
        with self._lock:
            if not clock() < self.expires:
                self._ticket = ""
            valid = bool(self._ticket) and secrets.compare_digest(
                ticket.encode("utf-8"), self._ticket.encode("utf-8")
            )
            if valid:
                self._ticket = ""
                return self.cookie
            return None

    def valid(self, cookie: str) -> bool:
        return secrets.compare_digest(cookie.encode("utf-8"), self.cookie.encode("utf-8"))
