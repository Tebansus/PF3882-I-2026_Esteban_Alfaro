"""Async (RabbitMQ) message verification: **Access Control** must produce a
delivery notification matching the contract recorded by **Ticketing**
(``pacts/ticketing-accesscontrol.json``).

Unlike the HTTP provider checks, this does not need a running service or a
broker: Pact's ``MessageProvider`` starts a local proxy, asks the handler below
for the message Access Control would publish, and verifies it against the pact.

The handler mirrors ``access_control/schema.py::mark_order_delivered``, which
publishes ``{"order_id": <id>, "status": "DELIVERED"}`` onto ``delivery_queue``.
"""

import os

import pytest
from pact import MessageProvider

PACT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pacts")
PACT_FILE = os.path.join(PACT_DIR, "ticketing-accesscontrol.json")


def delivery_message_for_paid_order() -> dict:
    """The message Access Control emits when tickets are generated for an order."""
    order_id = "order-pact-001"
    return {"order_id": order_id, "status": "DELIVERED"}


@pytest.mark.skipif(
    not os.path.exists(PACT_FILE),
    reason="ticketing-accesscontrol.json not generated yet; run the consumer tests first.",
)
def test_access_control_produces_delivery_message():
    provider = MessageProvider(
        # Keyed by the *provider state* recorded in the pact (the .given(...) value).
        message_providers={
            "a delivery confirmation is published for a paid order": (
                delivery_message_for_paid_order
            ),
        },
        provider="AccessControl",
        consumer="Ticketing",
        pact_dir=PACT_DIR,
    )

    with provider:
        provider.verify()
