"""Consumer contract: **Ticketing** (consumer) -> **Catalog** (provider).

These tests exercise the Ticketing service's view of the Catalog API. Running
them starts a Pact mock server, records the expected request/response pairs,
and writes ``pacts/ticketing-catalog.json`` which the Catalog provider must
later satisfy.
"""

from pact import EachLike, Like

from clients import CatalogClient


def test_fetch_event_returns_event_with_zones(catalog_pact):
    """Ticketing fetches an event before checkout to read zone pricing."""
    expected = {
        "id": "event-001",
        "venue": Like("Allianz Parque"),
        "zones": EachLike(
            {
                "name": Like("VIP Pit"),
                "price": Like(150.0),
                "available": Like(180),
            }
        ),
    }

    (
        catalog_pact
        .given("event event-001 exists with availability in zone VIP Pit")
        .upon_receiving("a request to fetch event event-001")
        .with_request("GET", "/events/event-001")
        .will_respond_with(200, body=expected)
    )

    with catalog_pact:
        client = CatalogClient(catalog_pact.uri)
        response = client.get_event("event-001")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == "event-001"
        assert body["zones"][0]["name"] == "VIP Pit"
        assert body["zones"][0]["price"] == 150.0


def test_reserve_inventory_creates_reservation(catalog_pact):
    """During checkout Ticketing locks zone capacity in the Catalog."""
    request_body = {
        "id": "order-pact-001",
        "event_id": "event-001",
        "zone_name": "VIP Pit",
        "quantity": 2,
    }
    expected = {
        "id": "order-pact-001",
        "event_id": "event-001",
        "zone_name": "VIP Pit",
        "quantity": 2,
        "status": "RESERVED",
    }

    (
        catalog_pact
        .given("event event-001 exists with availability in zone VIP Pit")
        .upon_receiving("a request to reserve inventory for an order")
        .with_request(
            "POST",
            "/inventory/reservations",
            body=request_body,
            headers={"Content-Type": "application/json"},
        )
        .will_respond_with(201, body=expected)
    )

    with catalog_pact:
        client = CatalogClient(catalog_pact.uri)
        response = client.reserve_inventory(
            reservation_id="order-pact-001",
            event_id="event-001",
            zone_name="VIP Pit",
            quantity=2,
        )

        assert response.status_code == 201
        assert response.json()["status"] == "RESERVED"


def test_confirm_reservation_after_payment(catalog_pact):
    """When an order is paid, Ticketing confirms the held reservation."""
    expected = {
        "id": "order-pact-001",
        "event_id": "event-001",
        "zone_name": "VIP Pit",
        "quantity": 2,
        "status": "CONFIRMED",
    }

    (
        catalog_pact
        .given("a reservation order-pact-001 is held for event event-001")
        .upon_receiving("a request to confirm a held reservation")
        .with_request("POST", "/inventory/reservations/order-pact-001/confirm")
        .will_respond_with(200, body=expected)
    )

    with catalog_pact:
        client = CatalogClient(catalog_pact.uri)
        response = client.confirm_reservation("order-pact-001")

        assert response.status_code == 200
        assert response.json()["status"] == "CONFIRMED"


def test_release_reservation_on_expiry(catalog_pact):
    """When an order expires, Ticketing releases the held reservation."""
    expected = {
        "id": "order-pact-001",
        "event_id": "event-001",
        "zone_name": "VIP Pit",
        "quantity": 2,
        "status": "RELEASED",
    }

    (
        catalog_pact
        .given("a reservation order-pact-001 is held for event event-001")
        .upon_receiving("a request to release a held reservation")
        .with_request("POST", "/inventory/reservations/order-pact-001/release")
        .will_respond_with(200, body=expected)
    )

    with catalog_pact:
        client = CatalogClient(catalog_pact.uri)
        response = client.release_reservation("order-pact-001")

        assert response.status_code == 200
        assert response.json()["status"] == "RELEASED"


def test_fetch_missing_event_returns_404(catalog_pact):
    """Ticketing must handle an unknown event id gracefully."""
    expected = {"detail": "Event not found"}

    (
        catalog_pact
        .given("event nonexistent-event does not exist")
        .upon_receiving("a request to fetch a non-existent event")
        .with_request("GET", "/events/nonexistent-event")
        .will_respond_with(404, body=expected)
    )

    with catalog_pact:
        client = CatalogClient(catalog_pact.uri)
        response = client.get_event("nonexistent-event")

        assert response.status_code == 404
        assert response.json()["detail"] == "Event not found"
