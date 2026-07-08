---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 2
entry_id: entry-0002
release_version: v0.1.1
kind: internal
summary: Fix trailing-slash handling in toctree href parsing and update tests
status: accepted
audience: null
scopes: []
source_refs:
  - git:54a5044dc77ca851fd3f0b5a597cb6abbf4b33be
paths:
  - sphinxpress/site_builder.py
  - tests/test_site_builder.py
issues: []
prs: []
sources: []
breaking: false
internal: true
order: 2
---

Corrects \_docname_from_html_href to use rstrip("/") instead of appending "index" when the href ends with a trailing slash.
