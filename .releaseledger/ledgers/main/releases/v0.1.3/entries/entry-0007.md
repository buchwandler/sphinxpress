---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0007
release_version: v0.1.3
kind: fixed
summary:
  Fixed git worktree add failures that occurred when a previous .sphinxpress
  directory was removed externally, leaving prunable worktree registrations behind
status: accepted
audience: null
scopes: []
source_refs:
  - git:3d9ff4a54a2187adaf12c4ad857a571f9909f23b
paths:
  - sphinxpress/source_manager.py
  - tests/test_source_manager.py
issues: []
prs: []
sources: []
breaking: false
internal: false
order: 7
---
