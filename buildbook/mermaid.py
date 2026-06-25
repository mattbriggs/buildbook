"""mermaid.py - Mermaid diagram pre-processor for the book build pipeline.

Finds ```mermaid fences in Markdown source files, renders each diagram to a
PNG image using the ``mmdc`` CLI, and rewrites the file with plain ``![]()``
image references that Pandoc understands.

:Example:

    .. code-block:: python

        import tempfile
        from pathlib import Path
        from buildbook.mermaid import render_mermaid_blocks

        with tempfile.TemporaryDirectory() as tmp:
            rewritten = render_mermaid_blocks(Path("chapter.md"), Path(tmp))
            pandoc_input = str(rewritten) if rewritten else "chapter.md"
"""
from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

#: Matches a fenced mermaid code block, capturing the diagram source.
_FENCE_RE = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)


def _check_mmdc() -> None:
    """Assert that ``mmdc`` (Mermaid CLI) is available on ``PATH``.

    :raises RuntimeError: If ``mmdc`` cannot be found.
    """
    if not shutil.which("mmdc"):
        raise RuntimeError(
            "mmdc not found in PATH. "
            "Install with: npm install -g @mermaid-js/mermaid-cli"
        )


def render_mermaid_blocks(
    md_path: Path,
    work_dir: Path,
    file_index: int = 0,
) -> Optional[Path]:
    """Render all mermaid fences in *md_path* to PNG images.

    For each mermaid fence found:

    1. Write the diagram source to a ``.mmd`` scratch file in *work_dir*.
    2. Call ``mmdc`` to render it as a ``.png`` in *work_dir*.
    3. Replace the fence with ``![](absolute/path/to/image.png)``.

    Returns the path to a rewritten Markdown file in *work_dir* when any
    diagrams were rendered, or ``None`` if the file contained no mermaid
    fences (the caller should then use the original file unchanged).

    :param md_path: Source Markdown file to process.
    :param work_dir: Scratch directory for generated images and temp Markdown.
    :param file_index: Integer prefix added to temp filenames so multiple
        source files with the same basename don't collide in *work_dir*.
    :return: Path to the rewritten file, or ``None`` if no diagrams found.
    :raises RuntimeError: If ``mmdc`` is not found on ``PATH``.
    :raises subprocess.CalledProcessError: If ``mmdc`` fails on a diagram.
    """
    text = md_path.read_text(encoding="utf-8")
    if not _FENCE_RE.search(text):
        return None

    _check_mmdc()

    diagram_counter = 0

    def _render(match: re.Match) -> str:  # type: ignore[type-arg]
        nonlocal diagram_counter
        diagram_counter += 1
        diagram_src = match.group(1)
        stem = f"{file_index:04d}-{md_path.stem}-diagram-{diagram_counter}"
        src_file = work_dir / f"{stem}.mmd"
        img_file = work_dir / f"{stem}.png"

        src_file.write_text(diagram_src, encoding="utf-8")
        logger.debug(
            "Rendering mermaid diagram %d from %s", diagram_counter, md_path.name
        )

        subprocess.run(
            ["mmdc", "-i", str(src_file), "-o", str(img_file)],
            check=True,
            capture_output=True,
        )

        return f"![]({img_file})"

    new_text = _FENCE_RE.sub(_render, text)

    tmp_md = work_dir / f"{file_index:04d}-{md_path.name}"
    tmp_md.write_text(new_text, encoding="utf-8")
    logger.debug(
        "Rewrote %s -> %s (%d diagram(s))", md_path.name, tmp_md, diagram_counter
    )
    return tmp_md
