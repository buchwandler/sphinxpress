from __future__ import annotations

import pytest
from pathlib import Path

from sphinxpress.errors import PathTraversalError
from sphinxpress.paths import docname_to_output_path, permalink_for


def test_docname_to_output_path_rejects_path_traversal():
    with pytest.raises(PathTraversalError):
        docname_to_output_path("../escape")


def test_permalink_for_index_page():
    assert permalink_for(Path("tools"), "booktx", "index") == "/tools/booktx/"
