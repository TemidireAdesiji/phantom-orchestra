"""WebSocket endpoint for real-time session signal streaming."""

import asyncio
import json

import structlog
from fastapi import WebSocket, WebSocketDisconnect

from phantom.conductor.session_manager import SessionManager
from phantom.signal.base import Signal
from phantom.signal.channel import ChannelSubscriber
from phantom.signal.codec import encode_signal

__all__ = ["WebSocketRelay"]

logger = structlog.get_logger(__name__)


class WebSocketRelay:
    """Bridges a SignalChannel to a WebSocket connection.

    Subscribes to the session's SignalChannel as a CONDUCTOR
    subscriber and forwards every signal to the connected client
    as a JSON payload.  Incoming client messages of type
    ``"message"`` are forwarded to the session as user messages.

    Args:
        websocket: The FastAPI WebSocket connection.
        session_id: Session whose channel to subscribe to.
        manager: SessionManager used to look up the session.
    """

    def __init__(
        self,
        websocket: WebSocket,
        session_id: str,
        manager: SessionManager,
    ) -> None:
        self._websocket = websocket
        self._session_id = session_id
        self._manager = manager
        self._active = False
        self._callback_id = f"ws_{session_id}"

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Accept the WebSocket and begin relaying signals.

        Looks up the session; closes with code 4004 if not found.
        Subscribes to the session channel and enters a read loop
        until the client disconnects.
        """
        await self._websocket.accept()
        self._active = True

        session = self._manager.get_session(self._session_id)
        if session is None:
            await self._websocket.close(
                code=4004,
                reason="Session not found",
            )
            return

        # Subscribe to channel signals
        def on_signal(signal: Signal) -> None:
            if self._active:
                asyncio.create_task(  # noqa: RUF006
                    self._send_signal(signal)
                )

        session.channel.subscribe(
            ChannelSubscriber.CONDUCTOR,
            on_signal,
            self._callback_id,
        )

        logger.info(
            "websocket_connected",
            session_id=self._session_id,
        )

        try:
            await self._read_loop()
        except WebSocketDisconnect:
            pass
        finally:
            self._active = False
            # Unsubscribe if session still exists
            active = self._manager.get_session(self._session_id)
            if active is not None:
                active.channel.unsubscribe(
                    ChannelSubscriber.CONDUCTOR,
                    self._callback_id,
                )
            logger.info(
                "websocket_disconnected",
                session_id=self._session_id,
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _read_loop(self) -> None:
        """Poll the WebSocket for client messages.

        Uses a 1-second timeout so the loop can check
        ``self._active`` without blocking indefinitely.
        """
        while self._active:
            try:
                raw = await asyncio.wait_for(
                    self._websocket.receive_text(),
                    timeout=1.0,
                )
                await self._handle_client_message(raw)
            except TimeoutError:
                pass

    async def _send_signal(self, signal: Signal) -> None:
        """Encode and send a signal to the WebSocket client.

        Silently marks the relay inactive on send errors so the
        read loop can exit cleanly.

        Args:
            signal: Signal to encode and transmit.
        """
        if not self._active:
            return
        try:
            payload = encode_signal(signal)
            await self._websocket.send_json(payload)
        except Exception as exc:
            logger.warning(
                "websocket_send_failed",
                session_id=self._session_id,
                error=str(exc),
            )
            self._active = False

    async def _handle_client_message(
        self,
        raw: str,
    ) -> None:
        """Parse a raw client message and dispatch it.

        Expects a JSON object with a ``"type"`` field.  When
        ``type == "message"``, the ``"content"`` value is forwarded
        to the session manager as a user message.

        Args:
            raw: Raw text received from the WebSocket client.
        """
        try:
            data: dict = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning(
                "invalid_websocket_json",
                session_id=self._session_id,
                error=str(exc),
            )
            return

        if data.get("type") == "message":
            content = data.get("content", "").strip()
            if content:
                try:
                    await self._manager.send_message(self._session_id, content)
                except KeyError as exc:
                    logger.warning(
                        "websocket_message_dropped",
                        session_id=self._session_id,
                        error=str(exc),
                    )
