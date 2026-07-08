# Configuration

`sphinxpress` reads `sphinxpress.toml` from the current directory unless `--config` is provided.

## Site settings

`[site]` controls generated Jekyll paths, layout names, and the public base URL.

## Build settings

`[build]` controls the work directory, Sphinx executable, warning policy, and parallel build setting.

Use `[build.env]` to enable a shared managed virtual environment for Sphinx and documentation dependencies.

## Book settings

`[book]`, `[epub]`, and `[pdf]` configure aggregate book metadata and output paths.

## Projects

Each `[[projects]]` entry points to one existing Sphinx documentation project:

```toml
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

Project names are used in generated URLs and must be URL-safe.
