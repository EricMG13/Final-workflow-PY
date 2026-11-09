"""S16 C10: a redirect may leave the scheme-default port only for the origin the manifest named."""

from collections.abc import Mapping

import pytest

from deploy_workflow.research import webfetch

HOST = "example.com"


class _Response:
    def __init__(self, status: int, headers: Mapping[str, str], body: bytes) -> None:
        self.status, self.headers, self.body = status, headers, body

    def getheader(self, name: str, default: str | None = None) -> str | None:
        return self.headers.get(name, default)

    def read(self, amt: int) -> bytes:
        out, self.body = self.body[:amt], self.body[amt:]
        return out


class _Connection:
    """Answers the first request of a fetch with the redirect (if any), later ones with 200."""

    def __init__(self, location: str | None, first: bool) -> None:
        self.location, self.first = location, first

    def request(self, method: str, url: str, *, headers: Mapping[str, str]) -> None:
        return None

    def getresponse(self) -> _Response:
        if self.location is not None and self.first:
            return _Response(302, {"Location": self.location}, b"")
        return _Response(200, {"Content-Type": "text/plain"}, b"landed")

    def close(self) -> None:
        return None


def _fetch(
    url: str, location: str | None
) -> tuple[list[tuple[str, int]], str | None, bytes | None]:
    seen: list[tuple[str, int]] = []

    def connect(target: webfetch.ConnectionTarget) -> _Connection:
        seen.append((target.host, target.port))
        return _Connection(location, first=len(seen) == 1)

    record, body, _media = webfetch.fetch(
        url,
        manifest_hosts=frozenset({HOST}),
        resolver=lambda _host: ["93.184.216.34"],
        connect=connect,
        cap=1000,
        clock=lambda: 0.0,
    )
    return seen, record.reason, body


# Hand-derived: only the first connection (443) happens when the redirect is refused.
@pytest.mark.parametrize(
    "location",
    [
        f"https://{HOST}:8443/admin",
        f"https://{HOST}:80/x",
        f"http://{HOST}:8080/x",
        f"https://{HOST}:444/x",
        f"https://{HOST.upper()}:8443/x",
    ],
)
def test_redirect_to_another_port_is_refused(location: str) -> None:
    seen, reason, body = _fetch(f"https://{HOST}/a", location)
    assert seen == [(HOST, 443)]
    assert body is None and reason is not None and "refused" in reason


@pytest.mark.parametrize("location", [f"https://{HOST}:443/b", f"https://{HOST}/b", "/b"])
def test_redirect_to_the_default_port_is_followed(location: str) -> None:
    seen, reason, body = _fetch(f"https://{HOST}/a", location)
    assert seen == [(HOST, 443), (HOST, 443)]
    assert reason is None and body == b"landed"


def test_redirect_to_the_origin_the_manifest_named_is_followed() -> None:
    # The manifest url itself names :8443, so that exact origin may be redirected to.
    seen, reason, body = _fetch(f"https://{HOST}:8443/a", f"https://{HOST}:8443/b")
    assert seen == [(HOST, 8443), (HOST, 8443)] and reason is None and body == b"landed"


def test_redirect_from_a_named_port_to_another_port_is_refused() -> None:
    seen, reason, body = _fetch(f"https://{HOST}:8443/a", f"https://{HOST}:9443/b")
    assert seen == [(HOST, 8443)] and body is None and reason is not None


def test_redirect_to_an_ipv6_literal_with_a_port_is_refused() -> None:
    seen, reason, body = _fetch(f"https://{HOST}/a", "https://[2001:db8::1]:8443/x")
    assert seen == [(HOST, 443)] and body is None and reason is not None


def _chain(
    url: str,
    locations: list[str],
    hosts: frozenset[str] = frozenset({HOST}),
    addresses: tuple[str, ...] = ("93.184.216.34",),
) -> tuple[list[tuple[str, int]], webfetch.FetchRecord, bytes | None]:
    """Each request answers 302 to the next location, then 200; the resolver gives one address per
    lookup in order (the last one repeated)."""
    seen: list[tuple[str, int]] = []
    pending, lookups = list(locations), list(addresses)

    def resolve(_host: str) -> list[str]:
        return [lookups.pop(0) if len(lookups) > 1 else lookups[0]]

    def connect(target: webfetch.ConnectionTarget) -> _Connection:
        seen.append((target.host, target.port))
        return _Connection(pending.pop(0) if pending else None, first=True)

    record, body, _media = webfetch.fetch(
        url, manifest_hosts=hosts, resolver=resolve, connect=connect, cap=1000, clock=lambda: 0.0
    )
    return seen, record, body


# S16 C10 review, hand-derived connection lists.
def test_a_chain_that_leaves_and_returns_to_the_named_origin_is_followed() -> None:
    seen, record, body = _chain(
        f"https://{HOST.upper()}:8443/a", [f"https://{HOST}/b", f"https://{HOST}:8443/c"]
    )
    assert seen == [(HOST, 8443), (HOST, 443), (HOST, 8443)]
    assert (record.reason, record.hops, body) == (None, 2, b"landed")


def test_another_manifest_host_is_reached_at_the_default_port_only() -> None:
    hosts = frozenset({"a.example", "b.example"})
    seen, record, body = _chain("https://b.example/x", ["https://a.example:8443/y"], hosts)
    assert seen == [("b.example", 443)] and body is None
    assert record.reason == (
        "redirect to a.example:8443 refused: not the default port or a named origin"
    )
    seen, record, body = _chain("https://b.example:8443/x", ["https://a.example/y"], hosts)
    assert seen == [("b.example", 8443), ("a.example", 443)] and body == b"landed"


def test_a_scheme_relative_redirect_to_another_port_is_refused() -> None:
    seen, record, body = _chain(f"https://{HOST}/a", [f"//{HOST}:8443/b"])
    assert seen == [(HOST, 443)] and body is None and record.reason is not None


def test_an_ipv6_origin_keeps_its_port_and_is_named_in_brackets() -> None:
    v6, hosts = "2001:db8::1", frozenset({"2001:db8::1"})
    seen, record, body = _chain(f"https://[{v6}]:8443/a", ["https://[2001:DB8::1]:8443/b"], hosts)
    assert seen == [(v6, 8443), (v6, 8443)] and body == b"landed"
    seen, record, body = _chain(f"https://[{v6}]:8443/a", [f"https://[{v6}]:9443/b"], hosts)
    assert seen == [(v6, 8443)] and body is None
    assert record.reason == (
        "redirect to [2001:db8::1]:9443 refused: not the default port or a named origin"
    )


def test_the_origin_port_keeps_the_redirect_limit_and_the_public_address_check() -> None:
    seen, record, body = _chain(f"https://{HOST}:8443/a", ["/1", "/2", "/3", "/4"])
    assert seen == [(HOST, 8443)] * 4 and body is None
    assert (record.reason, record.hops) == (
        f"https://{HOST}:8443/a redirected more than 3 times",
        3,
    )
    seen, record, body = _chain(
        f"https://{HOST}:8443/a",
        [f"https://{HOST}:8443/b"],
        addresses=("93.184.216.34", "10.0.0.1"),
    )
    assert seen == [(HOST, 8443)] and body is None
    assert record.reason == f"host {HOST} resolves to 10.0.0.1, which is not a public address"
