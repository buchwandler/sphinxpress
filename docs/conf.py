from __future__ import annotations

import os
import sys
from importlib import metadata

sys.path.insert(0, os.path.abspath(".."))

project = "sphinxpress"
copyright = "2026, sphinxpress contributors"
author = "sphinxpress contributors"

try:
    release = metadata.version("sphinxpress")
except metadata.PackageNotFoundError:
    try:
        from sphinxpress._version import __version__ as release
    except ImportError:
        release = "0.1.0"

version = ".".join(release.split(".")[:2])

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
]

source_suffix = {
    ".md": "markdown",
}

root_doc = "index"

myst_enable_extensions = [
    "colon_fence",
]

myst_heading_anchors = 3

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_rtd_theme"
html_title = "sphinxpress"

nitpicky = True

napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
}
