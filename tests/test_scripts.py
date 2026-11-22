"""The recheck and lookup scripts, with the network replaced."""
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from deals.model import load_set_menus  # noqa: E402
from deals.recheck import Fetched  # noqa: E402
from scripts.lookup_places import decide, needs_lookup, similarity  # noqa: E402
from scripts.recheck import accept, run_rechecks  # noqa: E402

PAGE = b"<html><body><h1>Lunch</h1><p>Three courses $39</p></body></html>"


def _file(tmp_path, **extra):
    row = {"id": "a-lunch", "restaurant": "A", "address": "1 St", "meal": "lunch", "days": ["mon"], "price": 39,
           "courses": 3, "proof_url": "https://a.example/m", "seen_on": "2026-11-01", "checked_on": "2026-11-01"}
    row.update(extra)
    p = tmp_path / "set_menus.json"
    p.write_text(json.dumps({"_doc": "x", "set_menus": [row]}), encoding="utf-8")
    return p


def test_accept_stores_the_page_as_proof_and_then_a_recheck_finds_it_unchanged(tmp_path):
    p = _file(tmp_path)
    fetch = lambda url: Fetched(200, PAGE, "text/html", None)
    accept(p, ["a-lunch"], fetch, date(2026, 11, 20))
    menus = load_set_menus(p)
    assert menus[0].checked_on == "2026-11-20" and menus[0].proof_hash
    checks = run_rechecks(menus, fetch, date(2026, 11, 22))
    assert (checks["a-lunch"].status, checks["a-lunch"].checked_on) == ("unchanged", "2026-11-22")
    assert json.loads(p.read_text(encoding="utf-8"))["_doc"] == "x"  # the rest of the file is kept


def test_an_unreachable_page_cannot_be_accepted(tmp_path):
    p = _file(tmp_path)
    import pytest
    with pytest.raises(SystemExit, match="unreachable"):
        accept(p, ["a-lunch"], lambda url: Fetched(None, b"", "", "timed out"), date(2026, 11, 20))
    assert load_set_menus(p)[0].proof_hash is None


def test_lookup_trusts_close_names_only():
    assert similarity("Joe's Pizza", "Joe's Pizza Broadway") > 0.6
    good = decide("Café Altro Paradiso", {"id": "P1", "displayName": {"text": "Cafe Altro Paradiso"},
                                          "location": {"latitude": 40.7, "longitude": -74.0}})
    assert good["place_id"] == "P1" and good["place_match"].startswith("trusted")
    bad = decide("Lilia", {"id": "P2", "displayName": {"text": "Lilia's Nail Salon & Spa"}, "location": {}})
    assert "place_id" not in bad and bad["place_match"].startswith("untrusted")
    assert decide("Lilia", None)["place_match"].startswith("no Google result")


def test_the_dry_run_lists_each_restaurant_once_and_skips_ones_already_tried(tmp_path):
    p = tmp_path / "set_menus.json"
    rows = [
        {"id": "a-lunch", "restaurant": "A", "address": "1 St", "meal": "lunch", "days": ["mon"], "price": 30,
         "courses": 2, "proof_url": "https://a.example/m", "seen_on": "2026-11-01", "checked_on": "2026-11-01"},
        {"id": "a-dinner", "restaurant": "A", "address": "1 St", "meal": "dinner", "days": ["mon"], "price": 60,
         "courses": 3, "proof_url": "https://a.example/m", "seen_on": "2026-11-01", "checked_on": "2026-11-01"},
        {"id": "b-lunch", "restaurant": "B", "address": "2 St", "meal": "lunch", "days": ["mon"], "price": 30,
         "courses": 2, "proof_url": "https://b.example/m", "seen_on": "2026-11-01", "checked_on": "2026-11-01",
         "place_match": "untrusted: Google says 'Bee' (0.5, 2026-11-01)"},
    ]
    p.write_text(json.dumps({"set_menus": rows}), encoding="utf-8")
    assert [m.restaurant for m in needs_lookup(load_set_menus(p))] == ["A"]


def test_an_unreachable_week_does_not_take_back_checked_on(tmp_path):
    from deals.freshness import effective_checked_on
    p = _file(tmp_path)
    ok = lambda url: Fetched(200, PAGE, "text/html", None)
    accept(p, ["a-lunch"], ok, date(2026, 11, 1))
    menus = load_set_menus(p)
    week1 = run_rechecks(menus, ok, date(2026, 11, 8))
    week2 = run_rechecks(menus, lambda url: Fetched(503, b"", "", None), date(2026, 11, 15), week1)
    week3 = run_rechecks(menus, lambda url: Fetched(200, b"<p>new menu</p>", "text/html", None), date(2026, 11, 22), week2)
    m = menus[0]
    assert week2["a-lunch"].status == "unreachable" and week3["a-lunch"].status == "changed"
    assert effective_checked_on(m.checked_on, m.proof_hash, week2["a-lunch"]) == "2026-11-08"
    assert effective_checked_on(m.checked_on, m.proof_hash, week3["a-lunch"]) == "2026-11-08"


def test_a_fetch_that_raises_is_unreachable_and_the_rest_still_run(tmp_path):
    p = tmp_path / "set_menus.json"
    row = lambda i: {"id": i, "restaurant": i, "address": "1 St", "meal": "lunch", "days": ["mon"], "price": 30,
                     "courses": 2, "proof_url": f"https://{i}.example/m", "seen_on": "2026-11-01", "checked_on": "2026-11-01"}
    p.write_text(json.dumps({"set_menus": [row("a"), row("b")]}), encoding="utf-8")

    def fetch(url):
        if url.startswith("https://a."):
            raise RuntimeError("socket blew up")
        return Fetched(200, PAGE, "text/html", None)
    checks = run_rechecks(load_set_menus(p), fetch, date(2026, 11, 22))
    assert checks["a"].status == "unreachable" and "socket blew up" in checks["a"].error
    assert checks["b"].status == "no baseline"
