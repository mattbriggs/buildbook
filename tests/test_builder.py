"""test_builder.py — Tests for :mod:`buildbook.builder`.

Covers :data:`FORMAT_MAP`, :class:`BuildResult`, and all public and private
methods of :class:`Builder`.  Pandoc is mocked throughout so the suite runs
without Pandoc installed.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from buildbook.builder import FORMAT_MAP, BuildResult, Builder
from buildbook.manifest import Manifest, ManifestEntry, ManuscriptMeta


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_builder(tmp_path: Path, output_dir: str = "../out") -> Builder:
    """Create a :class:`Builder` with a single chapter and a temp base dir.

    :param tmp_path: Pytest temporary directory.
    :param output_dir: Relative output directory placed in the manifest.
    :return: Configured Builder instance.
    :rtype: Builder
    """
    (tmp_path / "001.md").write_text("# Hello", encoding="utf-8")
    meta = ManuscriptMeta(title="Test", version="1.0.0", output_dir=output_dir)
    entries = [ManifestEntry(order=1, title="Ch1", file="001.md")]
    m = Manifest(manuscript=meta, content=entries)
    return Builder(m, base_dir=str(tmp_path))


# ---------------------------------------------------------------------------
# FORMAT_MAP
# ---------------------------------------------------------------------------


class TestFormatMap:
    """Tests for :data:`FORMAT_MAP`."""

    def test_contains_expected_keys(self):
        """FORMAT_MAP has exactly the five supported format keys."""
        assert set(FORMAT_MAP.keys()) == {"docx", "epub", "html", "md", "pdf"}

    def test_values_are_two_tuples(self):
        """Each value is a (pandoc_format, extension) pair."""
        for key, val in FORMAT_MAP.items():
            assert len(val) == 2, f"{key} value should be a 2-tuple"

    def test_extensions_match_format(self):
        """Extensions correspond to their format keys."""
        for key, (_, ext) in FORMAT_MAP.items():
            expected = "md" if key == "md" else key
            assert ext == expected


# ---------------------------------------------------------------------------
# BuildResult
# ---------------------------------------------------------------------------


class TestBuildResult:
    """Unit tests for :class:`BuildResult`."""

    def test_success_field(self):
        """success field is stored correctly."""
        r = BuildResult(success=True, output_path="/out/f.docx", command=["pandoc"])
        assert r.success is True

    def test_message_defaults_empty(self):
        """message defaults to an empty string."""
        r = BuildResult(success=True, output_path="/out/f.docx", command=[])
        assert r.message == ""


# ---------------------------------------------------------------------------
# Builder — Validation
# ---------------------------------------------------------------------------


class TestBuilderValidation:
    """Tests for :class:`Builder` input validation."""

    def test_invalid_format_raises_value_error(self, sample_manifest):
        """ValueError is raised for an unsupported format key."""
        b = Builder(sample_manifest)
        with pytest.raises(ValueError, match="Unsupported format"):
            b.build("rtf", "output")

    def test_pandoc_missing_raises_runtime_error(self, sample_manifest):
        """RuntimeError is raised when pandoc is not found on PATH."""
        b = Builder(sample_manifest)
        with patch("buildbook.builder.shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="pandoc not found"):
                b.build("docx", "output")

    def test_missing_content_file_raises_file_not_found(self, tmp_path, sample_meta):
        """FileNotFoundError is raised when a content file is missing."""
        entries = [ManifestEntry(order=1, title="X", file="missing.md")]
        m = Manifest(manuscript=sample_meta, content=entries)
        b = Builder(m, base_dir=str(tmp_path))
        with patch("buildbook.builder.shutil.which", return_value="/usr/bin/pandoc"):
            with pytest.raises(FileNotFoundError, match="missing.md"):
                b.build("docx", "output")


# ---------------------------------------------------------------------------
# Builder — Command assembly
# ---------------------------------------------------------------------------


class TestBuilderCommand:
    """Tests for :meth:`Builder._build_command`."""

    def _simple_builder(self, tmp_path: Path, meta: ManuscriptMeta) -> Builder:
        entries = [ManifestEntry(order=1, title="A", file="001.md")]
        m = Manifest(manuscript=meta, content=entries)
        return Builder(m, base_dir=str(tmp_path))

    def test_command_starts_with_pandoc(self, tmp_path, sample_meta):
        """The assembled command always starts with 'pandoc'."""
        b = self._simple_builder(tmp_path, sample_meta)
        cmd = b._build_command("docx", tmp_path / "out.docx", [])
        assert cmd[0] == "pandoc"

    def test_command_includes_output_format(self, tmp_path, sample_meta):
        """The requested Pandoc format appears in the command."""
        b = self._simple_builder(tmp_path, sample_meta)
        cmd = b._build_command("html", tmp_path / "out.html", [])
        assert "html" in cmd

    def test_command_includes_output_path(self, tmp_path, sample_meta):
        """The output path appears after the -o flag."""
        b = self._simple_builder(tmp_path, sample_meta)
        out = tmp_path / "result.docx"
        cmd = b._build_command("docx", out, [])
        assert str(out) in cmd

    def test_command_includes_title_metadata(self, tmp_path, sample_meta):
        """A metadata=title argument is present in the command."""
        b = self._simple_builder(tmp_path, sample_meta)
        cmd = b._build_command("docx", tmp_path / "out.docx", [])
        assert any("title=" in arg for arg in cmd)

    def test_command_includes_version_metadata(self, tmp_path, sample_meta):
        """A metadata=version argument is present when version is set."""
        b = self._simple_builder(tmp_path, sample_meta)
        cmd = b._build_command("docx", tmp_path / "out.docx", [])
        assert any("version=" in arg for arg in cmd)

    def test_command_appends_extra_args(self, tmp_path, sample_meta):
        """Extra args are injected into the command before the output flag."""
        b = self._simple_builder(tmp_path, sample_meta)
        cmd = b._build_command("html", tmp_path / "out.html", [], extra_args=["--toc"])
        assert "--toc" in cmd

    def test_command_omits_empty_author(self, tmp_path):
        """No author metadata is added when author is an empty string."""
        meta = ManuscriptMeta(title="T")
        m = Manifest(manuscript=meta, content=[])
        b = Builder(m, base_dir=str(tmp_path))
        cmd = b._build_command("docx", tmp_path / "out.docx", [])
        assert not any("author=" in arg for arg in cmd)


# ---------------------------------------------------------------------------
# Builder — Full build flow (Pandoc mocked)
# ---------------------------------------------------------------------------


class TestBuilderBuild:
    """Tests for the full :meth:`Builder.build` flow with Pandoc mocked."""

    def test_successful_build_returns_success_true(self, tmp_path):
        """A zero Pandoc return code produces BuildResult.success == True."""
        b = _make_builder(tmp_path)
        mock_proc = MagicMock(returncode=0)
        with patch("buildbook.builder.shutil.which", return_value="/usr/bin/pandoc"):
            with patch("buildbook.builder.subprocess.run", return_value=mock_proc):
                result = b.build("docx", "output")
        assert result.success is True

    def test_successful_build_output_path_has_extension(self, tmp_path):
        """The output path carries the correct file extension."""
        b = _make_builder(tmp_path)
        mock_proc = MagicMock(returncode=0)
        with patch("buildbook.builder.shutil.which", return_value="/usr/bin/pandoc"):
            with patch("buildbook.builder.subprocess.run", return_value=mock_proc):
                result = b.build("docx", "output")
        assert result.output_path.endswith(".docx")

    def test_failed_build_returns_success_false(self, tmp_path):
        """A non-zero Pandoc return code produces BuildResult.success == False."""
        b = _make_builder(tmp_path)
        mock_proc = MagicMock(returncode=1, stderr="pandoc error", stdout="")
        with patch("buildbook.builder.shutil.which", return_value="/usr/bin/pandoc"):
            with patch("buildbook.builder.subprocess.run", return_value=mock_proc):
                result = b.build("html", "output")
        assert result.success is False
        assert "pandoc error" in result.message

    def test_all_formats_produce_correct_extension(self, tmp_path):
        """Each supported format yields the expected file extension."""
        expected = {
            "docx": ".docx",
            "epub": ".epub",
            "html": ".html",
            "md": ".md",
            "pdf": ".pdf",
        }
        for fmt, ext in expected.items():
            b = _make_builder(tmp_path, output_dir=f"../out_{fmt}")
            mock_proc = MagicMock(returncode=0)
            with patch("buildbook.builder.shutil.which", return_value="/usr/bin/pandoc"):
                with patch("buildbook.builder.subprocess.run", return_value=mock_proc):
                    result = b.build(fmt, "output")
            assert result.output_path.endswith(ext), f"{fmt} should end with {ext}"

    def test_output_directory_created(self, tmp_path):
        """The output directory is created if it does not already exist."""
        b = _make_builder(tmp_path, output_dir="../new_output_dir")
        mock_proc = MagicMock(returncode=0)
        with patch("buildbook.builder.shutil.which", return_value="/usr/bin/pandoc"):
            with patch("buildbook.builder.subprocess.run", return_value=mock_proc):
                b.build("html", "output")
        # output_dir is relative to base_dir (tmp_path), so resolve from parent
        assert (tmp_path.parent / "new_output_dir").is_dir()

    def test_build_result_contains_command(self, tmp_path):
        """BuildResult.command is a non-empty list starting with 'pandoc'."""
        b = _make_builder(tmp_path)
        mock_proc = MagicMock(returncode=0)
        with patch("buildbook.builder.shutil.which", return_value="/usr/bin/pandoc"):
            with patch("buildbook.builder.subprocess.run", return_value=mock_proc):
                result = b.build("md", "output")
        assert result.command[0] == "pandoc"
