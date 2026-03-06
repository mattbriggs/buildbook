"""scanner.py — Content directory scanner for auto-generating manifests.

Provides :class:`Scanner`, which inspects a content directory for Markdown
files and produces a :class:`~buildbook.manifest.Manifest` that can be saved
as YAML.

Design patterns used:

* **Strategy Pattern** — title extraction uses a prioritised chain of
  strategies: first try reading the first ``#`` heading from the file; fall
  back to deriving a title from the filename stem.
* **Factory Method** — :meth:`Scanner.generate_manifest` acts as a factory
  that constructs a fully populated :class:`~buildbook.manifest.Manifest`
  from file-system data.

:Example:

    .. code-block:: python

        from pathlib import Path
        from buildbook.scanner import Scanner
        from buildbook.manifest import ManuscriptMeta

        scanner = Scanner()
        meta = ManuscriptMeta(title="My Book", author="Jane Author")
        manifest = scanner.generate_manifest(Path("content"), meta)
        scanner.save_manifest(manifest, Path("content/book.yaml"))
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import List, Optional

import yaml

from buildbook.manifest import Manifest, ManifestEntry, ManuscriptMeta

logger = logging.getLogger(__name__)

#: Matches a numeric prefix at the start of a filename, e.g. ``"001-"`` or ``"01_"``.
_ORDER_RE = re.compile(r"^(\d+)[-_]")


class Scanner:
    """Scans a directory for Markdown files and produces a build manifest.

    Uses a two-strategy approach for title extraction:

    1. Read the first ``# Heading`` from the file content.
    2. Derive a title from the filename stem (strips leading digits and
       converts hyphens/underscores to title-case words).

    :Example:

        .. code-block:: python

            scanner = Scanner()
            entries = scanner.scan(Path("content"))
    """

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_order(self, filename: str) -> int:
        """Extract a numeric sort order from a filename prefix.

        Filenames like ``001-intro.md`` or ``03_chapter.md`` yield ``1`` and
        ``3`` respectively.  Files without a numeric prefix are assigned order
        ``999``.

        :param filename: Bare filename (not a full path).
        :type filename: str
        :return: Integer sort order.
        :rtype: int
        """
        match = _ORDER_RE.match(filename)
        return int(match.group(1)) if match else 999

    def _extract_title(self, filepath: Path) -> str:
        """Extract a human-readable title for a Markdown file.

        Strategy 1: return the text of the first ``# `` heading found in the
        file.  Strategy 2 (fallback): derive a title from the filename stem by
        stripping the numeric prefix and converting delimiters to title case.

        :param filepath: Absolute or relative path to the Markdown file.
        :type filepath: Path
        :return: Extracted or derived title string.
        :rtype: str
        """
        try:
            for line in filepath.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped.startswith("# "):
                    return stripped[2:].strip()
        except OSError as exc:
            logger.debug("Could not read %s for title extraction: %s", filepath, exc)

        # Fallback: derive from stem
        stem = filepath.stem
        stem = _ORDER_RE.sub("", stem)
        return stem.replace("-", " ").replace("_", " ").title()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan(self, content_dir: Path) -> List[ManifestEntry]:
        """Scan *content_dir* for ``*.md`` files and return manifest entries.

        Files are sorted first by their numeric prefix (if present), then
        alphabetically.

        :param content_dir: Directory to scan for Markdown files.
        :type content_dir: Path
        :return: List of :class:`~buildbook.manifest.ManifestEntry` objects,
            sorted by order.
        :rtype: List[ManifestEntry]
        :raises NotADirectoryError: If *content_dir* does not exist or is not
            a directory.
        """
        if not content_dir.is_dir():
            raise NotADirectoryError(
                f"Content directory not found: {content_dir}"
            )

        md_files = sorted(content_dir.glob("*.md"), key=lambda p: p.name)
        entries: List[ManifestEntry] = []
        for filepath in md_files:
            order = self._extract_order(filepath.name)
            title = self._extract_title(filepath)
            entries.append(ManifestEntry(order=order, title=title, file=filepath.name))
            logger.debug("Found: order=%d  title=%r  file=%s", order, title, filepath.name)

        return sorted(entries, key=lambda e: e.order)

    def generate_manifest(
        self,
        content_dir: Path,
        meta: Optional[ManuscriptMeta] = None,
    ) -> Manifest:
        """Scan *content_dir* and return a fully populated :class:`~buildbook.manifest.Manifest`.

        Acts as a **Factory Method**: constructs and returns a :class:`Manifest`
        from file-system data without requiring the caller to manage
        :class:`ManifestEntry` objects directly.

        :param content_dir: Directory containing Markdown chapter files.
        :type content_dir: Path
        :param meta: Manuscript metadata to embed in the manifest.  If
            ``None``, a default :class:`~buildbook.manifest.ManuscriptMeta` is
            used with title ``"My Book"``.
        :type meta: ManuscriptMeta | None
        :return: Populated :class:`~buildbook.manifest.Manifest`.
        :rtype: Manifest
        """
        if meta is None:
            meta = ManuscriptMeta(title="My Book")
        entries = self.scan(content_dir)
        logger.info(
            "Generated manifest: %d entries from %s", len(entries), content_dir
        )
        return Manifest(manuscript=meta, content=entries)

    def save_manifest(self, manifest: Manifest, output_path: Path) -> None:
        """Serialise *manifest* to a YAML file at *output_path*.

        :param manifest: The manifest to write.
        :type manifest: Manifest
        :param output_path: Destination path for the YAML file.
        :type output_path: Path
        :raises OSError: If the file cannot be written.
        """
        data = manifest.to_dict()
        with output_path.open("w", encoding="utf-8") as fh:
            yaml.dump(data, fh, default_flow_style=False, allow_unicode=True, sort_keys=False)
        logger.info("Manifest saved to %s", output_path)
