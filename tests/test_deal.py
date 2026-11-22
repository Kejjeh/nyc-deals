"""Seam 1: a Set Menu -> Deal or not, with the reason."""
import pytest

from deals.model import SetMenu, deal_verdict, load_set_menus, validate


def menu(**kw):
    base = dict(id="x-lunch", restaurant="X", address="1 Main St, New York, NY", meal="lunch",
                days=("mon", "tue", "wed", "thu", "fri"), price=39, required_supplements=0, courses=3,
                proof_url="https://example.com/menu", seen_on="2026-11-20", checked_on="2026-11-20")
    base.update(kw)
    return SetMenu(**base)


def test_a_lunch_at_the_cap_is_a_deal():
    assert deal_verdict(menu(price=45)) == (True, "Deal")


def test_a_lunch_a_dollar_over_the_cap_is_not():
    assert deal_verdict(menu(price=46)) == (False, "over the $45 lunch cap ($46)")


def test_dinner_has_its_own_cap():
    assert deal_verdict(menu(meal="dinner", price=75)) == (True, "Deal")
    assert deal_verdict(menu(meal="dinner", price=76))[0] is False


def test_a_required_supplement_counts_towards_the_cap():
    # "$39, plus $10 for the steak course" when steak is the only main: $49
    m = menu(price=39, required_supplements=10)
    assert m.deal_price == 49
    assert deal_verdict(m) == (False, "over the $45 lunch cap ($49)")


def test_one_course_is_not_a_set_menu():
    assert deal_verdict(menu(courses=1)) == (False, "not a Set Menu: 1 course")


def test_brunch_has_no_cap_until_the_owner_sets_one():
    assert deal_verdict(menu(meal="brunch", price=20)) == (False, "no Deal Cap for brunch yet (owner decision)")


def test_unknown_course_count_is_only_accepted_on_the_program_rule():
    assert deal_verdict(menu(courses=None, courses_basis="restaurant_week_program", source="restaurant_week"))[0] is True
    # a research row cannot claim the program rule
    assert deal_verdict(menu(courses=None, courses_basis="restaurant_week_program")) == (False, "course count unknown")
    assert deal_verdict(menu(courses=None)) == (False, "course count unknown")


def test_price_per_course():
    assert menu(price=39, required_supplements=6, courses=3).price_per_course == 15
    assert menu(courses=None, courses_basis="restaurant_week_program").price_per_course is None


@pytest.mark.parametrize("field,value,message", [
    ("meal", "supper", "meal 'supper'"),
    ("days", ("mon", "funday"), "day 'funday'"),
    ("days", (), "no days"),
    ("price", 0, "price"),
    ("price", float("nan"), "price"),
    ("price", float("inf"), "price"),
    ("price", True, "price"),
    ("required_supplements", float("nan"), "required_supplements"),
    ("proof_url", "https://www.eater.com:443/maps/best-prix-fixe", "Discovery Source"),
    ("proof_url", "https://www.eater.com./maps/best-prix-fixe", "Discovery Source"),
    ("proof_url", "https://WWW.Yelp.com/biz/x", "Discovery Source"),
    ("proof_url", "http://example.com/menu", "https"),
    ("proof_url", "https://www.eater.com/maps/best-prix-fixe", "Discovery Source"),
    ("checked_on", "Nov 20", "checked_on"),
])
def test_a_bad_record_is_refused_by_name(field, value, message):
    with pytest.raises(ValueError, match=message):
        validate(menu(**{field: value}))


def test_set_menus_file_refuses_duplicate_ids(tmp_path):
    p = tmp_path / "set_menus.json"
    row = ('{"id": "a", "restaurant": "A", "address": "1 St", "meal": "lunch", "days": ["mon"], "price": 30,'
           ' "required_supplements": 0, "courses": 2, "proof_url": "https://a.example/m",'
           ' "seen_on": "2026-11-20", "checked_on": "2026-11-20"}')
    p.write_text('{"set_menus": [' + row + "," + row + "]}", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate id 'a'"):
        load_set_menus(p)


def test_an_unknown_field_is_refused(tmp_path):
    p = tmp_path / "set_menus.json"
    p.write_text('{"set_menus": [{"id": "a", "restaurant": "A", "address": "1 St", "meal": "lunch", "days": ["mon"],'
                 ' "price": 30, "courses": 2, "proof_url": "https://a.example/m", "seen_on": "2026-11-20",'
                 ' "checked_on": "2026-11-20", "pirce": 25}]}', encoding="utf-8")
    with pytest.raises(ValueError, match="unknown field 'pirce'"):
        load_set_menus(p)


def test_a_research_row_cannot_set_the_program_course_rule(tmp_path):
    p = tmp_path / "set_menus.json"
    p.write_text('{"set_menus": [{"id": "a", "restaurant": "A", "address": "1 St", "meal": "lunch", "days": ["mon"],'
                 ' "price": 30, "courses": null, "courses_basis": "restaurant_week_program",'
                 ' "proof_url": "https://a.example/m", "seen_on": "2026-11-20", "checked_on": "2026-11-20"}]}',
                 encoding="utf-8")
    with pytest.raises(ValueError, match="unknown field 'courses_basis'"):
        load_set_menus(p)
