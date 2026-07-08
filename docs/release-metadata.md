# Release metadata

`sphinxpress` can attach release tags and release URLs to generated navigation data.

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
