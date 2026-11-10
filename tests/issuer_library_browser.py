"""Browser harness for the Issuer Library front end: real Chromium over routed local files.

Every request a page makes is answered from the repository (the web folder, the design
fixture or a retained deliverable) or by a synthetic API reply; nothing reaches a server
or a provider. The session browser fixture lives in conftest.py.
"""

from __future__ import annotations

import json
import mimetypes
import re
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps/issuer-library"
WEB = APP / "web"
FIXTURE = ROOT / "artifacts/issuer-library/design-fixture"
ORIGIN = "http://127.0.0.1:54321"
EMPTY_STORE: dict[str, Any] = {"runs": {}, "outputs": {}, "inputs": {}, "pins": {}}
EMPTY_WORKSPACE: dict[str, Any] = {"reports": [], "models": [], "visuals": []}
DEFAULT_APP: dict[str, Any] = {
    "workspace": "/research",
    "policy_locked": False,
    "issues": [],
    "problem": "",
}
HELPERS = """
window.__fragment=(html,selector)=>{const t=document.createElement('template');t.innerHTML=html;
  return selector?[...t.content.querySelectorAll(selector)].map(e=>e.textContent):t.content.textContent;};
window.__calls=[];
const __realFetch=window.fetch;
window.fetch=async(url,options)=>{window.__calls.push({url:String(url),options});return __realFetch(url,options);};
"""
NO_TIMERS = "window.setInterval=()=>1;window.clearInterval=()=>{};"
# Intervals are kept, not run: a test fires them with __tick and reads what was started or cleared.
CAPTURED_TIMERS = (
    "window.__timers=new Map();window.__started=[];window.__cleared=[];window.__next=1;"
    "window.setInterval=fn=>{const id=window.__next++;window.__timers.set(id,fn);"
    "window.__started.push(id);return id;};"
    "window.clearInterval=id=>{window.__cleared.push(id);window.__timers.delete(id);};"
    "window.__tick=()=>{for(const fn of [...window.__timers.values()])fn();};"
)
Reply = Callable[[Any], Any]


def pageerrors(page: Any) -> list[str]:
    """Collect page errors and console errors; a test asserts the list stays empty."""
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))

    def console(message: Any) -> None:
        # A synthetic 404 or an aborted request is part of a check, not a script error.
        if message.type == "error" and not message.text.startswith("Failed to load resource"):
            errors.append(message.text)

    page.on("console", console)
    return errors


def content_type(path: Path) -> str:
    guessed = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    if guessed.startswith(("text/", "application/json", "application/javascript")):
        guessed += "; charset=utf-8"
    return guessed


def serve(page: Any, api: dict[str, Reply], roots: tuple[Path, ...] = (WEB, FIXTURE)) -> None:
    """Answer a path from the replies first; any other /api/ path is 404 and every other path
    comes from the first root holding it."""

    def handler(route: Any) -> None:
        path = urlsplit(route.request.url).path
        reply = api.get(path)
        if reply is not None:
            reply(route)
            return
        if path.startswith("/api/"):
            route.fulfill(status=404, body="Not Found")
            return
        if path.startswith("/files/"):
            candidates: tuple[Path, ...] = (ROOT / path.removeprefix("/files/"),)
        else:
            candidates = tuple(root / path.removeprefix("/") for root in roots)
        for file in candidates:
            if file.is_file():
                route.fulfill(body=file.read_bytes(), content_type=content_type(file))
                return
        route.fulfill(status=404, body="Not Found")

    page.route("**/*", handler)


def held(route: Any) -> None:
    """Leave the request unanswered, as a frame or a server that never responds."""


def json_reply(value: Any, status: int = 200) -> Reply:
    return lambda route: route.fulfill(
        status=status, body=json.dumps(value), content_type="application/json; charset=utf-8"
    )


def text_reply(text: str, status: int) -> Reply:
    return lambda route: route.fulfill(
        status=status, body=text, content_type="text/plain; charset=utf-8"
    )


