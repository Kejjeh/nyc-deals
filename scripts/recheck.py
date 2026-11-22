"""Recheck every research Set Menu's Proof page, or confirm one as the owner.

    python scripts/recheck.py                 # fetch every Proof page, write data/checks.json
    python scripts/recheck.py --accept ID ... # owner: I checked this page; store it as the Proof

Free: it fetches the restaurants' own public pages, nothing billed. Restaurant
Week Set Menus are not rechecked here; their freshness is nyc-restaurants' season
snapshot.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from deals import store  # noqa: E402
from deals.model import load_set_menus  # noqa: E402
from deals.recheck import Check, Fetched, classify, fetch  # noqa: E402


def run_rechecks(menus, fetch_fn, today: date, previous: dict[str, Check] | None = None) -> dict[str, Check]:
    """One Check per research Set Menu. `previous` is the last checks.json, so the
    last unchanged date survives a week the page is down or different."""
    previous = previous or {}
    out = {}
    for m in menus:
        if m.source != "research":
            continue
        try:
            fetched = fetch_fn(m.proof_url)
        except Exception as e:  # one bad page never stops the rest; it is unreachable, never gone
            fetched = Fetched(None, b"", "", f"{type(e).__name__}: {e}")
        c = replace(classify(m.proof_hash, fetched), url=m.proof_url, checked_on=today.isoformat())
        if c.status == "unchanged":
            c = replace(c, last_unchanged_on=c.checked_on, last_unchanged_fingerprint=c.fingerprint)
        elif m.id in previous:
            p = previous[m.id]
            c = replace(c, last_unchanged_on=p.last_unchanged_on, last_unchanged_fingerprint=p.last_unchanged_fingerprint)
        out[m.id] = c
    return out


def accept(path: Path, menu_ids: list[str], fetch_fn, today: date) -> list[str]:
    menus = {m.id: m for m in load_set_menus(path)}
    done = []
    for mid in menu_ids:
        if mid not in menus:
            raise SystemExit(f"no set menu with id {mid!r}")
        c = classify(None, fetch_fn(menus[mid].proof_url))
        if c.fingerprint is None:
            raise SystemExit(f"{mid}: its Proof page is {c.status} (HTTP {c.http}, {c.error}); not accepted")
        store.update_set_menu(path, mid, proof_hash=c.fingerprint, checked_on=today.isoformat())
        done.append(mid)
    return done


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--accept", nargs="+", metavar="ID")
    ap.add_argument("--today", type=date.fromisoformat, default=date.today())
    args = ap.parse_args(argv)
    if args.accept:
        for mid in accept(store.SET_MENUS, args.accept, fetch, args.today):
            print(f"accepted {mid}: Proof stored, Checked On {args.today}")
        return
    checks = run_rechecks(load_set_menus(store.SET_MENUS), fetch, args.today, store.load_checks())
    store.save_checks(checks)
    by = {}
    for mid, c in checks.items():
        by.setdefault(c.status, []).append(mid)
    print(f"Rechecked {len(checks)} Proof pages: " + (", ".join(f"{s} {len(v)}" for s, v in sorted(by.items())) or "none"))
    for status in ("changed", "gone", "unreachable", "no baseline"):
        for mid in by.get(status, []):
            print(f"  {status}: {mid}")


if __name__ == "__main__":
    main(sys.argv[1:])
