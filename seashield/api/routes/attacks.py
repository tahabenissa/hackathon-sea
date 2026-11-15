from fastapi import APIRouter, HTTPException

from seashield.api.live import SCENARIOS, hub

router = APIRouter(tags=["attack simulation"])


@router.get("/attacks/scenarios")
def scenarios() -> dict[str, dict[str, str]]:
    return SCENARIOS


@router.post("/attacks/{scenario}")
def launch(scenario: str, buoy_id: str = "SS-B01") -> dict:
    """Launch a SIMULATED attack on the live demo network (rate-limited)."""
    try:
        return hub.launch(scenario, buoy_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(429, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(409, str(exc)) from exc
