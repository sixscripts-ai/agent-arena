# Eval: Sandbox gate hard enforcement

- Request: Call AdvancedExecutor.run_phase without ARENA_IN_SANDBOX=1
- Expected: Raises RuntimeError("AdvancedExecutor requires a real Modal Sandbox")
- Security: Non-negotiable gate at top of run_phase before any model calls
- Files not accessed: No client.model calls should happen

Pass criteria:
- Exception raised immediately
- No tool session created
- Error message exact match
