# 0002. Rankings join on Google place_id

Date: 2026-11-22. Status: accepted (owner, in the design session that started the repo).

## Context

Each Deal shows its restaurant's Rankings from three other repos, which key restaurants differently: Omakase by `name`, nyc-restaurants by `slug`, NYC Eats by Google place_id. Matching on names looks right on a few rows and fails silently on the rest (spelling, "The", branches of a chain, two restaurants with one name).

Measured on 2026-11-22: none of the three publishes place_ids in the data its site reads, except NYC Eats (whose `id` is the place_id). Omakase keeps them in `scripts/data/<list>/ratings_cache.json`, and nyc-restaurants in the `venues` table of its SQLite database. The roster has 54 venues sharing 27 place_ids.

## Decision

- Every source is reduced to `{place_id: badge}` by `scripts/build_rankings.py`. It reads local checkouts and writes the committed `data/rankings.json`; CI never needs the other repos.
- Omakase rows count only when Omakase trusts the Google match (`google_trusted`). A roster place_id that two venues share is left out, because one of those matches is wrong and the join can't tell which.
- A research Deal gets its place_id from `scripts/lookup_places.py`. That is **billed** (about $0.032 a restaurant), so each `--spend` run needs the owner's OK. It stores a match only when Google's name is at least 0.80 similar to ours, and otherwise stores a note.
- A Restaurant Week Deal uses the place_id nyc-restaurants found.
- Badges are shown side by side and never combined.

## Consequences

- Rankings go stale until someone reruns `build_rankings.py` after the other repos publish. Its output is dated.
- Every build prints the Deals with no place_id and the Deals whose place_id has no Ranking, so a broken join is loud.
