"""In-memory storage repository for PhantomOrchestra.

Useful for tests and short-lived sessions where persistence across
process restarts is not required.  All data is lost when the process
exits.
"""

from __future__ import annotations

from phantom.vault.base import Repository

__all__ = ["MemoryRepository"]


class MemoryRepository(Repository):
    """Repository implementation backed by an in-process dictionary.

    Thread safety is *not* guaranteed; callers that share a single
    instance across threads should apply external locking.
    """

    def __init__(self) -> None:
        self._store: dict[str, str | bytes] = {}

    # ------------------------------------------------------------------
    # Repository interface
    # ------------------------------------------------------------------

    def persist(self, path: str, content: str | bytes) -> None:
        """Store ``content`` under ``path``.

        Args:
            path: Logical path used as a dictionary key.
            content: Text or binary content to store.
        """
        self._store[path] = content

    def retrieve(self, path: str) -> str:
        """Return the text content stored at ``path``.

        Binary values are decoded as UTF-8 before returning.

        Args:
            path: Logical path to look up.

        Returns:
            The stored content as a string.

        Raises:
            FileNotFoundError: When ``path`` is not in the store.
        """
        if path not in self._store:
            raise FileNotFoundError(f"No entry at path: {path!r}")
        value = self._store[path]
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value

    def enumerate(self, path: str) -> list[str]:
        """List all stored paths that start with ``path``.

        The prefix match uses the exact string ``path``; a trailing
        slash is *not* automatically appended.

        Args:
            path: Path prefix to filter on.

        Returns:
            Sorted list of matching keys.

        Raises:
            FileNotFoundError: When no entries match ``path``.
        """
        prefix = path if path.endswith("/") else path + "/"
        # Also match the exact path itself for single-file lookups
        matches = sorted(
            k for k in self._store if k == path or k.startswith(prefix)
        )
        if not matches:
            raise FileNotFoundError(f"No entries under path: {path!r}")
        return matches

    def remove(self, path: str) -> None:
        """Delete the entry at ``path``.

        Args:
            path: Logical path to remove.

        Raises:
            FileNotFoundError: When ``path`` is not in the store.
        """
        if path not in self._store:
            raise FileNotFoundError(f"No entry at path: {path!r}")
        del self._store[path]
