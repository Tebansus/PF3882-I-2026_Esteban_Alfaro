
# Ticketing system
```mermaid
flowchart TD
    A["Access Control (GraphQL)"]
    A-->B["Ticketing Checkout (REST over FastApi)"]
    B-->C["Event Catalog (REST over FastApi)"]
```
- URL del servicio de Catalog: http://localhost:8001/docs
- URL del servicio de Ticketing: http://localhost:8002/docs
- URL del servicio de Access Control: http://localhost:8003/graphql
