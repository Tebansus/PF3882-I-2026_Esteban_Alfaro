import os
from datetime import datetime
from pathlib import Path as FilePath
from uuid import uuid4

import requests
from fastapi import FastAPI, HTTPException, Path, status
from dotenv import load_dotenv

from correlation import (
    CorrelationIdMiddleware,
    configure_logging,
    install_requests_propagation,
)
from models import CheckoutRequest, Order, OrderItem


load_dotenv(FilePath(__file__).with_name(".env"))

CATALOG_SERVICE_URL = os.getenv("CATALOG_SERVICE_URL", "http://localhost:8001")

app = FastAPI(
    title="EasyPass Ticketing API",
    description="Bounded context responsible for checkout, reservations, and payment status.",
    version="1.0.0",
)

# --- Correlation IDs (cross-cutting; see correlation.py). Business logic below
# is untouched: the middleware captures/echoes the X-Correlation-ID header, the
# requests patch propagates it to Catalog, and logging records it. ---
configure_logging()
install_requests_propagation()
app.add_middleware(CorrelationIdMiddleware)


ORDERS: list[Order] = []


def find_order(order_id: str) -> Order | None:
    return next((order for order in ORDERS if order.id == order_id), None)


def fetch_event(event_id: str) -> dict:
    try:
        response = requests.get(f"{CATALOG_SERVICE_URL}/events/{event_id}", timeout=5)
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Catalog service is unavailable",
        ) from exc

    if response.status_code == status.HTTP_404_NOT_FOUND:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if not response.ok:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Catalog service returned an unexpected response",
        )

    return response.json()


def reserve_inventory(order_id: str, payload: CheckoutRequest) -> None:
    try:
        response = requests.post(
            f"{CATALOG_SERVICE_URL}/inventory/reservations",
            json={
                "id": order_id,
                "event_id": payload.event_id,
                "zone_name": payload.zone_name,
                "quantity": payload.quantity,
            },
            timeout=5,
        )
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Catalog inventory service is unavailable",
        ) from exc

    if response.status_code == status.HTTP_409_CONFLICT:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Insufficient inventory")
    if response.status_code == status.HTTP_404_NOT_FOUND:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog resource not found")
    if not response.ok:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Catalog inventory service returned an unexpected response",
        )


def confirm_inventory(order_id: str) -> None:
    try:
        response = requests.post(
            f"{CATALOG_SERVICE_URL}/inventory/reservations/{order_id}/confirm",
            timeout=5,
        )
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Catalog inventory service is unavailable",
        ) from exc

    if not response.ok:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Catalog inventory confirmation failed",
        )


def release_inventory(order_id: str) -> None:
    try:
        response = requests.post(
            f"{CATALOG_SERVICE_URL}/inventory/reservations/{order_id}/release",
            timeout=5,
        )
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Catalog inventory service is unavailable",
        ) from exc

    if not response.ok:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Catalog inventory release failed",
        )


def find_zone(event: dict, zone_name: str) -> dict | None:
    return next((zone for zone in event.get("zones", []) if zone.get("name") == zone_name), None)


@app.get(
    "/orders",
    response_model=list[Order],
    tags=["Orders"],
    summary="List all orders",
    description="Return all in-memory orders created through checkout.",
)
def list_orders() -> list[Order]:
    return ORDERS


@app.get(
    "/orders/{order_id}",
    response_model=Order,
    tags=["Orders"],
    summary="Get an order by ID",
    description="Return one order from the ticketing context.",
)
def get_order(
    order_id: str = Path(..., description="Unique order identifier."),
) -> Order:
    order = find_order(order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@app.post(
    "/checkout",
    response_model=Order,
    status_code=status.HTTP_201_CREATED,
    tags=["Checkout"],
    summary="Create an order from checkout",
    description="Validate the event and zone against Catalog, then create an order with captured pricing.",
)
def checkout(payload: CheckoutRequest) -> Order:
    event = fetch_event(payload.event_id)
    zone = find_zone(event, payload.zone_name)
    if zone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found for event")

    price = float(zone["price"])
    order_id = f"order-{uuid4()}"
    reserve_inventory(order_id, payload)

    order = Order(
        id=order_id,
        customer_id=payload.customer_id,
        status="CREATED",
        total=price * payload.quantity,
        items=[
            OrderItem(
                event_id=payload.event_id,
                zone_name=payload.zone_name,
                price_at_moment=price,
                quantity=payload.quantity,
            )
        ],
        created_at=datetime.utcnow(),
        delivered_at=None,
    )
    ORDERS.append(order)
    return order


@app.post(
    "/orders/{order_id}/pay",
    response_model=Order,
    tags=["Orders"],
    summary="Mark an order as paid",
    description="Transition an order from CREATED to PAID.",
)
def pay_order(
    order_id: str = Path(..., description="Unique order identifier."),
) -> Order:
    order = find_order(order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order.status != "CREATED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CREATED orders can be paid",
        )

    confirm_inventory(order.id)
    order.status = "PAID"
    return order


@app.post(
    "/orders/{order_id}/expire",
    response_model=Order,
    tags=["Orders"],
    summary="Expire a pending order",
    description="Release locked inventory and mark the order as EXPIRED when payment is not completed.",
)
def expire_order(
    order_id: str = Path(..., description="Unique order identifier."),
) -> Order:
    order = find_order(order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status != "CREATED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CREATED orders can be expired",
        )

    release_inventory(order.id)
    order.status = "EXPIRED"
    return order


@app.post(
    "/orders/{order_id}/deliver",
    response_model=Order,
    tags=["Orders"],
    summary="Mark an order as delivered",
    description="Internal integration endpoint used by Access Control after digital tickets are generated.",
)
def deliver_order(
    order_id: str = Path(..., description="Unique order identifier."),
) -> Order:
    order = find_order(order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status not in {"PAID", "DELIVERED"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PAID orders can be delivered",
        )

    order.status = "DELIVERED"
    order.delivered_at = datetime.utcnow()
    return order