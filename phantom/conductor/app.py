"""FastAPI application factory for PhantomOrchestra."""

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from phantom.conductor.models import HealthResponse
from phantom.conductor.routes import sessions
from phantom.conductor.session_manager import SessionManager
from phantom.conductor.websocket import WebSocketRelay
from phantom.score.loader import load_config
from phantom.toolkit.logging import configure_logging
from phantom.version import __version__

__all__ = ["ConductorApp", "create_app"]

logger = structlog.get_logger(__name__)

# Type alias exposed for import convenience
ConductorApp = FastAPI


def create_app(config_path: str | None = None) -> FastAPI:
    """Create and configure the PhantomOrchestra FastAPI application.

    Sets up CORS middleware, mounts all API routers, registers the
    WebSocket endpoint, and attaches shared state (SessionManager,
    OrchestraConfig) to ``app.state``.

    Args:
        config_path: Optional explicit path to a TOML config file.
            Falls back to the usual search order when None.

    Returns:
        A fully configured FastAPI application ready to be served.
    """
    configure_logging()
    config = load_config(config_path)

    start_time = time.time()
    manager = SessionManager(config)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "phantom_orchestra_starting",
            version=__version__,
        )
        yield
        logger.info("phantom_orchestra_stopping")

    app = FastAPI(
        title="PhantomOrchestra",
        description=("AI-driven autonomous task orchestration platform."),
        version=__version__,
        lifespan=lifespan,
    )

    # ------------------------------------------------------------------
    # Middleware
    # ------------------------------------------------------------------

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # Routers
    # ------------------------------------------------------------------

    app.include_router(sessions.router, prefix="/api/v1")

    # ------------------------------------------------------------------
    # Health endpoint (uses start_time captured in closure)
    # ------------------------------------------------------------------

    from fastapi import APIRouter

    health_router = APIRouter(
        prefix="/api/v1/health",
        tags=["health"],
    )

    @health_router.get("/", response_model=HealthResponse)
    async def get_health() -> HealthResponse:
        """Return current service health and uptime.

        Returns:
            HealthResponse with ``"ok"`` status, the application
            version, and elapsed seconds since startup.
        """
        return HealthResponse(
            status="ok",
            version=__version__,
            uptime_seconds=time.time() - start_time,
        )

    app.include_router(health_router)

    # ------------------------------------------------------------------
    # WebSocket endpoint
    # ------------------------------------------------------------------

    @app.websocket("/api/v1/sessions/{session_id}/ws")
    async def session_websocket(
        websocket: WebSocket,
        session_id: str,
    ) -> None:
        """Real-time signal stream for an active session.

        Accepts a WebSocket connection and relays all channel
        signals as JSON payloads.  Clients may send
        ``{"type": "message", "content": "..."}`` to inject user
        messages into the session.

        Args:
            websocket: Incoming WebSocket connection.
            session_id: Session whose signals to stream.
        """
        relay = WebSocketRelay(websocket, session_id, manager)
        await relay.connect()

    # ------------------------------------------------------------------
    # Shared application state
    # ------------------------------------------------------------------

    app.state.session_manager = manager
    app.state.config = config

    return app
