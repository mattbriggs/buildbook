"""test_mermaid.py - Tests for :mod:`buildbook.mermaid`.

Covers fence detection, successful rendering (mmdc mocked), mmdc-not-found
error, and mmdc process failure.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from buildbook.mermaid import render_mermaid_blocks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DIAGRAM_SRC = "graph TD\n    A --> B\n"

_MD_WITH_MERMAID = f"""\
# Chapter

Some text.

```mermaid
{_DIAGRAM_SRC}```

More text.
"""

_MD_NO_MERMAID = """\
# Chapter

Just prose, no diagrams here.
"""

_MD_TWO_DIAGRAMS = """\
# Chapter

```mermaid
graph LR
    X --> Y
```

Middle paragraph.

```mermaid
sequenceDiagram
    A->>B: hello
```
"""


def _write_md(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# No mermaid content
# ---------------------------------------------------------------------------


class TestNoMermaid:
    """render_mermaid_blocks returns None when no fences are present."""

    def test_returns_none_for_plain_markdown(self, tmp_path):
        md = _write_md(tmp_path, "plain.md", _MD_NO_MERMAID)
        result = render_mermaid_blocks(md, tmp_path)
        assert result is None

    def test_original_file_untouched(self, tmp_path):
        md = _write_md(tmp_path, "plain.md", _MD_NO_MERMAID)
        render_mermaid_blocks(md, tmp_path)
        assert md.read_text(encoding="utf-8") == _MD_NO_MERMAID


# ---------------------------------------------------------------------------
# Successful rendering (mmdc mocked)
# ---------------------------------------------------------------------------


class TestSuccessfulRender:
    """render_mermaid_blocks rewrites fences to image references."""

    def _run_with_mock(self, md_path: Path, work_dir: Path):
        """Call render_mermaid_blocks with mmdc mocked to create the output PNG."""

        def fake_run(cmd, **_kwargs):
            img_path = Path(cmd[cmd.index("-o") + 1])
            img_path.write_bytes(b"\x89PNG\r\n")
            return MagicMock(returncode=0)

        with patch("buildbook.mermaid.shutil.which", return_value="/usr/bin/mmdc"):
            with patch("buildbook.mermaid.subprocess.run", side_effect=fake_run):
                return render_mermaid_blocks(md_path, work_dir)

    def test_returns_path_for_mermaid_file(self, tmp_path):
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        md = _write_md(tmp_path, "chapter.md", _MD_WITH_MERMAID)
        result = self._run_with_mock(md, work_dir)
        assert result is not None
        assert result.exists()

    def test_rewritten_file_has_image_ref(self, tmp_path):
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        md = _write_md(tmp_path, "chapter.md", _MD_WITH_MERMAID)
        result = self._run_with_mock(md, work_dir)
        assert result is not None
        content = result.read_text(encoding="utf-8")
        assert "```mermaid" not in content
        assert "![](" in content
        assert ".png" in content

    def test_prose_preserved(self, tmp_path):
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        md = _write_md(tmp_path, "chapter.md", _MD_WITH_MERMAID)
        result = self._run_with_mock(md, work_dir)
        assert result is not None
        content = result.read_text(encoding="utf-8")
        assert "Some text." in content
        assert "More text." in content

    def test_two_diagrams_both_replaced(self, tmp_path):
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        md = _write_md(tmp_path, "multi.md", _MD_TWO_DIAGRAMS)
        result = self._run_with_mock(md, work_dir)
        assert result is not None
        content = result.read_text(encoding="utf-8")
        assert content.count("![]") == 2
        assert "```mermaid" not in content

    def test_file_index_prefix_in_output_names(self, tmp_path):
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        md = _write_md(tmp_path, "ch.md", _MD_WITH_MERMAID)
        self._run_with_mock(md, work_dir)
        names = [p.name for p in work_dir.iterdir()]
        assert any(n.startswith("0000-") for n in names)

    def test_different_file_indices_avoid_collision(self, tmp_path):
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        md_a = _write_md(tmp_path, "ch.md", _MD_WITH_MERMAID)

        with patch("buildbook.mermaid.shutil.which", return_value="/usr/bin/mmdc"):

            def fake_run(cmd, **_kwargs):
                img = Path(cmd[cmd.index("-o") + 1])
                img.write_bytes(b"\x89PNG")
                return MagicMock(returncode=0)

            with patch("buildbook.mermaid.subprocess.run", side_effect=fake_run):
                r1 = render_mermaid_blocks(md_a, work_dir, file_index=0)
                r2 = render_mermaid_blocks(md_a, work_dir, file_index=1)

        assert r1 is not None and r2 is not None
        assert r1.name != r2.name


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


class TestErrors:
    """Error paths raise the expected exceptions."""

    def test_mmdc_not_found_raises_runtime_error(self, tmp_path):
        md = _write_md(tmp_path, "chapter.md", _MD_WITH_MERMAID)
        with patch("buildbook.mermaid.shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="mmdc not found"):
                render_mermaid_blocks(md, tmp_path)

    def test_mmdc_failure_raises_called_process_error(self, tmp_path):
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        md = _write_md(tmp_path, "chapter.md", _MD_WITH_MERMAID)
        with patch("buildbook.mermaid.shutil.which", return_value="/usr/bin/mmdc"):
            with patch(
                "buildbook.mermaid.subprocess.run",
                side_effect=subprocess.CalledProcessError(1, "mmdc", stderr=b"parse error"),
            ):
                with pytest.raises(subprocess.CalledProcessError):
                    render_mermaid_blocks(md, work_dir)
