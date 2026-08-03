# Base Executor Reference

From backend/agent_arena/sandbox/executors/base.py

- class Executor with run_phase() abstract and run_battle() driving phase loop
- run_battle: for each non-judge phase emits phase_start, calls run_phase(), accumulates history, calls finish()
- finish(): rubric or default, client.judge(), client.round(..., event_type="scores"), on_status completed
- halted(status_check, deadline): returns cancelled/failed/None
- guard(value, markers): validates outcome against markers, exact or prefix with "_"
- emit_result(client, battle_id, phase, result): json.dumps + "EXECUTOR_RESULT: {payload}" + client.round(..., event_type="result")
