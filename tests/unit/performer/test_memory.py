"""Tests for PerformerMemory."""

import pytest

from phantom.performer.memory import PerformerMemory
from phantom.signal.base import SignalSource
from phantom.signal.channel import ChannelSubscriber, SignalChannel
from phantom.signal.depot import SignalDepot
from phantom.signal.directive.control import RecallDirective
from phantom.signal.report.control import RecallReport
from phantom.vault.memory_vault import MemoryRepository


@pytest.fixture
def channel():
    repo = MemoryRepository()
    depot = SignalDepot("mem-test", repo)
    ch = SignalChannel("mem-test", depot)
    yield ch
    ch.close()


class TestPerformerMemory:
    def test_store_adds_entry(self, channel):
        mem = PerformerMemory(channel)
        mem.store("important fact about Python", category="knowledge")
        assert len(mem._entries) == 1
        assert mem._entries[0].content == "important fact about Python"
        assert mem._entries[0].category == "knowledge"

    def test_store_all_adds_multiple(self, channel):
        mem = PerformerMemory(channel)
        mem.store_all(["fact one", "fact two", "fact three"])
        assert len(mem._entries) == 3

    def test_clear_removes_all_entries(self, channel):
        mem = PerformerMemory(channel)
        mem.store("entry")
        mem.clear()
        assert len(mem._entries) == 0

    def test_search_returns_python_entries_for_python_query(self, channel):
        mem = PerformerMemory(channel)
        mem.store("Python is a high-level language")
        mem.store("Docker is a containerisation platform")
        mem.store("Python uses indentation for blocks")
        results = mem.search("Python")
        contents = [e.content for e in results]
        # Both Python entries must appear somewhere in results
        assert any("high-level language" in c for c in contents)
        assert any("indentation" in c for c in contents)

    def test_search_with_category_filter(self, channel):
        mem = PerformerMemory(channel)
        mem.store("Python tip", category="lang")
        mem.store("Docker tip", category="infra")
        results = mem.search("tip", category="lang")
        assert all(e.category == "lang" for e in results)

    def test_recall_directive_triggers_report(self, channel):
        mem = PerformerMemory(channel)
        mem.store("The answer is 42")

        received = []
        channel.subscribe(
            ChannelSubscriber.TEST,
            received.append,
            "test-recall",
        )

        directive = RecallDirective(query="answer")
        channel.broadcast(directive, SignalSource.USER)

        # Allow async fan-out to complete
        import time

        time.sleep(0.1)

        recall_reports = [s for s in received if isinstance(s, RecallReport)]
        assert len(recall_reports) >= 1
        assert "42" in recall_reports[0].content
