---
name: battle-runtime-observability
description: >
  Design observability and debugging for competitive AI-agent runtimes. TRIGGER for
  battle traces, model/tool timing, execution events, judge feedback, progressive-round
  diagnostics, latency/cost/status dashboards, structured logs, replay, or explaining why
  an agent won, lost, stalled, repeated itself, or failed.
license: MIT
metadata:
  author: sixscripts-ai
  version: "1.0.0"
  category: agent-observability
  tags: "agents,observability,traces,battles,judge,latency,cost,debugging"
---

# Battle Runtime Observability

Instrument the battle runtime so developers can reconstruct what happened without reading raw server logs.

## Trace Model

Capture structured spans/events for:

- battle queued/started/completed
- phase start/end
- model request start/end
- tool call start/end
- sandbox execution start/end
- artifact submitted
- test/build result
- opponent context supplied
- judge request/result
- retry/recovery
- cancellation/timeout

Each event should include stable battle, execution, participant, phase, sequence, and timestamp fields.

## Agent Diagnostics

Make it possible to answer:

- Did the model receive its prior artifact?
- Did it receive opponent context when allowed?
- What changed from the previous version?
- Which test/build failed?
- How long did generation, tools, and sandbox execution take?
- Was a repeated output retried?
- What judge feedback was available before the next round?
- Was the failure transport, model, sandbox, policy, or user-code related?

## Judge Feedback

Store judge outputs separately from raw agent transcripts. When dimensional scores exist, persist them as structured fields. Never fabricate dimensions in the UI. Associate feedback with the exact artifact versions being judged.

## Metrics

Useful aggregates include model latency, tool latency, sandbox runtime, retries, failed runs, timeout rate, artifact size, version count, score delta by round, repeated-output rate, and reconnect frequency. Cost/token metrics should be displayed only when the backend actually provides them.

## Replay

A developer replay view should rebuild phase state, participant versions, tool activity, and final result from persisted events. Replays must be read-only and must not rerun side effects.

## Privacy and Safety

Redact credentials, authorization headers, secret environment variables, hidden chain-of-thought/reasoning, and internal stack traces before persistence or frontend display. Store only operational evidence needed to debug the runtime.

## UI Guidance

Prefer a compact activity timeline and per-agent inspector over a raw event dump. Allow filters by participant, phase, tool, status, and failure type. Preserve the latest artifact as the primary view while keeping detailed traces one interaction away.
