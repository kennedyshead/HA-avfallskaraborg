"""Sensors for Avfall & Återvinning Skaraborg."""

from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util, slugify

from .api import Bin
from .const import (
    ATTR_BIN_TYPE,
    ATTR_BINS,
    ATTR_DAYS_TO_PICKUP,
    ATTR_FORMATTED,
    BIN_ICONS,
    DEFAULT_BIN_ICON,
)
from .coordinator import AvfallKaraborgConfigEntry, AvfallKaraborgCoordinator
from .entity import AvfallKaraborgEntity


def _icon_for(bin_type: str) -> str:
    """Pick an icon for a bin type, which may combine two fractions.

    "Plast/Kartong" gets the plastic icon: the leading fraction wins, and a
    longer keyword breaks ties so "returpapper" beats "papper".
    """
    lowered = bin_type.casefold()
    best: tuple[int, int, str] | None = None
    for keyword, icon in BIN_ICONS.items():
        position = lowered.find(keyword)
        if position == -1:
            continue
        candidate = (position, -len(keyword), icon)
        if best is None or candidate[:2] < best[:2]:
            best = candidate
    return best[2] if best else DEFAULT_BIN_ICON


def _days_to(pickup_date: date) -> int:
    """Whole days from today until ``pickup_date`` in local time."""
    return (pickup_date - dt_util.now().date()).days


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AvfallKaraborgConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors for one address."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_new_bins() -> None:
        """Create a sensor for each bin type as it first appears."""
        new = [
            AvfallKaraborgBinSensor(coordinator, item.bin_type)
            for item in coordinator.data.bins
            if item.bin_type not in known
        ]
        known.update(item.bin_type for item in coordinator.data.bins)
        if new:
            async_add_entities(new)

    async_add_entities(
        [
            AvfallKaraborgNextPickupSensor(coordinator),
            AvfallKaraborgDaysToNextPickupSensor(coordinator),
        ]
    )
    _add_new_bins()
    # A household can gain a fraction (a new bin) between refreshes.
    entry.async_on_unload(coordinator.async_add_listener(_add_new_bins))


class AvfallKaraborgBinSensor(AvfallKaraborgEntity, SensorEntity):
    """Next pickup date for one bin type."""

    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator: AvfallKaraborgCoordinator, bin_type: str) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._bin_type = bin_type
        self._attr_name = bin_type
        self._attr_icon = _icon_for(bin_type)
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{slugify(bin_type)}"
        )

    @property
    def _bin(self) -> Bin | None:
        """The current data for this bin type, if still present."""
        return next(
            (b for b in self.coordinator.data.bins if b.bin_type == self._bin_type),
            None,
        )

    @property
    def available(self) -> bool:
        """Whether the bin is still part of the address' subscription."""
        return super().available and self._bin is not None

    @property
    def native_value(self) -> date | None:
        """The next pickup date."""
        item = self._bin
        return item.pickup_date if item else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Extra detail useful in automations and dashboards."""
        item = self._bin
        if item is None:
            return None
        return {
            ATTR_BIN_TYPE: item.bin_type,
            ATTR_DAYS_TO_PICKUP: _days_to(item.pickup_date),
            ATTR_FORMATTED: item.formatted,
        }


class AvfallKaraborgNextPickupSensor(AvfallKaraborgEntity, SensorEntity):
    """The earliest upcoming pickup across every bin type."""

    _attr_device_class = SensorDeviceClass.DATE
    _attr_translation_key = "next_pickup"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: AvfallKaraborgCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_next_pickup"

    @property
    def _next_bins(self) -> list[Bin]:
        """Every bin collected on the earliest upcoming date."""
        bins = self.coordinator.data.bins
        if not bins:
            return []
        earliest = min(item.pickup_date for item in bins)
        return [item for item in bins if item.pickup_date == earliest]

    @property
    def native_value(self) -> date | None:
        """The earliest pickup date."""
        upcoming = self._next_bins
        return upcoming[0].pickup_date if upcoming else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Which bins go out, and when."""
        upcoming = self._next_bins
        return {
            ATTR_BINS: [item.bin_type for item in upcoming],
            ATTR_DAYS_TO_PICKUP: (
                _days_to(upcoming[0].pickup_date) if upcoming else None
            ),
            ATTR_FORMATTED: upcoming[0].formatted if upcoming else None,
        }


class AvfallKaraborgDaysToNextPickupSensor(AvfallKaraborgEntity, SensorEntity):
    """Days remaining until the earliest upcoming pickup."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTime.DAYS
    _attr_translation_key = "days_to_next_pickup"
    _attr_icon = "mdi:calendar-range"

    def __init__(self, coordinator: AvfallKaraborgCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_days_to_next_pickup"

    @property
    def native_value(self) -> int | None:
        """Whole days until the next pickup; 0 means today."""
        bins = self.coordinator.data.bins
        if not bins:
            return None
        return _days_to(min(item.pickup_date for item in bins))
