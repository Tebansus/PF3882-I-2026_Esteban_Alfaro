from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from schema import schema


app = FastAPI(
    title="EasyPass Access Control API",
    description="Bounded context responsible for ticket generation and gate validation.",
    version="1.0.0",
)

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