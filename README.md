[![PyPI - Version](https://img.shields.io/pypi/v/sphinxpress)](https://pypi.org/project/sphinxpress/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/sphinxpress)
![PyPI - Downloads](https://img.shields.io/pypi/dm/sphinxpress)

# sphinxpress

`sphinxpress` publishes multiple independent Sphinx documentation projects as one documentation product: generated Jekyll/GitHub Pages pages, a combined EPUB, and a combined PDF.

It stays Sphinx-first. Each source project keeps its own `conf.py` and documentation tree. `sphinxpress` runs Sphinx builders, reads their output, and writes deterministic site and book artifacts for a larger publishing pipeline.

> Release status: early alpha. Pin versions and validate generated output before using in production documentation pipelines.

## Features

- Build Jekyll pages from Sphinx JSON output.
- Build one logical project as both latest release docs and committed `main` docs.
- Preserve readable Sphinx autodoc/API presentation in generated Jekyll pages with scoped, self-contained styling.
- Write per-project navigation data for site layouts.
- Protect generated pages from Jekyll 3 Liquid parsing without an external wrapper step.
- Build aggregate EPUB and PDF projects from selected Sphinx docs projects.
- Resolve release metadata from manual tags, git tags, or project metadata.
- Optionally create a shared managed virtual environment for Sphinx and documentation dependencies.

## Install

```bash
python -m pip install sphinxpress
```

For local development and documentation builds:

```bash
python -m pip install -e ".[dev,docs,pdf]"
python -m pytest -q
```

## Minimal configuration

Create `sphinxpress.toml` at the repository root:

```toml
[site]
root = "site"
base_url = "https://docs.example.com"
tools_dir = "tools"
nav_data_dir = "_data/tool_nav"
layout = "tool-doc"
title = "Example Docs"
protect_liquid = true

[site.versioning]
enabled = true
default = "release"

[[site.versioning.variants]]
name = "release"
label = "Latest release"
source = "release"
url_segment = ""

[[site.versioning.variants]]
name = "main"
label = "Current main"
source = "git_ref"
ref = "main"
url_segment = "main"

[build]
work_dir = ".sphinxpress"
sphinx_build = "sphinx-build"
fail_on_warning = true
keep_build_dir = false
parallel = "auto"

[book]
title = "Example Documentation"
author = "Example Team"
language = "en"
version = "0.1.0"
copyright = "2026, Example Team"
project_order = ["tool-a"]
docs_variant = "release"

[pdf]
builder = "weasyprint"
output = "dist/example-documentation.pdf"

[epub]
builder = "epub"
output = "dist/example-documentation.epub"

[release]
tag_prefix = "v"
release_url_template = "{repo_url}/releases/tag/{tag}"

[[projects]]
name = "tool-a"
title = "Tool A"
docs_root = "../tool-a/docs"
conf_dir = "../tool-a/docs"
root_doc = "index"
repo_url = "https://github.com/example/tool-a"
release_strategy = "manual"
release_tag = "v0.1.0"
site_variants = ["release", "main"]
version_refs = { main = "main" }
```

## Commands

```bash
sphinxpress check
sphinxpress list
sphinxpress build-site --all
sphinxpress build-site --all --variant release
sphinxpress build-epub --all
sphinxpress build-pdf --all
sphinxpress validate
```

With the versioning block above, `build-site --all` writes:

- `/tools/tool-a/` for the resolved release target
- `/tools/tool-a/main/` for the resolved `main` target
- `_data/tool_nav/tool-a.yml` and `_data/tool_nav/tool-a-main.yml` with a version switcher payload

`sphinxpress` does not fetch refs or tags automatically. If a configured release tag or
Git ref is missing locally, fetch it before building.

`build-pdf` uses sphinxpress's internal WeasyPrint backend by default. It builds
the aggregate docs as single HTML and renders that HTML to PDF, so LaTeX is not
required for the default path. Install the optional `pdf` extra or include
`weasyprint>=67` in the managed build environment. The legacy `latexpdf`
builder remains available when `[pdf].builder = "latexpdf"` is set explicitly.

`build-pdf` preflights the configured WeasyPrint executable before the
aggregate singlehtml build and reports the actionable `sphinxpress[pdf]` or
`weasyprint>=67` guidance if it is missing, avoiding a wasted singlehtml run.

## Build diagnostics

Every Sphinx, WeasyPrint, and managed-environment pip run writes a log file
under `[build].log_dir` (default `<work_dir>/logs`). The latest run for each
stage is mirrored to `latest-<stem>.log`, and failure messages include the
relevant `Log:` path. Use `[build].log_dir = "custom-logs"` in
`sphinxpress.toml` to override the default location.

## Managed build environment

`sphinxpress` can create one shared virtual environment for Sphinx and documentation dependencies:

```toml
[build.env]
enabled = true
scope = "shared"
python = "python3"
path = ".sphinxpress/venv"
upgrade_pip = true
packages = [
  "sphinx>=7",
  "myst-parser",
  "sphinx-rtd-theme",
  "weasyprint>=67",
  "tool-a==0.1.0",
]
```

For v0.1, only `scope = "shared"` is supported. `scope = "project"` is reserved for a future release and is rejected with a configuration error.

Use exact package requirements for project packages, for example `tool-a==0.1.0`. Legacy editable entries that match a configured project path are converted to `project-name==release-version` using the project release tag with `[release].tag_prefix` stripped. Unmatched editable paths are rejected. Package path arguments after `-r`, `--requirement`, `-c`, and `--constraint` are resolved relative to `sphinxpress.toml`.

When site versioning is enabled, the shared environment can keep exact released
package pins while `main` docs still import the resolved checkout. `sphinxpress`
prepends the resolved source root and its `src/` directory to `PYTHONPATH` for
each Sphinx subprocess instead of using editable installs.

## Documentation

Build the project documentation with:

```bash
python -m pip install -e ".[dev,docs,pdf]"
python -m sphinx -b html docs docs/_build/html
```
