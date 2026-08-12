---
name: terminal-sandbox-ui
description: >
  Design and implement professional terminal, execution-inspector, sandbox, debugger,
  and agent-runtime interfaces. TRIGGER for terminal UI/UX, code viewers, output panes,
  tool-call timelines, fixed-height execution consoles, artifact tabs, command palettes,
  diff views, log viewers, runtime status, or developer-console redesigns. Prefer a
  structured execution inspector over fake hacker-terminal aesthetics or endlessly
  growing logs.
license: MIT
metadata:
  author: sixscripts-ai
  version: "1.0.0"
  category: frontend-developer-tools
  tags: "terminal,sandbox,console,execution-inspector,developer-tools,ui,ux"
---

# Terminal Sandbox UI

Build terminal and sandbox interfaces as professional developer tools, not decorative shell windows.

## Core UX Model

Use a fixed-size execution inspector with internal scrolling. The page itself must not grow or auto-scroll as runtime data arrives.

Default information architecture:

- ARTIFACT: latest complete source/artifact.
- DIFF: previous version vs current version.
- OUTPUT: stdout/stderr/build/test output.
- TOOLS: structured tool and runtime events.
- VERSIONS: v1, v2, v3 history without resizing the panel.

Header should expose model/agent, role, state, elapsed time, and copy/open actions. Footer should expose compact metadata such as version, tool count, runtime, token count when available, and jump-to-latest.

## Interaction Rules

1. Keep the inspector height bounded on desktop and mobile.
2. Scroll only inside the active pane.
3. Never concatenate historical artifacts into one giant code block.
4. Use internal file navigation for multi-file artifacts.
5. Preserve selection when new events arrive unless the user is following latest.
6. Make auto-follow opt-in and local to Output/Tools panes.
7. Keyboard-enable all tabs, copy actions, version selection, and file navigation.
8. Use explicit queued/running/success/failed/cancelled/disconnected states.
9. Do not display network failures as empty data.
10. Long model IDs and paths must truncate gracefully with full values available by tooltip/copy.

## Visual Direction

Prefer near-black or neutral code surfaces, restrained accent color, thin borders, tight spacing, strong typography hierarchy, and monospace only for code/metadata. Avoid excessive glow, glassmorphism, giant rounded cards, animated background effects, and fake shell prompts.

## Structured Runtime Events

Render events as rows with fields such as:

- timestamp
- action: READ / WRITE / EDIT / EXEC / TEST / COMPARE / SUBMIT
- target
- state
- duration
- compact result

Expandable detail may include command, exit code, stdout/stderr summary, changed-file counts, or tool payloads. Never dump secrets or raw credentials.

## Required QA

Test with empty output, one event, 100+ events, long code, 5+ artifact versions, failed commands, reconnects, mobile stacking, keyboard-only navigation, and reduced-motion mode.
