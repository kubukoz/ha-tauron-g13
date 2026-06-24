"""Serve and auto-register the bundled Lovelace card.

The integration ships a pre-built ES module (``frontend/tauron-g13-timeline.js``)
and, in Lovelace *storage* mode, registers it as a dashboard resource so the
``custom:tauron-g13-timeline`` card is available with no manual setup. In YAML
mode HA owns the resource list, so the user adds one line themselves (documented
in the README).

Pattern follows the current core API: ``async_register_static_paths`` with
``StaticPathConfig`` (the non-deprecated path), and the Lovelace resource
collection for registration.
"""

from __future__ import annotations

import json
import logging
from functools import cache
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import CARD_FILENAME, CARD_URL_BASE

_LOGGER = logging.getLogger(__name__)


@cache
def _card_version() -> str:
    """Integration version, used as the resource cache-buster.

    Read from manifest.json so it can never drift from the released version;
    bumping the integration version forces browsers to reload the card.
    """
    manifest = Path(__file__).parent / "manifest.json"
    try:
        return json.loads(manifest.read_text())["version"]
    except (OSError, ValueError, KeyError):
        return "0"


class FrontendCardRegistration:
    """Registers the bundled card's static path and Lovelace resource (once)."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def async_register(self) -> None:
        await self._async_register_static_path()
        await self._async_register_resource()

    async def _async_register_static_path(self) -> None:
        """Expose the frontend/ directory under CARD_URL_BASE."""
        await self.hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    CARD_URL_BASE,
                    str(Path(__file__).parent / "frontend"),
                    cache_headers=False,
                )
            ]
        )

    async def _async_register_resource(self) -> None:
        """Add (or version-bump) the Lovelace resource in storage mode."""
        # hass.data[LOVELACE_DATA] holds a LovelaceData dataclass with
        # `.resource_mode` ("storage"/"yaml") and `.resources` (the collection).
        from homeassistant.components.lovelace.const import (
            LOVELACE_DATA,
            MODE_STORAGE,
        )

        lovelace = self.hass.data.get(LOVELACE_DATA)
        if lovelace is None:
            _LOGGER.warning("Lovelace not ready; G13 card resource not registered")
            return

        # In YAML mode the resource list is read-only; the user adds it manually.
        if lovelace.resource_mode != MODE_STORAGE:
            _LOGGER.info(
                "Lovelace resources in %s mode; add the G13 card manually: %s",
                lovelace.resource_mode,
                self._url(),
            )
            return

        resources = lovelace.resources
        # The storage collection loads lazily; ensure it's loaded before we read.
        if not resources.loaded:
            await resources.async_load()
            resources.loaded = True

        url = self._url()
        bare = f"{CARD_URL_BASE}/{CARD_FILENAME}"
        for item in resources.async_items():
            if item["url"].split("?")[0] == bare:
                if item["url"] != url:
                    await resources.async_update_item(
                        item["id"], {"res_type": "module", "url": url}
                    )
                return

        await resources.async_create_item({"res_type": "module", "url": url})
        _LOGGER.debug("Registered G13 timeline card resource: %s", url)

    @staticmethod
    def _url() -> str:
        # The ?v= cache-buster forces the browser to reload on version bumps.
        return f"{CARD_URL_BASE}/{CARD_FILENAME}?v={_card_version()}"
