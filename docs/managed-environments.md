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
  "tool-a==0.1.0",
]
```

When enabled, `sphinxpress` prepares the environment once per command and uses the venv-local `sphinx-build` executable for `check`, `validate`, `build-site`, `build-epub`, and `build-pdf`.

With site versioning enabled, keep exact released package pins in
`[build.env].packages` for the shared environment. sphinxpress prepends the
resolved checkout root and its `src/` directory to `PYTHONPATH` for each target
build so `main` documentation imports the selected source tree without any
editable install.

For PDF output, the same managed environment should also provide the
`weasyprint` executable. Add `weasyprint>=67` to `[build.env].packages` when
you use the default WeasyPrint PDF backend.

Pip upgrade and install failures during managed environment setup are reported as a sphinxpress `ValidationError` and include the `env-pip-upgrade` or `env-pip-install` log path from `[build].log_dir`. The corresponding latest log file contains the full pip stdout, stderr, and return code.

Use exact package requirements for project packages, for example `tool-a==0.1.0`. Legacy editable entries that match a configured project path are converted to `project-name==release-version` using the project release tag with `[release].tag_prefix` stripped. Unmatched editable paths are rejected. Package path arguments after `-r`, `--requirement`, `-c`, and `--constraint` are resolved relative to `sphinxpress.toml`.

This versioned-docs flow intentionally does **not** run `pip install -e <checkout>` for release or `main` targets.

For v0.1, only `scope = "shared"` is supported. `scope = "project"` is reserved for a future release and is rejected with a configuration error.
