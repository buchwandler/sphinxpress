# sphinxpress

`sphinxpress` publishes one or more Sphinx documentation projects as a single
documentation product:

1. one Jekyll/GitHub Pages site
2. one combined EPUB book
3. one combined PDF book

It stays Sphinx-first. Source projects remain normal Sphinx docs, and
`sphinxpress` orchestrates Sphinx builders instead of converting source files
itself.

## Features

- load one or more projects from `sphinxpress.toml`
- validate config, paths, Sphinx availability, and generated output structure
- build deterministic Jekyll pages from Sphinx JSON output
- generate `_data/tool_nav/*.yml` navigation metadata for each project
- create a temporary aggregate Sphinx project for combined EPUB/PDF builds
- resolve release metadata from manual tags, git tags, or project
  `pyproject.toml`

## Install

```bash
python -m pip install -e ".[dev]"
```

## Configuration

The repository includes a working sample `sphinxpress.toml` that points at the
fixture Sphinx projects under `tests/fixtures/`. A typical real-world config
looks like this:

```toml
[site]
root = "."
base_url = "https://docs.example.com"
tools_dir = "tools"
nav_data_dir = "_data/tool_nav"
layout = "tool-doc"
title = "Example Tool Docs"

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
project_order = ["tool-a", "tool-b"]

[pdf]
builder = "latexpdf"
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
release_strategy = "git_tag"

[[projects]]
name = "tool-b"
title = "Tool B"
docs_root = "../tool-b/docs"
conf_dir = "../tool-b/docs"
root_doc = "index"
repo_url = "https://github.com/example/tool-b"
release_strategy = "pyproject"
```

## Commands

```bash
sphinxpress check
sphinxpress list

sphinxpress build-site --all
sphinxpress build-site --project booktx
sphinxpress build-site --projects booktx,epub2text

sphinxpress build-pdf --all
sphinxpress build-epub --all
sphinxpress build-book --format pdf --all
sphinxpress build-book --format epub --all

sphinxpress update-release --project booktx --tag v0.4.1
sphinxpress update-releases --all

sphinxpress add-project --name newtool --docs ../newtool/docs --repo https://github.com/example/newtool
sphinxpress validate
sphinxpress validate --linkcheck
```

## Output model

### Site output

`build-site` renders Sphinx JSON pages and writes Jekyll Markdown files with
embedded HTML and front matter like:

```yaml
---
layout: tool-doc
title: "booktx quickstart"
permalink: /tools/booktx/quickstart/
nav_tool: booktx
---
```

Navigation data is written under `_data/tool_nav/<project>.yml` and includes
the tool name, repo URL, release metadata, and deterministic page entries.

### Book output

`build-epub` and `build-pdf` create a temporary aggregate Sphinx project under
`.sphinxpress/build/book/`, copy each selected project's docs under a unique
`projects/<name>/` prefix, render a combined `conf.py` and `index.rst`, then
invoke the correct Sphinx builder:

- EPUB: `sphinx-build -b epub`
- PDF: `sphinx-build -M latexpdf`

## Release metadata

Supported strategies:

- `manual`: use `release_tag` from `sphinxpress.toml`
- `git_tag`: use `git describe --tags --abbrev=0`
- `pyproject`: read `[project].version` and apply the configured prefix

## Determinism and safety

- generated file writes are constrained to the configured site root
- Sphinx docnames that attempt path traversal are rejected
- generated pages and YAML include generated-file notices
- repeated site builds produce byte-identical output for unchanged inputs

## GitHub Actions example

```yaml
name: Build documentation

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install package
        run: |
          python -m pip install -e ".[dev]"

      - name: Validate docs
        run: |
          sphinxpress validate

      - name: Build Jekyll site pages
        run: |
          sphinxpress build-site --all

      - name: Build EPUB
        run: |
          sphinxpress build-epub --all

      - name: Build PDF
        run: |
          sphinxpress build-pdf --all
```