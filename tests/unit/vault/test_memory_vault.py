"""Tests for MemoryRepository."""

import pytest

from phantom.vault.memory_vault import MemoryRepository


@pytest.fixture
def repo():
    """Return a fresh MemoryRepository for each test."""
    return MemoryRepository()


class TestMemoryRepositoryPersistRetrieve:
    def test_persist_and_retrieve_text(self, repo):
        repo.persist("file.txt", "content")
        assert repo.retrieve("file.txt") == "content"

    def test_persist_overwrites_existing_entry(self, repo):
        repo.persist("key", "original")
        repo.persist("key", "updated")
        assert repo.retrieve("key") == "updated"

    def test_retrieve_raises_file_not_found_when_absent(self, repo):
        with pytest.raises(FileNotFoundError):
            repo.retrieve("missing/file.json")

    def test_persist_bytes_retrieved_as_str(self, repo):
        repo.persist("bytes.bin", b"binary data")
        result = repo.retrieve("bytes.bin")
        assert result == "binary data"
        assert isinstance(result, str)


class TestMemoryRepositoryEnumerate:
    def test_enumerate_returns_entries_under_prefix(self, repo):
        repo.persist("session/00000000.json", "{}")
        repo.persist("session/00000001.json", "{}")
        entries = repo.enumerate("session")
        assert len(entries) == 2

    def test_enumerate_raises_for_no_matching_entries(self, repo):
        with pytest.raises(FileNotFoundError):
            repo.enumerate("empty-prefix")

    def test_enumerate_sorts_results(self, repo):
        repo.persist("ns/c", "3")
        repo.persist("ns/a", "1")
        repo.persist("ns/b", "2")
        entries = repo.enumerate("ns")
        assert entries == sorted(entries)

    def test_enumerate_does_not_include_unrelated_paths(self, repo):
        repo.persist("alpha/file.txt", "a")
        repo.persist("beta/file.txt", "b")
        entries = repo.enumerate("alpha")
        assert all(e.startswith("alpha") for e in entries)


class TestMemoryRepositoryRemove:
    def test_remove_deletes_entry(self, repo):
        repo.persist("del-me.txt", "bye")
        repo.remove("del-me.txt")
        with pytest.raises(FileNotFoundError):
            repo.retrieve("del-me.txt")

    def test_remove_raises_when_entry_absent(self, repo):
        with pytest.raises(FileNotFoundError):
            repo.remove("not-there.txt")
