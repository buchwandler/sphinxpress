# sphinxpress

`sphinxpress` publishes multiple Sphinx documentation projects as one documentation product:

- Jekyll/GitHub Pages pages generated from Sphinx JSON output
- a combined EPUB book
- a combined PDF book

`sphinxpress` does not replace Sphinx. Each source project remains a normal Sphinx project with its own `conf.py`, root document, extensions, and source files. `sphinxpress` orchestrates those projects and writes deterministic generated output for a site or book pipeline.

## When to use it

Use `sphinxpress` when you maintain several related Python tools or libraries and want one documentation site and one combined book artifact without merging the original docs projects.

## First steps

1. Install the package in your docs build environment.
2. Create `sphinxpress.toml` at the repository root.
3. Add one `[[projects]]` entry for each Sphinx docs project.
4. Run `sphinxpress check`.
5. Run `sphinxpress build-site --all`.
6. Commit or publish the generated Jekyll pages according to your site workflow.

```bash
python -m pip install sphinxpress
sphinxpress check
sphinxpress build-site --all
```

For development:

```bash
python -m pip install -e ".[dev,docs]"
python -m pytest -q
```

## Contents

```{toctree}
:maxdepth: 2

quickstart
configuration
managed-environments
commands
outputs
release-metadata
jekyll-integration
api
```
