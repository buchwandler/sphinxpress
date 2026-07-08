# Quickstart

Create a `sphinxpress.toml` file in the repository that will publish the docs.

```toml
[site]
root = "site"
base_url = "https://docs.example.com"
tools_dir = "tools"
nav_data_dir = "_data/tool_nav"
layout = "tool-doc"
title = "Example Docs"

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
project_order = ["tool-a"]

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
release_strategy = "manual"
release_tag = "v0.1.0"
```

Validate the configuration:

```bash
sphinxpress check
```

Build the Jekyll pages:

```bash
sphinxpress build-site --all
```

Build book outputs:

```bash
sphinxpress build-epub --all
sphinxpress build-pdf --all
```
