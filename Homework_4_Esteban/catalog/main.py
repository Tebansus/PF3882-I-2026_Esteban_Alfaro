from datetime import datetime

from fastapi import FastAPI, HTTPException, Path, status

from models import Event, EventCreate, InventoryReservation, InventoryReservationCreate, Venue, Zone


app = FastAPI(
    title="EasyPass Event Catalog API",
    description="Bounded context responsible for event discovery, venues, and base pricing.",
    version="1.0.0",
)


VENUES: list[Venue] = [
    Venue(id="venue-001", name="Allianz Parque", city="Sao Paulo", total_capacity=12000),
    Venue(id="venue-002", name="Movistar Arena", city="Santiago", total_capacity=8000),
]


EVENTS: list[Event] = [
    Event(
        id="event-001",
        lineup=["Offspring", "Sublime", "Rise Against"],
        venue_id="venue-001",
        venue="Allianz Parque",
        date_time=datetime.fromisoformat("2026-06-15T20:30:00"),
        zones=[
            Zone(
                id="zone-001",
                name="VIP Pit",
                price=150.0,
                total_capacity=500,
                available=180,
                reserved=0,
            ),
            Zone(
                id="zone-002",
                name="General Admission",
                price=80.0,
                total_capacity=5000,
                available=2210,
                reserved=0,
            ),
        ],
    ),
    Event(
        id="event-002",
        lineup=["Mon Laferte", "Los Bunkers", "Francisca Valenzuela"],
        venue_id="venue-002",
        venue="Movistar Arena",
        date_time=datetime.fromisoformat("2026-07-02T21:00:00"),
        zones=[
            Zone(
                id="zone-003",
                name="Front Stage",
                price=120.0,
                total_capacity=900,
                available=340,
                reserved=0,
            ),
            Zone(
                id="zone-004",
                name="Lower Bowl",
                price=65.0,
                total_capacity=2800,
                available=1260,
                reserved=0,
            ),
        ],
    ),
]

RESERVATIONS: list[InventoryReservation] = []


def find_event(event_id: str) -> Event | None:
    return next((event for event in EVENTS if event.id == event_id), None)


def find_venue(venue_id: str) -> Venue | None:
    return next((venue for venue in VENUES if venue.id == venue_id), None)


def find_zone(event: Event, zone_name: str) -> Zone | None:
    return next((zone for zone in event.zones if zone.name == zone_name), None)


def find_reservation(reservation_id: str) -> InventoryReservation | None:
    return next((reservation for reservation in RESERVATIONS if reservation.id == reservation_id), None)


@app.get(
    "/venues",
    response_model=list[Venue],
    tags=["Venues"],
    summary="List venues",
    description="Return the venues managed by the event catalog context.",
)
def list_venues() -> list[Venue]:
    return VENUES


@app.get(
    "/venues/{venue_id}",
    response_model=Venue,
    tags=["Venues"],
    summary="Get a venue by ID",
    description="Return a single venue with its total capacity.",
)
def get_venue(
    venue_id: str = Path(..., description="Unique venue identifier."),
) -> Venue:
    venue = find_venue(venue_id)
    if venue is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venue not found")
    return venue


@app.get(
    "/events",
    response_model=list[Event],
    tags=["Events"],
    summary="List all events",
    description="Return the complete catalog of published events with their configured zones.",
)
def list_events() -> list[Event]:
    return EVENTS


