"""Config flow for Tauron G13.

Setup itself is field-less - the zones are a fixed, published schedule. The one
thing worth tuning is how far back/ahead the dashboard `timeline` attribute
reaches, so that lives in an options flow you can open any time from the
integration's *Configure* button.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback

from .const import (
    CONF_TIMELINE_HOURS_AHEAD,
    CONF_TIMELINE_HOURS_BEHIND,
    DEFAULT_TIMELINE_HOURS_AHEAD,
    DEFAULT_TIMELINE_HOURS_BEHIND,
    DOMAIN,
    TIMELINE_MAX_HOURS_AHEAD,
    TIMELINE_MAX_HOURS_BEHIND,
)


class TauronG13ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow. Setup is a single confirmation; the tunable
    timeline range is exposed via the options flow below."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        # Only one instance makes sense.
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title="Tauron G13", data={})

        return self.async_show_form(step_id="user")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return TauronG13OptionsFlow()


class TauronG13OptionsFlow(OptionsFlow):
    """Lets the user set how many hours behind/ahead the timeline attribute spans."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        opts = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_TIMELINE_HOURS_BEHIND,
                    default=opts.get(
                        CONF_TIMELINE_HOURS_BEHIND, DEFAULT_TIMELINE_HOURS_BEHIND
                    ),
                ): vol.All(int, vol.Range(min=0, max=TIMELINE_MAX_HOURS_BEHIND)),
                vol.Required(
                    CONF_TIMELINE_HOURS_AHEAD,
                    default=opts.get(
                        CONF_TIMELINE_HOURS_AHEAD, DEFAULT_TIMELINE_HOURS_AHEAD
                    ),
                ): vol.All(int, vol.Range(min=1, max=TIMELINE_MAX_HOURS_AHEAD)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
