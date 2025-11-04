"""Base Signal class for the PhantomOrchestra event system."""

import dataclasses
import datetime
from dataclasses import dataclass, field
from enum import Enum, StrEnum
from typing import Any, ClassVar

__all__ = ["Signal", "SignalSource", "SignalType"]


class SignalSource(StrEnum):
    """Origin of a signal within the system."""

    PERFORMER = "performer"
    USER = "user"
    ENVIRONMENT = "environment"


class SignalType(StrEnum):
    """High-level classification of a signal."""

    DIRECTIVE = "directive"  # Actions emitted by a performer
    REPORT = "report"  # Observations returned to a performer


@dataclass
class Signal:
    """Abstract base for all signals flowing through PhantomOrchestra.

    Signals carry a monotonically increasing ``id`` assigned at
    broadcast time, an ISO-8601 ``timestamp``, the originating
    ``source``, and an optional ``cause`` (ID of the directive that
    triggered this signal).

    Subclasses should override the ``message`` property to provide a
    human-readable one-line summary suitable for logging.
    """

    INVALID_ID: ClassVar[int] = -1

    _id: int = field(default=-1, init=False, repr=False)
    _timestamp: str = field(default="", init=False, repr=False)
    _source: "SignalSource | None" = field(
        default=None, init=False, repr=False
    )
    _cause: "int | None" = field(default=None, init=False, repr=False)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def id(self) -> int:
        """Monotonically increasing signal identifier."""
        return self._id

    @id.setter
    def id(self, value: int) -> None:
        self._id = value

    @property
    def timestamp(self) -> str:
        """ISO-8601 UTC timestamp assigned at broadcast time."""
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value: str) -> None:
        self._timestamp = value

    @property
    def source(self) -> "SignalSource | None":
        """Origin of this signal."""
        return self._source

    @source.setter
    def source(self, value: "SignalSource | None") -> None:
        self._source = value

    @property
    def cause(self) -> "int | None":
        """ID of the directive that caused this signal, if any."""
        return self._cause

    @cause.setter
    def cause(self, value: "int | None") -> None:
        self._cause = value

    @property
    def message(self) -> str:
        """Human-readable one-line summary of this signal."""
        return f"{self.__class__.__name__}(id={self._id})"

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialise this signal to a JSON-compatible dictionary.

        Returns:
            Dictionary containing all public fields plus metadata
            fields (``_id``, ``_timestamp``, ``_source``, ``_cause``).
        """
        data: dict[str, Any] = {}

        # Emit metadata under their public names
        data["_id"] = self._id
        data["_timestamp"] = self._timestamp
        data["_source"] = (
            self._source.value if self._source is not None else None
        )
        data["_cause"] = self._cause
        data["_signal_class"] = self.__class__.__name__

        # Emit instance fields using dataclasses.fields() which
        # correctly excludes ClassVar declarations.
        for fdef in dataclasses.fields(self):
            fname = fdef.name
            if fname.startswith("_"):
                continue
            val = getattr(self, fname)
            if isinstance(val, Enum):
                data[fname] = val.value
            else:
                data[fname] = val

        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Signal":
        """Reconstruct a Signal from a serialised dictionary.

        Only populates fields that are declared on the concrete class.
        Metadata fields are restored separately.

        Args:
            data: Dictionary previously produced by ``to_dict()``.

        Returns:
            Populated instance of the calling class.
        """
        init_kwargs: dict[str, Any] = {}

        # dataclasses.fields() excludes ClassVar and init=False fields
        # correctly, avoiding injection of class-level constants.
        for fdef in dataclasses.fields(cls):  # type: ignore[arg-type]
            fname = fdef.name
            if fname.startswith("_") or not fdef.init:
                continue
            if fname in data:
                init_kwargs[fname] = data[fname]

        instance = cls(**init_kwargs)

        # Restore metadata
        instance._id = data.get("_id", Signal.INVALID_ID)
        instance._timestamp = data.get("_timestamp", "")
        raw_source = data.get("_source")
        instance._source = (
            SignalSource(raw_source) if raw_source is not None else None
        )
        instance._cause = data.get("_cause")

        return instance

    @staticmethod
    def _now_utc() -> str:
        """Return current UTC time as an ISO-8601 string."""
        return datetime.datetime.now(datetime.UTC).isoformat()
