"""Set Menus and the Deal test (GLOSSARY.md).

A Set Menu is a fixed price for a fixed set of 2 or more courses. It is a Deal
when its Deal Price (base price plus any supplement you cannot avoid) is at or
below the Deal Cap for its meal. The caps are owner decisions (2026-11-22);
brunch has none yet, so a brunch menu is never a Deal until the owner sets one.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field, fields
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

DEAL_CAPS = {"lunch": 45, "dinner": 75}  # dollars, before tax and tip. Owner decision 2026-11-22.
MEALS = ("lunch", "dinner", "brunch")
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
MIN_COURSES = 2
# Restaurant Week menus are multi-course by the program's own rules, so a
# missing course count is accepted for them and nothing else.
PROGRAM_COURSES = "restaurant_week_program"

# Roundups and review sites find candidates; they are never Proof.
DISCOVERY_HOSTS = ("eater.com", "theinfatuation.com", "timeout.com", "grubstreet.com", "nymag.com",
                   "secretnyc.co", "yelp.com", "tripadvisor.com", "google.com", "goo.gl")


@dataclass(frozen=True)
class SetMenu:
    id: str
    restaurant: str
    address: str
    meal: str
    days: tuple[str, ...]
    price: float
    courses: int | None
    proof_url: str
    seen_on: str
    checked_on: str
    required_supplements: float = 0
    courses_basis: str | None = None
    proof_hash: str | None = None
    place_id: str | None = None
    lat: float | None = None
    lng: float | None = None
    google_name: str | None = None
    place_match: str | None = None
    discovered_via: str | None = None
    notes: str = ""
    source: str = "research"  # or "restaurant_week"
    saving_usd: float | None = None  # only from nyc-restaurants' verified figures
    extra: dict = field(default_factory=dict, compare=False)

    @property
    def deal_price(self) -> float:
        return self.price + (self.required_supplements or 0)

    @property
    def price_per_course(self) -> float | None:
        return self.deal_price / self.courses if self.courses else None


def _money(x: float) -> str:
    return f"${x:g}" if float(x).is_integer() else f"${x:.2f}"


def deal_verdict(m: SetMenu) -> tuple[bool, str]:
    """(is it a Deal, why). The reason is shown in the build log for every non-Deal."""
    if m.courses is None:
        # Only the Restaurant Week importer may lean on the program rule; a research
        # row with no course count is not known to be a Set Menu.
        if m.courses_basis != PROGRAM_COURSES or m.source != "restaurant_week":
            return False, "course count unknown"
    elif m.courses < MIN_COURSES:
        return False, f"not a Set Menu: {m.courses} course{'s' if m.courses != 1 else ''}"
    cap = DEAL_CAPS.get(m.meal)
    if cap is None:
        return False, f"no Deal Cap for {m.meal} yet (owner decision)"
    if m.deal_price > cap:
        return False, f"over the {_money(cap)} {m.meal} cap ({_money(m.deal_price)})"
    return True, "Deal"


def _number(x) -> bool:
    """A real, finite number of dollars: not a bool, not NaN, not infinity."""
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _iso(value: str, name: str, menu_id: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(f"{menu_id}: {name} must be YYYY-MM-DD, not {value!r}")
    date.fromisoformat(value)


def validate(m: SetMenu) -> SetMenu:
    """Refuse a record that is not well formed, naming the field."""
    if not m.id or not m.restaurant:
        raise ValueError(f"set menu needs an id and a restaurant: {m!r}")
    if m.meal not in MEALS:
        raise ValueError(f"{m.id}: meal {m.meal!r} is not one of {MEALS}")
    if not m.days:
        raise ValueError(f"{m.id}: no days; Availability needs at least one")
    for d in m.days:
        if d not in DAYS:
            raise ValueError(f"{m.id}: day {d!r} is not one of {DAYS}")
    if not _number(m.price) or m.price <= 0:
        raise ValueError(f"{m.id}: price must be a positive number of dollars, not {m.price!r}")
    if not _number(m.required_supplements) or m.required_supplements < 0:
        raise ValueError(f"{m.id}: required_supplements must be 0 or more")
    if m.courses is not None and (not isinstance(m.courses, int) or m.courses < 1):
        raise ValueError(f"{m.id}: courses must be a whole number, not {m.courses!r}")
    url = urlparse(m.proof_url or "")
    if url.scheme != "https" or not url.hostname:
        raise ValueError(f"{m.id}: proof_url must be an https link to the restaurant's own page")
    host = url.hostname.rstrip(".")  # lowercased, no port, no user, no trailing dot
    if any(host == h or host.endswith("." + h) for h in DISCOVERY_HOSTS):
        raise ValueError(f"{m.id}: proof_url {host} is a Discovery Source, not the restaurant's own page")
    _iso(m.seen_on, "seen_on", m.id)
    _iso(m.checked_on, "checked_on", m.id)
    return m


# Fields only the Restaurant Week importer sets; a research row naming one is refused.
_FIELDS = {f.name for f in fields(SetMenu)} - {"extra", "source", "saving_usd", "courses_basis"}


def from_json(row: dict) -> SetMenu:
    unknown = set(row) - _FIELDS
    if unknown:
        raise ValueError(f"{row.get('id', '?')}: unknown field {sorted(unknown)[0]!r}")
    row = dict(row)
    row["days"] = tuple(row.get("days") or ())
    try:
        return validate(SetMenu(**row))
    except TypeError as e:
        raise ValueError(f"{row.get('id', '?')}: {e}") from None


def load_set_menus(path: Path) -> list[SetMenu]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    menus = [from_json(r) for r in data["set_menus"]]
    seen: set[str] = set()
    for m in menus:
        if m.id in seen:
            raise ValueError(f"{path}: duplicate id {m.id!r}")
        seen.add(m.id)
    return menus
