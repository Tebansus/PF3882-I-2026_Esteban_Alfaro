from datetime import datetime

from pydantic import BaseModel, Field


class Venue(BaseModel):
    id: str = Field(..., description="Unique identifier for the venue.")
    name: str = Field(..., description="Public name of the venue.")
    city: str = Field(..., description="City where the venue is located.")
    total_capacity: int = Field(..., ge=0, description="Total capacity available across the venue.")


class Zone(BaseModel):
    id: str = Field(..., description="Unique identifier for the venue zone.")
    name: str = Field(..., description="Commercial name of the zone.")
    price: float = Field(..., ge=0, description="Base ticket price for this zone.")
    total_capacity: int = Field(..., ge=0, description="Maximum capacity for the zone.")
    available: int = Field(..., ge=0, description="Remaining tickets available in the zone.")
    reserved: int = Field(0, ge=0, description="Tickets temporarily locked for pending orders.")


class ZoneCreate(BaseModel):
    id: str = Field(..., description="Unique identifier for the venue zone.")
    name: str = Field(..., description="Commercial name of the zone.")
    price: float = Field(..., ge=0, description="Base ticket price for this zone.")
    total_capacity: int = Field(..., ge=0, description="Maximum capacity for the zone.")
    available: int = Field(..., ge=0, description="Remaining tickets available in the zone.")


class Event(BaseModel):
    id: str = Field(..., description="Unique identifier for the event.")
    lineup: list[str] = Field(..., description="Artists performing at the event.")
    venue_id: str = Field(..., description="Venue identifier where the event takes place.")
    venue: str = Field(..., description="Venue where the event takes place.")
    date_time: datetime = Field(..., description="Scheduled date and time for the event.")
    zones: list[Zone] = Field(..., description="Available sale zones for the event.")


class EventCreate(BaseModel):
    id: str = Field(..., description="Unique identifier for the event.")
    lineup: list[str] = Field(..., description="Artists performing at the event.")
    venue_id: str = Field(..., description="Venue identifier where the event takes place.")
    venue: str = Field(..., description="Venue where the event takes place.")
    date_time: datetime = Field(..., description="Scheduled date and time for the event.")
    zones: list[ZoneCreate] = Field(..., description="Available sale zones for the event.")


class InventoryReservation(BaseModel):
    id: str = Field(..., description="Unique identifier for the reservation record.")
    event_id: str = Field(..., description="Event identifier associated with the reservation.")
    zone_name: str = Field(..., description="Zone reserved for the order.")
    quantity: int = Field(..., ge=1, description="Number of tickets reserved.")
    status: str = Field(..., description="Reservation lifecycle state.")


class InventoryReservationCreate(BaseModel):
    id: str = Field(..., description="Reservation identifier, usually matching the order ID.")
    event_id: str = Field(..., description="Event identifier associated with the reservation.")
    zone_name: str = Field(..., description="Zone requested for the reservation.")
    quantity: int = Field(..., ge=1, description="Number of tickets to lock.")