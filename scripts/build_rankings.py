"""Rebuild data/rankings.json from local checkouts of the owner's other repos.

    python scripts/build_rankings.py [--projects DIR]

Free and offline: it reads files already on this PC.
- Omakase: docs/<list>/data.json for the rank, and scripts/data/<list>/ratings_cache.json
  for the place_id. Only rows whose Google match Omakase trusts are used.
- NYC Eats: docs/data/restaurants.json, whose `id` is the place_id.
- nyc-restaurants: the venues table in data/processed/restaurant_week.sqlite for the
  place_id, and docs/data/venues.json for each venue's top honor.
Run it after any of those repos publishes new rankings, then commit the result.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from deals import store  # noqa: E402
from deals.rankings import merge, nyc_eats_badges, nyc_restaurants_badges, omakase_badges  # noqa: E402

OMAKASE_LISTS = ("omakase", "italian")  # the two NYC lists; philly and kensington are not NYC


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--projects", type=Path, default=store.ROOT.parent)
    args = ap.parse_args(argv)
    p = args.projects
    sources, reports = [], {}

    for lst in OMAKASE_LISTS:
        rows = store.read_json(p / "Omakase" / "docs" / lst / "data.json")
        cache = store.read_json(p / "Omakase" / "scripts" / "data" / lst / "ratings_cache.json")
        badges, rep = omakase_badges(rows, cache, lst)
        sources.append(badges)
        reports[f"Omakase {lst}"] = rep

    eats = store.read_json(p / "NYC Eats" / "docs" / "data" / "restaurants.json")
    badges, rep = nyc_eats_badges(eats["restaurants"])
    sources.append(badges)
    reports["NYC Eats"] = rep

    nr = p / "NYC Restaurant Week"
    db = sqlite3.connect(f"file:{(nr / 'data' / 'processed' / 'restaurant_week.sqlite').as_posix()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    venues = [dict(r) for r in db.execute("select venue_slug, place_id, status from venues")]
    labels = {v["slug"]: v.get("top_honor_label") for v in store.read_json(nr / "docs" / "data" / "venues.json")["venues"]}
    badges, rep = nyc_restaurants_badges(venues, labels)
    sources.append(badges)
    reports["NYC award roster"] = rep

    index = merge(*sources)
    store.write_json(store.RANKINGS, {
        "_doc": "place_id -> Ranking badges, built by scripts/build_rankings.py from local checkouts. Do not hand-edit.",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "reports": reports,
        "index": dict(sorted(index.items())),
    })
    for name, rep in reports.items():
        print(f"{name}: " + ", ".join(f"{k} {v}" for k, v in rep.items()))
    print(f"Wrote {store.RANKINGS.relative_to(store.ROOT)}: {len(index)} place_ids with a Ranking")


if __name__ == "__main__":
    main(sys.argv[1:])
