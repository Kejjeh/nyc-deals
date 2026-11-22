"""Seam 2: Checked On + today -> shown or Stale."""
from datetime import date

from deals.freshness import STALE_AFTER_DAYS, effective_checked_on, is_stale
from deals.recheck import Check


def test_thirty_days_old_is_still_shown_and_thirty_one_is_stale():
    assert STALE_AFTER_DAYS == 30
    assert not is_stale("2026-10-23", date(2026, 11, 22))  # 30 days
    assert is_stale("2026-10-22", date(2026, 11, 22))      # 31 days


def test_an_unchanged_recheck_moves_checked_on_forward():
    check = Check(url="https://a.example/m", status="unchanged", fingerprint="abc", checked_on="2026-11-20")
    assert effective_checked_on("2026-09-01", "abc", check) == "2026-11-20"


def test_a_changed_page_does_not_move_it():
    check = Check(url="https://a.example/m", status="changed", fingerprint="def", checked_on="2026-11-20")
    assert effective_checked_on("2026-09-01", "abc", check) == "2026-09-01"


def test_an_unreachable_page_does_not_move_it():
    check = Check(url="https://a.example/m", status="unreachable", fingerprint=None, checked_on="2026-11-20")
    assert effective_checked_on("2026-09-01", "abc", check) == "2026-09-01"


def test_a_recheck_of_an_older_baseline_does_not_count():
    # The owner re-confirmed the page (new proof_hash) after this check ran.
    check = Check(url="https://a.example/m", status="unchanged", fingerprint="old", checked_on="2026-11-20")
    assert effective_checked_on("2026-11-01", "new", check) == "2026-11-01"


def test_no_check_yet_keeps_the_owner_date():
    assert effective_checked_on("2026-11-01", None, None) == "2026-11-01"
