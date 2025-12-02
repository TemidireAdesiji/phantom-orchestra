"""Tests for vault factory."""

import pytest

from phantom.vault.factory import create_repository
from phantom.vault.local_vault import LocalRepository
from phantom.vault.memory_vault import MemoryRepository


class TestCreateRepository:
    def test_memory_type_returns_memory_repository(self):
        repo = create_repository("memory")
        assert isinstance(repo, MemoryRepository)

    def test_memory_type_ignores_path(self):
        repo = create_repository("memory", store_path="/ignored")
        assert isinstance(repo, MemoryRepository)

    def test_local_type_returns_local_repository(self, tmp_path):
        repo = create_repository("local", store_path=str(tmp_path))
        assert isinstance(repo, LocalRepository)

    def test_local_type_uses_default_path_when_none(self):
        repo = create_repository("local", store_path=None)
        assert isinstance(repo, LocalRepository)

    def test_unknown_type_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown store_type"):
            create_repository("s3")

    def test_case_insensitive_memory(self):
        repo = create_repository("MEMORY")
        assert isinstance(repo, MemoryRepository)

    def test_case_insensitive_local(self, tmp_path):
        repo = create_repository("LOCAL", store_path=str(tmp_path))
        assert isinstance(repo, LocalRepository)
