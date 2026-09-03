"""Data update coordinator for Avfall & Återvinning Skaraborg."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AvfallKaraborgApi, AvfallKaraborgError, PickupInfo
from .const import (
    CONF_PLANT_ID,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL_HOURS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

type AvfallKaraborgConfigEntry = ConfigEntry[AvfallKaraborgCoordinator]


class AvfallKaraborgCoordinator(DataUpdateCoordinator[PickupInfo]):
    """Poll the next pickup for a single address."""

    config_entry: AvfallKaraborgConfigEntry

    def __init__(self, hass: HomeAssistant, entry: AvfallKaraborgConfigEntry) -> None:
        """Initialise the coordinator."""
        hours = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_HOURS)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(hours=hours),
        )
        self.api = AvfallKaraborgApi(async_get_clientsession(hass))
        self._plant_id: str = entry.data[CONF_PLANT_ID]

    async def _async_update_data(self) -> PickupInfo:
        """Fetch the latest pickup data."""
        try:
            return await self.api.async_next_pickup(self._plant_id)
        except AvfallKaraborgError as err:
            raise UpdateFailed(str(err)) from err
