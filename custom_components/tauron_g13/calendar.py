"""Calendar entity: exposes G13 zone blocks as events for a timeline view.

The built-in Lovelace Calendar card renders these as a horizontal timeline, so
pointing it at this entity gives the "past 4h / next 12h in one strip" view
with no custom frontend code.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MAX_CALENDAR_DAYS, ZONE_LABELS
from .coordinator import TauronG13Coordinator
from .entity import TauronG13Entity


def _to_event(block: dict) -> CalendarEvent:
    zone = block["zone"].value
    return CalendarEvent(
        start=block["start"],
        end=block["end"],
        summary=ZONE_LABELS[zone],
        # Machine-readable zone in the description for cards/automations.
        description=zone,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: TauronG13Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TauronG13Calendar(coordinator, entry.entry_id)])


class TauronG13Calendar(TauronG13Entity, CalendarEntity):
    """Timeline of G13 zones, past and future."""

    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: TauronG13Coordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_calendar"
        self._attr_name = "Zones"

    @property
    def event(self) -> CalendarEvent | None:
        """The zone block currently in effect."""
        now = self.coordinator.now()
        start = self.coordinator.block_start(now)
        end = self.coordinator.next_change()
        zone = self.coordinator.current_zone()
        return _to_event({"start": start, "end": end, "zone": zone})

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return zone blocks intersecting the requested window."""
        # Clamp absurd windows so we never synthesize an unbounded list.
        max_end = start_date + timedelta(days=MAX_CALENDAR_DAYS)
        if end_date > max_end:
            end_date = max_end
        blocks = self.coordinator.upcoming(start_date, end_date)
        return [_to_event(b) for b in blocks]
