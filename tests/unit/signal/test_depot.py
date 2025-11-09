"""Tests for SignalDepot."""

from phantom.signal.depot import SignalDepot
from phantom.signal.directive.terminal import RunCommandDirective
from phantom.vault.local_vault import LocalRepository


def _make_cmd(cmd: str = "echo hi") -> RunCommandDirective:
    """Helper: build a RunCommandDirective with a set ID."""
    return RunCommandDirective(command=cmd)


class TestSignalDepotCursor:
    def test_cursor_starts_at_minus_one_for_empty_depot(
        self, memory_repository
    ):
        depot = SignalDepot(session_id="sess-a", repository=memory_repository)
        assert depot.cursor == -1

    def test_cursor_updates_after_commit(self, memory_repository):
        depot = SignalDepot(session_id="sess-b", repository=memory_repository)
        sig = _make_cmd()
        sig.id = 0
        depot.commit_signal(sig)
        assert depot.cursor == 0

    def test_cursor_reflects_highest_committed_id(self, memory_repository):
        depot = SignalDepot(session_id="sess-c", repository=memory_repository)
        for i in range(5):
            sig = _make_cmd()
            sig.id = i
            depot.commit_signal(sig)
        assert depot.cursor == 4


class TestSignalDepotCommitAndFetch:
    def test_committing_signal_persists_it(self, memory_repository):
        depot = SignalDepot(session_id="sess-d", repository=memory_repository)
        sig = RunCommandDirective(command="ls")
        sig.id = 0
        depot.commit_signal(sig)
        results = depot.fetch_signals(start_id=0, end_id=0)
        assert len(results) == 1

    def test_fetch_returns_signals_by_id_range(self, memory_repository):
        depot = SignalDepot(session_id="sess-e", repository=memory_repository)
        for i in range(6):
            sig = RunCommandDirective(command=f"cmd-{i}")
            sig.id = i
            depot.commit_signal(sig)

        results = depot.fetch_signals(start_id=2, end_id=4)
        assert len(results) == 3

    def test_fetch_with_limit(self, memory_repository):
        depot = SignalDepot(session_id="sess-f", repository=memory_repository)
        for i in range(10):
            sig = RunCommandDirective(command=f"cmd-{i}")
            sig.id = i
            depot.commit_signal(sig)

        results = depot.fetch_signals(start_id=0, limit=3)
        assert len(results) == 3

    def test_fetch_default_end_uses_cursor(self, memory_repository):
        depot = SignalDepot(session_id="sess-g", repository=memory_repository)
        for i in range(3):
            sig = RunCommandDirective(command=f"x-{i}")
            sig.id = i
            depot.commit_signal(sig)

        # No end_id → defaults to cursor
        results = depot.fetch_signals(start_id=0)
        assert len(results) == 3

    def test_missing_ids_are_skipped_gracefully(self, memory_repository):
        depot = SignalDepot(session_id="sess-h", repository=memory_repository)
        sig = RunCommandDirective(command="sparse")
        sig.id = 5  # gap: IDs 0-4 absent
        depot.commit_signal(sig)

        results = depot.fetch_signals(start_id=0, end_id=5)
        assert len(results) == 1


class TestSignalDepotPersistence:
    def test_cursor_recovered_from_local_repository(self, tmp_path):
        """Depot recreated from same local repo recovers cursor."""
        repo = LocalRepository(str(tmp_path / "vault"))
        depot1 = SignalDepot(session_id="persist-sess", repository=repo)
        for i in range(3):
            sig = RunCommandDirective(command=f"p-{i}")
            sig.id = i
            depot1.commit_signal(sig)

        # Create a second depot over the same repository
        depot2 = SignalDepot(session_id="persist-sess", repository=repo)
        assert depot2.cursor == 2

    def test_signals_readable_across_depot_instances(self, tmp_path):
        repo = LocalRepository(str(tmp_path / "vault2"))
        depot1 = SignalDepot(session_id="cross-sess", repository=repo)
        # Use RunCommandDirective (no nested non-serialisable fields)
        sig = RunCommandDirective(command="echo cross-depot")
        sig.id = 0
        depot1.commit_signal(sig)

        depot2 = SignalDepot(session_id="cross-sess", repository=repo)
        results = depot2.fetch_signals(start_id=0, end_id=0)
        assert len(results) == 1
        assert isinstance(results[0], RunCommandDirective)
