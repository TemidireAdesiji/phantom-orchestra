"""Local-filesystem storage repository for PhantomOrchestra.

Writes are performed atomically: content is written to a temporary
file adjacent to the destination, then renamed into place using
:func:`os.replace`.  This guarantees that readers never observe a
partially written file.

Path traversal protection is enforced by resolving all paths inside
the configured root and refusing any path that escapes it.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from phantom.vault.base import Repository

__all__ = ["LocalRepository"]


class LocalRepository(Repository):
    """Repository implementation backed by the local filesystem.

    Args:
        root_path: Absolute path to the directory that serves as the
            repository root.  Created automatically if it does not
            exist.

    Raises:
        PermissionError: When a supplied path would resolve to a
            location outside ``root_path``.
    """

    def __init__(self, root_path: str) -> None:
        self._root = Path(root_path).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve(self, path: str) -> Path:
        """Resolve ``path`` within the root, checking for traversal.

        Args:
            path: Repository-relative path.

        Returns:
            Absolute :class:`~pathlib.Path` within the root.

        Raises:
            PermissionError: When the resolved path escapes the root.
        """
        resolved = (self._root / path).resolve()
        try:
            resolved.relative_to(self._root)
        except ValueError:
            raise PermissionError(
                f"Path traversal detected: {path!r} resolves "
                f"outside repository root {self._root}"
            ) from None
        return resolved

    # ------------------------------------------------------------------
    # Repository interface
    # ------------------------------------------------------------------

    def persist(self, path: str, content: str | bytes) -> None:
        """Atomically write ``content`` to ``path``.

        Intermediate directories are created automatically.

        Args:
            path: Repository-relative destination path.
            content: Text or binary content to write.
        """
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)

        mode = "wb" if isinstance(content, bytes) else "w"
        encoding = None if isinstance(content, bytes) else "utf-8"

        fd, tmp_path = tempfile.mkstemp(
            dir=target.parent,
            prefix=".tmp-",
        )
        try:
            with os.fdopen(fd, mode, encoding=encoding) as fh:
                fh.write(content)
            os.replace(tmp_path, target)
        except Exception:
            # Clean up the temp file if anything goes wrong
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def retrieve(self, path: str) -> str:
        """Read and return the UTF-8 text content at ``path``.

        Args:
            path: Repository-relative source path.

        Returns:
            The file content as a string.

        Raises:
            FileNotFoundError: When the path does not exist.
        """
        target = self._resolve(path)
        if not target.exists():
            raise FileNotFoundError(f"No file at repository path: {path!r}")
        return target.read_text(encoding="utf-8")

    def enumerate(self, path: str) -> list[str]:
        """List all files under ``path``, sorted lexicographically.

        Args:
            path: Repository-relative directory path.

        Returns:
            Sorted list of repository-relative file paths.

        Raises:
            FileNotFoundError: When ``path`` does not exist.
        """
        target = self._resolve(path)
        if not target.exists():
            raise FileNotFoundError(
                f"No directory at repository path: {path!r}"
            )

        results: list[str] = []
        for item in sorted(target.rglob("*")):
            if item.is_file():
                rel = item.relative_to(self._root)
                results.append(str(rel))
        return results

    def remove(self, path: str) -> None:
        """Delete the file at ``path``.

        Args:
            path: Repository-relative path to remove.

        Raises:
            FileNotFoundError: When the path does not exist.
        """
        target = self._resolve(path)
        if not target.exists():
            raise FileNotFoundError(f"No file at repository path: {path!r}")
        target.unlink()
