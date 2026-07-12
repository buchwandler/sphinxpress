# Outputs

`sphinxpress` writes generated files for site and book workflows.

## Jekyll pages

`build-site` writes one page per Sphinx JSON document under the configured `site.root` and `site.tools_dir`.

When site versioning is enabled, the default variant keeps the stable release
URL while non-default variants add their configured segment:

- `tools/booktx/index.md` -> `/tools/booktx/`
- `tools/booktx/main/index.md` -> `/tools/booktx/main/`

Each generated page is wrapped in a `<div class="sphinxpress-doc">` and is preceded by a `<style data-sphinxpress-style="api">` block that ships a small, scoped sphinxpress stylesheet for Sphinx document-body elements. The stylesheet targets Python API descriptions, field lists, inline literals, and source links produced by `sphinx.ext.autodoc`. All rules are scoped to the `.sphinxpress-doc` wrapper so the host Jekyll theme is not affected outside generated pages.

## Navigation data

For each resolved project/variant target, `build-site` writes a YAML file under
`site.nav_data_dir`. Jekyll layouts can use this data to render both page
navigation and the version switcher for the logical project.

## EPUB and PDF

`build-epub` and `build-pdf` create a temporary aggregate Sphinx project under the configured work directory, then copy the final artifact to the configured output path.

By default, PDF builds render the aggregate docs as Sphinx `singlehtml`, apply
small sphinxpress-owned print CSS/HTML adjustments, and convert the result to
PDF with WeasyPrint. This avoids LaTeX for the default path. Set
`[pdf].builder = "latexpdf"` to keep using the legacy LaTeX-based Sphinx build.

## Build logs

Every Sphinx, WeasyPrint, and managed-environment pip command writes a
timestamped log under `[build].log_dir` (default `<work_dir>/logs`). Each run
produces a `YYYYMMDDTHHMMSSZ-<stem>.log` file and a `latest-<stem>.log` copy
that points at the most recent run. Failures include the relevant `Log:` path
in the sphinxpress error message so the full stdout and stderr can be reviewed
without rerunning the build.

## Generated-output manifest

`build-site` also writes `<work_dir>/site-output-manifest.json`. sphinxpress
uses this manifest to remove stale generated Markdown pages for the selected
targets without deleting hand-maintained content under the same tool tree.
