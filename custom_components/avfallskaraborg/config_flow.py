"""Config flow for Avfall & Återvinning Skaraborg."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .api import (
    AddressMatch,
    AvfallKaraborgApi,
    AvfallKaraborgError,
    AvfallKaraborgQueryTooShortError,
)
from .const import (
    CONF_ADDRESS,
    CONF_CITY,
    CONF_PLANT_ID,
    CONF_QUERY,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL_HOURS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_SEARCH_SCHEMA = vol.Schema({vol.Required(CONF_QUERY): TextSelector()})

# Keep the picker usable — a query like "Storgatan" matches hundreds of rows.
MAX_RESULTS = 100


def _unique_id(address: str, city: str) -> str:
    """Build a stable unique id.

    ``plant_id`` is a freshly encrypted blob on every search response, so it
    cannot identify an address across flows. The address itself can.
    """
    return f"{address.strip().casefold()}|{city.strip().casefold()}"


class AvfallKaraborgConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the address search and selection."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise flow state."""
        self._matches: list[AddressMatch] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a search string."""
        return await self._async_search_step("user", user_input)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let an existing entry point at a different address."""
        return await self._async_search_step("reconfigure", user_input)

    async def _async_search_step(
        self, step_id: str, user_input: dict[str, Any] | None
    ) -> ConfigFlowResult:
        """Run the search shared by the user and reconfigure steps."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api = AvfallKaraborgApi(async_get_clientsession(self.hass))
            try:
                matches = await api.async_search(user_input[CONF_QUERY])
            except AvfallKaraborgQueryTooShortError:
                errors["base"] = "query_too_short"
            except AvfallKaraborgError as err:
                _LOGGER.debug("Address search failed: %s", err)
                errors["base"] = "cannot_connect"
            else:
                if not matches:
                    errors["base"] = "no_results"
                else:
                    self._matches = matches[:MAX_RESULTS]
                    return await self.async_step_select()

        return self.async_show_form(
            step_id=step_id, data_schema=STEP_SEARCH_SCHEMA, errors=errors
        )

    async def async_step_select(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick one of the matched addresses."""
        if user_input is not None:
            match = next(
                (m for m in self._matches if m.plant_id == user_input[CONF_ADDRESS]),
                None,
            )
            if match is not None:
                data = {
                    CONF_ADDRESS: match.address,
                    CONF_CITY: match.city,
                    CONF_PLANT_ID: match.plant_id,
                }
                await self.async_set_unique_id(_unique_id(match.address, match.city))

                if self.source == SOURCE_RECONFIGURE:
                    reconfigure_entry = self._get_reconfigure_entry()
                    self._abort_if_unique_id_mismatch(reason="wrong_address")
                    return self.async_update_reload_and_abort(
                        reconfigure_entry, data=data
                    )

                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=match.label, data=data)

        options = [
            SelectOptionDict(value=match.plant_id, label=match.label)
            for match in self._matches
        ]
        return self.async_show_form(
            step_id="select",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): SelectSelector(
                        SelectSelectorConfig(
                            options=options, mode=SelectSelectorMode.DROPDOWN
                        )
                    )
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return AvfallKaraborgOptionsFlow()


class AvfallKaraborgOptionsFlow(OptionsFlow):
    """Allow tuning how often the backend is polled."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(
                data={CONF_UPDATE_INTERVAL: int(user_input[CONF_UPDATE_INTERVAL])}
            )

        current = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_HOURS
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_UPDATE_INTERVAL, default=current): NumberSelector(
                        NumberSelectorConfig(
                            min=1, max=48, step=1, mode=NumberSelectorMode.BOX
                        )
                    )
                }
            ),
        )
