# buildbook

A small Pandoc-based book build system for Markdown manuscripts. Use this
repository as a GitHub template, replace the sample chapters, keep a YAML
manifest for ordering and metadata, and build DOCX, EPUB, HTML, Markdown, or
PDF outputs with one command.

Current package version: `0.1.0`

## What It Does

- Builds an ordered manuscript from Markdown files listed in `content/book.yaml`.
- Passes manuscript metadata (`title`, `author`, `date`, `version`) to Pandoc.
- Writes finished files to the manifest's `output_dir` (`../output` by default).
- Can scan a content directory and generate a manifest with `buildbook init`.
- Renders fenced Mermaid diagrams through Mermaid CLI when diagrams are present.
- Includes pytest coverage for the manifest loader, scanner, builder, Mermaid
  preprocessor, and CLI.

## Prerequisites

### Python

Python 3.10 or later is required.

```bash
python --version
```

### Pandoc

Pandoc is required for `buildbook build` and must be available on `PATH`.

| Platform | Recommended install |
| --- | --- |
| macOS | `brew install pandoc` |
| Windows | `winget install JohnMacFarlane.Pandoc` or download from pandoc.org |
| Debian/Ubuntu | `sudo apt install pandoc` |
| Fedora | `sudo dnf install pandoc` |
| Any platform | Download from https://github.com/jgm/pandoc/releases |

Verify:

```bash
pandoc --version
```

Pandoc 3.x is recommended. Pandoc 2.11+ should work for the formats currently
supported by this project.

### Mermaid Diagrams

Markdown files may include fenced Mermaid diagrams:

````markdown
```mermaid
graph TD
    A --> B
```
````

When a Mermaid fence is present, `buildbook` uses Mermaid CLI (`mmdc`) to render
the diagram to PNG, rewrites the Markdown in a temporary build directory, and
then passes the rewritten file to Pandoc. Books without Mermaid fences do not
need `mmdc`.

Install Mermaid CLI with npm:

```bash
npm install -g @mermaid-js/mermaid-cli
mmdc --version
```

### PDF Output

PDF builds require a Pandoc PDF engine such as a LaTeX distribution or
`wkhtmltopdf`.

| Engine | Install |
| --- | --- |
| TeX Live | https://tug.org/texlive |
| MacTeX on macOS | `brew install --cask mactex-no-gui` |
| MiKTeX on Windows | https://miktex.org |
| wkhtmltopdf | https://wkhtmltopdf.org |

For `wkhtmltopdf`, pass the engine through to Pandoc:

```bash
buildbook build -f pdf -o my-book --pandoc-args "--pdf-engine=wkhtmltopdf"
```

DOCX, EPUB, HTML, and Markdown output do not require LaTeX.

## Quick Start

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install the package and development dependencies:

```bash
pip install -e ".[dev]"
```

Build from the sample manifest:

```bash
buildbook build -f docx -o my-book
buildbook build -f epub -o my-book
buildbook build -f html -o my-book --pandoc-args "--toc --standalone"
buildbook build -f md -o my-book
buildbook build -f pdf -o my-book
```

Outputs are written to `output/` with the extension for the requested format.

## CLI Reference

Check the installed CLI version:

```bash
buildbook --version
```

### `buildbook build`

Compile a manuscript through Pandoc.

```text
buildbook build -f FORMAT -o NAME [options]

required:
  -f, --format FORMAT     docx | epub | html | md | pdf
  -o, --output NAME       output filename without extension

optional:
  -m, --manifest FILE     YAML manifest path
                          default: content/book.yaml
  --pandoc-args ARGS      extra Pandoc flags as a quoted string
  -v, --verbose           enable DEBUG logging
  -h, --help              show help and exit
```

Examples:

```bash
buildbook build -f docx -o my-book
buildbook build -f epub -o my-book -m content/book.yaml
buildbook build -f pdf -o my-book-v1.0.0 --pandoc-args "--toc --number-sections"
buildbook build -f html -o my-book --pandoc-args "--toc --standalone" -v
```

`--pandoc-args` is intended for simple additional Pandoc flags and is split on
whitespace before the command is executed.

### `buildbook init`

Scan Markdown files in a content directory and write a manifest.

```text
buildbook init [options]

optional:
  --content-dir DIR       directory to scan
                          default: content
  --output FILE           generated manifest path
                          default: <content-dir>/book.yaml
  --title TITLE           manuscript title
                          default: "My Book"
  --author AUTHOR         author name
  --book-version VERSION  semantic version string
                          default: "0.1.0"
  --date DATE             publication date
                          default: current year
  --output-dir DIR        build output directory relative to the manifest
                          default: "../output"
  --force                 overwrite an existing manifest
  -v, --verbose           enable DEBUG logging
  -h, --help              show help and exit
```

Examples:

```bash
buildbook init --title "My Novel" --author "Jane Author"
buildbook init --content-dir chapters --output chapters/book.yaml
buildbook init \
  --title "My Novel" \
  --author "Jane Author" \
  --book-version "1.0.0" \
  --force
```

`init` reads the first level-one Markdown heading (`# Heading`) from each file
for the chapter title. If no heading is found, it derives a title from the
filename. Numeric prefixes such as `001-` or `03_` become the chapter order.
Files without a numeric prefix are assigned order `999`.

