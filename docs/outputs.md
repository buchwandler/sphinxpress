# Outputs

`sphinxpress` writes generated files for site and book workflows.

## Jekyll pages

`build-site` writes one page per Sphinx JSON document under the configured `site.root` and `site.tools_dir`.

## Navigation data

For each project, `build-site` writes a YAML file under `site.nav_data_dir`. Jekyll layouts can use this data to render project navigation.

## EPUB and PDF

`build-epub` and `build-pdf` create a temporary aggregate Sphinx project under the configured work directory, then copy the final artifact to the configured output path.

PDF builds use Sphinx's `latexpdf` builder and require LaTeX system packages outside Python.
