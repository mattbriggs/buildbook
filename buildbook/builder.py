"""builder.py — Pandoc-based manuscript builder.

Provides :class:`Builder`, which assembles a Pandoc command from a
:class:`~buildbook.manifest.Manifest` and executes it, and
:class:`BuildResult`, which carries the outcome of that execution.

Design patterns used:

* **Builder Pattern** — :class:`Builder` incrementally assembles a complex
  Pandoc command through dedicated helper methods before executing it.
* **Template Method Pattern** — :meth:`Builder.build` defines the algorithm
  skeleton (validate -> check Pandoc -> resolve inputs -> build command ->
  execute) while the private methods supply the variable steps.
* **Strategy Pattern** — :data:`FORMAT_MAP` maps each user-facing format key
  to a ``(pandoc_format, extension)`` pair, letting the caller choose an output
  strategy without branching logic in :class:`Builder`.

:Example:

    .. code-block:: python

        from buildbook.manifest import load_manifest
        from buildbook.builder import Builder

        manifest = load_manifest("content/book.yaml")
        builder = Builder(manifest, base_dir="content")
        result = builder.build("docx", "my-book")
        if result.success:
            print("Written to", result.output_path)
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from buildbook.manifest import Manifest
from buildbook.mermaid import render_mermaid_blocks

logger = logging.getLogger(__name__)

#: Mapping from user-facing format name to ``(pandoc_format, file_extension)``.
#: This implements the **Strategy Pattern**: each entry defines the conversion
#: strategy for a given output format.
FORMAT_MAP: Dict[str, Tuple[str, str]] = {
    "docx": ("docx", "docx"),
    "epub": ("epub", "epub"),
    "html": ("html", "html"),
    "md": ("markdown", "md"),
    "pdf": ("pdf", "pdf"),
}


@dataclass
class BuildResult:
    """Outcome of a single manuscript build operation (Data Transfer Object).

    :param success: ``True`` if Pandoc exited with return code 0.
    :param output_path: Path to the produced file (may not exist on failure).
    :param command: The exact Pandoc command that was executed.
    :param message: Human-readable success or error message.
    """

    success: bool
    output_path: str
    command: List[str]
    message: str = ""


class Builder:
    """Builds a manuscript from a :class:`~buildbook.manifest.Manifest` using Pandoc.

    Resolves content file paths relative to *base_dir*, concatenates them as
    Pandoc input, and writes the result to
    ``<output_dir>/<output_name>.<ext>``.

    Implements the **Builder Pattern**: the public :meth:`build` method
    orchestrates private helper methods that each handle one step of
    constructing and running the Pandoc command.

    :param manifest: The build manifest describing metadata and content files.
    :param base_dir: Directory used to resolve relative paths in the manifest.
        Defaults to the current working directory.
    """

    def __init__(self, manifest: Manifest, base_dir: str = ".") -> None:
        """Initialise the Builder.

        :param manifest: Parsed :class:`~buildbook.manifest.Manifest`.
        :param base_dir: Base directory for resolving content files and the
            output directory.
        """
        self.manifest = manifest
        self.base_dir = Path(base_dir)
        self._logger = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # Private helpers (Template Method steps)
    # ------------------------------------------------------------------

    def _check_pandoc(self) -> None:
        """Assert that ``pandoc`` is available on ``PATH``.

        :raises RuntimeError: If the ``pandoc`` executable cannot be found.
        """
        if not shutil.which("pandoc"):
            raise RuntimeError(
                "pandoc not found in PATH. "
                "Install from https://pandoc.org/installing.html"
            )

    def _resolve_inputs(self) -> List[str]:
        """Return absolute paths for all content files, in manifest order.

        :return: List of absolute file path strings.
        :rtype: List[str]
        :raises FileNotFoundError: If any content file does not exist on disk.
        """
        paths: List[str] = []
        for entry in self.manifest.ordered_entries:
            p = self.base_dir / entry.file
            if not p.exists():
                raise FileNotFoundError(
                    f"Content file not found: {p} (entry: {entry.title!r})"
                )
            paths.append(str(p))
        return paths

    def _build_command(
        self,
        pandoc_fmt: str,
        output_path: Path,
        input_files: List[str],
        extra_args: Optional[List[str]] = None,
    ) -> List[str]:
        """Assemble the Pandoc CLI command list.

        :param pandoc_fmt: Pandoc output format string (e.g. ``"docx"``).
        :param output_path: Destination file path.
        :param input_files: Ordered list of input Markdown file paths.
        :param extra_args: Additional Pandoc arguments appended before the
            ``-o`` flag.
        :return: Command as a list of strings for :func:`subprocess.run`.
        :rtype: List[str]
        """
        meta = self.manifest.manuscript
        cmd: List[str] = ["pandoc", "--from", "markdown", "--to", pandoc_fmt]

        if meta.title:
            cmd += ["--metadata", f"title={meta.title}"]
        if meta.author:
            cmd += ["--metadata", f"author={meta.author}"]
        if meta.date:
            cmd += ["--metadata", f"date={meta.date}"]
        if meta.version:
            cmd += ["--metadata", f"version={meta.version}"]

        if extra_args:
            cmd += extra_args

        cmd += ["-o", str(output_path)]
        cmd += input_files
        return cmd

    def _output_path(self, output_name: str, ext: str) -> Path:
        """Resolve and create the output directory, then return the output path.

        :param output_name: Base filename without extension.
        :param ext: File extension (without leading dot).
        :return: Resolved output file path.
        :rtype: Path
        """
        output_dir = self.base_dir / self.manifest.manuscript.output_dir
        path = output_dir / f"{output_name}.{ext}"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _preprocess_mermaid(
        self, input_files: List[str], work_dir: Path
    ) -> List[str]:
        """Render mermaid diagrams in each input file and return updated paths.

        For files that contain mermaid fences the rewritten temp file path is
        returned; files with no mermaid content are returned unchanged.

        :param input_files: Ordered list of absolute input file paths.
        :param work_dir: Scratch directory for rendered images and temp files.
        :return: List of file paths with mermaid-containing files replaced by
            their rewritten counterparts in *work_dir*.
        :raises RuntimeError: If ``mmdc`` is not found and diagrams are present.
        :raises subprocess.CalledProcessError: If ``mmdc`` fails to render.
        """
        result: List[str] = []
        for i, f in enumerate(input_files):
            rewritten = render_mermaid_blocks(Path(f), work_dir, file_index=i)
            result.append(str(rewritten) if rewritten is not None else f)
            if rewritten is not None:
                self._logger.info("Rendered mermaid diagrams in %s", Path(f).name)
        return result

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(
        self,
        fmt: str,
        output_name: str,
        extra_args: Optional[List[str]] = None,
    ) -> BuildResult:
        """Build the manuscript in the requested output format.

        Implements the **Template Method Pattern**: this method defines the
        fixed algorithm skeleton while delegating variable steps to private
        helpers.

        :param fmt: Output format key — one of ``"docx"``, ``"epub"``,
            ``"html"``, ``"md"``, or ``"pdf"``.
        :param output_name: Base filename for the output (no extension).
        :param extra_args: Additional Pandoc CLI arguments, e.g.
            ``["--toc", "--standalone"]``.
        :return: :class:`BuildResult` describing success or failure.
        :rtype: BuildResult
        :raises ValueError: If *fmt* is not in :data:`FORMAT_MAP`.
        :raises RuntimeError: If ``pandoc`` is not found on ``PATH``.
        :raises FileNotFoundError: If a content file listed in the manifest
            does not exist on disk.
        """
        if fmt not in FORMAT_MAP:
            raise ValueError(
                f"Unsupported format {fmt!r}. Choose from: "
                + ", ".join(FORMAT_MAP)
            )

        self._check_pandoc()

        pandoc_fmt, ext = FORMAT_MAP[fmt]
        out_path = self._output_path(output_name, ext)
        input_files = self._resolve_inputs()

        with tempfile.TemporaryDirectory(prefix="buildbook-") as tmp:
            processed_files = self._preprocess_mermaid(input_files, Path(tmp))
            cmd = self._build_command(pandoc_fmt, out_path, processed_files, extra_args)

            self._logger.info("Building %s -> %s", fmt, out_path)
            self._logger.debug("Command: %s", " ".join(cmd))

            proc = subprocess.run(cmd, capture_output=True, text=True)

        if proc.returncode == 0:
            msg = f"Built: {out_path}"
            self._logger.info(msg)
            return BuildResult(
                success=True,
                output_path=str(out_path),
                command=cmd,
                message=msg,
            )

        error_msg = proc.stderr.strip() or proc.stdout.strip()
        self._logger.error("Build failed: %s", error_msg)
        return BuildResult(
            success=False,
            output_path=str(out_path),
            command=cmd,
            message=error_msg,
        )
