# Tool Protocol

Models emit tools in reply. Strict sequential parser.

Single-line (stateless):
  TOOL read path=<rel>
  TOOL ls [path=<rel>]  # default .
  TOOL test path=<rel>
  TOOL clean path=<rel>

Block (header, body, END_TOOL):
  TOOL write path=<rel>
  <file contents>
  END_TOOL

  TOOL run [path=<rel>]
  <inline python>
  END_TOOL

- DONE line (exact) or no tool calls ends turn, text kept as final answer
- Unknown tool -> return "ERROR: unknown tool X" to model, don't crash phase
- Parser scans line-by-line, block mode until END_TOOL, avoids naive grep
