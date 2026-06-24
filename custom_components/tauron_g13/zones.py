"""Pure, side-effect-free engine for the Tauron G13 tariff zones.

This module has NO Home Assistant imports on purpose: it is the part that has
to be correct, so it is trivially unit-testable in isolation.

G13 is a static, published three-zone schedule (not a market tariff). The zone
depends only on:
  * the season (summer: Apr 1 - Sep 30, winter: Oct 1 - Mar 31),
  * whether it is a "free day" (Sat/Sun or a Polish public holiday),
  * the local clock hour in Europe/Warsaw.

Zone hours (per the Tauron Dystrybucja G13 tariff):

  Winter (Oct 1 - Mar 31):
    peak     16:00-21:00
    mid      07:00-13:00
    offpeak  everything else (13:00-16:00, 21:00-07:00)

  Summer (Apr 1 - Sep 30):
    peak     19:00-22:00
    mid      07:00-13:00
    offpeak  everything else (13:00-19:00, 22:00-07:00)

On free days the whole day is offpeak.

All datetimes passed in MUST be timezone-aware in Europe/Warsaw so that DST
transitions are handled correctly by the caller's tzinfo.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from enum import Enum


class Zone(str, Enum):
    """A G13 tariff zone. Inherits from str so the value serializes cleanly."""

    PEAK = "peak"
    MID = "mid"
    OFFPEAK = "offpeak"


def is_summer(d: date) -> bool:
    """Summer season runs Apr 1 - Sep 30 inclusive."""
    return 4 <= d.month <= 9


def is_weekend(d: date) -> bool:
    """Saturday (5) or Sunday (6). Poland has no 'working Saturday' rule."""
    return d.weekday() >= 5


def zone_at(dt: datetime, is_free_day: bool) -> Zone:
    """Return the tariff zone in effect at ``dt``.

    ``is_free_day`` collapses the weekend/holiday logic into a single flag so
    this function stays free of any holiday-calendar dependency. The caller is
    expected to OR together weekend detection and a holiday lookup.
    """
    if is_free_day or is_weekend(dt.date()):
        return Zone.OFFPEAK

    hour = dt.hour
    if is_summer(dt.date()):
        if 19 <= hour < 22:
            return Zone.PEAK
        if 7 <= hour < 13:
            return Zone.MID
        return Zone.OFFPEAK

    # winter
    if 16 <= hour < 21:
        return Zone.PEAK
    if 7 <= hour < 13:
        return Zone.MID
    return Zone.OFFPEAK


def next_boundary_after(dt: datetime, free_day_fn) -> datetime:
    """Return the first instant strictly after ``dt`` at which the zone changes.

    ``free_day_fn`` maps a ``date`` to a bool (free day or not). We advance hour
    by hour - boundaries always land on whole local hours and on midnight (where
    the day type can change) - which is robust across DST because we step using
    the caller's tz-aware arithmetic and re-read ``.hour`` each step.

    A pure clock-walk is intentionally simple over clever interval math: zones
    only ever flip on the hour, so at most ~24 cheap comparisons are needed.
    """
    current = zone_at(dt, free_day_fn(dt.date()))

    # Step to the top of the next hour first, then hour by hour.
    probe = (dt.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
    # Guard against runaway loops. A boundary always exists soon, but a run of
    # free days (a long holiday weekend, e.g. Fri evening through a Mon holiday
    # into Tue 07:00) can span several days of uninterrupted offpeak. Cap well
    # above any realistic Polish holiday cluster.
    for _ in range(24 * 14):
        if zone_at(probe, free_day_fn(probe.date())) != current:
            return probe
        probe = probe + timedelta(hours=1)
    # Should be unreachable for a well-formed schedule.
    return probe


def block_start_at(dt: datetime, free_day_fn) -> datetime:
    """Return the instant at which the zone block containing ``dt`` began.

    Walks backward on whole hours until the zone differs, then returns the hour
    after that. Bounded to two weeks for the same long-holiday reason as
    ``next_boundary_after``.
    """
    current = zone_at(dt, free_day_fn(dt.date()))
    probe = dt.replace(minute=0, second=0, microsecond=0)
    last_same = probe
    for _ in range(24 * 14):
        if zone_at(probe, free_day_fn(probe.date())) != current:
            return last_same
        last_same = probe
        probe = probe - timedelta(hours=1)
    return last_same


def events_between(start: datetime, end: datetime, free_day_fn) -> list[dict]:
    """Coalesce consecutive same-zone hours into blocks over ``[start, end)``.

    Returns a list of ``{"start": dt, "end": dt, "zone": Zone}`` dicts suitable
    for a calendar / timeline view. The first block's ``start`` is clamped to
    ``start`` and the last block's ``end`` is clamped to ``end`` so the window
    is reported exactly as requested.
    """
    if end <= start:
        return []

    events: list[dict] = []
    block_start = start
    block_zone = zone_at(start, free_day_fn(start.date()))

    # Walk on hour boundaries; the zone can only change on the hour.
    probe = start.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    while probe < end:
        z = zone_at(probe, free_day_fn(probe.date()))
        if z != block_zone:
            events.append({"start": block_start, "end": probe, "zone": block_zone})
            block_start = probe
            block_zone = z
        probe = probe + timedelta(hours=1)

    events.append({"start": block_start, "end": end, "zone": block_zone})
    return events
