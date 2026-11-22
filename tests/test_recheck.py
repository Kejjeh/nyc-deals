"""Seam 3: the old page vs the new page -> unchanged, changed, gone or unreachable."""
from deals.recheck import Fetched, classify, fingerprint

HTML = b"""<html><head><title>Menu</title><style>.x{color:red}</style>
<script>var csrf = "a81f";</script></head>
<body><h1>Lunch Prix Fixe</h1>  <p>Three courses   $39</p></body></html>"""


def test_whitespace_scripts_and_styles_do_not_change_the_fingerprint():
    other = HTML.replace(b"a81f", b"77c0").replace(b"  <p>", b"\n\n<p>").replace(b"red", b"blue")
    assert fingerprint(HTML, "text/html") == fingerprint(other, "text/html")


def test_a_new_price_changes_it():
    assert fingerprint(HTML, "text/html") != fingerprint(HTML.replace(b"$39", b"$42"), "text/html")


def test_a_pdf_is_compared_byte_for_byte():
    assert fingerprint(b"%PDF-1.7 a", "application/pdf") != fingerprint(b"%PDF-1.7 b", "application/pdf")


def ok(body=HTML, ctype="text/html; charset=utf-8"):
    return Fetched(status=200, body=body, content_type=ctype, error=None)


def test_same_page_is_unchanged():
    baseline = fingerprint(HTML, "text/html")
    assert classify(baseline, ok()).status == "unchanged"


def test_edited_page_is_changed():
    baseline = fingerprint(HTML, "text/html")
    assert classify(baseline, ok(HTML.replace(b"$39", b"$45"))).status == "changed"


def test_no_baseline_yet():
    assert classify(None, ok()).status == "no baseline"


def test_404_and_410_mean_gone():
    for code in (404, 410):
        assert classify("abc", Fetched(status=code, body=b"", content_type="text/html", error=None)).status == "gone"


def test_timeouts_429_and_5xx_are_unreachable_never_gone():
    for f in (Fetched(None, b"", "", "timed out"), Fetched(429, b"", "", None), Fetched(503, b"", "", None)):
        result = classify("abc", f)
        assert result.status == "unreachable"
        assert result.fingerprint is None


def test_a_dropped_connection_is_unreachable_not_a_crash(monkeypatch):
    import http.client
    import urllib.request
    from deals import recheck

    def boom(*a, **k):
        raise http.client.IncompleteRead(b"partial")
    monkeypatch.setattr(urllib.request, "urlopen", boom)
    got = recheck.fetch("https://a.example/m")
    assert got.status is None and got.error
    assert recheck.classify("h", got).status == "unreachable"
