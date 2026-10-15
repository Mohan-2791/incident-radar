from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter

from .db import Base, engine
from .loaders import make_loaders
from .schema import Context, schema
from .seed import seed_if_empty


async def get_context() -> Context:
    return Context(loaders=make_loaders())  # fresh loaders per request: batching without stale caches


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_if_empty()
    yield


app = FastAPI(title="Incident Radar", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(GraphQLRouter(schema, context_getter=get_context), prefix="/graphql")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
