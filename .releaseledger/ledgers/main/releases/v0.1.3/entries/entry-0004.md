---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0004
release_version: v0.1.3
kind: added
summary:
  Added Jekyll Liquid protection (protect_liquid, on by default) that wraps
  generated Sphinx HTML in a balanced raw block and neutralizes literal {% endraw
  %} examples
status: accepted
audience: null
scopes: []
source_refs:
  - git:7b8c7a4973b66867ead2f5dce706a55fa619b4a0
paths:
  - sphinxpress/jekyll_writer.py
  - sphinxpress/site_builder.py
  - sphinxpress/models.py
  - docs/configuration.md
  - docs/jekyll-integration.md
issues: []
prs: []
sources: []
breaking: false
internal: false
order: 4
---
