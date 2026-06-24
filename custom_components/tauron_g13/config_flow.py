"""Config flow for Tauron G13 - a single, field-less setup step."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN


class TauronG13ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow. There is nothing to configure: the zones are a
    fixed, published schedule, so setup is a single confirmation."""

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
