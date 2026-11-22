# Handoff

## State (2026-11-22)

Built from the design session of 2026-11-21/22 (decisions in `GLOSSARY.md` and `docs/adr/`). 56 tests pass. `data/set_menus.json` is empty, and no Restaurant Week season is running, so the site shows its empty state. `data/rankings.json` was built from the local checkouts on 2026-11-22. Counts:

| Source | Badges | Left out |
|---|---|---|
| Omakase omakase | 174 | 15 untrusted Google matches |
| Omakase italian | 145 | 7 untrusted Google matches |
| NYC Eats | 9,588 | none |
| NYC award roster | 524 | 541 no award, 180 no place_id, 121 closed, 54 sharing 27 place_ids |

Not yet on GitHub: no remote, no Pages, and the weekly Action has never run.

## Next, in order

1. **Owner:** create the public repo `Kejjeh/nyc-deals`, push, and turn on Pages from `main` / `docs`.
2. **Owner:** run `research/Deals_Research_Prompt.md` in a deep-research session. Check each candidate's Proof page, then add the confirmed ones to `data/set_menus.json`.
3. `python scripts/recheck.py --accept <ids>`, then `python scripts/lookup_places.py` (dry run), then `--spend` with the owner's OK (~$0.032 each). Then `python scripts/build.py`.
4. Watch the first weekly Recheck run. It commits to `main` and opens the "Recheck List" issue.

## Open owner decisions

- **Brunch cap.** There is none, so no brunch menu is a Deal. The summer 2026 Restaurant Week export had 181 restaurants with brunch prices.
- **Program rules assumed for Restaurant Week**, worth confirming before the winter 2027 season:
  - weekday prices run Monday to Friday, with no Saturday;
  - every menu has 2 or more courses (the export has course counts for only 3 of 636).

## Known limits

- A Proof page that changes something unrelated to the menu (a new banner) shows as "changed" and goes on the Recheck List. The owner then re-accepts it.
- Rankings are as fresh as the last `build_rankings.py` run.
