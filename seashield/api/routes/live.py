from fastapi import APIRouter

from seashield.api.live import hub

router = APIRouter(tags=["live"])


@router.get("/events")
def recent_events(limit: int = 200) -> list[dict]:
    """Latest engine events (verdict, evidence, both alert decisions, attack ground truth)."""
    return hub.snapshot(min(max(limit, 1), 400))


@router.get("/stats")
def stats() -> dict:
    """Running counters since the server started."""
    return hub.stats_snapshot()
