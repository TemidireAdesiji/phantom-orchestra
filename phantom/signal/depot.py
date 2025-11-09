"""Signal persistence depot for PhantomOrchestra.

Each signal is stored as a JSON file named with a zero-padded 8-digit
ID under ``<session_id>/`` within the repository root.  A simple LRU
cache keeps recently accessed signals in memory to reduce I/O.
"""

from __future__ import annotations

import json
import logging
from collections import OrderedDict
from typing import TYPE_CHECKING, Any

from phantom.signal.base import Signal
from phantom.signal.codec import decode_signal, encode_signal

if TYPE_CHECKING:
    from phantom.vault.base import Repository

__all__ = ["SignalDepot"]

logger = logging.getLogger(__name__)

_ID_WIDTH = 8
_JSON_ENCODING = "utf-8"


def _signal_path(session_id: str, signal_id: int) -> str:
    """Return the repository path for a given signal.

    Args:
        session_id: Current session identifier.
        signal_id: Numeric signal ID.

    Returns:
        Repository-relative path string.
    """
    padded = str(signal_id).zfill(_ID_WIDTH)
    return f"{session_id}/{padded}.json"


class SignalDepot:
    """Durable signal store backed by a Repository.

    Signals are persisted as individual JSON files, one per signal.
    An in-memory LRU cache of configurable size avoids redundant
    deserialisation for recently accessed signals.

    Args:
        session_id: Unique identifier for the current session; used
            as the directory prefix within the repository.
        repository: Storage back-end implementing the
            :class:`~phantom.vault.base.Repository` interface.
        cache_size: Maximum number of decoded signals to hold in the
            in-memory LRU cache.
    """

    def __init__(
        self,
        session_id: str,
        repository: Repository,
        cache_size: int = 25,
    ) -> None:
        self._session_id = session_id
        self._repository = repository
        self._cache_size = cache_size
        # OrderedDict used as an LRU cache: key = signal ID
        self._cache: OrderedDict[int, Signal] = OrderedDict()
        self._cursor: int = self._recover_cursor()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _recover_cursor(self) -> int:
        """Scan persisted files to find the highest existing signal ID.

        Returns:
            The highest signal ID found, or -1 if none exist.
        """
        try:
            entries = self._repository.enumerate(self._session_id)
        except FileNotFoundError:
            return -1

        max_id = -1
        for entry in entries:
            # Entry is a filename like "00000042.json"
            stem = entry.rstrip(".json").split("/")[-1]
            try:
                sid = int(stem)
                if sid > max_id:
                    max_id = sid
            except ValueError:
                pass
        return max_id

    def _put_cache(self, signal: Signal) -> None:
        """Insert a signal into the LRU cache, evicting if necessary."""
        sid = signal.id
        if sid in self._cache:
            self._cache.move_to_end(sid)
            return
        self._cache[sid] = signal
        if len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def commit_signal(self, signal: Signal) -> None:
        """Persist a signal to the repository.

        The signal must already have a valid ID assigned (i.e. it
        should have been broadcast through a :class:`SignalChannel`
        before being committed directly, or have its ID set manually
        during testing).

        Args:
            signal: The signal instance to persist.
        """
        data: dict[str, Any] = encode_signal(signal)
        payload = json.dumps(data, ensure_ascii=False, indent=2)
        path = _signal_path(self._session_id, signal.id)
        self._repository.persist(path, payload)
        if signal.id > self._cursor:
            self._cursor = signal.id
        self._put_cache(signal)
        logger.debug(
            "Committed signal id=%d type=%s",
            signal.id,
            signal.__class__.__name__,
        )

    def fetch_signals(
        self,
        start_id: int = 0,
        end_id: int | None = None,
        limit: int | None = None,
    ) -> list[Signal]:
        """Retrieve a range of signals from the depot.

        Args:
            start_id: Inclusive lower bound of signal IDs to return.
            end_id: Inclusive upper bound; defaults to ``cursor``.
            limit: Maximum number of signals to return; ``None`` means
                no limit.

        Returns:
            List of Signal instances in ascending ID order.
        """
        upper = end_id if end_id is not None else self._cursor
        signals: list[Signal] = []

        for sid in range(start_id, upper + 1):
            if limit is not None and len(signals) >= limit:
                break

            # Check cache first
            if sid in self._cache:
                self._cache.move_to_end(sid)
                signals.append(self._cache[sid])
                continue

            path = _signal_path(self._session_id, sid)
            try:
                raw = self._repository.retrieve(path)
            except FileNotFoundError:
                continue

            try:
                data = json.loads(raw)
                signal = decode_signal(data)
            except Exception as exc:
                logger.warning(
                    "Failed to decode signal at %s: %s",
                    path,
                    exc,
                )
                continue

            self._put_cache(signal)
            signals.append(signal)

        return signals

    @property
    def cursor(self) -> int:
        """The highest signal ID currently persisted in this depot."""
        return self._cursor
