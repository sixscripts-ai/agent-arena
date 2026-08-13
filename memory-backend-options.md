# Free Memory Backends for Agents (ranked)

Status: **SCRATCHED — user is going to find a new option. Do NOT use supermemory or agentmemory.**

| # | Backend | Repo | License | Cost / Self-host | One-line note |
|---|---|---|---|---|---|
| ~~1~~ | ~~**agentmemory**~~ | ~~https://github.com/rohitg00/agentmemory~~ | ~~MIT~~ | ~~$0 · fully local~~ | ~~SCRATCHED. cwd-relative store = memories silently lost on cwd change; auto-capture off; only 1 real save ever.~~ |
| ~~—~~ | ~~**opencode-supermemory**~~ | ~~https://github.com/supermemoryai/opencode-supermemory~~ | ~~—~~ | ~~cloud SaaS~~ | ~~SCRATCHED. Cloud plugin, never authenticated; ~40 "saves" all silently failed (no SUPERMEMORY_API_KEY).~~ |
| 2 | **Mem0** | https://github.com/mem0ai/mem0 | Apache-2.0 | Free self-host · hosted ~$19/mo | ~60k stars, drop-in CRUD API, OpenMemory MCP. LLM-gated writes; graph memory = cloud-Pro only. |
| 3 | **Letta (MemGPT)** | https://github.com/letta-ai/letta | Apache-2.0/MIT | Free self-host | Self-editing memory tiers; agent manages own context. Heavy (server + Postgres). |
| 4 | **Zep / Graphiti** | https://github.com/getzep/graphiti | Apache-2.0 | Free self-host | Bi-temporal knowledge graph, sub-200ms claims. Needs Neo4j/FalkorDB; LLM-heavy writes. |
| 5 | **OpenViking** | https://github.com/volcengine/OpenViking | AGPLv3 | Free self-host | Best depth (repo RAG + L0/L1/L2) but AGPL + separate LLM-backed server. Ruled out. |
| 6 | **LangMem** | https://github.com/langchain-ai/langmem | MIT | Free (library) | Primitives for LangGraph users; procedural self-editing memory. |

Source: https://plur.ai/blog/mem0-vs-letta-vs-zep/

## What the replacement must fix (from today's failures)
- **Verifiable saves**: every write must be confirmable (list endpoint / on-disk) — silent failure is disqualifying.
- **Deterministic store location**: not cwd-relative; store must survive cwd changes and restarts.
- **Works without an LLM key** OR clearly surfaces when a key is missing.
- **Auto-capture optional**: explicit saves must work; no silent no-op.

## Cleanup performed
- `.gitignore`: added `data/` (agentmemory store) — protects untracked store from git clean.
- agentmemory server still running (`:3111`, pid live) until replaced; can be killed on request.
- supermemory plugin never had a key; nothing to uninstall config-wise (no MCP config entry found).
