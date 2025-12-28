"""Session management REST endpoints for the Conductor API."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from phantom.conductor.models import (
    CreateSessionRequest,
    MessageRequest,
    SessionResponse,
)
from phantom.conductor.session_manager import SessionManager

if TYPE_CHECKING:
    from phantom.performer.scene import Scene

__all__ = ["router"]

router = APIRouter(prefix="/sessions", tags=["sessions"])


# ------------------------------------------------------------------
# Dependency
# ------------------------------------------------------------------


def _get_manager(request: Request) -> SessionManager:
    """Extract SessionManager from FastAPI application state.

    Args:
        request: Incoming HTTP request.

    Returns:
        The shared SessionManager instance.
    """
    manager: SessionManager = request.app.state.session_manager
    return manager


_ManagerDep = Annotated[SessionManager, Depends(_get_manager)]


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _scene_to_response(
    session_id: str,
    scene: Scene,
    message: str | None = None,
) -> SessionResponse:
    """Build a SessionResponse from a Scene.

    Args:
        session_id: The session identifier to embed.
        scene: The Scene instance to read state from.
        message: Optional human-readable status message.

    Returns:
        A populated SessionResponse.
    """
    return SessionResponse(
        session_id=session_id,
        state=scene.current_state,
        iterations=scene.iteration,
        budget_spent_usd=scene.budget_spent_usd,
        outputs=scene.outputs,
        message=message,
    )


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------


@router.post(
    "/",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new execution session",
)
async def create_session(
    request: CreateSessionRequest,
    manager: _ManagerDep,
) -> SessionResponse:
    """Create a new performer session and start execution.

    The session begins asynchronously; the returned state may
    still be ``LOADING`` or ``RUNNING`` immediately after creation.

    Args:
        request: Session creation parameters.
        manager: Injected SessionManager.

    Returns:
        SessionResponse with the newly created session state.

    Raises:
        HTTPException 422: When session parameters are invalid.
    """
    session_id = str(uuid.uuid4())
    try:
        scene = await manager.create_session(
            task=request.task,
            session_id=session_id,
            performer_name=request.performer_name,
            voice_name=request.voice_name,
            workspace_dir=request.workspace_dir,
            max_iterations=request.max_iterations,
            max_budget_usd=request.max_budget_usd,
        )
        return _scene_to_response(session_id, scene)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get(
    "/",
    response_model=list[dict],
    summary="List all active sessions",
)
async def list_sessions(
    manager: _ManagerDep,
) -> list[dict]:
    """Return a summary list of all active sessions.

    Args:
        manager: Injected SessionManager.

    Returns:
        List of session summary dicts.
    """
    return manager.list_sessions()


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Get session state",
)
async def get_session(
    session_id: str,
    manager: _ManagerDep,
) -> SessionResponse:
    """Return the current state of an existing session.

    Args:
        session_id: Session to query.
        manager: Injected SessionManager.

    Returns:
        SessionResponse with current state.

    Raises:
        HTTPException 404: When the session does not exist.
    """
    session = manager.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )
    return _scene_to_response(session_id, session.director.scene)


@router.post(
    "/{session_id}/messages",
    response_model=SessionResponse,
    summary="Send a message to a session",
)
async def send_message(
    session_id: str,
    request: MessageRequest,
    manager: _ManagerDep,
) -> SessionResponse:
    """Send a user message to a running or paused session.

    Args:
        session_id: Target session.
        request: Message content.
        manager: Injected SessionManager.

    Returns:
        Updated SessionResponse after the message is processed.

    Raises:
        HTTPException 404: When the session does not exist.
    """
    try:
        scene = await manager.send_message(session_id, request.content)
        return _scene_to_response(session_id, scene)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Stop and remove a session",
)
async def stop_session(
    session_id: str,
    manager: _ManagerDep,
) -> None:
    """Stop a running session and release its resources.

    Args:
        session_id: Session to terminate.
        manager: Injected SessionManager.

    Raises:
        HTTPException 404: When the session does not exist.
    """
    session = manager.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )
    await manager.stop_session(session_id)
