"""Shared entity base for Avfall & Återvinning Skaraborg."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ADDRESS, CONF_CITY, DOMAIN
from .coordinator import AvfallKaraborgCoordinator


class AvfallKaraborgEntity(CoordinatorEntity[AvfallKaraborgCoordinator]):
    """Base entity tying everything to one address device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AvfallKaraborgCoordinator) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        address = entry.data[CONF_ADDRESS]
        city = entry.data[CONF_CITY]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            entry_type=DeviceEntryType.SERVICE,
            manufacturer="Avfall & Återvinning Skaraborg",
            name=f"{address}, {city}" if city else address,
            configuration_url=(
                "https://www.avfallskaraborg.se"
                "/sophamtning/se-tomningsdagar-for-sophamtning/"
            ),
        )