class Screen:
    """One open page of the app, with the small operations the DOM checks need."""

    def __init__(self, page: Any) -> None:
        self.page = page
        self.errors = pageerrors(page)

    def go(self, hash_route: str) -> None:
        self.page.evaluate("hash=>{location.hash=hash;renderRoute();}", hash_route)

    def eval(self, script: str) -> Any:
        return self.page.evaluate(script)

    def text(self, selector: str) -> str:
        value: str = self.page.evaluate(
            "s=>{const e=document.querySelector(s);return e?e.textContent:null;}", selector
        )
        return value

    def texts(self, selector: str) -> list[str]:
        values: list[str] = self.page.evaluate(
            "s=>[...document.querySelectorAll(s)].map(e=>e.textContent)", selector
        )
        return values

    def attrs(self, selector: str, name: str) -> list[str | None]:
        values: list[str | None] = self.page.evaluate(
            "([s,n])=>[...document.querySelectorAll(s)].map(e=>e.getAttribute(n))",
            [selector, name],
        )
        return values

    def attr(self, selector: str, name: str) -> str | None:
        value: str | None = self.page.evaluate(
            "([s,n])=>{const e=document.querySelector(s);return e?e.getAttribute(n):null;}",
            [selector, name],
        )
        return value

    def count(self, selector: str) -> int:
        value: int = self.page.evaluate("s=>document.querySelectorAll(s).length", selector)
        return value

    def exists(self, selector: str) -> bool:
        return self.count(selector) > 0

    def click(self, selector: str) -> None:
        self.page.evaluate("s=>document.querySelector(s).click()", selector)

    def hidden(self, element_id: str) -> bool:
        value: bool = self.page.evaluate("i=>document.getElementById(i).hidden", element_id)
        return value

    def active(self) -> str:
        value: str = self.page.evaluate("document.activeElement?.id||''")
        return value

    def hash(self) -> str:
        value: str = self.page.evaluate("location.hash")
        return value

    def content(self) -> str:
        return self.text("#content")

    def inner_html(self, selector: str) -> str:
        value: str = self.page.evaluate("s=>document.querySelector(s).innerHTML", selector)
        return value

    def set_value(self, selector: str, value: str, event: str = "input") -> None:
        self.page.evaluate(
            "([s,v,e])=>{const el=document.querySelector(s);el.value=v;"
            "el.dispatchEvent(new Event(e,{bubbles:true}));}",
            [selector, value, event],
        )

    def press(self, selector: str, key: str, **extra: bool) -> bool:
        """Dispatch keydown on the selector, or on the active element when it is empty."""
        value: bool = self.page.evaluate(
            "([s,k,x])=>{const t=s?document.querySelector(s):document.activeElement;"
            "const e=new KeyboardEvent('keydown',{key:k,bubbles:true,cancelable:true,...x});"
            "t.dispatchEvent(e);return e.defaultPrevented;}",
            [selector, key, extra],
        )
        return value

    def focus(self, selector: str) -> None:
        self.page.evaluate("s=>document.querySelector(s).focus()", selector)

    def fragment_text(self, html: str) -> str:
        value: str = self.page.evaluate("h=>window.__fragment(h)", html)
        return value

    def calls(self) -> list[dict[str, Any]]:
        values: list[dict[str, Any]] = self.page.evaluate(
            "window.__calls.map(c=>({url:c.url,method:c.options?.method||'GET',"
            "headers:c.options?.headers||{}}))"
        )
        return values

    def close(self) -> None:
        self.page.context.close()


