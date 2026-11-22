"""The build: Set Menus + Rechecks + Rankings -> the site's Deals, with everything left out counted."""
import json
from datetime import date
from pathlib import Path

from deals.model import SetMenu
from deals.recheck import Check
from deals.restaurant_week import set_menus_from_season
from deals.site import build_site, recheck_list_markdown

TODAY = date(2026, 11, 22)
# Lombardi's-ish coordinates in Nolita, Manhattan (a point inside an NTA).
LAT, LNG = 40.7216, -73.9956


def m(id, **kw):
    base = dict(id=id, restaurant=id.title(), address="", meal="lunch", days=("mon",), price=30, courses=3,
                proof_url=f"https://{id}.example/menu", seen_on="2026-11-01", checked_on="2026-11-20",
                proof_hash="h", lat=LAT, lng=LNG)
    base.update(kw)
    return SetMenu(**base)


def test_only_fresh_deals_are_published_and_the_rest_is_counted():
    menus = [
        m("cheap", price=24),                                   # $8/course
        m("fresh-by-recheck", price=36, checked_on="2026-09-01"),  # owner date stale, Recheck moved it
        m("stale", checked_on="2026-10-01"),
        m("pricey", price=60),
        m("brunchy", meal="brunch"),
        m("changed", price=33),
    ]
    checks = {
        "fresh-by-recheck": Check("u", "unchanged", "h", "2026-11-18"),
        "changed": Check("u", "changed", "other", "2026-11-18"),
    }
    data, report = build_site(menus, checks, {}, TODAY)
    assert [d["id"] for d in data["deals"]] == ["cheap", "changed", "fresh-by-recheck"]  # by price per course
    assert data["deals"][2]["checked_on"] == "2026-11-18"
    assert report["not Deals"] == {"over the $45 lunch cap ($60)": 1, "no Deal Cap for brunch yet (owner decision)": 1}
    assert report["stale"] == [("stale", "2026-10-01", "research")]
    assert report["recheck"] == [("changed", "changed")]
    assert data["deals"][0]["borough"] == "Manhattan" and data["deals"][0]["neighborhood"]


def test_a_deal_with_no_coordinates_is_published_and_listed():
    data, report = build_site([m("nowhere", lat=None, lng=None)], {}, {}, TODAY)
    assert data["deals"][0]["borough"] is None
    assert report["no neighborhood"] == ["nowhere"]


def test_restaurant_week_deals_sort_after_known_per_course_prices():
    season = json.loads((Path(__file__).parent / "fixtures" / "srw26_sample.json").read_text(encoding="utf-8"))
    rw, _ = set_menus_from_season(season, date(2026, 8, 1))
    data, report = build_site(rw + [m("cheap", price=24, checked_on="2026-07-31")], {}, {}, date(2026, 8, 1))
    assert data["deals"][0]["id"] == "cheap"
    assert all(d["source"] == "restaurant_week" for d in data["deals"][1:])
    prices = [d["deal_price"] for d in data["deals"][1:]]
    assert prices == sorted(prices)
    assert report["not Deals"]["no Deal Cap for brunch yet (owner decision)"] >= 1


def test_the_recheck_list_names_every_item():
    _, report = build_site([m("stale", checked_on="2026-10-01"), m("changed")],
                           {"changed": Check("u", "changed", "x", "2026-11-18")}, {}, TODAY)
    md = recheck_list_markdown(report, TODAY)
    assert "- `changed`: changed" in md and "- `stale`: last checked 2026-10-01" in md


def test_stale_restaurant_week_deals_are_not_sent_to_accept():
    season = json.loads((Path(__file__).parent / "fixtures" / "srw26_sample.json").read_text(encoding="utf-8"))
    rw, _ = set_menus_from_season(season, date(2026, 8, 1))
    _, report = build_site(rw[:1], {}, {}, date(2026, 11, 2))  # months after the summer snapshot
    md = recheck_list_markdown(report, TODAY)
    assert report["stale"] and report["stale"][0][2] == "restaurant_week"
    assert "Nothing to accept" in md and "--accept" not in md
