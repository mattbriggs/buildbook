"""manifest.py — Manifest models and YAML loader for the book build system.

Provides dataclasses that represent a build manifest loaded from a YAML file,
plus the :func:`load_manifest` factory function for parsing that file.

These classes serve as **Data Transfer Objects (DTO)**: plain containers
that carry data between the loader, the scanner, and the builder with no
business logic of their own beyond sorting.

:Example:

    .. code-block:: python

        from buildbook.manifest import load_manifest

        manifest = load_manifest("content/book.yaml")
        for entry in manifest.ordered_entries:
            print(entry.order, entry.title, entry.file)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ManifestEntry:
    """A single content entry in the manuscript manifest.

    :param order: Integer sort order; lower values appear first in the build.
    :param title: Human-readable chapter title.
    :param file: Path to the Markdown source file, relative to the manifest.
    """

    order: int
    title: str
    file: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialise this entry to a plain dictionary.

        :return: Dictionary with keys ``order``, ``title``, and ``file``.
        :rtype: dict
        """
        return {"order": self.order, "title": self.title, "file": self.file}


@dataclass
class ManuscriptMeta:
    """Metadata describing the manuscript as a whole.

    :param title: Manuscript title passed to Pandoc as document metadata.
    :param author: Author name passed to Pandoc as document metadata.
    :param version: Book version string following `Semantic Versioning
        <https://semver.org>`_, e.g. ``"1.0.0"``.
    :param date: Publication date string passed to Pandoc as document metadata.
    :param output_dir: Directory (relative to the manifest file) where built
        artefacts are written.  Defaults to ``"../output"``.
    """

    title: str
    author: str = ""
    version: str = "0.1.0"
    date: str = ""
    output_dir: str = "../output"

    def to_dict(self) -> Dict[str, Any]:
        """Serialise this metadata to a plain dictionary.

        :return: Dictionary of manuscript metadata fields.
        :rtype: dict
        """
        return {
            "title": self.title,
            "author": self.author,
            "version": self.version,
            "date": self.date,
            "output_dir": self.output_dir,
        }


@dataclass
class Manifest:
    """Complete book build manifest.

    Acts as the top-level DTO passed from the loader / scanner to the
    :class:`~buildbook.builder.Builder`.

    :param manuscript: Metadata for the manuscript.
    :param content: List of :class:`ManifestEntry` objects in any order.
    """

    manuscript: ManuscriptMeta
    content: List[ManifestEntry] = field(default_factory=list)

    @property
    def ordered_entries(self) -> List[ManifestEntry]:
        """Return content entries sorted ascending by :attr:`ManifestEntry.order`.

        :return: Sorted list of :class:`ManifestEntry` objects.
        :rtype: List[ManifestEntry]
        """
        return sorted(self.content, key=lambda e: e.order)

    @property
    def ordered_files(self) -> List[str]:
        """Return file paths sorted ascending by entry order.

        :return: Sorted list of file path strings.
        :rtype: List[str]
        """
        return [e.file for e in self.ordered_entries]

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the full manifest to a plain dictionary for YAML output.

        :return: Dictionary with ``manuscript`` and ``content`` keys.
        :rtype: dict
        """
        return {
            "manuscript": self.manuscript.to_dict(),
            "content": [e.to_dict() for e in self.ordered_entries],
        }


def load_manifest(path: str) -> Manifest:
    """Load a :class:`Manifest` from a YAML file.

    Acts as a **Factory Function**: constructs and returns a fully populated
    :class:`Manifest` from declarative YAML, hiding the construction details
    from callers.

    Expected YAML structure::

        manuscript:
          title: "My Book"
          author: "Jane Author"     # optional
          version: "1.0.0"          # optional, default "0.1.0"
          date: "2026"              # optional
          output_dir: "../output"   # optional, default "../output"

        content:
          - order: 1
            title: "Introduction"
            file: "001-introduction.md"
          - order: 2
            title: "Chapter One"
            file: "002-chapter-one.md"

    :param path: Path to the YAML manifest file.
    :type path: str
    :return: Parsed :class:`Manifest` object.
    :rtype: Manifest
    :raises FileNotFoundError: If the YAML file does not exist.
    :raises KeyError: If a required field is absent from the YAML.
    :raises yaml.YAMLError: If the YAML is malformed.
    """
    manifest_path = Path(path)
    logger.debug("Loading manifest from %s", manifest_path)

    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest file not found: {manifest_path}")

    with manifest_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    raw_meta = data["manuscript"]
    meta = ManuscriptMeta(
        title=raw_meta["title"],
        author=raw_meta.get("author", ""),
        version=raw_meta.get("version", "0.1.0"),
        date=raw_meta.get("date", ""),
        output_dir=raw_meta.get("output_dir", "../output"),
    )

    entries = [
        ManifestEntry(
            order=int(e["order"]),
            title=e["title"],
            file=e["file"],
        )
        for e in data.get("content", [])
    ]

    logger.debug("Loaded %d content entries from %s", len(entries), manifest_path)
    return Manifest(manuscript=meta, content=entries)
