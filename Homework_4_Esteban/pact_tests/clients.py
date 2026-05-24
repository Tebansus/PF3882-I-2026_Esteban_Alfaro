"""Thin HTTP clients used by the Pact *consumer* tests.

Each method mirrors exactly how the real consumer service calls its provider,
so the generated contract reflects production behaviour:

* ``CatalogClient``  -> mirrors ``ticketing/main.py`` (``fetch_event`` and
  ``reserve_inventory``), i.e. how the Ticketing service talks to Catalog.
* ``TicketingClient`` -> mirrors ``access_control/schema.py`` (``fetch_order``),
  i.e. how the Access Control service talks to Ticketing.

The consumer tests point these clients at the Pact mock server instead of the
real provider, so the requests they make become the recorded contract.
"""

from __future__ import annotations

import requests


class CatalogClient:
    """How the Ticketing service consumes the Catalog (Event Catalog) API."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def get_event(self, event_id: str) -> requests.Response:
        # Mirrors ticketing/main.py::fetch_event
        return requests.get(f"{self.base_url}/events/{event_id}", timeout=5)

    def reserve_inventory(
        self,
        reservation_id: str,
        event_id: str,
        zone_name: str,
        quantity: int,
    ) -> requests.Response:
        # Mirrors ticketing/main.py::reserve_inventory
        return requests.post(
            f"{self.base_url}/inventory/reservations",
            json={
                "id": reservation_id,
                "event_id": event_id,
                "zone_name": zone_name,
                "quantity": quantity,
            },
            timeout=5,
        )

    def confirm_reservation(self, reservation_id: str) -> requests.Response:
        # Mirrors ticketing/main.py::confirm_inventory (called when an order is paid)
        return requests.post(
            f"{self.base_url}/inventory/reservations/{reservation_id}/confirm",
            timeout=5,
        )

    def release_reservation(self, reservation_id: str) -> requests.Response:
        # Mirrors ticketing/main.py::release_inventory (called when an order expires)
        return requests.post(
            f"{self.base_url}/inventory/reservations/{reservation_id}/release",
            timeout=5,
        )


class TicketingClient:
    """How the Access Control service consumes the Ticketing API."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def get_order(self, order_id: str) -> requests.Response:
        # Mirrors access_control/schema.py::fetch_order
        return requests.get(f"{self.base_url}/orders/{order_id}", timeout=5)
