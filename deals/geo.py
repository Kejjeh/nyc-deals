"""Neighborhood and borough from coordinates, never from a typed label.

Copied from Omakase's scripts/shared/geo.py (its ADR 0003): hand-rolled ray
casting over the vendored NYC 2020 Neighborhood Tabulation Areas.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

NTA_FILE = Path(__file__).resolve().parent.parent / "data" / "geo" / "nyc_nta_2020.geojson"


@dataclass(frozen=True)
class Area:
    code: str
    name: str
    borough: str


def _in_ring(x: float, y: float, ring: list) -> bool:
    inside, j = False, len(ring) - 1
    for i in range(len(ring)):
        xi, yi, xj, yj = ring[i][0], ring[i][1], ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _in_polygon(x: float, y: float, rings: list) -> bool:
    return bool(rings) and _in_ring(x, y, rings[0]) and not any(_in_ring(x, y, h) for h in rings[1:])


@lru_cache(maxsize=None)
def _features() -> tuple:
    out = []
    for feature in json.loads(NTA_FILE.read_text(encoding="utf-8"))["features"]:
        p = feature.get("properties", {})
        area = Area(p.get("nta2020"), p.get("ntaname"), p.get("boroname"))
        geom = feature.get("geometry") or {}
        polys = [geom["coordinates"]] if geom.get("type") == "Polygon" else geom.get("coordinates") or []
        for rings in polys:
            xs, ys = [q[0] for q in rings[0]], [q[1] for q in rings[0]]
            out.append((area, rings, (min(xs), min(ys), max(xs), max(ys))))
    return tuple(out)


def lookup(lat: float | None, lng: float | None) -> Area | None:
    if lat is None or lng is None:
        return None
    for area, rings, (x0, y0, x1, y1) in _features():
        if x0 <= lng <= x1 and y0 <= lat <= y1 and _in_polygon(lng, lat, rings):
            return area
    return None
