from fastapi import APIRouter

router = APIRouter(tags=["measurements"])


@router.get("/measurements")
def recent_measurements(buoy_id: str | None = None, limit: int = 200) -> list[dict]:
    """Latest measurements with their verdict. TODO Phase 7: query table `measurements`."""
    return []
