# 0001. A separate repo from nyc-restaurants

Date: 2026-11-22. Status: accepted (owner, in the design session that started the repo).

## Context

nyc-restaurants already has a Restaurant Week dashboard with prices and savings estimates, so a deals tracker could have been a new page there. But that repo's own decision log says "the roster is the spine; Restaurant Week is an attribute", and its README says its grade answers "which dinner, not which deal". Its scope is award-recognised restaurants. A year-round Deals list includes many restaurants with no award, and is entirely about value.

## Decision

- NYC Deals is its own repo with its own GitHub Pages site.
- It reads Restaurant Week menus from nyc-restaurants' published season export (`https://kejjeh.github.io/nyc-restaurants/data/seasons.json` and the season file it names) instead of scraping NYC Tourism again. It inherits that repo's place_id matches and savings figures, and uses the savings only where nyc-restaurants marks them `verified`.
- Restaurant Week menus must pass the same Deal Cap as any other Set Menu.

## Consequences

- If nyc-restaurants changes its export's shape, the import refuses by name (an unknown price label raises) rather than guessing. Fix it here.
- Restaurant Week Deals appear only while a season runs. Between seasons the import contributes nothing and says so in the build log.
- nyc-restaurants keeps its scope; nothing in it changes.
