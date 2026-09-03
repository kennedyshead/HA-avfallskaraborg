"""Client for the Nova backend used by avfallskaraborg.se."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import (
    API_NEXT_PICKUP,
    API_SEARCH,
    API_TOKEN,
    APP_IDENTIFIER,
    MIN_QUERY_LENGTH,
)

_LOGGER = logging.getLogger(__name__)

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Authorization": f"Bearer {API_TOKEN}",
    "X-App-Identifier": APP_IDENTIFIER,
}

TIMEOUT = ClientTimeout(total=30)


class AvfallKaraborgError(Exception):
    """Base error for this integration."""


class AvfallKaraborgConnectionError(AvfallKaraborgError):
    """The backend could not be reached or returned an unexpected response."""


class AvfallKaraborgQueryTooShortError(AvfallKaraborgError):
    """The search query is shorter than the backend accepts."""


@dataclass(frozen=True, slots=True)
class AddressMatch:
    """One address returned by the search endpoint."""

    address: str
    city: str
    plant_id: str

    @property
    def label(self) -> str:
        """Human readable label, matching the website's own formatting."""
        return f"{self.address}, {self.city}"


@dataclass(frozen=True, slots=True)
class Bin:
    """The next pickup for a single bin type."""

    bin_type: str
    pickup_date: date
    formatted: str


@dataclass(frozen=True, slots=True)
class PickupInfo:
    """Next pickup data for one address."""

    address: str
    city: str
    bins: list[Bin]


class AvfallKaraborgApi:
    """Thin async wrapper around the two public endpoints."""

    def __init__(self, session: ClientSession) -> None:
        """Initialise the client with a shared aiohttp session."""
        self._session = session

    async def async_search(self, query: str) -> list[AddressMatch]:
        """Search for addresses matching ``query``."""
        query = query.strip()
        if len(query) < MIN_QUERY_LENGTH:
            raise AvfallKaraborgQueryTooShortError(query)

        payload = await self._request("GET", API_SEARCH, {"address": query})
        if not isinstance(payload, dict):
            raise AvfallKaraborgConnectionError("Unexpected search response")

        matches: list[AddressMatch] = []
        # The response is keyed by city, each holding a list of addresses.
        for entries in payload.values():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                plant_id = entry.get("plant_number")
                address = entry.get("address")
                if not plant_id or not address:
                    continue
                matches.append(
                    AddressMatch(
                        address=address,
                        city=entry.get("zip_city") or "",
                        plant_id=plant_id,
                    )
                )
        return matches

    async def async_next_pickup(self, plant_id: str) -> PickupInfo:
        """Fetch the next pickup per bin type for one address."""
        payload = await self._request("POST", API_NEXT_PICKUP, {"plant_id": plant_id})
        if not isinstance(payload, dict) or "address" not in payload:
            raise AvfallKaraborgConnectionError("Unexpected pickup response")

        bins: list[Bin] = []
        for entry in payload.get("bins") or []:
            raw_date = entry.get("pickup_date")
            bin_type = entry.get("type")
            if not raw_date or not bin_type:
                continue
            try:
                pickup_date = date.fromisoformat(raw_date)
            except ValueError:
                _LOGGER.warning("Skipping bin %s with unparsable date %s", bin_type, raw_date)
                continue
            bins.append(
                Bin(
                    bin_type=bin_type,
                    pickup_date=pickup_date,
                    formatted=entry.get("formatted") or raw_date,
                )
            )

        bins.sort(key=lambda item: (item.pickup_date, item.bin_type))
        return PickupInfo(
            address=payload.get("address") or "",
            city=payload.get("city") or "",
            bins=bins,
        )

    async def _request(self, method: str, url: str, params: dict[str, str]):
        """Perform a request and return the decoded JSON body."""
        try:
            response = await self._session.request(
                method, url, params=params, headers=HEADERS, timeout=TIMEOUT
            )
            response.raise_for_status()
            # The backend serves JSON with a text/plain-ish content type at times.
            return await response.json(content_type=None)
        except ClientError as err:
            raise AvfallKaraborgConnectionError(f"Error talking to {url}: {err}") from err
        except (TimeoutError, ValueError) as err:
            raise AvfallKaraborgConnectionError(f"Bad response from {url}: {err}") from err