def open_app(  # noqa: PLR0913 - every keyword is optional; only route and store are needed
    browser: Any,
    hash_route: str,
    store: dict[str, Any] = EMPTY_STORE,
    workspace: dict[str, Any] = EMPTY_WORKSPACE,
    app: dict[str, Any] = DEFAULT_APP,
    api: dict[str, Reply] | None = None,
    viewport: tuple[int, int] = (1280, 720),
    timers: str = NO_TIMERS,
    init: str = "",
    device: dict[str, bool] | None = None,
) -> Screen:
    """The app at a route: boot reads the catalogue and store the way the server would send them."""
    context = browser.new_context(
        viewport={"width": viewport[0], "height": viewport[1]}, **(device or {})
    )
    page = context.new_page()
    screen = Screen(page)
    page.add_init_script(HELPERS + timers + init)
    catalogue = {
        "workspace": app["workspace"],
        "policy_locked": app["policy_locked"],
        "issues": app["issues"],
        "real": [],
    }
    full_store = {"handoffs": handoffs_of(store), **store, **workspace, "issues": app["issues"]}
    replies: dict[str, Reply] = {
        "/api/catalogue": json_reply(catalogue),
        "/api/workspace": (
            text_reply(app["problem"], 503) if app["problem"] else json_reply(full_store)
        ),
        "/api/runs/list": json_reply([]),
    }
    replies.update(api or {})
    serve(page, replies)
    # Not the load event: it also waits for every frame, and a check may hold a frame open.
    page.goto(f"{ORIGIN}/index.html#{hash_route}", wait_until="domcontentloaded")
    page.wait_for_function("typeof current!=='undefined'&&current!==null")
    return screen


def handoffs_of(store: dict[str, Any]) -> dict[str, Any]:
    """The sections /api/workspace sends once per digest; hydrate puts them back on each output."""
    handoffs: dict[str, Any] = {}
    for output in store.get("outputs", {}).values():
        if "sections" not in output:
            continue
        if handoffs.setdefault(output["sha256"], output["sections"]) != output["sections"]:
            raise ValueError(f"{output['id']} shares a digest with a handoff of other content")
    return handoffs


def catalogue_reply(store: dict[str, Any], app: dict[str, Any] = DEFAULT_APP) -> Reply:
    """/api/catalogue with one metric-free record per store run, as most runs are served."""
    real = [
        {
            "id": run["folder"],
            "issuer": "none" if run.get("issuerKey") is None else run["issuerKey"],
            "name": run["issuer"],
            "title": run["run"],
            "sector": run["sector"],
            "workflow": "Annual review",
            "date": "2024-12-31",
            "period": run["period"],
            "period_kind": "Annual actual",
            "metrics": {},
            "completion": None,
            "checkpoints": None,
            "ratings": [],
            "gaps": [],
            "summary": "Synthetic record.",
            "artifacts": [],
        }
        for run in store["runs"].values()
    ]
    return json_reply(
        {
            "sources": {},
            "real": real,
            "workspace": app["workspace"],
            "policy_locked": app["policy_locked"],
            "issues": app["issues"],
        }
    )


def design_store() -> tuple[dict[str, Any], dict[str, Any]]:
    """The curated fixture that designs/build.py writes; built strictly so a stale pin fails."""
    subprocess.run([sys.executable, "-B", str(APP / "designs/build.py")], check=True, cwd=ROOT)

    def script_value(name: str) -> Any:
        text = (FIXTURE / name).read_text(encoding="utf-8")
        return json.loads(text[text.index("=") + 1 :].strip().rstrip(";"))

    return script_value("data.js"), script_value("workspace-data.js")


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("**", "").replace("`", "")).strip()


RETAINED = (
    "(sel)=>{const copy=document.querySelector(sel).cloneNode(true);"
    "copy.querySelectorAll('abbr.module-ref').forEach(a=>a.replaceWith(a.title));"
    "return copy.textContent.replace(/\\*\\*|`/g,'').replace(/\\s+/g,' ').trim();}"
)


def retained_text(screen: Screen, selector: str) -> str:
    """A reader page's text with each shown module name turned back into the retained code."""
    text: str = screen.page.evaluate(RETAINED, selector)
    return text


def js(screen: Screen, body: str) -> Any:
    """Run a function body in the page with `d` and `norm` defined, returning what it returns."""
    return screen.eval(
        "()=>{const norm=s=>s.replace(/\\*\\*|`/g,'').replace(/\\s+/g,' ').trim();"
        "const d=document;" + body + "}"
    )


