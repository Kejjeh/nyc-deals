# Monthly research prompt: NYC Set Menus

Paste everything below the line into a deep-research session once a month. The output is a list of **candidates**. None of them goes on the site until the owner has opened its Proof page and added it to `data/set_menus.json`.

---

Find restaurants in New York City (all five boroughs) that currently offer a **Set Menu**: one fixed price for a fixed set of two or more courses.

**What counts**
- A Set Menu of 2 or more courses at one fixed price, served at lunch, dinner or brunch.
- Report every one you find. The price test is applied afterwards, but the ones that matter are at or under **$45 for lunch** and **$75 for dinner**, before tax and tip.
- Count a supplement as part of the price only when you cannot avoid it (for example, the steak course is the only main and costs $10 more). Leave out optional add-ons and drinks.
- Leave out: à la carte specials, happy hours, tasting menus over $150, catering and private-event menus, NYC Restaurant Week menus (we already have those), and anything closed or "coming soon".

**Proof rules (the most important part)**
- For each Set Menu, give the URL of the **restaurant's own page** that shows it: its website's menu page or menu PDF. Booking pages the restaurant runs (Resy, Tock, OpenTable) are acceptable when the restaurant's site has no menu.
- Eater, The Infatuation, Time Out, Grub Street, Secret NYC, Yelp, TripAdvisor and Google are **Discovery Sources**. Use them to find candidates, but never give them as proof. If you can't find the restaurant's own page showing the menu and price, put the candidate under "Unconfirmed" with the roundup link.
- Give the date you saw the proof page.
- Quote the exact price text from the proof page (for example "3-course lunch $39").

**Output format**
For each confirmed candidate, return one JSON object per line, with exactly these fields:

```json
{"id": "restaurant-slug-lunch", "restaurant": "Name as the restaurant writes it", "address": "Street, Borough, NY ZIP", "meal": "lunch", "days": ["mon","tue","wed","thu","fri"], "price": 39, "required_supplements": 0, "courses": 3, "proof_url": "https://the-restaurant.com/menus/lunch", "seen_on": "YYYY-MM-DD", "checked_on": "YYYY-MM-DD", "discovered_via": "https://roundup-where-you-found-it", "notes": "exact price text from the proof page"}
```

- `meal` is one of `lunch`, `dinner`, `brunch`. Make one object per meal; a place with both lunch and dinner menus gets two.
- `days` are the days that menu is served (`mon` to `sun`). If the page doesn't say, write "days not stated" in `notes` and list the days the restaurant is open for that meal.
- `checked_on` is the same as `seen_on`.

Then list:
1. **Unconfirmed**: candidates you found only in roundups, with the roundup link.
2. **Changed or gone**: any restaurant you expected to have a Set Menu that no longer shows one.
