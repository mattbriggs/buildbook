"""test_manifest.py — Tests for :mod:`buildbook.manifest`.

Covers :class:`ManifestEntry`, :class:`ManuscriptMeta`, :class:`Manifest`,
and the :func:`load_manifest` factory function.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from buildbook.manifest import Manifest, ManifestEntry, ManuscriptMeta, load_manifest


# ---------------------------------------------------------------------------
# ManifestEntry
# ---------------------------------------------------------------------------


class TestManifestEntry:
    """Unit tests for :class:`ManifestEntry`."""

    def test_stores_all_fields(self):
        """All three fields are stored and accessible."""
        entry = ManifestEntry(order=3, title="Epilogue", file="013-epilogue.md")
        assert entry.order == 3
        assert entry.title == "Epilogue"
        assert entry.file == "013-epilogue.md"

    def test_order_is_int(self):
        """order field must be an integer."""
        entry = ManifestEntry(order=1, title="X", file="x.md")
        assert isinstance(entry.order, int)

    def test_to_dict_round_trips(self):
        """to_dict() produces the expected keys and values."""
        entry = ManifestEntry(order=5, title="Middle", file="005-middle.md")
        d = entry.to_dict()
        assert d == {"order": 5, "title": "Middle", "file": "005-middle.md"}


# ---------------------------------------------------------------------------
# ManuscriptMeta
# ---------------------------------------------------------------------------


class TestManuscriptMeta:
    """Unit tests for :class:`ManuscriptMeta`."""

    def test_title_required(self):
        """title is the only positional argument."""
        m = ManuscriptMeta(title="My Book")
        assert m.title == "My Book"

    def test_optional_defaults(self):
        """Optional fields default to sensible empty values."""
        m = ManuscriptMeta(title="My Book")
        assert m.author == ""
        assert m.date == ""
        assert m.version == "0.1.0"
        assert m.output_dir == "../output"

    def test_version_stored(self):
        """version field round-trips correctly."""
        m = ManuscriptMeta(title="B", version="2.3.4")
        assert m.version == "2.3.4"

    def test_custom_output_dir(self):
        """output_dir can be overridden."""
        m = ManuscriptMeta(title="B", output_dir="dist")
        assert m.output_dir == "dist"

    def test_to_dict_contains_version(self):
        """to_dict() includes the version field."""
        m = ManuscriptMeta(title="T", version="1.0.0")
        d = m.to_dict()
        assert d["version"] == "1.0.0"


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


class TestManifest:
    """Unit tests for :class:`Manifest`."""

    def test_ordered_entries_sorted(self, sample_meta):
        """ordered_entries returns entries sorted by order regardless of list position."""
        entries = [
            ManifestEntry(order=3, title="C", file="003.md"),
            ManifestEntry(order=1, title="A", file="001.md"),
            ManifestEntry(order=2, title="B", file="002.md"),
        ]
        m = Manifest(manuscript=sample_meta, content=entries)
        assert [e.order for e in m.ordered_entries] == [1, 2, 3]

    def test_ordered_files_returns_sorted_paths(self, sample_manifest):
        """ordered_files returns file paths in ascending order."""
        assert sample_manifest.ordered_files == [
            "001-chapter-one.md",
            "002-chapter-two.md",
        ]

    def test_empty_content_is_valid(self, sample_meta):
        """A manifest with no content entries is valid."""
        m = Manifest(manuscript=sample_meta)
        assert m.ordered_entries == []
        assert m.ordered_files == []

    def test_to_dict_structure(self, sample_manifest):
        """to_dict() produces a dictionary with 'manuscript' and 'content' keys."""
        d = sample_manifest.to_dict()
        assert "manuscript" in d
        assert "content" in d
        assert isinstance(d["content"], list)
        assert d["manuscript"]["version"] == "1.2.3"

    def test_to_dict_content_sorted(self, sample_meta):
        """to_dict() serialises content in sorted order."""
        entries = [
            ManifestEntry(order=2, title="B", file="002.md"),
            ManifestEntry(order=1, title="A", file="001.md"),
        ]
        m = Manifest(manuscript=sample_meta, content=entries)
        d = m.to_dict()
        assert d["content"][0]["order"] == 1
        assert d["content"][1]["order"] == 2


# ---------------------------------------------------------------------------
# load_manifest (Factory Function)
# ---------------------------------------------------------------------------


class TestLoadManifest:
    """Unit tests for :func:`load_manifest`."""

    def test_loads_title(self, manifest_yaml_file):
        """Manifest title is read from YAML."""
        m = load_manifest(str(manifest_yaml_file))
        assert m.manuscript.title == "Test Book"

    def test_loads_author(self, manifest_yaml_file):
        """Manifest author is read from YAML."""
        m = load_manifest(str(manifest_yaml_file))
        assert m.manuscript.author == "Test Author"

    def test_loads_version(self, manifest_yaml_file):
        """Manifest version field is read from YAML."""
        m = load_manifest(str(manifest_yaml_file))
        assert m.manuscript.version == "0.2.0"

    def test_loads_content_count(self, manifest_yaml_file):
        """All content entries are loaded."""
        m = load_manifest(str(manifest_yaml_file))
        assert len(m.content) == 2

    def test_loads_entry_fields(self, manifest_yaml_file):
        """First entry has correct order, title, and file fields."""
        m = load_manifest(str(manifest_yaml_file))
        first = m.ordered_entries[0]
        assert first.order == 1
        assert first.title == "Intro"
        assert first.file == "001-intro.md"

    def test_missing_file_raises_file_not_found(self, tmp_path):
        """FileNotFoundError is raised when the YAML file does not exist."""
        with pytest.raises(FileNotFoundError):
            load_manifest(str(tmp_path / "nonexistent.yaml"))

    def test_missing_manuscript_key_raises_key_error(self, tmp_path):
        """KeyError is raised when the 'manuscript' key is absent."""
        bad = tmp_path / "bad.yaml"
        bad.write_text("content: []\n", encoding="utf-8")
        with pytest.raises(KeyError):
            load_manifest(str(bad))

    def test_malformed_yaml_raises(self, tmp_path):
        """A YAML parse error is raised for malformed input."""
        bad = tmp_path / "bad.yaml"
        bad.write_text(":\n  - :\n    bad: [unclosed", encoding="utf-8")
        with pytest.raises(Exception):
            load_manifest(str(bad))

    def test_optional_fields_default(self, tmp_path):
        """Optional fields default correctly when absent from YAML."""
        data = {"manuscript": {"title": "No Author"}, "content": []}
        p = tmp_path / "m.yaml"
        p.write_text(yaml.dump(data), encoding="utf-8")
        m = load_manifest(str(p))
        assert m.manuscript.author == ""
        assert m.manuscript.version == "0.1.0"
        assert m.manuscript.output_dir == "../output"
