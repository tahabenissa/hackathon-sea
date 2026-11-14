"""API entry point.  Run locally:  uvicorn seashield.api.main:app --reload"""

from fastapi import FastAPI

from seashield import __version__
from seashield.api.routes import alerts, attacks, buoys, health, incidents, measurements
from seashield.api.ws import router as ws_router

app = FastAPI(
    title="SeaShield AI API",
    version=__version__,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

for module in (health, buoys, measurements, incidents, alerts, attacks):
    app.include_router(module.router, prefix="/api")
app.include_router(ws_router)
