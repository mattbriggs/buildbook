"""cli.py — Command-line interface for the buildbook book build system.

Provides two subcommands:

``build``
    Read a YAML manifest, concatenate Markdown source files in order, and
    pass them to Pandoc to produce a finished document.

``init``
    Scan a content directory for Markdown files, infer chapter order and
    titles, and write a YAML manifest ready for use with ``build``.

Usage::

    buildbook build -f <format> -o <output-name> [options]
    buildbook init [options]

Supported formats:  ``docx`` | ``epub`` | ``html`` | ``md`` | ``pdf``

:Example:

    .. code-block:: shell

        # Build a Word document
        buildbook build -f docx -o my-book

        # Build an EPUB from a specific manifest
        buildbook build -f epub -o my-book -m content/book.yaml

        # Build a PDF with extra Pandoc flags and verbose logging
        buildbook build -f pdf -o my-book --pandoc-args "--toc --number-sections" -v

        # Auto-generate a manifest from the content directory
        buildbook init --title "My Book" --author "Jane Author" --book-version "1.0.0"

Design note:
    Each subcommand handler (``_cmd_build``, ``_cmd_init``) follows the
    **Command Pattern**: it encapsulates a complete operation, accepting parsed
    arguments and returning an integer exit code.
"""
from __future__ import annotations

import argparse
import datetime
import logging
import sys
from pathlib import Path
from typing import List, Optional

from buildbook import __version__
from buildbook.builder import FORMAT_MAP, Builder
from buildbook.manifest import ManuscriptMeta, load_manifest
from buildbook.scanner import Scanner

#: Default manifest path relative to the current working directory.
_DEFAULT_MANIFEST = "content/book.yaml"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def _setup_logging(verbose: bool) -> None:
    """Configure the root logger.

    When *verbose* is ``True`` the level is set to ``DEBUG`` so all internal
    messages are shown.  Otherwise only ``WARNING`` and above are emitted.

    :param verbose: Enable ``DEBUG`` level logging.
    :type verbose: bool
    """
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        format="%(levelname)-8s %(name)s: %(message)s",
        level=level,
    )


# ---------------------------------------------------------------------------
# Subcommand: build
# ---------------------------------------------------------------------------


