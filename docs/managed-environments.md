# Managed build environments

`sphinxpress` can create a dedicated virtual environment for Sphinx and project documentation dependencies. This is useful when the surrounding site pipeline is not a Python docs environment, such as a Jekyll-only GitHub Pages workflow.

Enable it with `[build.env]`:

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
  "-e", "../tool-a",
]
```

When enabled, `sphinxpress` prepares the environment once per command and uses the venv-local `sphinx-build` executable for `check`, `validate`, `build-site`, `build-epub`, and `build-pdf`.

For PDF output, the same managed environment should also provide the
`weasyprint` executable. Add `weasyprint>=67` to `[build.env].packages` when
you use the default WeasyPrint PDF backend.

Package path arguments after `-e`, `--editable`, `-r`, `--requirement`, `-c`, and `--constraint` are resolved relative to `sphinxpress.toml`.

For v0.1, only `scope = "shared"` is supported. `scope = "project"` is reserved for a future release and is rejected with a configuration error.
