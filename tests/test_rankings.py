"""Seam 5: Rankings from the owner's other sites, joined to Deals by Google place_id.

Fixtures are rows copied verbatim from Omakase, NYC Eats and nyc-restaurants (2026-11-22).
"""
import json
from pathlib import Path

from deals.model import SetMenu
from deals.rankings import attach, merge, nyc_eats_badges, nyc_restaurants_badges, omakase_badges

F = Path(__file__).parent / "fixtures"
load = lambda name: json.loads((F / name).read_text(encoding="utf-8"))


def test_omakase_ranks_by_composite_and_skips_untrusted_google_matches():
    rows, cache = load("omakase_data_sample.json"), load("omakase_ratings_cache_sample.json")
    badges, report = omakase_badges(rows, cache, "omakase")
    # Composite 4.102 (Hatsuhana) > 3.723 (Inase) > 3.47 (Akimori); Inase's Google match is untrusted.
    assert sorted(b["label"] for b in badges.values()) == ["Omakase list #1 of 3", "Omakase list #3 of 3"]
    assert report == {"badges": 2, "untrusted Google match": 1}
    assert badges[cache["Hatsuhana"]["place_id"]]["site"] == "Omakase"


def test_nyc_eats_ids_are_place_ids():
    badges, report = nyc_eats_badges(load("nyc_eats_sample.json")["restaurants"])
    assert badges["ChIJGfdZtJdbwokREUPcjASYSr4"]["label"] == "NYC Eats score 4.89"
    assert report == {"badges": 2}


def test_nyc_restaurants_shows_the_top_honor_and_skips_venues_without_one():
    venues = load("nyc_restaurants_venues_sample.json")
    labels = {"100-feast": None, "1803-nyc": "Michelin Bib Gourmand"}
    badges, report = nyc_restaurants_badges(venues, labels)
    assert badges == {"ChIJ0yKXaB9awokR6WFqdEE9aBY": {
        "site": "NYC award roster", "label": "Michelin Bib Gourmand",
        "url": "https://kejjeh.github.io/nyc-restaurants/"}}
    assert report == {"badges": 1, "no award": 1, "no place_id": 1}


def test_a_place_id_two_venues_share_is_left_out_and_reported():
    venues = [{"venue_slug": "a", "place_id": "P1", "status": "open"},
              {"venue_slug": "b", "place_id": "P1", "status": "open"}]
    badges, report = nyc_restaurants_badges(venues, {"a": "Michelin star", "b": "James Beard"})
    assert badges == {}
    assert report == {"shared place_id (left out)": 2}


def test_closed_venues_get_no_badge():
    badges, report = nyc_restaurants_badges([{"venue_slug": "a", "place_id": "P1", "status": "closed"}], {"a": "Michelin star"})
    assert badges == {} and report == {"closed": 1}


def menu(id, place_id):
    return SetMenu(id=id, restaurant=id, address="", meal="lunch", days=("mon",), price=30, courses=2,
                   proof_url="https://a.example/m", seen_on="2026-11-20", checked_on="2026-11-20", place_id=place_id)


def test_deals_get_every_badge_for_their_place_id_and_misses_are_listed():
    index = merge({"P1": {"site": "Omakase", "label": "#1"}}, {"P1": {"site": "NYC Eats", "label": "4.9"}})
    ranked, report = attach([menu("a", "P1"), menu("b", "P2"), menu("c", None)], index)
    assert [b["site"] for b in ranked["a"]] == ["Omakase", "NYC Eats"]
    assert ranked["b"] == [] and ranked["c"] == []
    assert report == {"no place_id": ["c"], "no Ranking for its place_id": ["b"]}
