"""Reading and writing the committed data files."""
from __future__ import annotations

import json
from pathlib import Path

from deals.recheck import Check

ROOT = Path(__file__).resolve().parent.parent
SET_MENUS = ROOT / "data" / "set_menus.json"
CHECKS = ROOT / "data" / "checks.json"
RANKINGS = ROOT / "data" / "rankings.json"
RECHECK_LIST = ROOT / "data" / "recheck_list.md"
SITE_DATA = ROOT / "docs" / "data.json"
SEASON_INDEX = "https://kejjeh.github.io/nyc-restaurants/data/seasons.json"


def read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    Path(path).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def load_checks(path: Path = CHECKS) -> dict[str, Check]:
    if not Path(path).exists():
        return {}
    return {k: Check(**v) for k, v in read_json(path)["checked"].items()}


def save_checks(checks: dict[str, Check], path: Path = CHECKS) -> None:
    write_json(path, {"_doc": "Last Recheck of each research Set Menu's Proof page. Written by scripts/recheck.py.",
                      "checked": {k: c.to_json() for k, c in sorted(checks.items())}})


def update_set_menu(path: Path, menu_id: str, **fields) -> None:
    """Set fields on one row of set_menus.json, keeping every other row and key as it was."""
    data = read_json(path)
    rows = [r for r in data["set_menus"] if r["id"] == menu_id]
    if len(rows) != 1:
        raise SystemExit(f"{path}: no set menu with id {menu_id!r}")
    rows[0].update(fields)
    write_json(path, data)
