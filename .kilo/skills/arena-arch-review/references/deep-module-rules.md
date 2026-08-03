# Deep Module Rules — Vocabulary for Arena

Based on "A Philosophy of Software Design" (John Ousterhout).

## Interface vs Implementation

- Deep module: simple interface, complex hidden implementation.
- Shallow: complex interface, simple impl (bad).
- Example Shallow: CodePane currently exposes modelId, label, code, status, tok, color, artifactMeta, win, winText — 9 props. Could be deepened to `artifact: {modelId, role, code}` + `presentation` inferred.

## Information Hiding

- Executor's Popen killpg, _resolve checks are hidden behind ToolSession.run(). Caller shouldn't know about killpg.

## Seams

Where to split:
- frontend/src/hooks/useBattleStream.ts: seam between SSE protocol and UI state. Interface: {arts, scores, status, phase}. Hidden: reconnect backoff, dedup, sorting.
- backend sandbox/executors/orchestrator.py: seam between phase loop and individual executor. Interface: run_phase(phase, role_to_model). Hidden: halted check, history accumulation, phase_start event.
- backend/event_bus.py: seam between durable snapshot + live subscribe. Interface: stream(battle_id) → AsyncIterable<Event>. Hidden: created_at+event_id sort, seen_ids.

## Connascence (coupling types)

- Connascence of Position: NewBattle selected array position maps to roles array position — fragile if roles reorder. Fix: Map role->model_id.
- Connascence of Name: executor registry keyed by NAME and SLUG — name collision risk due to slugify truncation 36.
- Connascence of Meaning: guard() markers ESCAPE_OK etc — convention not typed. Should be enum.

## AI-Navigability

- Files < 250 LOC, one concept, searchable via semantic search "battle stream dedup".
- Avoid barrel files, avoid 12-col grid magic numbers without comment.
- Favor explicit roles typing: type Role = "builder" | "breaker" | "defender" | ...

## Checklist for Deepening

1. What does module hide? If answer "nothing", it's shallow.
2. Could you describe interface in one sentence?
3. Is there a single seam that if moved reduces cross-file imports?
4. Can you test it without spinning full backend/frontend?
5. Does it have a test file that documents its contract?

## Example Deep Module for Arena

```
class BattleStream:
  def __init__(self, battle_id, token_provider): ...
  async def events(self) -> AsyncIterator[StreamEvent]: ...
  def current_state(self) -> {arts, scores, status}
```
Interface tiny, impl handles abort, refreshJwt, backoff, sorting, dedup.
