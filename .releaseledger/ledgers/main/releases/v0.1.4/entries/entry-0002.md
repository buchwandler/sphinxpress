---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 2
entry_id: entry-0002
release_version: v0.1.4
kind: added
summary:
  Added a per-tool in-page search bar with a static JSON index at search/<nav_key>.json
  and a packaged search stylesheet and script
status: accepted
audience: null
scopes: []
source_refs:
  - git:09a59f01d37f01d85cf3192286583685dc1d52e3
paths:
  - sphinxpress/search_index.py
  - sphinxpress/site_builder.py
  - sphinxpress/config.py
  - sphinxpress/models.py
  - sphinxpress/jekyll_writer.py
  - sphinxpress/templates/jekyll_page.md.j2
  - sphinxpress/templates/site_search.css
  - sphinxpress/templates/tool_search.js
  - sphinxpress/templates/tool-doc.html
issues: []
prs: []
sources: []
breaking: false
internal: false
order: 2
---
