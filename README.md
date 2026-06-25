# buildbook

A Pandoc-based generic book build system — **use this repository as a GitHub
template** to start any book project.

Write your chapters in Markdown, describe their order in a YAML manifest, and
compile to Word, EPUB, PDF, HTML, or Markdown with a single command.

---

## Table of Contents

- [Prerequisites](#prerequisites)
  - [Pandoc](#pandoc)
  - [Mermaid diagrams](#mermaid-diagrams)
  - [PDF output](#pdf-output)
  - [Python](#python)
- [Quick Start](#quick-start)
- [CLI Reference](#cli-reference)
  - [build](#build)
  - [init](#init)
- [Manifest Format](#manifest-format)
- [Semantic Versioning](#semantic-versioning)
- [Project Structure](#project-structure)
- [Running Tests](#running-tests)
- [Adding a Chapter](#adding-a-chapter)
- [Using as a GitHub Template](#using-as-a-github-template)
- [Design Notes](#design-notes)

---

## Prerequisites

### Pandoc

Pandoc is the document-conversion engine that powers `buildbook`. It must be
installed separately and available on your `PATH`.

| Platform | Recommended method |
|---|---|
| **macOS** | `brew install pandoc` |
| **Windows** | Download from [pandoc.org/installing](https://pandoc.org/installing.html) or `winget install JohnMacFarlane.Pandoc` |
| **Linux (Debian/Ubuntu)** | `sudo apt install pandoc` |
| **Linux (Fedora)** | `sudo dnf install pandoc` |
| **Any platform** | Download from [github.com/jgm/pandoc/releases](https://github.com/jgm/pandoc/releases) |

Verify the installation:

```bash
pandoc --version
```

Pandoc 3.x is recommended. Version 2.11+ will work for all formats except
those requiring newer Lua filters.

### Mermaid diagrams

Markdown files may include fenced Mermaid diagrams:

````markdown
```mermaid
graph TD
    A --> B
```
````

When Mermaid fences are present, `buildbook` renders them to PNG files with
Mermaid CLI before invoking Pandoc, then passes rewritten Markdown with image
references that Pandoc can include in DOCX, EPUB, HTML, PDF, and Markdown
outputs.

Install Mermaid CLI with npm:

```bash
npm install -g @mermaid-js/mermaid-cli
mmdc --version
```

Books without Mermaid fences do not require `mmdc`.

### PDF output

PDF output requires a LaTeX distribution **or** `wkhtmltopdf`:

| Engine | Install |
|---|---|
| **TeX Live** (recommended, cross-platform) | [tug.org/texlive](https://tug.org/texlive/) |
| **MacTeX** (macOS) | `brew install --cask mactex-no-gui` |
| **MiKTeX** (Windows) | [miktex.org](https://miktex.org) |
| **wkhtmltopdf** (lightweight alternative) | [wkhtmltopdf.org](https://wkhtmltopdf.org) — pass `--pandoc-args "--pdf-engine=wkhtmltopdf"` |

EPUB, DOCX, HTML, and concatenated Markdown **do not** require LaTeX.

### Python

Python 3.10 or later is required:

```bash
python --version
```

---

## Quick Start

### 1. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate      # macOS / Linux
# .venv\Scripts\activate       # Windows PowerShell
```

### 2. Install buildbook

```bash
pip install -e ".[dev]"
```

This installs the `buildbook` CLI and all development dependencies (pytest).

### 3. Run your first build

```bash
# Word document (no LaTeX required)
buildbook build -f docx -o my-book

# EPUB
buildbook build -f epub -o my-book

# PDF (requires LaTeX)
buildbook build -f pdf -o my-book

# HTML with table of contents
buildbook build -f html -o my-book --pandoc-args "--toc --standalone"

# Concatenated Markdown
buildbook build -f md -o my-book
```

Output files are written to `output/`.

---

## CLI Reference

### build

Compile a manuscript via Pandoc.

```
buildbook build -f FORMAT -o NAME [options]

required:
  -f, --format FORMAT     output format: docx | epub | html | md | pdf
  -o, --output NAME       base output filename without extension

optional:
  -m, --manifest FILE     YAML manifest path  (default: content/book.yaml)
  --pandoc-args ARGS      extra Pandoc flags as a quoted string
  -v, --verbose           enable DEBUG logging
  -h, --help              show help and exit
```

**Examples:**

```bash
buildbook build -f docx -o my-book
buildbook build -f pdf  -o my-book-v1.0 --pandoc-args "--toc --number-sections"
buildbook build -f html -o my-book -m content/book.yaml --pandoc-args "--standalone"
buildbook build -f epub -o my-book -v
```

---

### init

Scan the content directory for Markdown files and generate a `book.yaml`
manifest automatically.

```
buildbook init [options]

optional:
  --content-dir DIR       directory to scan  (default: content)
  --output FILE           path for the generated manifest
                          (default: <content-dir>/book.yaml)
  --title TITLE           manuscript title  (default: "My Book")
  --author AUTHOR         author name
  --book-version VERSION  semantic version string  (default: "0.1.0")
  --date DATE             publication date  (default: current year)
  --output-dir DIR        build output directory relative to manifest
                          (default: "../output")
  --force                 overwrite an existing manifest
  -v, --verbose           enable DEBUG logging
  -h, --help              show help and exit
```

**Examples:**

```bash
# Generate manifest from the default content/ directory
buildbook init --title "My Novel" --author "Jane Author"

# Specify a custom directory and version
buildbook init --content-dir chapters --book-version "1.0.0"

# Overwrite an existing manifest
buildbook init --title "Updated Title" --force
```

`init` reads the first `# Heading` from each Markdown file to extract its
chapter title. If no heading is found, the title is derived from the
filename (e.g. `003-getting-started.md` becomes `"Getting Started"`).

---

## Manifest Format

The manifest is a YAML file with two sections. File paths in `content:` are
resolved relative to the directory containing the manifest file.

```yaml
manuscript:
  title: "My Book"
  author: "Jane Author"       # optional
  version: "1.0.0"            # optional; follows Semantic Versioning
  date: "2026"                # optional; passed to Pandoc as metadata
  output_dir: "../output"     # optional; relative to the manifest file

content:
  - order: 1
    title: "Introduction"
    file: "001-introduction.md"
  - order: 2
    title: "Chapter One"
    file: "002-chapter-one.md"
  - order: 3
    title: "Chapter Two"
    file: "003-chapter-two.md"
```

Files are concatenated in ascending `order` value regardless of their
position in the list. The default manifest is `content/book.yaml`.

---

## Semantic Versioning

The `version` field in the manifest tracks the edition of the book following
[Semantic Versioning](https://semver.org):

| Segment | Meaning |
|---|---|
| **MAJOR** | Incompatible structural or content rewrite |
| **MINOR** | New chapters, significant additions |
| **PATCH** | Corrections, copy-edits, formatting fixes |

**Recommended workflow:**

1. Start at `0.1.0` during drafting.
2. Bump to `1.0.0` for the first published edition.
3. Update the manifest with `buildbook init --book-version 1.0.0 --force`
   or edit `content/book.yaml` directly.
4. Include the version in the output filename:

```bash
buildbook build -f pdf -o my-book-v1.0.0
```

5. Tag the release in Git:

```bash
git tag -a v1.0.0 -m "First edition"
git push origin v1.0.0
```

---

## Project Structure

```
buildbook/              Python package (the build tool — extend but do not delete)
  __init__.py           Package version (__version__)
  manifest.py           ManifestEntry, ManuscriptMeta, Manifest DTOs + loader
  builder.py            Builder class, BuildResult dataclass, FORMAT_MAP
  mermaid.py            Renders Mermaid fences to Pandoc-readable images
  scanner.py            Scanner — auto-generates manifests from a directory
  cli.py                CLI entry point (build and init subcommands)

content/                Your book content (edit freely)
  001-introduction.md   Sample chapter — replace with your own
  002-chapter-one.md    Sample chapter — replace with your own
  003-chapter-two.md    Sample chapter — replace with your own
  book.yaml             Build manifest — edit to match your book

output/                 Compiled artefacts land here (git-ignored, .gitkeep kept)

tests/
  conftest.py           Shared pytest fixtures
  test_manifest.py      Tests for manifest models and loader
  test_builder.py       Tests for Builder (Pandoc mocked)
  test_mermaid.py       Tests for Mermaid preprocessing (mmdc mocked)
  test_scanner.py       Tests for Scanner
  test_cli.py           End-to-end CLI tests

pyproject.toml          Package config, entry points, dependencies, tool settings
CHANGELOG.md            Release history in Keep a Changelog format
.github/workflows/      GitHub Actions CI — runs tests on Python 3.10 / 3.11 / 3.12
.vscode/                VS Code settings and recommended extensions
```

---

## Running Tests

With the virtual environment activated:

```bash
pytest
```

All tests mock the Pandoc and Mermaid CLI subprocesses — neither Pandoc nor
`mmdc` need to be installed to run the test suite.

Run with coverage:

```bash
pytest --cov=buildbook --cov-report=term-missing
```

---

## Adding a Chapter

1. Create your Markdown file in `content/`, e.g. `content/004-conclusion.md`.
   Open it with a `# Heading` to set the chapter title.

2. Either add an entry to `content/book.yaml` manually:

   ```yaml
   - order: 4
     title: "Conclusion"
     file: "004-conclusion.md"
   ```

   Or regenerate the manifest automatically (`--force` to overwrite):

   ```bash
   buildbook init --force
   ```

3. Rebuild:

   ```bash
   buildbook build -f docx -o my-book
   ```

---

## Using as a GitHub Template

This repository is designed to be a **GitHub Template Repository**.

### First time

1. On GitHub, click **Use this template → Create a new repository**.
2. Clone your new repository:

   ```bash
   git clone https://github.com/YOU/YOUR-BOOK.git
   cd YOUR-BOOK
   ```

3. Create the virtual environment and install:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

4. Replace the sample chapters in `content/` with your own writing.
5. Update `content/book.yaml` — set your title, author, and `version: "0.1.0"`.
6. Update the compare links at the bottom of `CHANGELOG.md` to point to your
   repository URL.
7. Commit and start writing.

### What carries over from the template

- The `buildbook/` package and CLI — no changes needed unless you want to extend it.
- The `tests/` suite — existing tests continue to work; add your own alongside them.
- GitHub Actions CI (`.github/workflows/ci.yml`) — runs automatically on push and PR.
- VS Code settings (`.vscode/`) — Python interpreter, linting, and Markdown
  word-wrap are pre-configured.

---

## Design Notes

`buildbook` uses several software design patterns to keep the codebase small
and extensible:

| Pattern | Location |
|---|---|
| **Builder** | `Builder` assembles the Pandoc command incrementally through private helper methods |
| **Template Method** | `Builder.build()` defines the algorithm skeleton; `_check_pandoc()`, `_resolve_inputs()`, and `_build_command()` supply the variable steps |
| **Strategy** | `FORMAT_MAP` maps each format key to a `(pandoc_format, extension)` pair — adding a new format requires one dictionary entry |
| **Factory Method** | `load_manifest()` constructs a fully populated `Manifest` from YAML without exposing construction details to callers |
| **Command** | Each CLI subcommand handler (`_cmd_build`, `_cmd_init`) is a self-contained function that encapsulates one operation and returns an integer exit code |
| **Data Transfer Object** | `ManifestEntry`, `ManuscriptMeta`, `Manifest`, and `BuildResult` are plain dataclasses that carry data between layers with no business logic |

All public symbols carry **Sphinx-compatible docstrings** (`:param:`,
`:type:`, `:return:`, `:rtype:`, `:raises:`), making the codebase ready for
automated API documentation with Sphinx or pdoc.
