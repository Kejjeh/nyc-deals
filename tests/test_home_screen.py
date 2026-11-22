"""The site installs as a home-screen app: manifest, icons and the page tags that point at them."""
import json
import re
import struct
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"
PAGE = (DOCS / "index.html").read_text(encoding="utf-8")


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"{path.name} is not a PNG"
    return struct.unpack(">II", data[16:24])


def _manifest() -> dict:
    return json.loads((DOCS / "app.webmanifest").read_text(encoding="utf-8"))


def test_manifest_opens_the_site_full_screen_from_its_own_folder():
    m = _manifest()
    assert m["name"] == "NYC Deals"
    assert m["display"] == "standalone"
    # Relative, so it works under kejjeh.github.io/nyc-deals/ and on a local server.
    assert m["start_url"] == "./" and m["scope"] == "./"


def test_every_manifest_icon_exists_at_its_stated_size():
    icons = _manifest()["icons"]
    assert {i["purpose"] for i in icons} == {"any", "maskable"}
    for icon in icons:
        w, h = (int(n) for n in icon["sizes"].split("x"))
        assert _png_size(DOCS / icon["src"]) == (w, h), icon["src"]


def test_page_links_the_manifest_and_the_ios_icon():
    assert '<link rel="manifest" href="app.webmanifest">' in PAGE
    href = re.search(r'<link rel="apple-touch-icon" href="([^"]+)">', PAGE).group(1)
    assert _png_size(DOCS / href) == (180, 180)


def test_content_security_policy_lets_the_manifest_load():
    # default-src 'none' would otherwise block the manifest fetch.
    csp = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', PAGE).group(1)
    assert "manifest-src 'self'" in csp
