"""The Tauron G13 integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN
from .coordinator import TauronG13Coordinator
from .frontend_registration import FrontendCardRegistration

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.CALENDAR,
]

# Marks that the bundled card's resource has been (or is being) registered, so
# it happens once regardless of entry reloads.
_CARD_REGISTERED = f"{DOMAIN}_card_registered"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tauron G13 from a config entry."""
    coordinator = TauronG13Coordinator(hass)
    await coordinator.async_start()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Reload when timeline-range options change so the sensor picks up the new span.
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    _async_register_card_once(hass)
    return True


@callback
def _async_register_card_once(hass: HomeAssistant) -> None:
    """Register the bundled Lovelace card exactly once, after HA has started.

    Deferred to EVENT_HOMEASSISTANT_STARTED so the Lovelace resource store is
    ready; guarded by a flag so entry reloads don't re-register it.
    """
    if hass.data.get(_CARD_REGISTERED):
        return
    hass.data[_CARD_REGISTERED] = True

    registration = FrontendCardRegistration(hass)

    if hass.is_running:
        hass.async_create_task(registration.async_register())
    else:
        hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STARTED,
            lambda _evt: hass.async_create_task(registration.async_register()),
        )


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: TauronG13Coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        coordinator.async_shutdown()
    return unload_ok
