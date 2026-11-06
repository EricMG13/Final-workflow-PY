"""Copy approved report assets and the reviewed legacy adapter; no analysis."""

import json
import shutil
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parents[1]
SHARED = ROOT / "src/deploy_vii/assets"
WEB = APP / "web"
for name in [
    "RedHatDisplay-SemiBold.woff2",
    "RedHatDisplay-Bold.woff2",
    "RedHatText-Regular.woff2",
    "RedHatText-Medium.woff2",
    "RedHatText-SemiBold.woff2",
    "RedHatMono-Medium.woff2",
    "RedHatMono-SemiBold.woff2",
    "OFL.txt",
]:
    (WEB / "fonts").mkdir(exist_ok=True)
    shutil.copyfile(SHARED / "fonts" / name, WEB / "fonts" / name)
(WEB / "brand").mkdir(exist_ok=True)
shutil.copyfile(SHARED / "brand/symbol.svg", WEB / "brand/symbol.svg")
catalogue = json.loads((ROOT / "examples/issuer-library/catalog.json").read_text(encoding="utf-8"))
catalogue["illustrative"] = []
(WEB / "legacy-catalog.json").write_text(json.dumps(catalogue, indent=2) + "\n", encoding="utf-8")
# Keep the existing form and its rules; add a narrow parent-message bridge.
import base64
import re

# The supplied symbol is the app's only branding. Inline it so the same asset
# works in opaque, offline report frames without relaxing their image policy.
symbol = base64.b64encode((WEB / "brand/symbol.svg").read_bytes()).decode()
(WEB / "brand.css").write_text(
    ".brand-mark { border:0; background:center / 24px 24px no-repeat "
    f'url("data:image/svg+xml;base64,{symbol}"); }}\n',
    encoding="utf-8",
)
form = (ROOT / "docs/templates/context-form.html").read_text(encoding="utf-8")
# Only the embedded form hides numbering; the standalone template keeps it.
for number, label in [(4, "Deal terms"), (5, "Quotes"), (7, "Valuation")]:
    form = form.replace(f"section {number}", f"“{label}”")


def font_url(match):
    file = SHARED / "fonts" / match[1]
    return "data:font/woff2;base64," + base64.b64encode(file.read_bytes()).decode()


form = re.sub(r"\.\./\.\./src/deploy_vii/assets/fonts/([^\x27]+)", font_url, form)
form = form.replace("font-src 'self'", "font-src data:")
form = form.replace(
    "</head>",
    "<style>" + (WEB / "context-embed.css").read_text(encoding="utf-8") + "</style></head>",
)
bridge = "<script>" + (WEB / "context-embed.js").read_text(encoding="utf-8") + "</script>"
(WEB / "context-form.html").write_text(
    form.replace("</body>", bridge + "</body>"), encoding="utf-8"
)
