# Jekyll integration

`sphinxpress build-site` writes Markdown files with Jekyll front matter plus HTML rendered by Sphinx's JSON builder.

The generated page front matter includes:

- `layout`
- `title`
- `permalink`
- `nav_tool`

Navigation data is written as YAML under the configured `site.nav_data_dir` path. A site layout can use `nav_tool` to select the matching navigation file.

Generated files include a notice so they can be distinguished from hand-written site pages.
