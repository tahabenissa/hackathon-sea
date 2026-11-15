"""API entry point.  Run locally:  uvicorn seashield.api.main:app --reload"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from seashield import __version__
from seashield.api.live import hub
from seashield.api.routes import alerts, attacks, buoys, health, incidents, live, measurements
from seashield.api.ws import router as ws_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    hub.start(asyncio.get_running_loop())
    yield
    hub.stop()


app = FastAPI(
    title="SeaShield AI API",
    version=__version__,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

for module in (health, buoys, live, measurements, incidents, alerts, attacks):
    app.include_router(module.router, prefix="/api")
app.include_router(ws_router)
