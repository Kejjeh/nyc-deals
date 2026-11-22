"""Restaurant Week Deals, read from nyc-restaurants' own season export.

nyc-restaurants scrapes NYC Tourism's listing under that site's terms; this
repo reads the result instead of scraping it again (ADR 0001).

Per record, prices come from `meal_types_raw` ("$30 Lunch Price", "$45 Sunday
Dinner Price", ...). Weekday prices run Monday to Friday and Sunday prices run
on Sunday, under the program's rules. Sunday prices are dropped when the record
says the restaurant is not open for the program on Sundays. The free-text `days`
field is kept as a note, not parsed. Course counts are not in the export;
Restaurant Week menus are multi-course by the program's rules
(`courses_basis = "restaurant_week_program"`).
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import date

from deals.model import PROGRAM_COURSES, SetMenu, validate

_LABEL = re.compile(r"^\$(\d+(?:\.\d+)?) (Sunday )?(Lunch/Brunch|Lunch|Dinner) Price$")
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri")
SKIPPED_SUNDAY = "Sunday price listed but not open for Restaurant Week on Sundays"


def _prices(record: dict) -> list[tuple[str, float, str]]:
    """(meal, price, day group) per price label; refuses a label it does not know."""
    out = []
    for label in record.get("meal_types_raw") or []:
        m = _LABEL.match(label)
        if not m:
            raise ValueError(f"{record['slug']}: unknown Restaurant Week price label {label!r}")
        price, sunday, meal = float(m.group(1)), bool(m.group(2)), m.group(3)
        if sunday:
            out.append(("brunch" if meal == "Lunch/Brunch" else meal.lower(), price, "sun"))
        else:
            out.append(("lunch" if meal == "Lunch" else "dinner" if meal == "Dinner" else "brunch", price, "weekday"))
    return out


def set_menus_from_season(season: dict, today: date) -> tuple[list[SetMenu], Counter]:
    skipped: Counter = Counter()
    records = season["restaurants"]
    start, end = date.fromisoformat(season["season_start"]), date.fromisoformat(season["program_end"])
    if today > end:
        skipped[f"season over (ended {end})"] = len(records)
        return [], skipped
    if today < start:
        skipped[f"season not started (starts {start})"] = len(records)
        return [], skipped
    snapshot = season["snapshot_date"]
    menus: list[SetMenu] = []
    for r in records:
        if r.get("end_date") and date.fromisoformat(r["end_date"]) < today:
            skipped["ended before today"] += 1
            continue
        groups: dict[tuple[str, float], list[str]] = {}
        for meal, price, group in _prices(r):
            if group == "sun" and not r.get("sunday"):
                skipped[SKIPPED_SUNDAY] += 1
                continue
            days = groups.setdefault((meal, price), [])
            days.extend(d for d in (("sun",) if group == "sun" else WEEKDAYS) if d not in days)
        links = r.get("links") or {}
        proof = links.get("menu") if str(links.get("menu", "")).startswith("https://") else links.get("listing")
        google = r.get("google") or {}
        for (meal, price), days in groups.items():
            ordered = tuple(d for d in WEEKDAYS + ("sun",) if d in days)
            saving = (r.get("gap_usd") if r.get("gap_basis") == "verified" and r.get("rw_price") == price else None)
            menus.append(validate(SetMenu(
                id=f"rw-{r['slug']}-{meal}-{price:g}",
                restaurant=r["name"], address=r.get("address") or "", meal=meal, days=ordered, price=price,
                courses=None, courses_basis=PROGRAM_COURSES, proof_url=proof, seen_on=snapshot, checked_on=snapshot,
                place_id=google.get("place_id"), lat=r.get("lat"), lng=r.get("lng"),
                notes=f"Days per nyc-restaurants: {r['days']}" if r.get("days") else "",
                source="restaurant_week", saving_usd=saving,
            )))
    return menus, skipped
