# Jekyll integration

`sphinxpress build-site` writes Markdown files with Jekyll front matter plus HTML rendered by Sphinx's JSON builder.

The generated page front matter includes:

- `layout`
- `title`
- `permalink`
- `nav_tool`

Navigation data is written as YAML under the configured `site.nav_data_dir` path. A site layout can use `nav_tool` to select the matching navigation file.

Generated files include a notice so they can be distinguished from hand-written site pages.

## Scoped API stylesheet

Every generated Jekyll page wraps the Sphinx body in a stable root container:

```html
<div class="sphinxpress-doc">...Sphinx body HTML...</div>
```

A small, scoped stylesheet is embedded as a `<style data-sphinxpress-style="api">` block immediately above the wrapper. The stylesheet:

- styles Python API descriptions, field lists, inline literals, and source links
- uses CSS custom properties so host themes can recolor the panels
- supports light and dark host themes via `prefers-color-scheme: dark`
- hides the `[source]` link in `print` media

The stylesheet is fully self-contained: it does not depend on Sphinx theme assets, fonts, or JavaScript, and it does not parse or rewrite the Sphinx signature HTML.

Host layouts should:

- preserve the `<div class="sphinxpress-doc">` wrapper
- avoid overriding `.sphinxpress-doc dt.sig` with highly specific rules that would defeat the embedded style
- rely on the embedded style for API presentation instead of shipping duplicate rules
