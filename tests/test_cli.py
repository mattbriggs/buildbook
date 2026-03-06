"""test_cli.py — Integration-style tests for :mod:`buildbook.cli`.

Tests the ``build`` and ``init`` subcommands of :func:`buildbook.cli.main`
end-to-end, mocking Pandoc subprocess calls and file-system side effects
where needed.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from buildbook.cli import main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_manifest(tmp_path: Path, output_dir: str = "../out") -> Path:
    """Write a minimal valid manifest YAML and a chapter file, return manifest path.

    :param tmp_path: Pytest temporary directory.
    :param output_dir: Value for the output_dir field.
    :return: Path to the written manifest file.
    :rtype: Path
    """
    (tmp_path / "001.md").write_text("# Hello", encoding="utf-8")
    data = {
        "manuscript": {"title": "T", "version": "1.0.0", "output_dir": output_dir},
        "content": [{"order": 1, "title": "Ch1", "file": "001.md"}],
    }
    manifest_path = tmp_path / "m.yaml"
    manifest_path.write_text(yaml.dump(data), encoding="utf-8")
    return manifest_path


# ---------------------------------------------------------------------------
# build subcommand — argument validation
# ---------------------------------------------------------------------------


class TestBuildArgValidation:
    """Tests for argument validation in the ``build`` subcommand."""

    def test_missing_format_exits(self):
        """SystemExit is raised when -f / --format is missing."""
        with pytest.raises(SystemExit):
            main(["build", "-o", "output"])

    def test_missing_output_exits(self):
        """SystemExit is raised when -o / --output is missing."""
        with pytest.raises(SystemExit):
            main(["build", "-f", "docx"])

    def test_invalid_format_exits(self):
        """SystemExit is raised for an unsupported format value."""
        with pytest.raises(SystemExit):
            main(["build", "-f", "rtf", "-o", "output"])


# ---------------------------------------------------------------------------
# build subcommand — runtime errors
# ---------------------------------------------------------------------------


class TestBuildRuntimeErrors:
    """Tests for runtime error handling in the ``build`` subcommand."""

    def test_missing_manifest_returns_1(self, tmp_path):
        """Exit code 1 is returned when the manifest file does not exist."""
        code = main(["build", "-f", "docx", "-o", "out", "-m", str(tmp_path / "no.yaml")])
        assert code == 1

    def test_invalid_manifest_yaml_returns_1(self, tmp_path):
        """Exit code 1 is returned for malformed YAML."""
        bad = tmp_path / "bad.yaml"
        bad.write_text("not: valid: yaml: [", encoding="utf-8")
        code = main(["build", "-f", "docx", "-o", "out", "-m", str(bad)])
        assert code == 1

    def test_failed_pandoc_returns_1(self, tmp_path):
        """Exit code 1 is returned when Pandoc exits with a non-zero code."""
        manifest_path = _write_manifest(tmp_path)
        mock_proc = MagicMock(returncode=1, stderr="pandoc: error", stdout="")
        with patch("buildbook.builder.shutil.which", return_value="/usr/bin/pandoc"):
            with patch("buildbook.builder.subprocess.run", return_value=mock_proc):
                code = main(["build", "-f", "docx", "-o", "out", "-m", str(manifest_path)])
        assert code == 1


# ---------------------------------------------------------------------------
# build subcommand — successful builds
# ---------------------------------------------------------------------------


class TestBuildSuccess:
    """Tests for successful build outcomes."""

    def test_successful_build_returns_0(self, tmp_path):
        """Exit code 0 is returned on a successful build."""
        manifest_path = _write_manifest(tmp_path)
        mock_proc = MagicMock(returncode=0)
        with patch("buildbook.builder.shutil.which", return_value="/usr/bin/pandoc"):
            with patch("buildbook.builder.subprocess.run", return_value=mock_proc):
                code = main(["build", "-f", "docx", "-o", "output", "-m", str(manifest_path)])
        assert code == 0

    def test_extra_pandoc_args_passed_through(self, tmp_path):
        """Extra Pandoc arguments from --pandoc-args appear in the subprocess call."""
        manifest_path = _write_manifest(tmp_path)
        captured: list[str] = []

        def fake_run(cmd, **_):
            captured.extend(cmd)
            return MagicMock(returncode=0)

        with patch("buildbook.builder.shutil.which", return_value="/usr/bin/pandoc"):
            with patch("buildbook.builder.subprocess.run", side_effect=fake_run):
                main([
                    "build", "-f", "html", "-o", "output",
                    "-m", str(manifest_path),
                    "--pandoc-args", "--toc --standalone",
                ])

        assert "--toc" in captured
        assert "--standalone" in captured

    def test_all_formats_return_0(self, tmp_path):
        """All five supported formats return exit code 0 on success."""
        for fmt in ("docx", "epub", "html", "md", "pdf"):
            manifest_path = _write_manifest(tmp_path, output_dir=f"../out_{fmt}")
            mock_proc = MagicMock(returncode=0)
            with patch("buildbook.builder.shutil.which", return_value="/usr/bin/pandoc"):
                with patch("buildbook.builder.subprocess.run", return_value=mock_proc):
                    code = main([
                        "build", "-f", fmt, "-o", "output", "-m", str(manifest_path)
                    ])
            assert code == 0, f"format {fmt!r} should return 0"


# ---------------------------------------------------------------------------
# init subcommand
# ---------------------------------------------------------------------------


class TestInitSubcommand:
    """Tests for the ``init`` subcommand."""

    def test_creates_manifest_file(self, tmp_path):
        """init writes a YAML manifest to <content-dir>/book.yaml."""
        (tmp_path / "001-intro.md").write_text("# Intro", encoding="utf-8")
        code = main([
            "init",
            "--content-dir", str(tmp_path),
            "--title", "My Book",
            "--author", "Jane",
        ])
        assert code == 0
        assert (tmp_path / "book.yaml").exists()

    def test_generated_yaml_is_valid(self, tmp_path):
        """The generated manifest is valid YAML with expected keys."""
        (tmp_path / "001-intro.md").write_text("# Intro", encoding="utf-8")
        main(["init", "--content-dir", str(tmp_path)])
        data = yaml.safe_load((tmp_path / "book.yaml").read_text(encoding="utf-8"))
        assert "manuscript" in data
        assert "content" in data

    def test_title_stored_in_manifest(self, tmp_path):
        """The --title argument is written into the manifest."""
        (tmp_path / "001.md").write_text("# X", encoding="utf-8")
        main(["init", "--content-dir", str(tmp_path), "--title", "Custom Title"])
        data = yaml.safe_load((tmp_path / "book.yaml").read_text(encoding="utf-8"))
        assert data["manuscript"]["title"] == "Custom Title"

    def test_version_stored_in_manifest(self, tmp_path):
        """The --book-version argument is written into the manifest."""
        (tmp_path / "001.md").write_text("# X", encoding="utf-8")
        main(["init", "--content-dir", str(tmp_path), "--book-version", "2.0.0"])
        data = yaml.safe_load((tmp_path / "book.yaml").read_text(encoding="utf-8"))
        assert data["manuscript"]["version"] == "2.0.0"

    def test_refuses_overwrite_without_force(self, tmp_path):
        """init returns 1 and does not overwrite an existing manifest without --force."""
        (tmp_path / "001.md").write_text("# X", encoding="utf-8")
        existing = tmp_path / "book.yaml"
        existing.write_text("existing: content\n", encoding="utf-8")
        code = main(["init", "--content-dir", str(tmp_path)])
        assert code == 1
        assert existing.read_text(encoding="utf-8") == "existing: content\n"

    def test_force_overwrites_existing_manifest(self, tmp_path):
        """init with --force replaces an existing manifest."""
        (tmp_path / "001.md").write_text("# X", encoding="utf-8")
        existing = tmp_path / "book.yaml"
        existing.write_text("old: data\n", encoding="utf-8")
        code = main(["init", "--content-dir", str(tmp_path), "--force"])
        assert code == 0
        data = yaml.safe_load(existing.read_text(encoding="utf-8"))
        assert "manuscript" in data

    def test_custom_output_path(self, tmp_path):
        """The --output argument controls where the manifest is written."""
        (tmp_path / "001.md").write_text("# X", encoding="utf-8")
        out = tmp_path / "custom" / "manifest.yaml"
        out.parent.mkdir()
        code = main(["init", "--content-dir", str(tmp_path), "--output", str(out)])
        assert code == 0
        assert out.exists()

    def test_nonexistent_content_dir_returns_1(self, tmp_path):
        """init returns 1 when the content directory does not exist."""
        code = main(["init", "--content-dir", str(tmp_path / "missing")])
        assert code == 1

    def test_scans_correct_number_of_files(self, tmp_path):
        """init discovers all Markdown files in the content directory."""
        for i in range(1, 4):
            (tmp_path / f"00{i}-ch.md").write_text(f"# Ch {i}", encoding="utf-8")
        main(["init", "--content-dir", str(tmp_path), "--force"])
        data = yaml.safe_load((tmp_path / "book.yaml").read_text(encoding="utf-8"))
        assert len(data["content"]) == 3


# ---------------------------------------------------------------------------
# --version flag
# ---------------------------------------------------------------------------


class TestVersionFlag:
    """Tests for the top-level --version flag."""

    def test_version_exits_cleanly(self):
        """--version raises SystemExit (argparse standard behaviour)."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0