@app.get(
    "/events/{event_id}",
    response_model=Event,
    tags=["Events"],
    summary="Get an event by ID",
    description="Retrieve the detailed information for one event from the catalog.",
)
def get_event(
    event_id: str = Path(..., description="Unique event identifier."),
) -> Event:
    event = find_event(event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


@app.get(
    "/events/{event_id}/zones",
    response_model=list[Zone],
    tags=["Events"],
    summary="List zones for an event",
    description="Return only the available zones configured for a specific event.",
)
def get_event_zones(
    event_id: str = Path(..., description="Unique event identifier."),
) -> list[Zone]:
    event = find_event(event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event.zones


@app.post(
    "/events",
    response_model=Event,
    status_code=status.HTTP_201_CREATED,
    tags=["Events"],
    summary="Create a new event",
    description="Add a new event to the in-memory catalog database.",
)
def create_event(payload: EventCreate) -> Event:
    if find_event(payload.id) is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Event already exists")
    if find_venue(payload.venue_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venue not found")

    event = Event(**payload.model_dump())
    EVENTS.append(event)
    return event


@app.post(
    "/inventory/reservations",
    response_model=InventoryReservation,
    status_code=status.HTTP_201_CREATED,
    tags=["Inventory"],
    summary="Reserve inventory for an order",
    description="Lock zone capacity temporarily while Ticketing keeps the order pending payment.",
)
def reserve_inventory(payload: InventoryReservationCreate) -> InventoryReservation:
    if find_reservation(payload.id) is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reservation already exists")

    event = find_event(payload.event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    zone = find_zone(event, payload.zone_name)
    if zone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found for event")
    if zone.available < payload.quantity:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Insufficient inventory")

    zone.available -= payload.quantity
    zone.reserved += payload.quantity

    reservation = InventoryReservation(
        id=payload.id,
        event_id=payload.event_id,
        zone_name=payload.zone_name,
        quantity=payload.quantity,
        status="RESERVED",
    )
    RESERVATIONS.append(reservation)
    return reservation


@app.get(
    "/inventory/reservations/{reservation_id}",
    response_model=InventoryReservation,
    tags=["Inventory"],
    summary="Get a reservation by ID",
    description="Return one temporary inventory reservation.",
)
def get_reservation(
    reservation_id: str = Path(..., description="Unique reservation identifier."),
) -> InventoryReservation:
    reservation = find_reservation(reservation_id)
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    return reservation


@app.post(
    "/inventory/reservations/{reservation_id}/confirm",
    response_model=InventoryReservation,
    tags=["Inventory"],
    summary="Confirm a reservation after payment",
    description="Persist the reserved inventory consumption after Ticketing marks the order as paid.",
)
def confirm_reservation(
    reservation_id: str = Path(..., description="Unique reservation identifier."),
) -> InventoryReservation:
    reservation = find_reservation(reservation_id)
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    if reservation.status != "RESERVED":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reservation cannot be confirmed")

    event = find_event(reservation.event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    zone = find_zone(event, reservation.zone_name)
    if zone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found for event")

    zone.reserved -= reservation.quantity
    reservation.status = "CONFIRMED"
    return reservation


@app.post(
    "/inventory/reservations/{reservation_id}/release",
    response_model=InventoryReservation,
    tags=["Inventory"],
    summary="Release a reservation",
    description="Return locked inventory back to the zone when a reservation expires or is cancelled.",
)
def release_reservation(
    reservation_id: str = Path(..., description="Unique reservation identifier."),
) -> InventoryReservation:
    reservation = find_reservation(reservation_id)
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    if reservation.status != "RESERVED":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reservation cannot be released")

    event = find_event(reservation.event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    zone = find_zone(event, reservation.zone_name)
    if zone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found for event")

    zone.available += reservation.quantity
    zone.reserved -= reservation.quantity
    reservation.status = "RELEASED"
    return reservation


# ---------------------------------------------------------------------------
# Pact provider-state support (TEST ONLY)
#
# Activated only when the environment variable PACT_PROVIDER_STATES=true.
# Before replaying each interaction recorded by a consumer (Ticketing), the
# Pact provider verifier POSTs the desired "state" to this endpoint so the
# in-memory catalog can be reset to a deterministic baseline. This endpoint is
# never part of the production Catalog API and is excluded from the OpenAPI docs.
# ---------------------------------------------------------------------------
import copy as _copy
import os as _os

from fastapi import Request as _Request

# Snapshot of the seeded catalog captured at import time, before any mutation.
_SEEDED_EVENTS = _copy.deepcopy(EVENTS)


def _reset_catalog_to_baseline() -> None:
    """Restore the catalog to its freshly-seeded state (events + no reservations)."""
    EVENTS[:] = _copy.deepcopy(_SEEDED_EVENTS)
    RESERVATIONS.clear()


def _seed_held_reservation() -> None:
    """Lock 2 VIP Pit tickets under reservation 'order-pact-001' (status RESERVED).

    Used by the confirm/release contract interactions, which require an existing
    RESERVED reservation to act on.
    """
    event = find_event("event-001")
    zone = find_zone(event, "VIP Pit")
    zone.available -= 2
    zone.reserved += 2
    RESERVATIONS.append(
        InventoryReservation(
            id="order-pact-001",
            event_id="event-001",
            zone_name="VIP Pit",
            quantity=2,
            status="RESERVED",
        )
    )


def _apply_catalog_state(state: str | None) -> None:
    # Always start from a clean, deterministic baseline.
    _reset_catalog_to_baseline()
    # The confirm/release interactions additionally need a RESERVED reservation.
    if state and "reservation" in state.lower() and "held" in state.lower():
        _seed_held_reservation()


if _os.getenv("PACT_PROVIDER_STATES", "false").lower() == "true":

    @app.post("/_pact/provider_states", include_in_schema=False)
    async def setup_provider_state(request: _Request) -> dict[str, str | None]:
        try:
            payload = await request.json()
        except Exception:
            payload = {}

        state = payload.get("state") or payload.get("states")
        if isinstance(state, list):
            state = state[0] if state else None

        _apply_catalog_state(state)
        return {"result": state}