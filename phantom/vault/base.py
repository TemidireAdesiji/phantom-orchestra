"""Abstract base class for PhantomOrchestra storage repositories."""

from abc import ABC, abstractmethod

__all__ = ["Repository"]


class Repository(ABC):
    """Storage abstraction for PhantomOrchestra artefacts.

    All path arguments are repository-relative strings using forward
    slashes as separators (UNIX-style).  Implementations are
    responsible for mapping these logical paths to their underlying
    storage medium.

    Raises:
        FileNotFoundError: From :meth:`retrieve` and :meth:`remove`
            when the target path does not exist.
        PermissionError: When a path traversal attack is detected
            (implementation-specific).
    """

    @abstractmethod
    def persist(self, path: str, content: str | bytes) -> None:
        """Write ``content`` to ``path``, creating parents as needed.

        If a file already exists at ``path`` it is overwritten.

        Args:
            path: Repository-relative destination path.
            content: Text or binary content to write.
        """
        ...

    @abstractmethod
    def retrieve(self, path: str) -> str:
        """Read and return the text content at ``path``.

        Args:
            path: Repository-relative source path.

        Returns:
            The file content decoded as UTF-8.

        Raises:
            FileNotFoundError: When ``path`` does not exist.
        """
        ...

    @abstractmethod
    def enumerate(self, path: str) -> list[str]:
        """List all entries under the given ``path`` prefix.

        Args:
            path: Repository-relative directory path.

        Returns:
            Sorted list of repository-relative paths for all files
            found under ``path``.

        Raises:
            FileNotFoundError: When ``path`` does not exist.
        """
        ...

    @abstractmethod
    def remove(self, path: str) -> None:
        """Delete the file at ``path``.

        Args:
            path: Repository-relative path to remove.

        Raises:
            FileNotFoundError: When ``path`` does not exist.
        """
        ...

    def exists(self, path: str) -> bool:
        """Return ``True`` when ``path`` exists in the repository.

        The default implementation calls :meth:`retrieve` and
        catches :class:`FileNotFoundError`.  Subclasses may override
        with a more efficient check.

        Args:
            path: Repository-relative path to test.

        Returns:
            ``True`` if the path exists, ``False`` otherwise.
        """
        try:
            self.retrieve(path)
            return True
        except FileNotFoundError:
            return False
