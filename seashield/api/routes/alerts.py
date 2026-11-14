from fastapi import APIRouter

router = APIRouter(tags=["alerts"])


@router.get("/alerts")
def list_alerts(pipeline: str | None = None) -> list[dict]:
    """Alerts from both pipelines ('unprotected' vs 'seashield') for the side-by-side view.

    TODO Phase 7: query table `alerts`.
    """
    return []
