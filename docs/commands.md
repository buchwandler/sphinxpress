# Commands

## `sphinxpress check`

Loads configuration, prepares the managed environment if enabled, verifies `sphinx-build`, and runs Sphinx dummy builds.

## `sphinxpress list`

Lists configured projects and resolved release metadata.

## `sphinxpress build-site`

Builds Jekyll pages and navigation data.

```bash
sphinxpress build-site --all
sphinxpress build-site --project tool-a
sphinxpress build-site --projects tool-a,tool-b
```

## `sphinxpress build-epub`

Builds the combined EPUB artifact.

```bash
sphinxpress build-epub --all
```

## `sphinxpress build-pdf`

Builds the combined PDF artifact with Sphinx's `latexpdf` builder. Requires LaTeX system dependencies.

```bash
sphinxpress build-pdf --all
```

## `sphinxpress build-book`

Format-dispatching wrapper around PDF and EPUB builds.

```bash
sphinxpress build-book --format epub --all
sphinxpress build-book --format pdf --all
```

## `sphinxpress update-release`

Updates one project's stored `release_tag`.

```bash
sphinxpress update-release --project tool-a --tag v0.1.0
```

## `sphinxpress update-releases`

Resolves and updates release tags for all configured projects.

```bash
sphinxpress update-releases --all
```

## `sphinxpress add-project`

Appends a new `[[projects]]` entry to `sphinxpress.toml`.

```bash
sphinxpress add-project \
  --name tool-a \
  --docs ../tool-a/docs \
  --repo https://github.com/example/tool-a
```

## `sphinxpress validate`

Runs checks, validates generated Jekyll output, and verifies aggregate book project creation.

```bash
sphinxpress validate
sphinxpress validate --linkcheck
```
