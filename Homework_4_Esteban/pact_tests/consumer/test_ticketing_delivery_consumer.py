"""Async (RabbitMQ) message contract: **Ticketing** consumes the delivery
notification published by **Access Control** on the ``delivery_queue``.

This is a Pact *message* pact (not HTTP). Ticketing is the message **consumer**:
its RabbitMQ callback receives ``{"order_id": ..., "status": "DELIVERED"}`` and
marks the matching PAID order as DELIVERED. The test feeds the contracted
message to a faithful copy of that handler and asserts the transition, then
writes ``pacts/ticketing-accesscontrol.json``.

The handler below mirrors the callback in ``ticketing/main.py``
(``start_rabbitmq_consumer`` -> ``callback``).
"""

import os
from datetime import datetime

from pact import Like, MessageConsumer, Provider

PACT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pacts")


class _Order:
    """Minimal stand-in for ticketing/models.py::Order (fields the handler touches)."""

    def __init__(self, order_id: str, status: str) -> None:
        self.id = order_id
        self.status = status
        self.delivered_at = None


def handle_delivery_message(message: dict, orders: dict[str, _Order]) -> _Order | None:
    """Mirror of the RabbitMQ callback logic in ticketing/main.py."""
    order_id = message.get("order_id")
    if message.get("status") == "DELIVERED" and order_id:
        order = orders.get(order_id)
        if order and order.status in {"PAID", "DELIVERED"}:
            order.status = "DELIVERED"
            order.delivered_at = datetime.utcnow()
            return order
    return None


def test_ticketing_consumes_delivery_notification():
    pact = MessageConsumer("Ticketing").has_pact_with(
        Provider("AccessControl"),
        pact_dir=PACT_DIR,
    )

    (
        pact
        .given("a delivery confirmation is published for a paid order")
        .expects_to_receive("a delivery notification that an order was fulfilled")
        .with_content({"order_id": Like("order-pact-001"), "status": "DELIVERED"})
        .with_metadata({"contentType": "application/json"})
    )

    # The concrete message that Access Control publishes onto delivery_queue.
    incoming_message = {"order_id": "order-pact-001", "status": "DELIVERED"}
    orders = {"order-pact-001": _Order("order-pact-001", "PAID")}

    with pact:
        updated = handle_delivery_message(incoming_message, orders)

        assert updated is not None
        assert updated.status == "DELIVERED"
        assert updated.delivered_at is not None
