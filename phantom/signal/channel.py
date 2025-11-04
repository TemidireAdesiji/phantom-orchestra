"""Thread-safe pub/sub signal channel for PhantomOrchestra.

Signals are assigned a monotonic ID and ISO-8601 timestamp at
broadcast time, persisted via the configured :class:`SignalDepot`,
then dispatched to all registered subscribers on per-subscriber
thread pools to prevent one slow subscriber from blocking others.

Secret masking is applied recursively to signal content before any
subscriber callback is invoked.
"""

from __future__ import annotations

import dataclasses
import logging
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from enum import StrEnum

from phantom.signal.base import Signal, SignalSource
from phantom.signal.depot import SignalDepot

__all__ = ["ChannelSubscriber", "SignalChannel"]

logger = logging.getLogger(__name__)

_MAX_WORKERS_PER_SUBSCRIBER = 2


class ChannelSubscriber(StrEnum):
    """Well-known subscriber identities within the channel."""

    DIRECTOR = "director"
    STAGE = "stage"
    CONDUCTOR = "conductor"
    MEMORY = "memory"
    MAIN = "main"
    TEST = "test"


# Type alias for subscriber callbacks
_CallbackFn = Callable[[Signal], None]


class SignalChannel:
    """Thread-safe publish/subscribe bus for :class:`Signal` objects.

    Subscribers register named callbacks; each subscriber gets its own
    :class:`~concurrent.futures.ThreadPoolExecutor` so that a slow
    callback does not starve others.

    Secret values may be registered via :meth:`mask_secrets`; all
    registered secret strings are replaced with ``"<REDACTED>"`` in
    signal content before callbacks are invoked.

    Args:
        session_id: Unique identifier for the current session.
        depot: Persistence back-end for committed signals.
    """

    def __init__(
        self,
        session_id: str,
        depot: SignalDepot,
    ) -> None:
        self._session_id = session_id
        self._depot = depot
        self._lock = threading.Lock()
        self._next_id: int = max(depot.cursor + 1, 0)

        # {subscriber_id: {callback_id: callable}}
        self._subscribers: dict[
            ChannelSubscriber,
            dict[str, _CallbackFn],
        ] = {}

        # Per-subscriber thread pools
        self._executors: dict[ChannelSubscriber, ThreadPoolExecutor] = {}

        # Secrets to redact: {plain_text: "<REDACTED>"}
        self._secrets: dict[str, str] = {}
        self._closed: bool = False

    # ------------------------------------------------------------------
    # Subscription management
    # ------------------------------------------------------------------

    def subscribe(
        self,
        subscriber_id: ChannelSubscriber,
        callback: _CallbackFn,
        callback_id: str,
    ) -> None:
        """Register a callback for a given subscriber identity.

        Args:
            subscriber_id: The logical subscriber category.
            callback: Callable invoked with each broadcast signal.
            callback_id: Unique name for this callback within the
                subscriber; used for targeted unsubscription.
        """
        with self._lock:
            if subscriber_id not in self._subscribers:
                self._subscribers[subscriber_id] = {}
                self._executors[subscriber_id] = ThreadPoolExecutor(
                    max_workers=_MAX_WORKERS_PER_SUBSCRIBER,
                    thread_name_prefix=(f"channel-{subscriber_id.value}"),
                )
            self._subscribers[subscriber_id][callback_id] = callback
        logger.debug(
            "Subscribed %s/%s to channel %s",
            subscriber_id.value,
            callback_id,
            self._session_id,
        )

    def unsubscribe(
        self,
        subscriber_id: ChannelSubscriber,
        callback_id: str,
    ) -> None:
        """Remove a previously registered callback.

        Args:
            subscriber_id: The subscriber category.
            callback_id: The callback name to remove.
        """
        with self._lock:
            callbacks = self._subscribers.get(subscriber_id, {})
            callbacks.pop(callback_id, None)
            if not callbacks and subscriber_id in self._executors:
                self._executors[subscriber_id].shutdown(wait=False)
                del self._executors[subscriber_id]
                del self._subscribers[subscriber_id]
        logger.debug(
            "Unsubscribed %s/%s from channel %s",
            subscriber_id.value,
            callback_id,
            self._session_id,
        )

    # ------------------------------------------------------------------
    # Broadcasting
    # ------------------------------------------------------------------

    def broadcast(
        self,
        signal: Signal,
        source: SignalSource,
    ) -> None:
        """Assign ID + timestamp, persist, and notify all subscribers.

        The signal is mutated in-place with its ``id``, ``timestamp``,
        and ``source`` before any downstream operation.  Secret masking
        is applied to a shallow copy before callbacks receive it.

        Args:
            signal: The signal to broadcast.
            source: Origin of this signal.
        """
        if self._closed:
            logger.warning(
                "Attempted broadcast on closed channel %s",
                self._session_id,
            )
            return

        with self._lock:
            signal.id = self._next_id
            self._next_id += 1
            signal.timestamp = Signal._now_utc()
            signal.source = source

        # Persist before notifying subscribers
        try:
            self._depot.commit_signal(signal)
        except Exception as exc:
            logger.error(
                "Failed to commit signal id=%d: %s",
                signal.id,
                exc,
            )

        masked = self._apply_masking(signal)

        with self._lock:
            snapshot = {
                sub_id: dict(cbs) for sub_id, cbs in self._subscribers.items()
            }
            executors = dict(self._executors)

        for sub_id, callbacks in snapshot.items():
            executor = executors.get(sub_id)
            if executor is None:
                continue
            for cb_id, callback in callbacks.items():
                executor.submit(
                    self._safe_invoke,
                    callback,
                    masked,
                    sub_id,
                    cb_id,
                )

    @staticmethod
    def _safe_invoke(
        callback: _CallbackFn,
        signal: Signal,
        sub_id: ChannelSubscriber,
        cb_id: str,
    ) -> None:
        """Invoke a subscriber callback, logging any exceptions."""
        try:
            callback(signal)
        except Exception as exc:
            logger.exception(
                "Subscriber %s/%s raised an exception: %s",
                sub_id.value,
                cb_id,
                exc,
            )

    # ------------------------------------------------------------------
    # Secret masking
    # ------------------------------------------------------------------

    def mask_secrets(self, secrets: dict[str, str]) -> None:
        """Register secret strings for redaction before broadcasting.

        Each key in ``secrets`` whose value is non-empty will be
        replaced with ``"<REDACTED>"`` in signal content strings.

        Args:
            secrets: Mapping of ``{plain_text: label}``; the label is
                not currently used but reserved for future audit logging.
        """
        with self._lock:
            for plain, _label in secrets.items():
                if plain:
                    self._secrets[plain] = "<REDACTED>"

    def _apply_masking(self, signal: Signal) -> Signal:
        """Return the signal after redacting registered secrets.

        If no secrets are registered, returns the original signal
        object unmodified to avoid unnecessary copying.

        Args:
            signal: Signal to mask.

        Returns:
            The same signal (or a copy with secrets replaced).
        """
        with self._lock:
            secrets = dict(self._secrets)

        if not secrets:
            return signal

        # Walk public string fields and replace secrets in-place.
        # Use dataclasses.fields() to exclude ClassVar declarations.
        for fdef in dataclasses.fields(signal):
            fname = fdef.name
            if fname.startswith("_"):
                continue
            val = getattr(signal, fname, None)
            if not isinstance(val, str):
                continue
            masked = val
            for plain, replacement in secrets.items():
                masked = masked.replace(plain, replacement)
            if masked != val:
                setattr(signal, fname, masked)

        return signal

    # ------------------------------------------------------------------
    # Lifecycle & replay
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Shut down all subscriber thread pools gracefully."""
        with self._lock:
            self._closed = True
            executors = dict(self._executors)
            self._subscribers.clear()
            self._executors.clear()

        for executor in executors.values():
            executor.shutdown(wait=True)
        logger.info("SignalChannel %s closed.", self._session_id)

    def replay(
        self,
        start_id: int = 0,
        end_id: int | None = None,
    ) -> list[Signal]:
        """Retrieve persisted signals without re-broadcasting them.

        Useful for reconstructing session state on restart.

        Args:
            start_id: Inclusive lower bound on signal IDs.
            end_id: Inclusive upper bound; ``None`` means all signals
                up to the current cursor.

        Returns:
            List of Signal instances in ascending ID order.
        """
        return self._depot.fetch_signals(
            start_id=start_id,
            end_id=end_id,
        )