If `--output` points outside the content directory, make sure the parent
directory already exists. If `--force` is used, the manifest is rewritten with
the metadata supplied on the command line, so pass your current title, author,
version, date, and output directory or edit the YAML manually afterward.

## Manifest Format

The manifest is YAML with `manuscript` metadata and an ordered `content` list.
Content file paths and `output_dir` are resolved relative to the directory that
contains the manifest.

```yaml
manuscript:
  title: "My Book"
  author: "Jane Author"
  version: "1.0.0"
  date: "2026"
  output_dir: "../output"

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

Entries are built in ascending `order` value, regardless of their position in
the YAML list.

Optional metadata defaults:

| Field | Default |
| --- | --- |
| `author` | empty string |
| `version` | `0.1.0` |
| `date` | empty string when loading a manifest, current year when generated by `init` |
| `output_dir` | `../output` |

## Versioning Books

The manifest `version` field is intended to track the edition of the book using
Semantic Versioning.

| Segment | Suggested meaning |
| --- | --- |
| MAJOR | Incompatible structural or content rewrite |
| MINOR | New chapters or significant additions |
| PATCH | Corrections, copy edits, and formatting fixes |

Typical flow:

```bash
# First published edition
# Edit content/book.yaml and set version: "1.0.0"
buildbook build -f pdf -o my-book-v1.0.0

# Optional release tag
git tag -a v1.0.0 -m "First edition"
git push origin v1.0.0
```

If you prefer to regenerate the manifest while changing the version, pass the
rest of the manuscript metadata too:

```bash
buildbook init \
  --title "My Book" \
  --author "Jane Author" \
  --book-version "1.0.0" \
  --date "2026" \
  --force
```

## Project Structure

```text
buildbook/
  __init__.py           package version
  builder.py            Pandoc command assembly and build execution
  cli.py                command-line entry point
  manifest.py           manifest dataclasses and YAML loader
  mermaid.py            Mermaid fence renderer
  scanner.py            Markdown scanner and manifest generator

content/
  001-introduction.md   sample chapter
  002-chapter-one.md    sample chapter
  003-chapter-two.md    sample chapter
  book.yaml             default build manifest

output/
  .gitkeep              keeps the ignored output directory in Git

tests/
  conftest.py           shared pytest fixtures
  test_builder.py       builder tests with Pandoc mocked
  test_cli.py           CLI tests
  test_manifest.py      manifest loader tests
  test_mermaid.py       Mermaid preprocessing tests with mmdc mocked
  test_scanner.py       scanner tests

.github/workflows/ci.yml  GitHub Actions test workflow for Python 3.10-3.12
.vscode/                  VS Code settings and recommended extensions
CHANGELOG.md              release history
LICENSE                   MIT license
pyproject.toml            packaging, dependencies, entry point, pytest, Ruff
```

Build artifacts in `output/`, virtual environments, caches, coverage reports,
and package metadata are ignored by `.gitignore`.

## Running Tests

With the virtual environment activated:

```bash
pytest
```

The tests mock Pandoc and Mermaid subprocess calls, so Pandoc and `mmdc` are not
required for the test suite.

Run coverage:

```bash
pytest --cov=buildbook --cov-report=term-missing
```

The checked-in CI workflow runs:

```bash
pytest --tb=short
```

on Python 3.10, 3.11, and 3.12.

## Adding a Chapter

Create a Markdown file in `content/`, preferably with a numeric prefix:

```text
content/004-conclusion.md
```

Start it with a level-one heading:

```markdown
# Conclusion
```

Then either add it to `content/book.yaml` manually:

```yaml
- order: 4
  title: "Conclusion"
  file: "004-conclusion.md"
```

or regenerate the manifest, passing your current metadata because `--force`
rewrites the whole file:

```bash
buildbook init --title "My Book" --author "Jane Author" --force
```

Then rebuild:

```bash
buildbook build -f docx -o my-book
```

## Using This as a Template

1. On GitHub, choose **Use this template** and create a new repository.
2. Clone the new repository.
3. Create a virtual environment and run `pip install -e ".[dev]"`.
4. Replace the sample Markdown files in `content/`.
5. Update `content/book.yaml` with your title, author, version, date, and
   chapter list, or regenerate it with `buildbook init --force` plus the
   metadata flags you want to keep.
6. Update `CHANGELOG.md` and its compare links for your repository.
7. Commit and start building releases.

The template includes the Python package, CLI, tests, GitHub Actions workflow,
VS Code settings, `.gitignore`, sample content, and output directory placeholder.

## Design Notes

`buildbook` keeps the implementation intentionally small:

| Pattern | Location |
| --- | --- |
| Builder | `Builder` assembles and executes the Pandoc command |
| Template Method | `Builder.build()` coordinates validation, path resolution, preprocessing, command assembly, and execution |
| Strategy | `FORMAT_MAP` maps each output key to a Pandoc format and extension |
| Factory Method | `load_manifest()` and `Scanner.generate_manifest()` construct domain objects from YAML or the file system |
| Command | CLI handlers `_cmd_build()` and `_cmd_init()` wrap one operation each |
| Data Transfer Object | `ManifestEntry`, `ManuscriptMeta`, `Manifest`, and `BuildResult` carry data between layers |

Public modules and symbols include Sphinx-style docstrings for future generated
API documentation.
