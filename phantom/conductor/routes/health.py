"""Health check route for the Conductor API."""

from fastapi import APIRouter

from phantom.conductor.models import HealthResponse
from phantom.version import __version__

__all__ = ["router"]

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Return service health status.

    This route is intended as a lightweight liveness probe.
    It does not check downstream dependencies.

    Returns:
        HealthResponse with status ``"ok"``, version string, and
        a note that uptime is tracked at the application level.
    """
    return HealthResponse(
        status="ok",
        version=__version__,
        uptime_seconds=0.0,
    )
