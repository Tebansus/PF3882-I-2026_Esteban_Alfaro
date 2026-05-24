"""Consumer contract: **Access Control** (consumer) -> **Ticketing** (provider).

These tests exercise the Access Control service's view of the Ticketing API.
Access Control calls ``GET /orders/{id}`` to confirm an order is PAID before it
generates access tokens. Running them writes ``pacts/accesscontrol-ticketing.json``
which the Ticketing provider must later satisfy.
"""

from pact import EachLike, Like

from clients import TicketingClient


def test_fetch_paid_order_returns_order(ticketing_pact):
    """Access Control reads a PAID order (and its items) to mint tickets."""
    expected = {
        "id": "order-pact-001",
        "status": "PAID",
        "items": EachLike(
            {
                "event_id": Like("event-001"),
                "zone_name": Like("VIP Pit"),
                "price_at_moment": Like(150.0),
                "quantity": Like(2),
            }
        ),
    }

    (
        ticketing_pact
        .given("a paid order order-pact-001 exists")
        .upon_receiving("a request to fetch a paid order")
        .with_request("GET", "/orders/order-pact-001")
        .will_respond_with(200, body=expected)
    )

    with ticketing_pact:
        client = TicketingClient(ticketing_pact.uri)
        response = client.get_order("order-pact-001")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "PAID"
        assert body["items"][0]["quantity"] == 2
        assert body["items"][0]["zone_name"] == "VIP Pit"


def test_fetch_missing_order_returns_404(ticketing_pact):
    """Access Control must handle an unknown order id gracefully."""
    expected = {"detail": "Order not found"}

    (
        ticketing_pact
        .given("order order-missing does not exist")
        .upon_receiving("a request to fetch a non-existent order")
        .with_request("GET", "/orders/order-missing")
        .will_respond_with(404, body=expected)
    )

    with ticketing_pact:
        client = TicketingClient(ticketing_pact.uri)
        response = client.get_order("order-missing")

        assert response.status_code == 404
        assert response.json()["detail"] == "Order not found"
