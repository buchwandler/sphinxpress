# Configuration

`sphinxpress` reads `sphinxpress.toml` from the current directory unless `--config` is provided.

## Build logs

`[build].log_dir` (default `<work_dir>/logs`) controls where sphinxpress writes timestamped command logs. The directory is created on demand. Each Sphinx, WeasyPrint, and managed-environment pip run writes one `YYYYMMDDTHHMMSSZ-<stem>.log` file plus a `latest-<stem>.log` copy that points at the most recent run. Stable log stems include:

- `site-<project>-json`
- `validate-<project>-dummy` and `validate-<project>-linkcheck`
- `book-epub-sphinx`
- `book-pdf-singlehtml`
- `book-pdf-weasyprint`
- `env-pip-upgrade` and `env-pip-install`

Override the default location in `sphinxpress.toml`:

```toml
[build]
work_dir = ".sphinxpress"
log_dir = ".sphinxpress/logs"
```

Sphinx and WeasyPrint failures include the relevant `Log:` path so the full stdout and stderr can be inspected without rerunning the build.

## Site settings

`[site]` controls generated Jekyll paths, layout names, and the public base URL.

## Build settings

`[build]` controls the work directory, Sphinx executable, warning policy, and parallel build setting.

Use `[build.env]` to enable a shared managed virtual environment for Sphinx and documentation dependencies.

## Book settings

`[book]`, `[epub]`, and `[pdf]` configure aggregate book metadata and output
paths. `[pdf].builder` now defaults to `weasyprint`, which renders aggregate
`singlehtml` output to PDF without LaTeX. Set `[pdf].builder = "latexpdf"` only
when you explicitly want the legacy LaTeX-based Sphinx path.

EPUB builds should provide non-empty `version` and `copyright` values:

```toml
[book]
title = "Example Documentation"
author = "Example Team"
language = "en"
version = "0.1.0"
copyright = "2026, Example Team"
```

Use `suppress_warnings = ["ref.python"]` only as a temporary aggregate-book workaround for ambiguous Python cross-references that cannot yet be fixed in source docs.

If `[build.env].enabled = true` and you want PDF output, include
`weasyprint>=67` in `[build.env].packages` so the managed environment provides
the `weasyprint` executable used by the PDF build.

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
