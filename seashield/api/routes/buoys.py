from fastapi import APIRouter

from seashield.common.registry import load_buoys
from seashield.config import get_settings

router = APIRouter(tags=["buoys"])


@router.get("/buoys")
def list_buoys() -> list[dict]:
    """Buoy registry (from config/buoys.yaml for now; DB table `buoys` in Phase 7)."""
    return [b.__dict__ for b in load_buoys(get_settings().buoys_file)]
