"""Constants for the Avfall & Återvinning Skaraborg integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "avfallskaraborg"

# The public web widget on avfallskaraborg.se talks to this Nova backend and
# ships these credentials in its client bundle. They are not user specific.
API_BASE: Final = "https://gullspang.avfallsapp.se/api/nova"
API_SEARCH: Final = f"{API_BASE}/v1/next-pickup/search"
API_NEXT_PICKUP: Final = f"{API_BASE}/v1/next-pickup/address"
APP_IDENTIFIER: Final = "70bae483-3268-4875-93f5-14f2274ec7cb"
API_TOKEN: Final = "J6lD4hVH8pRMQZeBSoCvtCZj1V0wvgg0QvBqSDTH9fce942d"

CONF_ADDRESS: Final = "address"
CONF_CITY: Final = "city"
CONF_PLANT_ID: Final = "plant_id"
CONF_QUERY: Final = "query"
CONF_UPDATE_INTERVAL: Final = "update_interval"

MIN_QUERY_LENGTH: Final = 3
DEFAULT_UPDATE_INTERVAL_HOURS: Final = 6

ATTR_BINS: Final = "bins"
ATTR_BIN_TYPE: Final = "bin_type"
ATTR_DAYS_TO_PICKUP: Final = "days_to_pickup"
ATTR_FORMATTED: Final = "formatted"

# Bin types are free text from the source and may be combined with a slash,
# e.g. "Plast/Kartong"; see _icon_for in sensor.py for how these are matched.
BIN_ICONS: Final[dict[str, str]] = {
    "brännbart": "mdi:trash-can",
    "restavfall": "mdi:trash-can",
    "matavfall": "mdi:food-apple",
    "trädgårdsavfall": "mdi:leaf",
    "plast": "mdi:bottle-soda-classic-outline",
    "kartong": "mdi:package-variant-closed",
    "papper": "mdi:newspaper-variant-multiple",
    "returpapper": "mdi:newspaper-variant-multiple",
    "tidning": "mdi:newspaper-variant-multiple",
    "glas": "mdi:bottle-wine",
    "metall": "mdi:recycle-variant",
    "slam": "mdi:water-pump",
    "latrin": "mdi:toilet",
}
DEFAULT_BIN_ICON: Final = "mdi:trash-can-outline"
