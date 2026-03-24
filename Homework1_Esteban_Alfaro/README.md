# "EasyPass" Ticketing System - Bounded Contexts

Three bounded contexts communicating via APIs (synchronous) and events (asynchronous) to manage the entire lifecycle of a concert ticket: from discovery, through high traffic purchasing, to scanning at the venue gates.

## Table of Contents

- [Contexts and Documentation](#contexts-and-documentation)
- [Diagram: Context Interaction](#diagram-context-interaction)
  - [Event Flow (Sequence)](#event-flow-sequence)
- [Events by Context](#events-by-context)
- [Summary of Each Context](#summary-of-each-context)

---

## Contexts and Documentation

| Context | Responsibility | Documentation |
| :--- | :--- | :--- |
| **Event Catalog** | Managing the discovery and offering of concerts/tours | [01-event-catalog-context.md](01-event-catalog-context.md) |
| **Ticketing & Checkout** | Managing reservations and financial transactions | [02-ticketing-checkout-context.md](02-ticketing-checkout-context.md) |
| **Access Control** | Managing QR codes and venue entry | [03-access-control-context.md](03-access-control-context.md) |

---

## Diagram: Context Interaction

- **Solid lines**: API (Checkout queries the Catalog for availability and pricing).
- **Dotted lines**: Events (Asynchronous via an Event Bus / SQS / SNS).

```mermaid
flowchart TB
    subgraph Catalog["Event Catalog"]
        C_API[Query API]
        C_EV[Events: EventPublished, ZoneSoldOut]
    end
    subgraph Ticketing["Ticketing & Checkout"]
        T_Checkout[Reserve / Checkout]
        T_EV[Events: OrderPaid, ReservationExpired]
    end
    subgraph Access["Access Control"]
        A_Create[Generate Digital Ticket]
        A_EV[Events: TicketGenerated, AccessGranted]
    end
    
    C_API -->|Query event/pricing| T_Checkout
    C_EV -.->|Subscribed| T_Checkout
    T_EV -.->|OrderPaid| A_Create
    A_EV -.->|Subscribed| Ticketing
```

### Event Flow (Sequence)

```mermaid
sequenceDiagram
    participant Catalog as Event Catalog
    participant Ticketing as Ticketing & Checkout
    participant Access as Access Control
    participant Bus as Event Bus

    Catalog->>Bus: EventPublished(id, venue, zones)
    Ticketing->>Catalog: API: Get current pricing and availability
    Ticketing->>Ticketing: Lock inventory (5-min Reservation)
    Ticketing->>Bus: OrderPaid(orderId, zones, user)
    Bus->>Access: OrderPaid
    Access->>Access: Generate Digital QR Tickets
    Access->>Bus: TicketGenerated(orderId, qrCodes)
    Bus->>Ticketing: (Optional: Update status to Delivered)
```

---

## Events by Context

| Context | Emits | Consumes |
| :--- | :--- | :--- |
| **Catalog** | EventPublished, ZoneSoldOut, EventCancelled | OrderPaid, ReservationExpired (to update stock) |
| **Ticketing** | OrderCreated (Reservation), OrderPaid, ReservationExpired | EventPublished |
| **Access** | TicketGenerated, AccessGranted, AccessDenied | OrderPaid |

---

## Summary of Each Context

The core concept ("Ticket" / "User") drastically changes meaning depending on the context. This justifies the division into microservices:

| Concept | Event Catalog | Ticketing & Checkout | Access Control |
| :--- | :--- | :--- | :--- |
| **Ticket** | A price and a zone tier | A financial line item | A cryptographic QR Token |
| **User** | Fan / Browser | Payer / Cardholder | Attendee |
| **Status** | Available / Sold Out | Pending / Paid | Valid / Scanned |