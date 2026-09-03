"""Calendar for Avfall & Återvinning Skaraborg pickups."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import CONF_ADDRESS, CONF_CITY
from .coordinator import AvfallKaraborgConfigEntry, AvfallKaraborgCoordinator
from .entity import AvfallKaraborgEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AvfallKaraborgConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the pickup calendar."""
    async_add_entities([AvfallKaraborgCalendar(entry.runtime_data)])


class AvfallKaraborgCalendar(AvfallKaraborgEntity, CalendarEntity):
    """All known upcoming pickups as all-day events.

    The backend only exposes the *next* pickup per bin type, so the calendar
    never looks further ahead than that.
    """

    _attr_translation_key = "pickups"
    _attr_icon = "mdi:calendar-check"

    def __init__(self, coordinator: AvfallKaraborgCoordinator) -> None:
        """Initialise the calendar."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_calendar"

    def _events(self) -> list[CalendarEvent]:
        """Build one all-day event per bin type."""
        entry = self.coordinator.config_entry
        location = ", ".join(
            part for part in (entry.data[CONF_ADDRESS], entry.data[CONF_CITY]) if part
        )
        return [
            CalendarEvent(
                summary=item.bin_type,
                start=item.pickup_date,
                end=item.pickup_date + timedelta(days=1),
                location=location,
            )
            for item in self.coordinator.data.bins
        ]

    @property
    def event(self) -> CalendarEvent | None:
        """The next pickup that has not passed yet."""
        today: date = dt_util.now().date()
        upcoming = [event for event in self._events() if event.start >= today]
        return min(upcoming, key=lambda event: event.start) if upcoming else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return the events falling inside the requested window."""
        start = dt_util.as_local(start_date).date()
        end = dt_util.as_local(end_date).date()
        return [
            event for event in self._events() if start <= event.start < end
        ]
