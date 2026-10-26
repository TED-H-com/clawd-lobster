# Clawd-Lobster Architecture

Detailed project structure and internals. For overview, see [README.md](README.md).

> **For a deep dive into the architecture, event loop lifecycle, and a guide for authoring custom handlers, please see [Architecture, Event Loop, and Handlers Guide](docs/architecture-and-handlers.md).**

## Full File Tree

```
clawd-lobster/
├── skills/                          Skill modules (each with skill.json manifest)
│   ├── memory-server/               32-tool MCP memory with salience + evolution
│   │   ├── mcp_memory/              Python package (pip install -e .)
│   │   └── skill.json               Manifest
│   ├── connect-odoo/                Odoo ERP integration (XML-RPC + poller)
│   │   ├── connect_odoo/            MCP server + poller
│   │   └── skill.json               Manifest
│   ├── evolve/                      Self-evolution prompt pattern
│   │   └── skill.json               Manifest
│   ├── heartbeat/                   Session keep-alive (cron)
│   │   └── skill.json               Manifest
│   ├── absorb/                      Knowledge ingestion from any source
│   │   └── skill.json               Manifest
│   ├── spec/                        Guided planning + blitz execution
│   │   └── skill.json               Manifest
│   ├── codex-bridge/                Delegate work to OpenAI Codex
│   │   └── skill.json               Manifest
│   ├── notebooklm-bridge/           Free RAG + content engine via NotebookLM
│   │   └── skill.json               Manifest
│   ├── migrate/                     Import from existing setups
│   │   └── skill.json               Manifest
│   └── learned/                     Auto-generated skills from experience
│
├── scripts/
│   ├── skill-manager.py             Skill Management CLI
│   ├── sync-all.ps1                 Windows: auto git sync + decay
│   ├── sync-all.sh                  Linux/macOS: auto git sync + decay
│   ├── heartbeat.ps1                Windows: session keep-alive
│   ├── heartbeat.sh                 Linux/macOS: session keep-alive
│   ├── new-workspace.ps1            Create workspace + GitHub repo
│   ├── workspace-create.py          Automated workspace creation
│   ├── validate-spec.py             Hard validation for spec artifacts
│   ├── setup-hooks.sh               Install git pre-commit hooks (Unix)
│   ├── setup-hooks.ps1              Install git pre-commit hooks (Windows)
│   ├── evolve-tick.py               Pattern extraction + proposals + salience decay
│   ├── notebooklm-sync.py           Auto-push workspace docs to NotebookLM
│   ├── init_db.py                   Initialize memory database
│   └── security-scan.py             5-tool security scanner
│
├── templates/                       Config templates (no secrets)
│   ├── global-CLAUDE.md
│   ├── workspace-CLAUDE.md
│   ├── mcp.json.template
│   └── settings.json.template
│
├── webapp/                          Skill Management Dashboard
│   └── index.html                   3-tab UI: Skills + Setup + Settings
│
├── knowledge/                       Shared knowledge base (git-synced)
├── soul/                            Agent personality (optional)
├── workspaces.example.json          Registry format (workspaces.json is per-machine, untracked)
├── install.ps1                      Windows installer (4-phase)
├── install.sh                       Linux/macOS installer (4-phase)
├── Dockerfile                       Docker build
├── docker-compose.yml               Docker Compose config
├── LICENSE                          MIT
└── README.md
```

## Runtime Layers

| Layer | What | Lines | RAM | When |
|-------|------|-------|-----|------|
| **Runtime** | MCP Memory Server (32 tools + SQLite) | ~1,400 | ~25 MB | Always on |
| **Runtime** | Odoo Connector (if enabled) | ~280 | ~22 MB | When enabled |
| **Cron** | evolve-tick (proposal generator) | ~465 | ~20 MB peak | Every 2h, then exits |
| **Cron** | heartbeat + sync | ~300 | ~5 MB peak | Every 30min, then exits |
| **Cron** | NotebookLM sync (if enabled) | ~200 | ~15 MB peak | After blitz, then exits |
| **Static** | Web UI (browser renders it) | ~1,900 | 0 on server | On demand |
| **Setup** | Installers, workspace-create, skill-manager | ~2,800 | 0 | Run once |
| **Docs** | SKILL.md files, README, CHANGELOG | ~3,500 | 0 | Claude reads on demand |
| **Config** | skill.json manifests, templates | ~900 | 0 | Read at startup |

**Resident footprint: one Python process (~25 MB) + SQLite.** Everything else either runs-and-exits (cron), lives in the browser (Web UI), or is just files Claude reads when needed.
