---
name: artifact-workspace-versioning
description: >
  Build persistent progressive workspaces for coding agents, sandboxes, and multi-round
  battles. TRIGGER for artifact history, file snapshots, version selection, code diffs,
  workspace persistence, incremental edits, test-result attachment, restore/replay, or
  preventing agents from regenerating from scratch each round.
license: MIT
metadata:
  author: sixscripts-ai
  version: "1.0.0"
  category: agent-workspaces
  tags: "artifacts,workspace,versions,diff,snapshots,progressive-code,history"
---

# Artifact Workspace Versioning

Treat an agent's previous working artifact as canonical state for the next iteration.

## Canonical Model

Keep separate concepts for:

- workspace: current editable file tree
- artifact_version: immutable submitted snapshot
- execution_result: build/test/runtime result attached to a version
- diff: derived change between versions
- opponent_artifact: approved read-only competitive context

Do not collapse all history into one transcript.

## Progressive Coding Workflow

Round 1 creates a baseline workspace. Later rounds should open the prior workspace, inspect feedback/opponent evidence, make targeted edits, verify them, and submit a new immutable version.

Preferred loop:

OBSERVE -> COMPARE -> PLAN -> PATCH -> TEST -> SUBMIT -> SCORE -> REPEAT

Do not restart from the original task unless the workspace is genuinely unsalvageable.

## Version Metadata

Every submitted version should capture:

- version number
- participant/model
- phase/round
- created_at
- file manifest or artifact body
- changed files
- additions/removals when available
- execution/test status
- score/judge feedback when available
- parent version

## Diff UX

Generate real line/file diffs rather than character-count heuristics. Preserve unchanged context, clearly show additions/removals, and handle file create/delete/rename where the artifact model supports it.

## Storage Rules

Use immutable version records and a mutable working copy. Cap large artifacts deliberately; do not silently truncate canonical files. If only excerpts are sent to the model, keep the full server-side artifact intact.

## Recovery

Reopening a battle should hydrate the latest canonical artifacts and version list before attaching to the live stream. Reconnects must not create duplicate versions.

## Testing

Cover one version, 10+ versions, identical resubmission, multi-file snapshots, failed test before submit, reconnect duplication, version restore, artifact too large, opponent visibility rules, and persistence after process restart.
