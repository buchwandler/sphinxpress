from __future__ import annotations

from pathlib import Path

import pytest

from sphinxpress.errors import PathTraversalError
from sphinxpress.paths import (
    docname_to_output_path,
    nav_key_for,
    output_path_for,
    permalink_for,
)


def test_docname_to_output_path_rejects_path_traversal():
    with pytest.raises(PathTraversalError):
        docname_to_output_path("../escape")


def test_permalink_for_index_page():
    assert permalink_for(Path("tools"), "booktx", "index") == "/tools/booktx/"


def test_output_path_for_variant_page():
    assert output_path_for(
        Path("tools"),
        "booktx",
        "quickstart",
        variant_segment="main",
    ) == Path("tools/booktx/main/quickstart.md")


def test_permalink_for_variant_index_page():
    assert (
        permalink_for(
            Path("tools"),
            "booktx",
            "index",
            variant_segment="main",
        )
        == "/tools/booktx/main/"
    )


def test_nav_key_for_default_and_non_default_variants():
    assert nav_key_for("booktx", "release", is_default=True) == "booktx"
    assert nav_key_for("booktx", "main", is_default=False) == "booktx-main"
