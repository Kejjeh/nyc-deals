# Agent guide

## What this is

A public, year-round list of New York City fixed-price menus that are cheap enough to count as Deals. Each Deal links to the restaurant's own menu as Proof and shows Rankings from the owner's other sites. A static site (`docs/`, GitHub Pages) built from committed JSON by Python 3.13 standard library code. No database, no framework. **Current state: built; no research Deals yet.** The site shows Restaurant Week Deals only while a season runs. Read `HANDOFF.md` for what's next. `GLOSSARY.md` is the domain glossary; use its terms exactly (Set Menu, Deal, Deal Cap, Deal Price, Availability, Proof, Discovery Source, Recheck, Checked On, Stale Deal, Recheck List, Ranking).

## Commands (all verified from repo root)

```bash
pip install -r requirements.txt            # pytest only
python -m pytest -q                        # ~0.3s, offline. Expect: 68 passed
python scripts/build.py                    # -> docs/data.json + data/recheck_list.md (fetches nyc-restaurants' public season index; free)
python scripts/recheck.py                  # fetch every research Proof page -> data/checks.json (free)
python scripts/recheck.py --accept ID ...  # owner has checked this Proof page: store it, Checked On = today
python scripts/build_rankings.py           # -> data/rankings.json from local checkouts of Omakase, NYC Eats, NYC Restaurant Week (free)
python scripts/lookup_places.py            # dry run: who needs a place_id, and the cost
python scripts/lookup_places.py --spend    # BILLED (~$0.032 per restaurant). Only with the owner's OK for that run
python -m http.server -d docs 8000         # view the site (file:// can't fetch data.json)
```

## Architecture map

| File | Role |
|---|---|
| `deals/model.py` | Set Menu record, validation, the Deal test. `DEAL_CAPS` lives here (owner decision) |
| `deals/restaurant_week.py` | nyc-restaurants season export -> Set Menus (ADR 0001) |
| `deals/recheck.py` | Proof page fingerprint and Recheck classification |
| `deals/freshness.py` | Checked On and the 30-day stale rule |
| `deals/rankings.py` | Each source -> `{place_id: badge}`; attach badges to Deals (ADR 0002) |
| `deals/geo.py` | Neighborhood from coordinates (copied from Omakase; NTA file in `data/geo/`) |
| `deals/site.py` | Builds the site's data and the Recheck List; counts everything left out |
| `scripts/*.py` | The commands above |
| `data/set_menus.json` | **Source of truth**: research Set Menus, each added after the owner checked its Proof |
| `data/checks.json`, `data/rankings.json`, `data/recheck_list.md`, `docs/data.json` | Generated. Never hand-edit |
| `research/Deals_Research_Prompt.md` | The monthly research prompt |
| `.github/workflows/recheck.yml` | Weekly: recheck, rebuild, commit, update the one "Recheck List" issue |

## Conventions and gotchas

- **Owner decisions** (2026-11-22). Never change them without the owner:
  - caps of $45 lunch and $75 dinner;
  - no brunch cap yet, so brunch is never a Deal;
  - 30 days to stale;
  - Proof must be the restaurant's own page;
  - Rankings shown separately, never combined;
  - savings only for Restaurant Week (verified).
- **Adding a research Set Menu.** Take a candidate from the research output. The owner opens its proof_url; add the row to `data/set_menus.json`, then run `recheck.py --accept <id>` so the Proof is stored. Then run `lookup_places.py`: dry run first, and `--spend` only with the owner's OK.
- `validate()` refuses a Discovery Source (Eater, Infatuation, Yelp, Google, ...) as proof_url, an http link, unknown fields and duplicate ids. Fix the row; don't loosen the check.
- **Join key** for Rankings is the Google place_id, never the name (ADR 0002). The build prints Deals with no place_id and Deals with no Ranking.
- A Recheck that can't reach a page (timeout, 429, 5xx, dropped connection) is "unreachable", never "gone", and never moves Checked On. Each Check carries the last unchanged date forward from the previous `checks.json`, so a bad week can't take back an earlier confirmation either.
- `courses_basis` (the Restaurant Week course rule) is set only by the importer; a research row naming it is refused. The page also hides any Deal past 30 days on its own, in case the weekly rebuild didn't run.
- `docs/data.json` changes on every build (its `generated_at`). That's expected.
- **Do not read into context:** `data/geo/nyc_nta_2020.geojson` (2.4 MB), `data/rankings.json` (1.7 MB). Inspect them with `python -c`.

## Before you finish any task

1. `python -m pytest -q` -> `68 passed` (more if you added tests).
2. `python scripts/build.py` -> exits 0. Read the counts. Out of season, expect `no Restaurant Week season running: 1`.
3. `git diff --stat` -> only intended files, plus `docs/data.json` and `data/recheck_list.md`.

## Model routing

Safe for Sonnet: adding confirmed Set Menus, docs, site styling, tests, running the free commands. Escalate to Opus: `deal_verdict`, freshness, Recheck classification, the rankings join, the Restaurant Week import rules, and anything that contradicts an ADR or an owner decision.

## Secrets

The Google Places key lives in the `GOOGLE_PLACES_KEY` environment variable or in `scripts/config.py`, which is gitignored (copy `scripts/config.example.py`). Never commit it, print it, or paste it anywhere.
