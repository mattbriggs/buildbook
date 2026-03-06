"""test_scanner.py — Tests for :mod:`buildbook.scanner`.

Covers :class:`Scanner` methods: ``_extract_order``, ``_extract_title``,
``scan``, ``generate_manifest``, and ``save_manifest``.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from buildbook.manifest import ManuscriptMeta
from buildbook.scanner import Scanner


# ---------------------------------------------------------------------------
# _extract_order
# ---------------------------------------------------------------------------


class TestExtractOrder:
    """Tests for :meth:`Scanner._extract_order`."""

    def setup_method(self):
        """Create a fresh Scanner for each test."""
        self.scanner = Scanner()

    def test_three_digit_prefix(self):
        """A '001-' prefix yields order 1."""
        assert self.scanner._extract_order("001-introduction.md") == 1

    def test_two_digit_prefix(self):
        """A '03_' prefix yields order 3."""
        assert self.scanner._extract_order("03_chapter.md") == 3

    def test_no_prefix_returns_999(self):
        """A filename without a numeric prefix yields 999."""
        assert self.scanner._extract_order("appendix.md") == 999

    def test_leading_zeros_stripped(self):
        """Leading zeros in a numeric prefix are handled correctly."""
        assert self.scanner._extract_order("010-ten.md") == 10


# ---------------------------------------------------------------------------
# _extract_title
# ---------------------------------------------------------------------------


class TestExtractTitle:
    """Tests for :meth:`Scanner._extract_title`."""

    def setup_method(self):
        """Create a fresh Scanner for each test."""
        self.scanner = Scanner()

    def test_reads_h1_heading(self, tmp_path):
        """The first '# Heading' in the file is returned as the title."""
        f = tmp_path / "001-intro.md"
        f.write_text("# My Introduction\n\nSome text.", encoding="utf-8")
        assert self.scanner._extract_title(f) == "My Introduction"

    def test_skips_non_heading_lines(self, tmp_path):
        """Lines before the first heading are ignored."""
        f = tmp_path / "001-intro.md"
        f.write_text("---\ntitle: meta\n---\n# Real Title\n", encoding="utf-8")
        assert self.scanner._extract_title(f) == "Real Title"

    def test_fallback_to_filename_stem(self, tmp_path):
        """When no heading is found, the title is derived from the filename."""
        f = tmp_path / "002-getting-started.md"
        f.write_text("No heading here.\n", encoding="utf-8")
        assert self.scanner._extract_title(f) == "Getting Started"

    def test_fallback_with_numeric_prefix(self, tmp_path):
        """The numeric prefix is stripped when deriving a title from the filename."""
        f = tmp_path / "005-advanced-topics.md"
        f.write_text("", encoding="utf-8")
        title = self.scanner._extract_title(f)
        assert "005" not in title
        assert "Advanced Topics" == title

    def test_unreadable_file_falls_back(self, tmp_path):
        """A non-existent path falls back to the filename stem gracefully."""
        f = tmp_path / "003-chapter.md"
        # File does not exist — _extract_title must not raise
        title = self.scanner._extract_title(f)
        assert "Chapter" in title


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------


class TestScan:
    """Tests for :meth:`Scanner.scan`."""

    def setup_method(self):
        """Create a fresh Scanner for each test."""
        self.scanner = Scanner()

    def test_finds_markdown_files(self, tmp_path):
        """All .md files in the directory are discovered."""
        (tmp_path / "001-a.md").write_text("# A", encoding="utf-8")
        (tmp_path / "002-b.md").write_text("# B", encoding="utf-8")
        entries = self.scanner.scan(tmp_path)
        assert len(entries) == 2

    def test_entries_sorted_by_order(self, tmp_path):
        """Entries are sorted by their numeric prefix regardless of discovery order."""
        (tmp_path / "003-c.md").write_text("# C", encoding="utf-8")
        (tmp_path / "001-a.md").write_text("# A", encoding="utf-8")
        (tmp_path / "002-b.md").write_text("# B", encoding="utf-8")
        entries = self.scanner.scan(tmp_path)
        assert [e.order for e in entries] == [1, 2, 3]

    def test_ignores_non_markdown_files(self, tmp_path):
        """Non-Markdown files in the directory are ignored."""
        (tmp_path / "001-a.md").write_text("# A", encoding="utf-8")
        (tmp_path / "notes.txt").write_text("notes", encoding="utf-8")
        (tmp_path / "book.yaml").write_text("manuscript:", encoding="utf-8")
        entries = self.scanner.scan(tmp_path)
        assert len(entries) == 1

    def test_empty_directory_returns_empty_list(self, tmp_path):
        """An empty directory returns an empty list without error."""
        entries = self.scanner.scan(tmp_path)
        assert entries == []

    def test_raises_for_nonexistent_directory(self, tmp_path):
        """NotADirectoryError is raised for a path that does not exist."""
        with pytest.raises(NotADirectoryError):
            self.scanner.scan(tmp_path / "does_not_exist")

    def test_entry_file_field_is_basename(self, tmp_path):
        """ManifestEntry.file contains only the filename, not the full path."""
        (tmp_path / "001-intro.md").write_text("# Intro", encoding="utf-8")
        entries = self.scanner.scan(tmp_path)
        assert entries[0].file == "001-intro.md"


# ---------------------------------------------------------------------------
# generate_manifest
# ---------------------------------------------------------------------------


class TestGenerateManifest:
    """Tests for :meth:`Scanner.generate_manifest`."""

    def setup_method(self):
        """Create a fresh Scanner for each test."""
        self.scanner = Scanner()

    def test_returns_manifest(self, tmp_path):
        """A Manifest object is returned."""
        from buildbook.manifest import Manifest
        entries_dir = tmp_path
        (entries_dir / "001-intro.md").write_text("# Intro", encoding="utf-8")
        manifest = self.scanner.generate_manifest(entries_dir)
        assert isinstance(manifest, Manifest)

    def test_uses_provided_meta(self, tmp_path):
        """The provided ManuscriptMeta is embedded in the manifest."""
        (tmp_path / "001-intro.md").write_text("# Intro", encoding="utf-8")
        meta = ManuscriptMeta(title="Custom Title", version="3.0.0")
        manifest = self.scanner.generate_manifest(tmp_path, meta)
        assert manifest.manuscript.title == "Custom Title"
        assert manifest.manuscript.version == "3.0.0"

    def test_default_meta_when_none(self, tmp_path):
        """A default ManuscriptMeta is used when meta is not provided."""
        (tmp_path / "001-intro.md").write_text("# Intro", encoding="utf-8")
        manifest = self.scanner.generate_manifest(tmp_path)
        assert manifest.manuscript.title == "My Book"

    def test_content_length_matches_files(self, tmp_path):
        """The number of content entries matches the Markdown files found."""
        for i in range(1, 4):
            (tmp_path / f"00{i}-ch.md").write_text(f"# Ch {i}", encoding="utf-8")
        manifest = self.scanner.generate_manifest(tmp_path)
        assert len(manifest.content) == 3


# ---------------------------------------------------------------------------
# save_manifest
# ---------------------------------------------------------------------------


class TestSaveManifest:
    """Tests for :meth:`Scanner.save_manifest`."""

    def setup_method(self):
        """Create a fresh Scanner for each test."""
        self.scanner = Scanner()

    def test_file_is_created(self, tmp_path, sample_manifest):
        """The manifest YAML file is written to the specified path."""
        out = tmp_path / "output.yaml"
        self.scanner.save_manifest(sample_manifest, out)
        assert out.exists()

    def test_yaml_is_valid(self, tmp_path, sample_manifest):
        """The written file is valid YAML."""
        out = tmp_path / "output.yaml"
        self.scanner.save_manifest(sample_manifest, out)
        data = yaml.safe_load(out.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_round_trips_title(self, tmp_path, sample_manifest):
        """The manuscript title round-trips through YAML serialisation."""
        out = tmp_path / "output.yaml"
        self.scanner.save_manifest(sample_manifest, out)
        data = yaml.safe_load(out.read_text(encoding="utf-8"))
        assert data["manuscript"]["title"] == sample_manifest.manuscript.title

    def test_round_trips_version(self, tmp_path, sample_manifest):
        """The manuscript version round-trips through YAML serialisation."""
        out = tmp_path / "output.yaml"
        self.scanner.save_manifest(sample_manifest, out)
        data = yaml.safe_load(out.read_text(encoding="utf-8"))
        assert data["manuscript"]["version"] == sample_manifest.manuscript.version

    def test_content_entries_present(self, tmp_path, sample_manifest):
        """All content entries appear in the written YAML."""
        out = tmp_path / "output.yaml"
        self.scanner.save_manifest(sample_manifest, out)
        data = yaml.safe_load(out.read_text(encoding="utf-8"))
        assert len(data["content"]) == len(sample_manifest.content)
