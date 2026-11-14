from fastapi import APIRouter

router = APIRouter(tags=["attack simulation"])

SCENARIOS = ["tamper", "replay", "spike", "false_wind", "suppress", "drift"]


@router.get("/attacks/scenarios")
def scenarios() -> list[str]:
    return SCENARIOS


@router.post("/attacks/{scenario}")
def launch(scenario: str, buoy_id: str = "SS-B01") -> dict:
    """Trigger a SIMULATED attack from the dashboard's attack console.

    TODO Phase 8: forward to the attacker service; protect this endpoint
    (demo token) so strangers cannot trigger attacks on the public URL.
    """
    return {"scenario": scenario, "buoy_id": buoy_id, "launched": False}
