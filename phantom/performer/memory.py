"""Conversation memory for contextual recall in PhantomOrchestra."""

from dataclasses import dataclass

from phantom.signal.base import Signal, SignalSource
from phantom.signal.channel import ChannelSubscriber, SignalChannel
from phantom.signal.directive.control import RecallDirective
from phantom.signal.report.control import RecallReport

__all__ = ["MemoryEntry", "PerformerMemory"]


@dataclass
class MemoryEntry:
    """A single item stored in the performer's long-term memory.

    Attributes:
        content: The stored text content.
        category: Logical grouping label for the entry.
        relevance_score: Static priority weight; higher values are
            returned before lower ones when scores are equal.
    """

    content: str
    category: str = "general"
    relevance_score: float = 1.0


class PerformerMemory:
    """Keyword-based long-term memory for a performer session.

    Subscribes to the :class:`SignalChannel` and responds to
    :class:`RecallDirective` signals by performing a simple keyword
    search over stored entries and broadcasting a
    :class:`RecallReport` with the top results.

    Args:
        channel: The session's SignalChannel to subscribe to.
    """

    def __init__(self, channel: SignalChannel) -> None:
        self._channel = channel
        self._entries: list[MemoryEntry] = []
        channel.subscribe(
            ChannelSubscriber.MEMORY,
            self._handle_signal,
            "memory_main",
        )

    # ------------------------------------------------------------------
    # Signal handling
    # ------------------------------------------------------------------

    def _handle_signal(self, signal: Signal) -> None:
        """Route incoming signals to relevant handlers.

        Currently handles :class:`RecallDirective` only; all other
        signal types are silently ignored.

        Args:
            signal: Signal received from the channel.
        """
        if isinstance(signal, RecallDirective):
            relevant = self._retrieve(signal.query)
            report = RecallReport(
                content="\n".join(e.content for e in relevant),
                context_entries=[e.content for e in relevant],
            )
            self._channel.broadcast(report, SignalSource.ENVIRONMENT)

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    def store(
        self,
        content: str,
        category: str = "general",
        relevance_score: float = 1.0,
    ) -> None:
        """Add a new entry to memory.

        Args:
            content: Text to store.
            category: Logical label for the entry.
            relevance_score: Static weight used for tie-breaking
                during retrieval.
        """
        self._entries.append(
            MemoryEntry(
                content=content,
                category=category,
                relevance_score=relevance_score,
            )
        )

    def store_all(
        self,
        items: list[str],
        category: str = "general",
    ) -> None:
        """Store multiple text items at once.

        Args:
            items: List of text strings to store.
            category: Logical label applied to all items.
        """
        for item in items:
            self.store(item, category=category)

    def clear(self, category: str | None = None) -> None:
        """Remove stored entries.

        Args:
            category: When provided, remove only entries with this
                category label.  When ``None``, clear all entries.
        """
        if category is None:
            self._entries.clear()
        else:
            self._entries = [
                e for e in self._entries if e.category != category
            ]

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def _retrieve(
        self,
        query: str,
        max_results: int = 5,
    ) -> list[MemoryEntry]:
        """Simple keyword-based retrieval.

        Scores each entry by counting how many query words appear in
        its content (case-insensitive).  Entries with higher keyword
        overlap rank first; ties are broken by ``relevance_score``.

        Args:
            query: Natural-language query string.
            max_results: Maximum number of entries to return.

        Returns:
            Up to ``max_results`` MemoryEntry objects, most relevant
            first.
        """
        query_words = query.lower().split()
        if not query_words:
            # No query words: return most recently stored entries
            return list(reversed(self._entries))[:max_results]

        scored: list[tuple[MemoryEntry, float]] = []
        for entry in self._entries:
            lower_content = entry.content.lower()
            keyword_hits = sum(
                1 for word in query_words if word in lower_content
            )
            # Combine keyword hits with static relevance score
            combined = keyword_hits + entry.relevance_score * 0.1
            scored.append((entry, combined))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [entry for entry, _ in scored[:max_results]]

    def search(
        self,
        query: str,
        max_results: int = 5,
        category: str | None = None,
    ) -> list[MemoryEntry]:
        """Public retrieval method with optional category filter.

        Args:
            query: Natural-language query string.
            max_results: Maximum number of entries to return.
            category: When provided, only search within this
                category.

        Returns:
            Matching MemoryEntry objects.
        """
        if category is not None:
            original = self._entries
            self._entries = [e for e in original if e.category == category]
            results = self._retrieve(query, max_results)
            self._entries = original
            return results

        return self._retrieve(query, max_results)

    @property
    def entry_count(self) -> int:
        """Total number of stored memory entries."""
        return len(self._entries)
