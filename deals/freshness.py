"""Checked On and Stale Deals (GLOSSARY.md).

A Deal is shown while its Checked On date is 30 days old or less (owner
decision, 2026-11-22). Checked On is the later of:
- the date the owner last confirmed it against its Proof (`checked_on`), and
- the date of the last Recheck that found the Proof page unchanged from the
  version the owner confirmed (`proof_hash`). That date is carried forward
  in checks.json, so a later changed, gone or unreachable Recheck neither
  moves Checked On nor takes back what an earlier unchanged one gave.
"""
from __future__ import annotations

from datetime import date

STALE_AFTER_DAYS = 30


def effective_checked_on(owner_checked_on: str, proof_hash: str | None, check) -> str:
    if check is None or proof_hash is None:
        return owner_checked_on
    dates = [owner_checked_on]
    if check.status == "unchanged" and check.fingerprint == proof_hash:
        dates.append(check.checked_on)
    if check.last_unchanged_on and check.last_unchanged_fingerprint == proof_hash:
        dates.append(check.last_unchanged_on)
    return max(dates)


def is_stale(checked_on: str, today: date) -> bool:
    return (today - date.fromisoformat(checked_on)).days > STALE_AFTER_DAYS
