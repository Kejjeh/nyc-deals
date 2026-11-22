"""Seam 4: nyc-restaurants' Restaurant Week export -> Set Menus.

The fixture holds 8 records copied verbatim from nyc-restaurants'
docs/data/seasons/srw26.json (2026-11-22), chosen for their variety.
"""
import json
from datetime import date
from pathlib import Path

import pytest

from deals.model import deal_verdict
from deals.restaurant_week import set_menus_from_season

SEASON = json.loads((Path(__file__).parent / "fixtures" / "srw26_sample.json").read_text(encoding="utf-8"))
IN_SEASON = date(2026, 8, 1)
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri")


@pytest.fixture(scope="module")
def menus():
    got, skipped = set_menus_from_season(SEASON, IN_SEASON)
    return {m.id: m for m in got}, skipped


def test_one_set_menu_per_meal_and_price(menus):
    by_id, _ = menus
    feast = {i: (m.meal, m.price, m.days) for i, m in by_id.items() if i.startswith("rw-100-feast-")}
    assert feast == {
        "rw-100-feast-lunch-30": ("lunch", 30, WEEKDAYS),
        "rw-100-feast-dinner-45": ("dinner", 45, WEEKDAYS + ("sun",)),  # weekday + Sunday dinner merged
        "rw-100-feast-brunch-30": ("brunch", 30, ("sun",)),             # "$30 Sunday Lunch/Brunch Price"
    }


def test_sunday_menus_are_dropped_when_the_restaurant_skips_sundays(menus):
    by_id, skipped = menus
    assert by_id["rw-ai-fiori-dinner-60"].days == WEEKDAYS  # sunday: false in the export
    assert skipped["Sunday price listed but not open for Restaurant Week on Sundays"] == 1


def test_the_free_text_days_note_is_kept_not_parsed(menus):
    by_id, _ = menus
    assert by_id["rw-ai-fiori-dinner-60"].notes == "Days per nyc-restaurants: Mon-Fri"


def test_fields_come_across(menus):
    by_id, _ = menus
    m = by_id["rw-100-feast-lunch-30"]
    assert (m.restaurant, m.place_id, m.source, m.courses, m.courses_basis) == (
        "100 Feast", "ChIJf83T8ghbwokRZ8mODC62yPI", "restaurant_week", None, "restaurant_week_program")
    assert m.proof_url == "https://nyc-tourism-public.s3.amazonaws.com/srw26/menus/51359-100Feast-menu.pdf"
    assert m.checked_on == "2026-08-10"  # the season snapshot
    assert (round(m.lat, 4), round(m.lng, 4)) == (40.7139, -73.9933)


def test_a_restaurant_with_no_place_id_still_comes_across(menus):
    by_id, _ = menus
    assert by_id["rw-five-napkin-burger-hells-kitchen-lunch-30"].place_id is None


def test_only_verified_savings_are_shown_and_only_on_the_matching_price(menus):
    by_id, _ = menus
    assert by_id["rw-53-lunch-45"].saving_usd == 33          # gap_basis "verified", rw_price 45
    assert by_id["rw-100-feast-lunch-30"].saving_usd is None  # gap_basis "estimate"


def test_restaurant_week_menus_pass_the_same_cap(menus):
    by_id, _ = menus
    assert deal_verdict(by_id["rw-aqua-boil-lunch-60"]) == (False, "over the $45 lunch cap ($60)")
    assert deal_verdict(by_id["rw-8282-dinner-60"]) == (True, "Deal")


def test_a_restaurant_that_left_early_is_dropped_after_its_end_date():
    got, skipped = set_menus_from_season(SEASON, date(2026, 8, 20))  # 1803 NYC ended 08-16
    assert not any(m.id.startswith("rw-1803-nyc-") for m in got)
    assert any(m.id.startswith("rw-100-feast-") for m in got)
    assert skipped["ended before today"] > 0


def test_out_of_season_nothing_comes_across():
    got, skipped = set_menus_from_season(SEASON, date(2026, 11, 22))
    assert got == []
    assert skipped == {"season over (ended 2026-09-06)": 8}


def test_an_unknown_price_label_is_refused_by_name():
    season = json.loads(json.dumps(SEASON))
    season["restaurants"][0]["meal_types_raw"] = ["$30 Happy Hour Price"]
    with pytest.raises(ValueError, match="'\\$30 Happy Hour Price'"):
        set_menus_from_season(season, IN_SEASON)
