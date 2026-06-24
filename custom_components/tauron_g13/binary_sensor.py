"""Binary sensors for cheap / peak zones - convenient automation conditions."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import TauronG13Coordinator
from .entity import TauronG13Entity
from .zones import Zone


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: TauronG13Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            TauronG13IsCheap(coordinator, entry.entry_id),
            TauronG13IsPeak(coordinator, entry.entry_id),
        ]
    )


class TauronG13IsCheap(TauronG13Entity, BinarySensorEntity):
    """On during the off-peak (cheapest) zone - run flexible loads now."""

    _attr_icon = "mdi:cash-check"

    def __init__(self, coordinator: TauronG13Coordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_is_cheap"
        self._attr_name = "Is cheap"

    @property
    def is_on(self) -> bool:
        return self.coordinator.current_zone() is Zone.OFFPEAK


class TauronG13IsPeak(TauronG13Entity, BinarySensorEntity):
    """On during the afternoon peak (most expensive) zone - defer loads."""

    _attr_icon = "mdi:cash-remove"

    def __init__(self, coordinator: TauronG13Coordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_is_peak"
        self._attr_name = "Is peak"

    @property
    def is_on(self) -> bool:
        return self.coordinator.current_zone() is Zone.PEAK
