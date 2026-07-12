# Release metadata

`sphinxpress` can attach release tags and release URLs to generated navigation
data.

Release metadata and source selection are related but separate:

- release metadata answers "what release label and URL should this target show?"
- source selection answers "which checkout should Sphinx actually build?"

For versioned site builds, the `release` variant resolves a release tag and
materializes that exact Git object before running Sphinx. A `git_ref` variant
resolves an explicit branch, remote ref, or commit SHA and materializes that
commit separately.

Supported project strategies are:

- `manual`, using the project's configured `release_tag`
- `git_tag`, resolving the latest matching git tag
- `pyproject`, reading package metadata from `pyproject.toml`

The release URL is formatted with `[release].release_url_template`:

```toml
[release]
tag_prefix = "v"
release_url_template = "{repo_url}/releases/tag/{tag}"
```

Use `update-release` to set one manual tag and `update-releases` to refresh all resolvable tags.

For `git_ref` variants, the source URL is formatted with
`[release].branch_url_template`:

```toml
[release]
branch_url_template = "{repo_url}/tree/{ref}"
```

Versioned builds do not fetch refs or tags automatically. If a configured
release tag or `git_ref` is missing locally, sphinxpress raises an actionable
error instead of falling back to the current working tree.

The `git_tag` strategy still uses `git describe --tags --abbrev=0`, so
"latest release" means the nearest reachable tag from the checked-out history,
not a separate semantic-version sort across all tags.
