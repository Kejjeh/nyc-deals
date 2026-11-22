"""Recheck: fetch a Deal's Proof page and compare it with the confirmed version.

The fingerprint of an HTML page is a hash of its visible text with scripts,
styles and whitespace removed, so a rotating token or a restyle does not count
as a change. Any other content (a PDF menu) is hashed byte for byte.

Results:
- unchanged:   same fingerprint as the owner confirmed; moves Checked On.
- changed:     different fingerprint; goes on the Recheck List.
- no baseline: the owner has not confirmed a version yet (`recheck.py --accept`).
- gone:        404 or 410; goes on the Recheck List.
- unreachable: timeout, 429 or 5xx. Never treated as gone and never cached as
               final; the next run simply tries again.
"""
from __future__ import annotations

import hashlib
import http.client
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from html.parser import HTMLParser

USER_AGENT = "nyc-deals-recheck/1.0 (+https://github.com/Kejjeh/nyc-deals)"
TIMEOUT_S = 20


@dataclass(frozen=True)
class Fetched:
    status: int | None
    body: bytes
    content_type: str
    error: str | None


@dataclass(frozen=True)
class Check:
    url: str
    status: str
    fingerprint: str | None
    checked_on: str
    http: int | None = None
    error: str | None = None
    # The last Recheck that found the page unchanged, carried forward from the
    # previous checks.json so an unreachable or changed week does not undo it.
    last_unchanged_on: str | None = None
    last_unchanged_fingerprint: str | None = None

    def to_json(self) -> dict:
        return asdict(self)


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "template"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "template") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def visible_text(html: str) -> str:
    p = _Text()
    p.feed(html)
    return re.sub(r"\s+", " ", " ".join(p.parts)).strip()


def fingerprint(body: bytes, content_type: str) -> str:
    if "html" in (content_type or "").lower():
        body = visible_text(body.decode("utf-8", errors="replace")).encode("utf-8")
    return hashlib.sha256(body).hexdigest()[:16]


def classify(proof_hash: str | None, fetched: Fetched) -> Check:
    """The status part of a Check (url and date are filled in by the caller)."""
    def check(status, fp=None):
        return Check(url="", status=status, fingerprint=fp, checked_on="", http=fetched.status, error=fetched.error)
    if fetched.error or fetched.status is None or fetched.status == 429 or fetched.status >= 500:
        return check("unreachable")
    if fetched.status in (404, 410):
        return check("gone")
    if fetched.status >= 400:
        return check("unreachable")
    fp = fingerprint(fetched.body, fetched.content_type)
    if proof_hash is None:
        return check("no baseline", fp)
    return check("unchanged" if fp == proof_hash else "changed", fp)


def fetch(url: str) -> Fetched:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/pdf,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as res:
            return Fetched(res.status, res.read(), res.headers.get("Content-Type", ""), None)
    except urllib.error.HTTPError as e:
        return Fetched(e.code, b"", e.headers.get("Content-Type", "") if e.headers else "", None)
    except (urllib.error.URLError, http.client.HTTPException, TimeoutError, OSError, ValueError) as e:
        return Fetched(None, b"", "", str(getattr(e, "reason", e)))
