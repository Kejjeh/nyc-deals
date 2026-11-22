// NYC Deals site. Pure functions are exported for tests/js; the DOM code runs only in a browser.

export const DAY_ORDER = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
const DAY_NAMES = { mon: "Mon", tue: "Tue", wed: "Wed", thu: "Thu", fri: "Fri", sat: "Sat", sun: "Sun" };

/** "Mon–Fri, Sun": runs of three or more days collapse into a range. */
export function formatDays(days) {
  const idx = DAY_ORDER.map((d) => days.includes(d));
  const parts = [];
  for (let i = 0; i < 7; ) {
    if (!idx[i]) { i++; continue; }
    let j = i;
    while (j + 1 < 7 && idx[j + 1]) j++;
    const run = DAY_ORDER.slice(i, j + 1).map((d) => DAY_NAMES[d]);
    parts.push(run.length >= 3 ? `${run[0]}–${run[run.length - 1]}` : run.join(", "));
    i = j + 1;
  }
  return parts.join(", ");
}

export function money(x) {
  return Number.isInteger(x) ? `$${x}` : `$${x.toFixed(2)}`;
}

/** The weekday of a Date in New York, as "mon".."sun". */
export function nycWeekday(now = new Date()) {
  const name = now.toLocaleDateString("en-US", { weekday: "short", timeZone: "America/New_York" }).toLowerCase();
  return name.slice(0, 3);
}

/** New York's date as "YYYY-MM-DD". */
export function nycIsoDate(now = new Date()) {
  const parts = new Intl.DateTimeFormat("en-US", { timeZone: "America/New_York", year: "numeric", month: "2-digit", day: "2-digit" })
    .formatToParts(now).reduce((o, p) => ({ ...o, [p.type]: p.value }), {});
  return `${parts.year}-${parts.month}-${parts.day}`;
}

/** Is a Deal's Checked On within the window on `todayIso`? The build drops stale Deals; this
 * also drops them from a page that has not been rebuilt since (the weekly job did not run). */
export function isFresh(deal, todayIso, staleAfterDays) {
  const days = (Date.parse(`${todayIso}T00:00:00Z`) - Date.parse(`${deal.checked_on}T00:00:00Z`)) / 86400000;
  return days <= staleAfterDays;
}

/** Does a Deal pass the filters? `day` may be "any", "today" or a day code. */
export function matches(deal, f, today) {
  if (f.meal !== "any" && deal.meal !== f.meal) return false;
  const day = f.day === "today" ? today : f.day;
  if (day !== "any" && !deal.days.includes(day)) return false;
  if (f.borough !== "any" && deal.borough !== f.borough) return false;
  if (f.maxPrice != null && deal.deal_price > f.maxPrice) return false;
  return true;
}

export function boroughs(deals) {
  return [...new Set(deals.map((d) => d.borough).filter(Boolean))].sort();
}

/** The price line: Deal Price, with any required supplement spelled out. Empty when it would only repeat the price. */
export function priceLine(d) {
  if (!d.required_supplements && d.courses == null) return "";
  const per = d.price_per_course == null ? "" : ` · ${money(Math.round(d.price_per_course * 100) / 100)} a course`;
  const courses = d.courses == null ? "" : ` · ${d.courses} courses`;
  const supp = d.required_supplements ? ` (${money(d.price)} + ${money(d.required_supplements)} required)` : "";
  return `${money(d.deal_price)}${supp}${courses}${per}`;
}

// ---------------------------------------------------------------- browser only
if (typeof document !== "undefined") {
  const $ = (id) => document.getElementById(id);
  const state = { meal: "any", day: "any", borough: "any", maxPrice: null, data: null };
  const fmtDate = (s) => new Date(s + "T12:00:00Z").toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });

  function text(tag, cls, value) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    n.textContent = value;
    return n;
  }

  function card(d) {
    const li = document.createElement("li");
    li.className = "deal";
    const head = document.createElement("div");
    head.className = "deal-head";
    head.append(text("h3", "", d.restaurant), text("span", "price", money(d.deal_price)));
    li.append(head);
    const where = [d.neighborhood, d.borough].filter(Boolean).join(", ") || "Neighborhood unknown";
    li.append(text("p", "meta", `${d.meal[0].toUpperCase() + d.meal.slice(1)} · ${formatDays(d.days)} · ${where}`));
    const line = priceLine(d);
    if (line) li.append(text("p", "line", line));
    if (d.rankings.length || d.source === "restaurant_week") {
      const badges = document.createElement("div");
      badges.className = "badges";
      if (d.source === "restaurant_week") badges.append(text("span", "badge rw", "Restaurant Week"));
      for (const r of d.rankings) {
        const a = document.createElement("a");
        a.className = "badge"; a.href = r.url; a.rel = "noopener"; a.textContent = r.label; a.title = r.site;
        badges.append(a);
      }
      li.append(badges);
    }
    if (d.saving_usd != null) li.append(text("p", "saving", `About ${money(d.saving_usd)} less than ordering the same meal off the regular menu (checked by nyc-restaurants).`));
    if (d.notes) li.append(text("p", "note", d.notes));
    const proof = document.createElement("p");
    proof.className = "proof";
    const a = document.createElement("a");
    a.href = d.proof_url; a.rel = "noopener"; a.textContent = "the menu";
    proof.append(`Checked ${fmtDate(d.checked_on)} against `, a);
    li.append(proof);
    return li;
  }

  function render() {
    const today = nycWeekday();
    const shown = state.data.deals.filter((d) => matches(d, state, today));
    $("count").textContent = `${shown.length} of ${state.data.deals.length} Deals`;
    $("list").replaceChildren(...shown.map(card));
    $("none").hidden = shown.length > 0 || state.data.deals.length === 0;
    $("empty").hidden = state.data.deals.length > 0;
  }

  async function start() {
    try {
      const res = await fetch("data.json", { cache: "no-store" });
      if (!res.ok) throw new Error(String(res.status));
      state.data = await res.json();
      const todayIso = nycIsoDate();
      state.data.deals = state.data.deals.filter((d) => isFresh(d, todayIso, state.data.stale_after_days));
    } catch (e) {
      $("empty").hidden = false;
      $("empty").textContent = "The list could not be loaded. Try again in a minute.";
      return;
    }
    const caps = state.data.caps;
    $("rule").textContent = `A Deal is a fixed-price menu of two or more courses at or under ${money(caps.lunch)} for lunch or ${money(caps.dinner)} for dinner, before tax and tip, counting any supplement you can't avoid. Every Deal links to the restaurant's own menu and drops off if nobody has confirmed it in ${state.data.stale_after_days} days.`;
    $("updated").textContent = `Updated ${fmtDate(state.data.today)}`;
    const sel = $("borough");
    for (const b of boroughs(state.data.deals)) sel.append(new Option(b, b));
    $("meal").addEventListener("change", (e) => { state.meal = e.target.value; render(); });
    $("day").addEventListener("change", (e) => { state.day = e.target.value; render(); });
    sel.addEventListener("change", (e) => { state.borough = e.target.value; render(); });
    $("max").addEventListener("change", (e) => { state.maxPrice = e.target.value === "any" ? null : Number(e.target.value); render(); });
    render();
  }

  start();
}
