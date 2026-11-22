"""Find the Google place_id and coordinates for research Set Menus that lack them.

    python scripts/lookup_places.py            # dry run: lists what it would look up and the cost. Free.
    python scripts/lookup_places.py --spend    # BILLED: one Places Text Search per restaurant

Billed: about $0.032 per lookup (Places API Text Search, ~$32 per 1,000). Run
--spend only with the owner's OK for that run (CLAUDE.md). The key is read from
the GOOGLE_PLACES_KEY environment variable or the gitignored scripts/config.py;
it is never printed.

A match counts only when Google's name is close to ours (similarity >= 0.80
after normalising). Otherwise nothing is stored but a `place_match` note, so a
wrong business never brings its Rankings or its neighborhood with it.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
import urllib.request
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from deals import store  # noqa: E402
from deals.model import load_set_menus  # noqa: E402

COST_PER_LOOKUP = 0.032
TRUST_THRESHOLD = 0.80
ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
FIELDS = "places.id,places.displayName,places.location,places.formattedAddress"


def normalise(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"&", " and ", s)
    s = re.sub(r"\b(the|restaurant|nyc|new york)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalise(a), normalise(b)).ratio()


def needs_lookup(menus) -> list:
    seen, out = set(), []
    for m in menus:
        if m.source == "research" and not m.place_id and not m.place_match and (m.restaurant, m.address) not in seen:
            seen.add((m.restaurant, m.address))
            out.append(m)
    return out


def _key() -> str:
    key = os.environ.get("GOOGLE_PLACES_KEY")
    if not key:
        try:
            from scripts import config  # type: ignore  # gitignored
            key = getattr(config, "GOOGLE_PLACES_KEY", None)
        except ImportError:
            key = None
    if not key:
        raise SystemExit("No key: set GOOGLE_PLACES_KEY or create scripts/config.py (gitignored) from config.example.py")
    return key


def search(name: str, address: str, key: str) -> dict | None:
    body = json.dumps({"textQuery": f"{name}, {address}", "maxResultCount": 1}).encode()
    req = urllib.request.Request(ENDPOINT, data=body, method="POST", headers={
        "Content-Type": "application/json", "X-Goog-Api-Key": key, "X-Goog-FieldMask": FIELDS})
    with urllib.request.urlopen(req, timeout=30) as res:
        places = json.load(res).get("places") or []
    return places[0] if places else None


def decide(menu_name: str, place: dict | None) -> dict:
    """Fields to store for one lookup result: trusted match, or only a note."""
    today = date.today().isoformat()
    if not place:
        return {"place_match": f"no Google result ({today})"}
    google_name = (place.get("displayName") or {}).get("text", "")
    score = similarity(menu_name, google_name)
    if score < TRUST_THRESHOLD:
        return {"place_match": f"untrusted: Google says {google_name!r} ({score:.2f}, {today})"}
    loc = place.get("location") or {}
    return {"place_id": place["id"], "lat": loc.get("latitude"), "lng": loc.get("longitude"),
            "google_name": google_name, "place_match": f"trusted ({score:.2f}, {today})"}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--spend", action="store_true", help="make the billed calls")
    args = ap.parse_args(argv)
    todo = needs_lookup(load_set_menus(store.SET_MENUS))
    print(f"{len(todo)} restaurant(s) need a lookup: about ${len(todo) * COST_PER_LOOKUP:.2f}")
    for m in todo:
        print(f"  {m.restaurant} | {m.address}")
    if not args.spend or not todo:
        print("Dry run: nothing was called." if todo else "Nothing to do.")
        return
    key = _key()
    menus = load_set_menus(store.SET_MENUS)
    for m in todo:
        fields = decide(m.restaurant, search(m.restaurant, m.address, key))
        for other in menus:  # every Set Menu of the same restaurant gets the same result
            if (other.restaurant, other.address) == (m.restaurant, m.address):
                store.update_set_menu(store.SET_MENUS, other.id, **fields)
        print(f"  {m.restaurant}: {fields['place_match']}")


if __name__ == "__main__":
    main(sys.argv[1:])
