"""Tests for the pure zone engine.

Run with:  python -m pytest custom_components/tauron_g13/tests -q
Requires:  pytest, holidays
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import holidays
import pytest

# zones is loaded as a bare module by conftest.py so these tests don't need
# Home Assistant installed.
from zones import (  # noqa: E402
    Zone,
    block_start_at,
    events_between,
    is_summer,
    next_boundary_after,
    zone_at,
)

TZ = ZoneInfo("Europe/Warsaw")
PL = holidays.Poland(years=range(2023, 2031))


def free_day(d) -> bool:
    """The free-day predicate used in production: weekend OR Polish holiday."""
    return d.weekday() >= 5 or d in PL


def dt(y, m, d, h, minute=0) -> datetime:
    return datetime(y, m, d, h, minute, tzinfo=TZ)


# --------------------------------------------------------------------------- #
# Season detection
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "month,summer",
    [(1, False), (3, False), (4, True), (9, True), (10, False), (12, False)],
)
def test_season(month, summer):
    assert is_summer(datetime(2026, month, 15).date()) is summer


def test_season_flip_boundaries():
    # Mar 31 is still winter, Apr 1 is summer.
    assert is_summer(datetime(2026, 3, 31).date()) is False
    assert is_summer(datetime(2026, 4, 1).date()) is True
    # Sep 30 summer, Oct 1 winter.
    assert is_summer(datetime(2026, 9, 30).date()) is True
    assert is_summer(datetime(2026, 10, 1).date()) is False


# --------------------------------------------------------------------------- #
# Zone classification on an ordinary workday
# --------------------------------------------------------------------------- #


def test_winter_workday_zones():
    # 2026-01-13 is a Tuesday (winter).
    assert zone_at(dt(2026, 1, 13, 3), free_day(datetime(2026, 1, 13).date())) is Zone.OFFPEAK
    assert zone_at(dt(2026, 1, 13, 8), free_day(datetime(2026, 1, 13).date())) is Zone.MID
    assert zone_at(dt(2026, 1, 13, 14), free_day(datetime(2026, 1, 13).date())) is Zone.OFFPEAK
    assert zone_at(dt(2026, 1, 13, 17), free_day(datetime(2026, 1, 13).date())) is Zone.PEAK
    assert zone_at(dt(2026, 1, 13, 21), free_day(datetime(2026, 1, 13).date())) is Zone.OFFPEAK


def test_summer_workday_zones():
    # 2026-07-14 is a Tuesday (summer).
    fd = free_day(datetime(2026, 7, 14).date())
    assert zone_at(dt(2026, 7, 14, 6), fd) is Zone.OFFPEAK
    assert zone_at(dt(2026, 7, 14, 8), fd) is Zone.MID
    assert zone_at(dt(2026, 7, 14, 14), fd) is Zone.OFFPEAK  # 13-19 cheap in summer
    assert zone_at(dt(2026, 7, 14, 20), fd) is Zone.PEAK  # 19-22 peak
    assert zone_at(dt(2026, 7, 14, 23), fd) is Zone.OFFPEAK


def test_boundary_hours_are_inclusive_exclusive():
    fd = free_day(datetime(2026, 1, 13).date())
    # Peak is [16,21): 16:00 in, 21:00 out.
    assert zone_at(dt(2026, 1, 13, 16, 0), fd) is Zone.PEAK
    assert zone_at(dt(2026, 1, 13, 15, 59), fd) is Zone.OFFPEAK
    assert zone_at(dt(2026, 1, 13, 20, 59), fd) is Zone.PEAK
    assert zone_at(dt(2026, 1, 13, 21, 0), fd) is Zone.OFFPEAK


# --------------------------------------------------------------------------- #
# Free days: weekends + holidays (including the 24 Dec 2025 change)
# --------------------------------------------------------------------------- #


def test_weekend_is_all_offpeak():
    # 2026-01-17 is a Saturday: even at 17:00 (would be winter peak) it's cheap.
    fd = free_day(datetime(2026, 1, 17).date())
    assert zone_at(dt(2026, 1, 17, 17), fd) is Zone.OFFPEAK


def test_movable_holiday_corpus_christi():
    # Boze Cialo 2026 = 2026-06-04 (Thursday). Should be offpeak all day.
    d = datetime(2026, 6, 4).date()
    assert d in PL
    assert zone_at(dt(2026, 6, 4, 20), free_day(d)) is Zone.OFFPEAK


def test_christmas_eve_2024_is_not_free():
    # 24 Dec 2024 (Tuesday) was NOT yet a statutory day off -> normal zones.
    d = datetime(2024, 12, 24).date()
    assert d not in PL
    # 17:00 in winter on a workday -> peak.
    assert zone_at(dt(2024, 12, 24, 17), free_day(d)) is Zone.PEAK


def test_christmas_eve_2025_is_free():
    # 24 Dec 2025 onward IS a statutory day off -> offpeak all day.
    d = datetime(2025, 12, 24).date()
    assert d in PL
    assert zone_at(dt(2025, 12, 24, 17), free_day(d)) is Zone.OFFPEAK


# --------------------------------------------------------------------------- #
# next_boundary_after
# --------------------------------------------------------------------------- #


def test_next_boundary_simple():
    # Winter workday at 08:30 (MID); next change is end of mid at 13:00.
    nb = next_boundary_after(dt(2026, 1, 13, 8, 30), free_day)
    assert nb == dt(2026, 1, 13, 13, 0)


def test_next_boundary_crosses_midnight_into_weekend():
    # Friday 2026-01-16 23:30 (offpeak). Saturday is offpeak all day, so the
    # next *zone change* is not at midnight - it's Monday 07:00.
    nb = next_boundary_after(dt(2026, 1, 16, 23, 30), free_day)
    assert nb == dt(2026, 1, 19, 7, 0)  # Monday MID begins


# --------------------------------------------------------------------------- #
# block_start_at
# --------------------------------------------------------------------------- #


def test_block_start_mid_morning():
    # Winter workday 10:00 is MID, which began at 07:00.
    bs = block_start_at(dt(2026, 1, 13, 10, 0), free_day)
    assert bs == dt(2026, 1, 13, 7, 0)


def test_block_start_spans_long_weekend():
    # Saturday 2026-01-17 10:00 is offpeak; the block began Friday 21:00
    # (end of Friday's winter peak).
    bs = block_start_at(dt(2026, 1, 17, 10, 0), free_day)
    assert bs == dt(2026, 1, 16, 21, 0)


# --------------------------------------------------------------------------- #
# events_between (timeline / calendar source)
# --------------------------------------------------------------------------- #


def test_events_coalesce_and_clamp():
    # Window: winter Tuesday 14:00 -> 22:00.
    # Expected blocks: 14-16 offpeak, 16-21 peak, 21-22 offpeak.
    evs = events_between(dt(2026, 1, 13, 14), dt(2026, 1, 13, 22), free_day)
    assert [e["zone"] for e in evs] == [Zone.OFFPEAK, Zone.PEAK, Zone.OFFPEAK]
    assert evs[0]["start"] == dt(2026, 1, 13, 14)
    assert evs[0]["end"] == dt(2026, 1, 13, 16)
    assert evs[1]["end"] == dt(2026, 1, 13, 21)
    assert evs[-1]["end"] == dt(2026, 1, 13, 22)  # clamped to window end


def test_events_contiguous_no_gaps():
    evs = events_between(dt(2026, 7, 14, 0), dt(2026, 7, 15, 0), free_day)
    for a, b in zip(evs, evs[1:]):
        assert a["end"] == b["start"]
    assert evs[0]["start"] == dt(2026, 7, 14, 0)
    assert evs[-1]["end"] == dt(2026, 7, 15, 0)


def test_events_empty_when_end_not_after_start():
    assert events_between(dt(2026, 1, 13, 12), dt(2026, 1, 13, 12), free_day) == []


# --------------------------------------------------------------------------- #
# DST: the engine reads local .hour, so wall-clock zones stay aligned.
# --------------------------------------------------------------------------- #


def test_dst_spring_forward_zone_uses_wall_clock():
    # 2026-03-29 Europe/Warsaw springs forward 02:00 -> 03:00 (a Sunday, so it's
    # offpeak anyway, but verify no crash and correct classification).
    fd = free_day(datetime(2026, 3, 29).date())
    assert zone_at(dt(2026, 3, 29, 10), fd) is Zone.OFFPEAK  # Sunday


def test_dst_autumn_fallback_workday():
    # 2026-10-25 falls back (Sunday). Take the following Monday 2026-10-26
    # which is winter -> verify peak window at 17:00.
    d = datetime(2026, 10, 26).date()
    assert zone_at(dt(2026, 10, 26, 17), free_day(d)) is Zone.PEAK
