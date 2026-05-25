from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from correlation import (
    CorrelationIdMiddleware,
    configure_logging,
    install_requests_propagation,
)
from schema import schema


app = FastAPI(
    title="EasyPass Access Control API",
    description="Bounded context responsible for ticket generation and gate validation.",
    version="1.0.0",
)

# --- Correlation IDs (cross-cutting; see correlation.py). Business logic and
# GraphQL resolvers are untouched: the middleware captures/echoes the
# X-Correlation-ID header on the /graphql HTTP request, the requests patch
# propagates it to Ticketing, and logging records it. ---
configure_logging()
install_requests_propagation()
app.add_middleware(CorrelationIdMiddleware)

graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")


@app.get(
    "/",
    tags=["Health"],
    summary="Access control service info",
    description="Simple entry point indicating the GraphQL endpoint location.",
)
def root() -> dict[str, str]:
    return {"message": "Access Control GraphQL API available at /graphql"}