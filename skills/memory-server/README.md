# Memory Server

!python -c "import sqlite3, os, glob; dbs=glob.glob(os.path.expanduser('~/.claude-memory/memory.db')) or glob.glob('.claude-memory/memory.db'); print(f'DB: {dbs[0]}, Size: {os.path.getsize(dbs[0])//1024}KB') if dbs else print('No memory.db found')" 2>/dev/null || echo "Memory DB check failed"

> The Thin Ledger: unified memory with provenance, correction workflow, and three lifecycle operations.

## What It Does

Memory Server is the core persistence layer for clawd-lobster. It implements the **Thin Ledger pattern**: three layers working together, each with a clear role.

| Layer | Name | What It Does |
|-------|------|-------------|
| **SQLite** | The Ledger | Operational truth: decisions, TODOs, audit log, salience, provenance |
| **Git Wiki** | The Library | Compiled knowledge: cross-referenced markdown pages with citations |
| **Oracle Vector DB** | The Vault | Deep recall: all knowledge vectorized, cross-machine semantic search |

## Three Lifecycle Operations

**INGEST**: New information enters the system:
- Raw sources land in `knowledge/raw/`
- LLM summarizes → creates wiki pages with provenance (agent, confidence, lifecycle)
- SQLite stores metadata, decisions, salience scores

**QUERY**: Finding what you need:
- Search SQLite (structured) + Wiki (ripgrep) + Oracle (vector, if enabled)
- Answers cite sources. Valuable answers get written back to the wiki.

**LINT**: Keeping knowledge healthy (runs in evolve-tick.py):
- Broken wiki links, orphan pages, stale claims (>90 days untouched)
- Pending corrections in `.pending/` need review
- DB/wiki drift detection

## How It Works

Runs as an always-on MCP server (`python -m mcp_memory.server`) that exposes 27 tools over MCP.

**Salience engine:**
- Access: +5%, Reinforce: +20%, Decay: -1%/day (30-day half-life)

**Provenance** on every knowledge record:
- `source_agent`: who wrote it (claude, codex, gemini)
- `confidence`: how sure (0.0-1.0)
- `lifecycle`: state (raw → extracted → synthesized → accepted → superseded)
- `upstream_ids`: what L1 events led to this

**Key tool groups:**
- **Store/Record**: `memory_store`, `memory_record_decision`, `memory_record_resolved`, `memory_record_question`, `memory_record_knowledge`
- **Retrieve**: `memory_list`, `memory_get`, `memory_get_summary`, `memory_search`
- **Correct**: `memory_propose_correction` (creates claim_challenge + .pending/ file)
- **Manage**: `memory_delete`, `memory_reinforce`, `memory_compact`, `memory_status`
- **Skills**: `memory_learn_skill`, `memory_list_skills`, `memory_improve_skill`
- **Audit/Logs**: `memory_log_action`, `memory_audit_search`, `memory_audit_stats`, `memory_daily_report`, `memory_activity_log`
- **TODOs**: `memory_todo_add`, `memory_todo_list`, `memory_todo_update`, `memory_todo_search`
- **Cloud**: `memory_oracle_summary`

## Correction Workflow

Agents cannot directly edit wiki pages. They propose corrections:

1. Agent calls `memory_propose_correction(wiki_page, issue, evidence, proposed_fix)`
2. Creates `claim_challenges` record in SQLite + `.pending/<page>.md` file
3. Lead agent or human reviews the proposal
4. Accept → update wiki, mark old content as superseded
5. Reject → close with reason

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `oracle_enabled` | boolean | `false` | Enable Oracle Vector DB (The Vault) |
| `embeddings_enabled` | boolean | `false` | Enable OpenAI embeddings for vector search |

## Dependencies

| Type | Requirement |
|------|-------------|
| System | Python 3 |
| Python | `fastmcp >=3.0, <4.0` |
| Skills | None (this is the foundation) |

No credentials required for SQLite-only. Oracle needs connection string. Embeddings need OpenAI key.

## Gotchas

1. **Storing too much, retrieving too little.** Always `memory_search` before storing (avoid duplicates) and before starting a task (leverage past learnings).

2. **Salience decay making important items invisible.** Items untouched for 30+ days sink in rankings. Periodically `memory_reinforce` foundational decisions.

3. **SQLite lock contention.** If MCP server and evolve-tick access `memory.db` simultaneously, use WAL mode and retry on lock errors.

4. **Forgetting to compact.** Low-salience noise accumulates. Run `memory_compact` weekly or via evolve cycle.

5. **Oracle sync assumes network.** When enabled, writes attempt Oracle sync. Network down = potential blocking. SQLite is always source of truth.

*Architecture absorbed from [MemPalace](https://github.com/milla-jovovich/mempalace) (spatial structure) and [Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (INGEST/QUERY/LINT). See `openspec/MEMORY-ARCHITECTURE.md` for the full design.*

**Version:** 0.5.0 | **Kind:** mcp-server | **Category:** core
