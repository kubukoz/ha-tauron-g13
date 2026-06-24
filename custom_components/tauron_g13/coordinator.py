"""Coordinator: owns the holiday calendar, the free-day predicate, and the
no-poll scheduling that recomputes the zone exactly at each boundary."""

from __future__ import annotations

import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

import holidays

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.util import dt as dt_util

from .const import TIMEZONE
from .zones import (
    Zone,
    block_start_at,
    events_between,
    next_boundary_after,
    zone_at,
)

_LOGGER = logging.getLogger(__name__)


class TauronG13Coordinator:
    """Computes the current G13 zone and re-arms a timer at the next boundary.

    Entities subscribe via ``async_add_listener``; the coordinator calls every
    listener whenever the zone changes (i.e. at each boundary, on startup, and
    on HA timezone/clock events).
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._tz = ZoneInfo(TIMEZONE)
        # Built lazily and extended as years roll over.
        self._holidays = holidays.Poland(years=self._relevant_years())
        self._listeners: list[CALLBACK_TYPE] = []
        self._unsub_timer: CALLBACK_TYPE | None = None
        self.zone: Zone | None = None

    # -- public API used by entities ---------------------------------------- #

    @property
    def timezone(self) -> ZoneInfo:
        return self._tz

    def now(self) -> datetime:
        """Current time in the G13 schedule's timezone (Europe/Warsaw)."""
        return dt_util.utcnow().astimezone(self._tz)

    def is_free_day(self, d: date) -> bool:
        """Weekend or Polish public holiday."""
        if d.year not in self._holidays.years:
            # Extend the cached holiday set if we've crossed into a new year.
            self._holidays = holidays.Poland(years=self._relevant_years())
        return d.weekday() >= 5 or d in self._holidays

    def current_zone(self) -> Zone:
        return zone_at(self.now(), self.is_free_day(self.now().date()))

    def next_change(self) -> datetime:
        return next_boundary_after(self.now(), self.is_free_day)

    def block_start(self, when: datetime) -> datetime:
        return block_start_at(when.astimezone(self._tz), self.is_free_day)

    def upcoming(self, start: datetime, end: datetime) -> list[dict]:
        return events_between(
            start.astimezone(self._tz), end.astimezone(self._tz), self.is_free_day
        )

    @callback
    def async_add_listener(self, update_callback: CALLBACK_TYPE) -> CALLBACK_TYPE:
        """Register a listener; returns an unsubscribe callable."""
        self._listeners.append(update_callback)

        @callback
        def remove() -> None:
            if update_callback in self._listeners:
                self._listeners.remove(update_callback)

        return remove

    # -- lifecycle ---------------------------------------------------------- #

    async def async_start(self) -> None:
        self._recompute_and_reschedule()

    @callback
    def async_shutdown(self) -> None:
        if self._unsub_timer is not None:
            self._unsub_timer()
            self._unsub_timer = None

    # -- internals ---------------------------------------------------------- #

    def _relevant_years(self) -> range:
        # Cover last year through next year so cross-midnight / new-year lookups
        # always resolve without a rebuild mid-call.
        y = dt_util.utcnow().astimezone(ZoneInfo(TIMEZONE)).year
        return range(y - 1, y + 2)

    @callback
    def _recompute_and_reschedule(self, _now: datetime | None = None) -> None:
        self.zone = self.current_zone()
        for listener in self._listeners:
            listener()

        nxt = self.next_change()
        # async_track_point_in_time expects a tz-aware datetime; it handles the
        # conversion. Scheduling a single shot at the exact boundary means no
        # polling and no drift.
        if self._unsub_timer is not None:
            self._unsub_timer()
        self._unsub_timer = async_track_point_in_time(
            self.hass, self._recompute_and_reschedule, nxt
        )
        _LOGGER.debug("G13 zone=%s, next change at %s", self.zone, nxt.isoformat())