def until(page: Any, expression: str, timeout: float = 5.0) -> None:
    """Poll a condition from Python. wait_for_function builds its check with eval, which a
    retained report's content security policy refuses."""
    deadline = time.monotonic() + timeout
    while not page.evaluate(expression):
        if time.monotonic() > deadline:
            raise AssertionError(f"timed out waiting for {expression}")
        page.wait_for_timeout(20)


def release(opened: list[Screen]) -> None:
    """Fixture teardown: no opened page had errors; all are closed even if one failed."""
    try:
        for screen in opened:
            assert screen.errors == []
    finally:
        for screen in opened:
            screen.close()


class ContextForm:
    def __init__(self, browser: Any) -> None:
        self.page = browser.new_context().new_page()
        self.errors = pageerrors(self.page)
        self.page.add_init_script(
            "window.__messages=[];window.postMessage=v=>{window.__messages.push(v)};"
        )
        serve(self.page, {})
        self.page.goto(f"{ORIGIN}/context-form.html")
        until(self.page, "typeof update==='function'", timeout=10)

    def set(self, element_id: str, value: str) -> None:
        self.page.evaluate(
            "([i,v])=>{const f=document.getElementById(i);f.value=v;"
            "f.dispatchEvent(new Event('input',{bubbles:true}));}",
            [element_id, value],
        )

    def pick(self, element_id: str) -> None:
        self.page.evaluate(
            "i=>{const c=document.getElementById(i);c.checked=true;"
            "c.dispatchEvent(new Event('change',{bubbles:true}));}",
            element_id,
        )

    def declare(self) -> None:
        self.pick("issue_classification-high_yield")
        self.pick("legal_documents-executed")

    def submit(self) -> dict[str, Any]:
        value: dict[str, Any] = self.page.evaluate(
            "()=>{window.dispatchEvent(new MessageEvent('message',"
            "{source:window,data:{type:'cpos:get-context'}}));"
            "return window.__messages.filter(m=>m.type==='cpos:context').at(-1);}"
        )
        return value

    def load(self, folder: Path, text: str) -> None:
        """Choose a saved context file and wait until the form reports it loaded."""
        saved = folder / "context.json"
        saved.write_text(text, encoding="utf-8")
        self.page.set_input_files("#load", saved)
        until(
            self.page,
            "document.getElementById('loadmsg').textContent.startsWith('Loaded')",
            timeout=10,
        )

    def close(self) -> None:
        assert self.errors == []
        self.page.context.close()


def squash(text: str) -> str:
    return " ".join(text.split())


class Library:
    """The Library screen of the real app, driven through the page's own controls."""

    def __init__(self, screen: Screen) -> None:
        self.screen = screen

    def ids(self) -> list[str]:
        selector = "#library-results button[data-library-select]"
        return [i or "" for i in self.screen.attrs(selector, "data-library-select")]

    def set(self, element_id: str, value: str) -> None:
        self.screen.page.evaluate(
            "([id,v])=>{const el=document.getElementById(id);el.value=v;"
            "el.dispatchEvent(new Event(el.tagName==='SELECT'?'change':'input',{bubbles:true}));}",
            [element_id, value],
        )

    def text(self, element_id: str) -> str:
        return squash(self.screen.text(f"#{element_id}"))

    def detail(self) -> str:
        return self.text("run-detail")

    def sort_click(self, name: str) -> None:
        self.screen.click(f'[data-library-sort="{name}"]')

    def aria_sort(self, name: str) -> str | None:
        return self.screen.attr(f'th:has([data-library-sort="{name}"])', "aria-sort")

    def select(self, run_id: str) -> None:
        self.screen.click(f'[data-library-select="{run_id}"]')

    def focused(self, name: str) -> tuple[str | None, str | None]:
        value: list[str | None] = self.screen.eval(
            f"(()=>{{const a=document.activeElement;"
            f"return [a.dataset.{name},a.getAttribute('aria-pressed')];}})()"
        )
        return value[0], value[1]


LibraryOpener = Callable[..., Library]
