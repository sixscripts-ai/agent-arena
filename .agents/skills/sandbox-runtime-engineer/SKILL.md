---
name: sandbox-runtime-engineer
description: >
  Architect and implement isolated code-execution runtimes and developer sandboxes.
  TRIGGER for ephemeral workspaces, containerized execution, process supervision,
  stdout/stderr streaming, cancellation, timeouts, filesystem workspaces, resource
  quotas, language runners, test execution, sandbox lifecycle, or execution APIs.
license: MIT
metadata:
  author: sixscripts-ai
  version: "1.0.0"
  category: sandbox-runtime
  tags: "sandbox,code-execution,containers,runtime,processes,filesystem,streaming"
---

# Sandbox Runtime Engineer

Design code execution as a supervised runtime with explicit lifecycle, isolation, observability, and cleanup.

## Runtime Lifecycle

Model each execution as:

QUEUED -> STARTING -> RUNNING -> SUCCEEDED | FAILED | TIMED_OUT | CANCELLED

Every run should have a stable execution ID, workspace ID, timestamps, exit status, and reason for termination.

## Execution Contract

A runner should accept a structured request containing the language/runtime, command or entrypoint, workspace snapshot, environment allowlist, timeout, CPU/memory limits, network policy, and output limits.

Return or stream structured events instead of one giant log string:

- execution_started
- process_started
- stdout_chunk
- stderr_chunk
- file_changed
- test_result
- process_exited
- execution_completed
- execution_failed

Events need monotonically increasing sequence numbers so clients can deduplicate and reconnect safely.

## Workspace Model

1. Create an isolated ephemeral workspace per execution or battle participant.
2. Materialize only approved files.
3. Mount secrets only when strictly required and never into user-readable paths.
4. Snapshot artifact state between rounds when progressive editing is required.
5. Separate source files, generated output, caches, and metadata.
6. Destroy ephemeral runtime state after retention rules expire.

## Process Supervision

Use a supervisor that can:

- stream stdout and stderr independently
- enforce wall-clock timeout
- terminate the full process tree
- handle cancellation deterministically
- cap output bytes and line counts
- preserve exit code and signal
- prevent zombie processes
- detect runner startup failure separately from user-code failure

Do not rely on frontend disconnects to stop execution.

## Performance

Prefer warm runtime pools where safe, deterministic dependency caching, incremental workspace snapshots, bounded log buffers, and backpressure-aware streaming. Avoid spawning expensive infrastructure for every tiny UI event.

## Testing

Cover successful execution, syntax error, runtime exception, infinite loop timeout, huge stdout, huge stderr, child-process spawning, cancellation, reconnect/replay, missing dependency, workspace persistence across rounds, and cleanup after failure.
