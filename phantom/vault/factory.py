"""Factory for creating Repository instances in PhantomOrchestra."""

from phantom.vault.base import Repository
from phantom.vault.local_vault import LocalRepository
from phantom.vault.memory_vault import MemoryRepository

__all__ = ["create_repository"]

_DEFAULT_LOCAL_PATH = "/tmp/phantom/store"  # noqa: S108


def create_repository(
    store_type: str,
    store_path: str | None = None,
) -> Repository:
    """Instantiate the correct Repository for the given store type.

    Supported values for ``store_type``:

    * ``"local"`` — persists data to the local filesystem at
      ``store_path`` (defaults to ``/tmp/phantom/store``).
    * ``"memory"`` — stores data in process memory only; all data is
      lost when the process exits.  ``store_path`` is ignored.

    Args:
        store_type: One of ``"local"`` or ``"memory"``.
        store_path: Root path for ``"local"`` repositories.  Ignored
            for ``"memory"``.  Defaults to ``/tmp/phantom/store``.

    Returns:
        A concrete :class:`~phantom.vault.base.Repository` instance.

    Raises:
        ValueError: When ``store_type`` is not recognised.
    """
    normalised = store_type.strip().lower()

    if normalised == "local":
        root = store_path or _DEFAULT_LOCAL_PATH
        return LocalRepository(root_path=root)

    if normalised == "memory":
        return MemoryRepository()

    raise ValueError(
        f"Unknown store_type {store_type!r}. "
        f"Expected one of: 'local', 'memory'."
    )
