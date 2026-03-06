# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

_Changes planned or in progress that have not yet been released._

---

## [0.1.0] — 2026-03-06

### Added

- Initial release of the `buildbook` template.
- `buildbook build` command: compile a YAML-manifest-driven Markdown
  manuscript into DOCX, EPUB, HTML, PDF, or concatenated Markdown via Pandoc.
- `buildbook init` command: scan a content directory for Markdown files,
  infer chapter order and titles, and write a ready-to-use YAML manifest.
- `ManuscriptMeta.version` field for semantic-versioning support in manifests.
- Three sample chapters in `content/` as starting-point placeholders.
- `pyproject.toml`-based packaging with an editable-install dev workflow.
- GitHub Actions CI workflow running the test suite on Python 3.10–3.12.
- VS Code workspace settings and recommended extensions.

[Unreleased]: https://github.com/YOUR_USERNAME/YOUR_REPO/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/YOUR_USERNAME/YOUR_REPO/releases/tag/v0.1.0
