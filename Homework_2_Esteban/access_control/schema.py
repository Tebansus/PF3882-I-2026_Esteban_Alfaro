import os
from datetime import datetime
from pathlib import Path as FilePath
from uuid import uuid4

import requests
import strawberry
from dotenv import load_dotenv
from graphql import GraphQLError


load_dotenv(FilePath(__file__).with_name(".env"))

TICKETING_SERVICE_URL = os.environ["TICKETING_SERVICE_URL"]


@strawberry.type(description="Ticket access token used at venue entry points.")
class AccessToken:
    id: str
    order_id: str
    event_id: str
    qr_hash: str
    zone_name: str
    status: str
    scanned_at: datetime | None


TOKENS: list[AccessToken] = []


def find_ticket_by_qr(qr_hash: str) -> AccessToken | None:
    return next((token for token in TOKENS if token.qr_hash == qr_hash), None)


def find_tickets_by_order(order_id: str) -> list[AccessToken]:
    return [token for token in TOKENS if token.order_id == order_id]


def fetch_order(order_id: str) -> dict:
    try:
        response = requests.get(f"{TICKETING_SERVICE_URL}/orders/{order_id}", timeout=5)
    except requests.RequestException as exc:
        raise GraphQLError("Ticketing service is unavailable") from exc

    if response.status_code == 404:
        raise GraphQLError("Order not found")

    if not response.ok:
        raise GraphQLError("Ticketing service returned an unexpected response")

    return response.json()


def mark_order_delivered(order_id: str) -> None:
    try:
        response = requests.post(f"{TICKETING_SERVICE_URL}/orders/{order_id}/deliver", timeout=5)
    except requests.RequestException as exc:
        raise GraphQLError("Ticketing delivery update is unavailable") from exc

    if not response.ok:
        raise GraphQLError("Ticketing could not mark the order as DELIVERED")


@strawberry.type(description="Read operations for the access control bounded context.")
class Query:
    @strawberry.field(description="Return all generated tickets for a specific order.")
    def tickets(self, order_id: str) -> list[AccessToken]:
        return find_tickets_by_order(order_id)

    @strawberry.field(description="Return one ticket by its QR hash.")
    def ticket(self, qr_hash: str) -> AccessToken | None:
        return find_ticket_by_qr(qr_hash)


@strawberry.type(description="Write operations for ticket generation and gate scanning.")
class Mutation:
    @strawberry.mutation(description="Generate access tokens from a paid order fetched from Ticketing.")
    def generate_tickets(self, order_id: str) -> list[AccessToken]:
        existing_tokens = find_tickets_by_order(order_id)
        if existing_tokens:
            return existing_tokens

        order = fetch_order(order_id)
        if order.get("status") != "PAID":
            raise GraphQLError("Tickets can only be generated for PAID orders")

        items = order.get("items", [])
        if not items:
            raise GraphQLError("The order does not contain any items")

        generated_tokens: list[AccessToken] = []
        for item in items:
            quantity = int(item.get("quantity", 0))
            zone_name = item.get("zone_name", "Unknown Zone")
            event_id = item.get("event_id", "unknown-event")
            for _ in range(quantity):
                token = AccessToken(
                    id=f"token-{uuid4()}",
                    order_id=order_id,
                    event_id=event_id,
                    qr_hash=str(uuid4()),
                    zone_name=zone_name,
                    status="VALID",
                    scanned_at=None,
                )
                TOKENS.append(token)
                generated_tokens.append(token)

        mark_order_delivered(order_id)
        return generated_tokens

    @strawberry.mutation(description="Validate a ticket scan and detect duplicate access attempts.")
    def scan_ticket(self, qr_hash: str) -> AccessToken | None:
        token = find_ticket_by_qr(qr_hash)
        if token is None:
            return None

        if token.status == "VALID":
            token.status = "SCANNED"
            token.scanned_at = datetime.utcnow()
        elif token.status == "SCANNED":
            token.status = "DENIED"

        return token


schema = strawberry.Schema(query=Query, mutation=Mutation)