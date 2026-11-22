# NYC Deals

A public, year-round tracker of fixed-price restaurant menus in New York City that are cheap enough to count as Deals. Each one is shown with its restaurant's rankings from the owner's other sites.

## Menus

**Set Menu**:
A menu of two or more courses served for one fixed price.
_Avoid_: Tasting menu (when used to mean any fixed-price menu), course menu

**Deal**:
A Set Menu whose Deal Price is at or below the Deal Cap for its meal. A Deal is one menu, never a restaurant: a place with a $42 lunch and an $85 dinner has one Deal.
_Avoid_: Special, offer, promo, prix fixe (as a synonym for Deal), deal spot

**Deal Cap**:
The highest Deal Price a Set Menu can have and still be a Deal: $45 for lunch, $75 for dinner, before tax and tip.
_Avoid_: Price limit, threshold

**Deal Price**:
A Set Menu's base price plus any supplement you cannot avoid. Optional add-ons and drinks are left out.
_Avoid_: Price (on its own), menu price, cost

**Availability**:
The meal (lunch, dinner or brunch) and the days of the week a Deal is served.
_Avoid_: Hours, schedule

**Restaurant Week Deal**:
A Deal from the NYC Restaurant Week program, taken from the nyc-restaurants export and valid only during its season. It must pass the same Deal Cap as any other Set Menu.
_Avoid_: RW menu (in prose)

## Evidence and freshness

**Proof**:
The restaurant's own page (its menu or website) showing the Deal, with the date it was seen.
_Avoid_: Source (when a roundup is meant)

**Discovery Source**:
A roundup or list (Eater, The Infatuation, and so on) used only to find candidate Deals, never as Proof.
_Avoid_: Proof, citation

**Recheck**:
A fresh fetch of a Deal's Proof page. If the page is unchanged, that confirms the Deal; if it changed or won't load, the Deal goes on the Recheck List.
_Avoid_: Refresh, scrape

**Checked On**:
The date a Deal was last confirmed against its Proof, by an unchanged Recheck or by the owner.
_Avoid_: Updated, last seen

**Stale Deal**:
A Deal whose Checked On date is more than 30 days old. It is left off the public site until it is rechecked.
_Avoid_: Expired deal, old deal

**Recheck List**:
The Stale Deals and changed Proof pages that need the owner's confirmation, printed on every run.
_Avoid_: Todo list, queue

## Rankings

**Ranking**:
A score or award for a Deal's restaurant from one of the owner's other sites (Omakase, NYC Eats, nyc-restaurants), shown on the Deal as its own badge. Rankings are never combined into one score.
_Avoid_: Rating (the individual Google, Yelp or Infatuation number), grade
