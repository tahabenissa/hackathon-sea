from typing import Literal

from fastapi import APIRouter

router = APIRouter(tags=["incidents"])


@router.get("/incidents")
def list_incidents(status: str | None = None) -> list[dict]:
    """Security incidents with evidence. TODO Phase 7: query table `incidents`."""
    return []


@router.post("/incidents/{incident_id}/review")
def review_incident(incident_id: int,
                    decision: Literal["CONFIRMED_ATTACK", "FALSE_POSITIVE"]) -> dict:
    """Human operator decision (fail-safe principle: a human makes the final call)."""
    # TODO Phase 7: update incident + release or discard the held alert
    return {"incident_id": incident_id, "decision": decision, "saved": False}
