"""buildbook — A Pandoc-based generic book build system.

This package provides a CLI and library for compiling Markdown source files
into finished book formats (DOCX, EPUB, HTML, PDF, Markdown) via Pandoc.

Typical usage::

    buildbook build -f docx -o my-book -m content/book.yaml
    buildbook init --title "My Book" --author "Jane Author"

:data:`__version__`: Package version string following `Semantic Versioning
    <https://semver.org>`_.
"""

__version__: str = "0.1.0"
