"""conftest.py — Pytest configuration for the buildbook test suite.

Shared fixtures used across all test modules live here so they are
available without explicit imports.

Note:
    Install the package in editable mode before running the suite::

        pip install -e ".[dev]"
        pytest

    This ensures ``buildbook`` is importable without ``sys.path`` manipulation.
"""
from __future__ import annotations

import pytest
import yaml

from buildbook.manifest import Manifest, ManifestEntry, ManuscriptMeta


@pytest.fixture()
def sample_meta() -> ManuscriptMeta:
    """Return a minimal :class:`~buildbook.manifest.ManuscriptMeta` instance.

    :return: Populated manuscript metadata.
    :rtype: ManuscriptMeta
    """
    return ManuscriptMeta(
        title="Test Manuscript",
        author="Test Author",
        version="1.2.3",
        date="2026",
        output_dir="../output",
    )


@pytest.fixture()
def sample_entries() -> list[ManifestEntry]:
    """Return two :class:`~buildbook.manifest.ManifestEntry` objects in ascending order.

    :return: List of two manifest entries.
    :rtype: list[ManifestEntry]
    """
    return [
        ManifestEntry(order=1, title="Chapter One", file="001-chapter-one.md"),
        ManifestEntry(order=2, title="Chapter Two", file="002-chapter-two.md"),
    ]


@pytest.fixture()
def sample_manifest(sample_meta: ManuscriptMeta, sample_entries: list[ManifestEntry]) -> Manifest:
    """Return a :class:`~buildbook.manifest.Manifest` built from the sample fixtures.

    :param sample_meta: Manuscript metadata fixture.
    :param sample_entries: Content entries fixture.
    :return: Fully populated manifest.
    :rtype: Manifest
    """
    return Manifest(manuscript=sample_meta, content=sample_entries)


@pytest.fixture()
def manifest_yaml_file(tmp_path):
    """Write a valid YAML manifest to a temp file and return its :class:`~pathlib.Path`.

    :param tmp_path: Pytest-provided temporary directory.
    :return: Path to the written YAML file.
    :rtype: pathlib.Path
    """
    data = {
        "manuscript": {
            "title": "Test Book",
            "author": "Test Author",
            "version": "0.2.0",
            "date": "2026",
            "output_dir": "../output",
        },
        "content": [
            {"order": 1, "title": "Intro", "file": "001-intro.md"},
            {"order": 2, "title": "Body", "file": "002-body.md"},
        ],
    }
    p = tmp_path / "test.yaml"
    p.write_text(yaml.dump(data), encoding="utf-8")
    return p
