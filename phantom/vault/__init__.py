"""Vault module: storage repositories for PhantomOrchestra."""

from phantom.vault.base import Repository
from phantom.vault.factory import create_repository
from phantom.vault.local_vault import LocalRepository
from phantom.vault.memory_vault import MemoryRepository

__all__ = [
    "LocalRepository",
    "MemoryRepository",
    "Repository",
    "create_repository",
]