def _add_build_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    """Register the ``build`` subcommand on *subparsers*.

    :param subparsers: The subparser action group from the parent parser.
    """
    parser = subparsers.add_parser(
        "build",
        help="Compile a manuscript via Pandoc",
        description=(
            "Read a YAML manifest, concatenate Markdown files in order, "
            "and compile them with Pandoc into the requested output format."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
formats:
  docx    Microsoft Word document (.docx)
  epub    EPUB e-book (.epub)
  html    HTML document (.html)
  md      Concatenated Markdown (.md)
  pdf     PDF document (.pdf)  — requires LaTeX or wkhtmltopdf

examples:
  buildbook build -f docx -o my-book
  buildbook build -f epub -o my-book -m content/book.yaml
  buildbook build -f pdf  -o my-book --pandoc-args "--toc --number-sections"
  buildbook build -f html -o my-book --pandoc-args "--toc --standalone" -v
        """,
    )
    parser.add_argument(
        "-f", "--format",
        required=True,
        choices=list(FORMAT_MAP.keys()),
        metavar="FORMAT",
        help="output format: docx | epub | html | md | pdf  (required)",
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        metavar="NAME",
        help="output filename without extension  (required)",
    )
    parser.add_argument(
        "-m", "--manifest",
        default=_DEFAULT_MANIFEST,
        metavar="FILE",
        help=f"path to YAML manifest  (default: {_DEFAULT_MANIFEST})",
    )
    parser.add_argument(
        "--pandoc-args",
        default="",
        metavar="ARGS",
        help='extra Pandoc arguments as a quoted string, e.g. "--toc --standalone"',
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="enable verbose DEBUG logging",
    )


def _cmd_build(args: argparse.Namespace) -> int:
    """Execute the ``build`` subcommand.

    Implements the **Command Pattern**: encapsulates the build operation,
    returning an integer exit code.

    :param args: Parsed argument namespace from the ``build`` subparser.
    :type args: argparse.Namespace
    :return: ``0`` on success, ``1`` on any error.
    :rtype: int
    """
    _setup_logging(args.verbose)
    log = logging.getLogger(__name__)

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"Error: manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    try:
        manifest = load_manifest(str(manifest_path))
    except Exception as exc:  # noqa: BLE001
        print(f"Error loading manifest: {exc}", file=sys.stderr)
        return 1

    log.debug(
        "Manifest loaded: %d entries, version=%s",
        len(manifest.content),
        manifest.manuscript.version,
    )

    extra: Optional[List[str]] = (
        args.pandoc_args.split() if args.pandoc_args.strip() else None
    )

    builder = Builder(manifest, base_dir=str(manifest_path.parent))

    try:
        result = builder.build(args.format, args.output, extra_args=extra)
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if result.success:
        print(f"Success: {result.output_path}")
        log.debug("Command: %s", " ".join(result.command))
        return 0

    print(f"Build failed:\n{result.message}", file=sys.stderr)
    return 1


# ---------------------------------------------------------------------------
# Subcommand: init
# ---------------------------------------------------------------------------


def _add_init_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    """Register the ``init`` subcommand on *subparsers*.

    :param subparsers: The subparser action group from the parent parser.
    """
    parser = subparsers.add_parser(
        "init",
        help="Scan the content directory and generate a YAML manifest",
        description=(
            "Scan a content directory for Markdown files, infer chapter "
            "order and titles, and write a ready-to-use YAML manifest."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  buildbook init
  buildbook init --title "My Novel" --author "Jane Author"
  buildbook init --content-dir chapters --output chapters/book.yaml
  buildbook init --book-version "1.2.0" --force
        """,
    )
    parser.add_argument(
        "--content-dir",
        default="content",
        metavar="DIR",
        help="directory to scan for Markdown files  (default: content)",
    )
    parser.add_argument(
        "--output",
        default=None,
        metavar="FILE",
        help="path for the generated YAML manifest  (default: <content-dir>/book.yaml)",
    )
    parser.add_argument(
        "--title",
        default="My Book",
        metavar="TITLE",
        help='manuscript title  (default: "My Book")',
    )
    parser.add_argument(
        "--author",
        default="",
        metavar="AUTHOR",
        help="author name",
    )
    parser.add_argument(
        "--book-version",
        default="0.1.0",
        metavar="VERSION",
        help='semantic version string  (default: "0.1.0")',
    )
    parser.add_argument(
        "--date",
        default=str(datetime.date.today().year),
        metavar="DATE",
        help=f"publication date  (default: current year)",
    )
    parser.add_argument(
        "--output-dir",
        default="../output",
        metavar="DIR",
        help='build output directory relative to the manifest  (default: "../output")',
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite the manifest file if it already exists",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="enable verbose DEBUG logging",
    )


def _cmd_init(args: argparse.Namespace) -> int:
    """Execute the ``init`` subcommand.

    Implements the **Command Pattern**: scans the content directory,
    generates a manifest, and writes it to disk.

    :param args: Parsed argument namespace from the ``init`` subparser.
    :type args: argparse.Namespace
    :return: ``0`` on success, ``1`` on any error.
    :rtype: int
    """
    _setup_logging(args.verbose)
    log = logging.getLogger(__name__)

    content_dir = Path(args.content_dir).resolve()
    if not content_dir.is_dir():
        print(f"Error: content directory not found: {content_dir}", file=sys.stderr)
        return 1

    output_path = (
        Path(args.output) if args.output else content_dir / "book.yaml"
    )

    if output_path.exists() and not args.force:
        print(
            f"Error: '{output_path}' already exists. Use --force to overwrite.",
            file=sys.stderr,
        )
        return 1

    meta = ManuscriptMeta(
        title=args.title,
        author=args.author,
        version=args.book_version,
        date=args.date,
        output_dir=args.output_dir,
    )

    scanner = Scanner()
    try:
        manifest = scanner.generate_manifest(content_dir, meta)
    except NotADirectoryError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        scanner.save_manifest(manifest, output_path)
    except OSError as exc:
        print(f"Error writing manifest: {exc}", file=sys.stderr)
        return 1

    print(f"Manifest written: {output_path}")
    print(f"  Title:   {meta.title}")
    print(f"  Author:  {meta.author or '(not set)'}")
    print(f"  Version: {meta.version}")
    print(f"  Entries: {len(manifest.content)}")
    log.debug("Scanned %d files from %s", len(manifest.content), content_dir)
    return 0


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    """Run the buildbook CLI.

    Parses *argv* (or ``sys.argv[1:]`` when ``None``), dispatches to the
    appropriate subcommand handler, and returns an integer exit code.

    :param argv: Argument list to parse.  Defaults to ``sys.argv[1:]``.
    :type argv: list[str] | None
    :return: Exit code — ``0`` on success, ``1`` on error.
    :rtype: int
    """
    parser = argparse.ArgumentParser(
        prog="buildbook",
        description="A Pandoc-based book build system.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True

    _add_build_subparser(subparsers)
    _add_init_subparser(subparsers)

    args = parser.parse_args(argv)

    if args.command == "build":
        return _cmd_build(args)
    if args.command == "init":
        return _cmd_init(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
