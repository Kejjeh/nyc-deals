"""Turn Set Menus into the public site's data, and say what was left out and why.

Only fresh Deals are published. Everything else is counted in the run log, and
the Recheck List (data/recheck_list.md) names each item the owner has to look at.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timezone

from deals import geo
from deals.freshness import STALE_AFTER_DAYS, effective_checked_on, is_stale
from deals.model import DEAL_CAPS, SetMenu, deal_verdict
from deals.rankings import attach

RECHECK_STATUSES = ("changed", "gone", "unreachable", "no baseline")


def _sort_key(d: dict):
    ppc = d["price_per_course"]
    return (ppc is None, ppc if ppc is not None else d["deal_price"], d["deal_price"], d["restaurant"])


def build_site(menus: list[SetMenu], checks: dict, rankings_index: dict, today: date) -> tuple[dict, dict]:
    ranked, ranking_report = attach(menus, rankings_index)
    counts: Counter = Counter()
    not_deals: Counter = Counter()
    stale, recheck, no_area = [], [], []
    deals = []
    for m in menus:
        counts[f"set menus ({m.source})"] += 1
        ok, why = deal_verdict(m)
        if not ok:
            not_deals[why] += 1
            continue
        check = checks.get(m.id)
        checked_on = effective_checked_on(m.checked_on, m.proof_hash, check)
        if m.source == "research" and check is not None and check.status in RECHECK_STATUSES:
            recheck.append((m, check.status))
        if is_stale(checked_on, today):
            stale.append((m, checked_on))
            continue
        area = geo.lookup(m.lat, m.lng)
        if area is None:
            no_area.append(m.id)
        deals.append({
            "id": m.id, "restaurant": m.restaurant, "address": m.address, "meal": m.meal, "days": list(m.days),
            "price": m.price, "required_supplements": m.required_supplements, "deal_price": m.deal_price,
            "courses": m.courses, "price_per_course": m.price_per_course,
            "borough": area.borough if area else None, "neighborhood": area.name if area else None,
            "proof_url": m.proof_url, "checked_on": checked_on, "source": m.source,
            "saving_usd": m.saving_usd, "notes": m.notes, "rankings": ranked[m.id],
        })
    deals.sort(key=_sort_key)
    counts["Deals published"] = len(deals)
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "today": today.isoformat(),
        "caps": DEAL_CAPS,
        "stale_after_days": STALE_AFTER_DAYS,
        "deals": deals,
    }
    report = {
        "counts": dict(counts), "not Deals": dict(not_deals),
        "stale": [(m.id, c, m.source) for m, c in stale], "recheck": [(m.id, s) for m, s in recheck],
        "no neighborhood": no_area, "rankings": ranking_report,
    }
    return data, report


def recheck_list_markdown(report: dict, today: date) -> str:
    research_stale = [(i, c) for i, c, source in report["stale"] if source == "research"]
    rw_stale = [(i, c) for i, c, source in report["stale"] if source == "restaurant_week"]
    accept = "Check its Proof page, then confirm it with `python scripts/recheck.py --accept <id>`."
    lines = [f"# Recheck List ({today.isoformat()})", "", "Deals the owner needs to look at.", ""]
    if report["recheck"]:
        lines += ["## Proof page changed, gone or unreachable", "", accept, ""]
        lines += [f"- `{i}`: {s}" for i, s in report["recheck"]] + [""]
    if research_stale:
        lines += [f"## Stale (Checked On more than {STALE_AFTER_DAYS} days ago; off the site)", "", accept, ""]
        lines += [f"- `{i}`: last checked {c}" for i, c in research_stale] + [""]
    if rw_stale:
        lines += [f"## Restaurant Week, stale (season snapshot more than {STALE_AFTER_DAYS} days old; off the site)", "",
                  "Nothing to accept: these come back when nyc-restaurants publishes a newer snapshot.", ""]
        lines += [f"- `{i}`: snapshot {c}" for i, c in rw_stale] + [""]
    if not report["recheck"] and not report["stale"]:
        lines += ["Nothing to recheck.", ""]
    return "\n".join(lines)
