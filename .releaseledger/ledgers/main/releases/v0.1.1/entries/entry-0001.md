---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0001
release_version: v0.1.1
kind: fixed
summary: Strip Sphinx headerlink permalinks from generated HTML pages
status: accepted
audience: null
scopes: []
source_refs:
  - git:0dbe946c343735b62d9a2c7f104c00693a58f973
paths:
  - sphinxpress/jekyll_writer.py
  - sphinxpress/site_builder.py
  - tests/test_jekyll_writer.py
  - tests/test_site_builder.py
issues: []
prs: []
sources: []
breaking: false
internal: false
order: 1
---

Removes heading permalink anchors added by Sphinx from the generated Jekyll output. Also improves site builder to skip Jekyll-hidden docnames (prefixed with `_`), order navigation pages by the root toctree when present, and exclude Sphinx internal pages (genindex, py-modindex, search) from tool nav.
