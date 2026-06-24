"""Shared base entity: subscribes to the coordinator and groups under one device."""

from __future__ import annotations

from homeassistant.helpers.device_info import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .coordinator import TauronG13Coordinator


class TauronG13Entity(Entity):
    """Base for all G13 entities."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator: TauronG13Coordinator, entry_id: str) -> None:
        self.coordinator = coordinator
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="Tauron G13",
            manufacturer="Tauron",
            model="G13 tariff zones",
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
