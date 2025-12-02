"""Tests for LocalRepository."""

import pytest

from phantom.vault.local_vault import LocalRepository


@pytest.fixture
def repo(tmp_path):
    """Return a LocalRepository rooted at a temp path."""
    return LocalRepository(str(tmp_path / "local-repo"))


class TestLocalRepositoryPersistRetrieve:
    def test_persist_and_retrieve_text_content(self, repo):
        repo.persist("notes/readme.txt", "Hello, world!")
        result = repo.retrieve("notes/readme.txt")
        assert result == "Hello, world!"

    def test_persist_creates_intermediate_directories(self, repo):
        repo.persist("a/b/c/deep.txt", "deep content")
        result = repo.retrieve("a/b/c/deep.txt")
        assert result == "deep content"

    def test_persist_is_idempotent_overwrites_content(self, repo):
        repo.persist("item.txt", "first")
        repo.persist("item.txt", "second")
        result = repo.retrieve("item.txt")
        assert result == "second"

    def test_retrieve_raises_file_not_found_for_missing_file(self, repo):
        with pytest.raises(FileNotFoundError):
            repo.retrieve("does/not/exist.txt")


class TestLocalRepositoryEnumerate:
    def test_enumerate_lists_files_under_path(self, repo):
        repo.persist("dir/a.txt", "a")
        repo.persist("dir/b.txt", "b")
        entries = repo.enumerate("dir")
        assert len(entries) == 2

    def test_enumerate_sorts_lexicographically(self, repo):
        repo.persist("sorted/c.txt", "c")
        repo.persist("sorted/a.txt", "a")
        repo.persist("sorted/b.txt", "b")
        entries = repo.enumerate("sorted")
        basenames = [e.split("/")[-1] for e in entries]
        assert basenames == sorted(basenames)

    def test_enumerate_raises_for_missing_directory(self, repo):
        with pytest.raises(FileNotFoundError):
            repo.enumerate("nonexistent-dir")


class TestLocalRepositoryRemove:
    def test_remove_deletes_file(self, repo):
        repo.persist("target.txt", "to be deleted")
        repo.remove("target.txt")
        with pytest.raises(FileNotFoundError):
            repo.retrieve("target.txt")

    def test_remove_raises_file_not_found_for_missing_file(self, repo):
        with pytest.raises(FileNotFoundError):
            repo.remove("ghost.txt")


class TestLocalRepositoryPathTraversal:
    def test_path_traversal_raises_permission_error(self, repo):
        with pytest.raises(PermissionError):
            repo.persist("../../etc/passwd", "evil")

    def test_retrieve_traversal_raises_permission_error(self, repo):
        with pytest.raises(PermissionError):
            repo.retrieve("../../etc/shadow")
