# Test Cases

- parse_tool_calls block: single write block -> 1 call
- parse single-line: read, ls, test
- multiple blocks: write+run+write
- DONE detection: text with DONE line -> no tools, done=True
- ToolSession write/read/ls: WROTE, content match, listing contains file
- ToolSession .. escape: read ../secret -> ERROR escape
- ToolSession run timeout: busy.py while True -> TIMEOUT after 1s, steps >=1, process group killed
- Gate: run_phase without ARENA_IN_SANDBOX -> RuntimeError
- Full loop FakeTransport: model_replies with tool then DONE, assert 2 artifacts, rounds contain race phase
- Registry: get_executor name "Tool-using coding race" and slug "tool-using-coding-race" -> AdvancedExecutor
