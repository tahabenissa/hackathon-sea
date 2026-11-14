from fastapi import APIRouter

from seashield import __version__

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict[str, str]:
    # TODO Phase 7: add DB + MQTT connectivity, message rate, CPU/RAM
    return {"status": "ok", "version": __version__}
