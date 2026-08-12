---
name: realtime-execution-streaming
description: >
  Build robust realtime event streaming for code execution, terminals, agent battles,
  sandboxes, and observability consoles. TRIGGER for SSE, WebSocket, reconnect logic,
  ordered execution events, deduplication, backpressure, live logs, replay, event schemas,
  or frontend state synchronization during long-running jobs.
license: MIT
metadata:
  author: sixscripts-ai
  version: "1.0.0"
  category: realtime-systems
  tags: "sse,websocket,streaming,reconnect,events,backpressure,replay"
---

# Realtime Execution Streaming

Make realtime execution state reliable under reconnects, duplicate delivery, slow clients, and long-running jobs.

## Event Envelope

Prefer one canonical envelope:

- event_id: globally unique
- sequence: monotonic within execution/battle
- execution_id or battle_id
- participant/model_id when relevant
- phase
- type
- created_at
- payload
- schema_version

Use event IDs and sequence numbers for deduplication. Never infer ordering solely from browser arrival time.

## Delivery Semantics

Design for at-least-once delivery. Clients must be idempotent.

On reconnect:

1. Send last seen event ID/sequence.
2. Replay missing persisted events when available.
3. Resume the live stream.
4. Avoid re-appending duplicate artifacts or tool calls.
5. Reconcile final server state after stream completion.

## Frontend State

Keep bounded buffers for transient logs while separately preserving canonical artifacts and version history. Do not store the entire session as one concatenated text blob.

Maintain independent stores for:

- execution status
- phase state
- latest artifact per participant
- artifact versions
- tool events
- stdout/stderr events
- judge scores/results
- connection state

## Backpressure

Batch high-frequency output updates. Do not rerender React on every character/token when chunks can be coalesced safely. Cap client-side retained logs and virtualize large lists where needed.

## Connection UX

Expose explicit CONNECTING / LIVE / RECONNECTING / DISCONNECTED / COMPLETE states. A reconnect should not erase already-rendered artifacts. Failed transport is different from failed user code.

## Testing

Simulate duplicate events, out-of-order delivery, network drop during execution, reconnect after 30 seconds, stream termination before final event, large stdout bursts, concurrent participant streams, stale browser tabs, and server restart when replay is supported.
