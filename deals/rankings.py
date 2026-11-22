"""Rankings: scores and awards from the owner's other sites, keyed by Google place_id.

Names are not a join key (two repos spell the same restaurant differently, and a
shared name can be two restaurants), so every source is reduced to
{place_id: badge} first (ADR 0002). A Ranking is shown as its own badge; badges
are never combined into one score.

Each builder returns (badges, report). The report counts what was left out and
why, so a drop in coverage is visible on every run.
"""
from __future__ import annotations

from collections import Counter

OMAKASE_URL = "https://kejjeh.github.io/omakase/{list}/"
NYC_EATS_URL = "https://kejjeh.github.io/nyc-eats/"
AWARDS_URL = "https://kejjeh.github.io/nyc-restaurants/"


def omakase_badges(rows: list[dict], ratings_cache: dict, list_name: str) -> tuple[dict, dict]:
    """One Omakase cuisine list: rank by composite rating; only trusted Google matches carry a place_id."""
    ranked = sorted((r for r in rows if r.get("composite_rating") is not None),
                    key=lambda r: r["composite_rating"], reverse=True)
    n = len(ranked)
    badges, report = {}, Counter()
    for i, r in enumerate(ranked, 1):
        if not r.get("google_trusted"):
            report["untrusted Google match"] += 1
            continue
        pid = (ratings_cache.get(r["name"]) or {}).get("place_id")
        if not pid:
            report["no place_id"] += 1
            continue
        badges[pid] = {"site": "Omakase", "label": f"{list_name.capitalize()} list #{i} of {n}",
                       "url": OMAKASE_URL.format(list=list_name)}
        report["badges"] += 1
    return badges, dict(report)


def nyc_eats_badges(rows: list[dict]) -> tuple[dict, dict]:
    badges, report = {}, Counter()
    for r in rows:
        pid = r.get("id") or ""
        if not pid.startswith("ChIJ") or r.get("score") is None:
            report["no place_id or score"] += 1
            continue
        badges[pid] = {"site": "NYC Eats", "label": f"NYC Eats score {r['score']:.2f}", "url": NYC_EATS_URL}
        report["badges"] += 1
    return badges, dict(report)


def nyc_restaurants_badges(venues: list[dict], top_honor_labels: dict) -> tuple[dict, dict]:
    """The award roster: each open venue's top honor. A place_id two venues share is
    left out, because one of the two Google matches is wrong and we cannot tell which."""
    counts = Counter(v["place_id"] for v in venues if v.get("place_id"))
    badges, report = {}, Counter()
    for v in venues:
        pid = v.get("place_id")
        if not pid:
            report["no place_id"] += 1
        elif counts[pid] > 1:
            report["shared place_id (left out)"] += 1
        elif v.get("status") == "closed":
            report["closed"] += 1
        elif not top_honor_labels.get(v["venue_slug"]):
            report["no award"] += 1
        else:
            badges[pid] = {"site": "NYC award roster", "label": top_honor_labels[v["venue_slug"]], "url": AWARDS_URL}
            report["badges"] += 1
    return badges, dict(report)


def merge(*sources: dict) -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = {}
    for source in sources:
        for pid, badge in source.items():
            index.setdefault(pid, []).append(badge)
    return index


def attach(menus, index: dict[str, list[dict]]) -> tuple[dict[str, list[dict]], dict[str, list[str]]]:
    ranked, report = {}, {"no place_id": [], "no Ranking for its place_id": []}
    for m in menus:
        if not m.place_id:
            report["no place_id"].append(m.id)
        elif m.place_id not in index:
            report["no Ranking for its place_id"].append(m.id)
        ranked[m.id] = list(index.get(m.place_id, [])) if m.place_id else []
    return ranked, report
