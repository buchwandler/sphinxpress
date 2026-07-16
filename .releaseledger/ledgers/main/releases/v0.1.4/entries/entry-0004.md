---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 2
entry_id: entry-0004
release_version: v0.1.4
kind: added
summary:
  Added `sphinxpress sync-layout` to copy tool-doc.html into the consumer's
  _layouts/, skipping identical files and refusing drift
status: accepted
audience: null
scopes: []
source_refs:
  - git:c094ce82c540b52352f88d86d4c70c39a4c341af
paths:
  - sphinxpress/cli.py
  - sphinxpress/layout_sync.py
  - docs/jekyll-integration.md
  - tests/test_layout_sync.py
issues: []
prs: []
sources: []
breaking: false
internal: false
order: 4
---
