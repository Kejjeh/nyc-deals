import { test } from "node:test";
import assert from "node:assert/strict";
import { boroughs, formatDays, isFresh, matches, money, nycIsoDate, nycWeekday, priceLine } from "../../docs/app.js";

test("days read like a menu", () => {
  assert.equal(formatDays(["mon", "tue", "wed", "thu", "fri"]), "Mon–Fri");
  assert.equal(formatDays(["mon", "tue", "wed", "thu", "fri", "sun"]), "Mon–Fri, Sun");
  assert.equal(formatDays(["sat", "sun"]), "Sat, Sun");
  assert.equal(formatDays(["tue", "thu"]), "Tue, Thu");
});

const deal = { meal: "lunch", days: ["mon", "tue"], borough: "Manhattan", deal_price: 39 };
const any = { meal: "any", day: "any", borough: "any", maxPrice: null };

test("filters: meal, day, today, borough and price", () => {
  assert.ok(matches(deal, any, "wed"));
  assert.ok(!matches(deal, { ...any, meal: "dinner" }, "wed"));
  assert.ok(matches(deal, { ...any, day: "tue" }, "wed"));
  assert.ok(!matches(deal, { ...any, day: "today" }, "wed"));
  assert.ok(matches(deal, { ...any, day: "today" }, "mon"));
  assert.ok(!matches(deal, { ...any, borough: "Queens" }, "wed"));
  assert.ok(!matches(deal, { ...any, maxPrice: 30 }, "wed"));
  assert.ok(matches(deal, { ...any, maxPrice: 45 }, "wed"));
});

test("a deal with no borough only shows under All boroughs", () => {
  assert.ok(!matches({ ...deal, borough: null }, { ...any, borough: "Manhattan" }, "mon"));
  assert.deepEqual(boroughs([{ borough: "Queens" }, { borough: null }, { borough: "Brooklyn" }, { borough: "Queens" }]), ["Brooklyn", "Queens"]);
});

test("the price line spells out a required supplement and the per-course price", () => {
  assert.equal(priceLine({ deal_price: 49, price: 39, required_supplements: 10, courses: 3, price_per_course: 49 / 3 }),
    "$49 ($39 + $10 required) · 3 courses · $16.33 a course");
  assert.equal(priceLine({ deal_price: 60, price: 60, required_supplements: 0, courses: null, price_per_course: null }), "");
  assert.equal(priceLine({ deal_price: 30, price: 30, required_supplements: 0, courses: 2, price_per_course: 15 }), "$30 · 2 courses · $15 a course");
  assert.equal(money(12.5), "$12.50");
});

test("today is New York's day, not the viewer's", () => {
  // 03:00 UTC on Tuesday 2026-11-24 is still Monday evening in New York.
  assert.equal(nycWeekday(new Date("2026-11-24T03:00:00Z")), "mon");
});

test("a page not rebuilt for weeks still hides Deals past the window", () => {
  assert.ok(isFresh({ checked_on: "2026-10-23" }, "2026-11-22", 30));   // 30 days: shown
  assert.ok(!isFresh({ checked_on: "2026-10-22" }, "2026-11-22", 30));  // 31 days: hidden
  assert.equal(nycIsoDate(new Date("2026-11-24T03:00:00Z")), "2026-11-23");
});
