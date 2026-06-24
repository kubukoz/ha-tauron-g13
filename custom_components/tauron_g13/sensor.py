"""The current-zone sensor."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, ZONE_LABELS
from .coordinator import TauronG13Coordinator
from .entity import TauronG13Entity
from .zones import Zone, is_summer, zone_at


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: TauronG13Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TauronG13ZoneSensor(coordinator, entry.entry_id)])


class TauronG13ZoneSensor(TauronG13Entity, SensorEntity):
    """Current G13 zone: peak / mid / offpeak."""

    _attr_translation_key = "zone"
    _attr_icon = "mdi:transmission-tower"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [z.value for z in Zone]

    def __init__(self, coordinator: TauronG13Coordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_zone"
        self._attr_name = "Zone"

    @property
    def native_value(self) -> str:
        return self.coordinator.current_zone().value

    @property
    def extra_state_attributes(self) -> dict:
        now = self.coordinator.now()
        nxt = self.coordinator.next_change()
        # The zone that will be in effect right after the boundary.
        nz = zone_at(nxt, self.coordinator.is_free_day(nxt.date()))
        minutes = int((nxt - now).total_seconds() // 60)
        return {
            "label": ZONE_LABELS[self.coordinator.current_zone().value],
            "season": "summer" if is_summer(now.date()) else "winter",
            "is_free_day": self.coordinator.is_free_day(now.date()),
            "next_zone": nz.value,
            "next_change": nxt.isoformat(),
            "minutes_until_change": minutes,
        }
