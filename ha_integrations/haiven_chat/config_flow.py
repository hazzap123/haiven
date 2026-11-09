"""Pick which existing Anthropic entry's key Haiven Chat reuses."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.selector import SelectOptionDict, SelectSelector, SelectSelectorConfig

from .const import CONF_ANTHROPIC_ENTRY_ID, DOMAIN


class HaivenChatConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entries = self.hass.config_entries.async_entries("anthropic")
        if not entries:
            return self.async_abort(reason="no_anthropic")
        if user_input is not None:
            return self.async_create_entry(title="Haiven Chat", data=user_input)
        options = [SelectOptionDict(value=e.entry_id, label=e.title) for e in entries]
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ANTHROPIC_ENTRY_ID, default=options[0]["value"]): SelectSelector(
                        SelectSelectorConfig(options=options)
                    )
                }
            ),
        )
