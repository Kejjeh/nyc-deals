"""Build docs/data.json (the site) and data/recheck_list.md from the committed data.

    python scripts/build.py [--today YYYY-MM-DD] [--season-index PATH_OR_URL]

Reads data/set_menus.json, data/checks.json and data/rankings.json, plus the
running Restaurant Week season (if any) from nyc-restaurants' published export.
Free: no billed call. Prints what was left out and why.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from deals import store  # noqa: E402
from deals.model import load_set_menus  # noqa: E402
from deals.restaurant_week import set_menus_from_season  # noqa: E402
from deals.site import build_site, recheck_list_markdown  # noqa: E402


def _read(source: str) -> dict:
    if source.startswith("https://"):
        req = urllib.request.Request(source, headers={"User-Agent": "nyc-deals-build/1.0"})
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.load(res)
    return store.read_json(Path(source))


def restaurant_week(index_source: str, today: date):
    """Set Menus from the season running today, or none. A failed fetch raises."""
    index = _read(index_source)
    running = [s for s in index["seasons"] if date.fromisoformat(s["start"]) <= today <= date.fromisoformat(s["end"])]
    if not running:
        return [], {"no Restaurant Week season running": 1}
    if len(running) > 1:
        raise SystemExit(f"{len(running)} Restaurant Week seasons overlap {today}: {[s['code'] for s in running]}")
    base = index_source.rsplit("/", 1)[0]
    file = f"{base}/{running[0]['file']}" if index_source.startswith("https://") else str(Path(index_source).parent / running[0]["file"])
    return set_menus_from_season(_read(file), today)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--today", type=date.fromisoformat, default=date.today())
    ap.add_argument("--season-index", default=store.SEASON_INDEX)
    ap.add_argument("--no-restaurant-week", action="store_true")
    args = ap.parse_args(argv)

    menus = load_set_menus(store.SET_MENUS)
    rw, rw_skipped = ([], {"skipped (--no-restaurant-week)": 1}) if args.no_restaurant_week \
        else restaurant_week(args.season_index, args.today)
    rankings = store.read_json(store.RANKINGS)["index"] if store.RANKINGS.exists() else {}
    data, report = build_site(menus + rw, store.load_checks(), rankings, args.today)
    store.write_json(store.SITE_DATA, data)
    store.RECHECK_LIST.write_text(recheck_list_markdown(report, args.today), encoding="utf-8")

    print(f"Built {store.SITE_DATA.relative_to(store.ROOT)} for {args.today}")
    for k, v in sorted(report["counts"].items()):
        print(f"  {k}: {v}")
    for k, v in sorted(dict(rw_skipped).items()):
        print(f"  Restaurant Week left out, {k}: {v}")
    for k, v in sorted(report["not Deals"].items()):
        print(f"  not a Deal, {k}: {v}")
    print(f"  stale (off the site): {len(report['stale'])}")
    print(f"  on the Recheck List: {len(report['recheck'])}")
    print(f"  no neighborhood (no coordinates or outside NYC): {len(report['no neighborhood'])}")
    for k, ids in report["rankings"].items():
        print(f"  {k}: {len(ids)}" + (f" ({', '.join(ids[:10])}{' ...' if len(ids) > 10 else ''})" if ids else ""))


if __name__ == "__main__":
    main(sys.argv[1:])
