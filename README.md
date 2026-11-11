# Clawd-Lobster

![Version](https://img.shields.io/badge/version-0.6.0-blue)
![License](https://img.shields.io/github/license/teddashh/clawd-lobster)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)

**English** · [繁體中文](README.zh-TW.md)

Clawd-Lobster wraps the Claude Code CLI with a per-workspace MCP memory server, a four-role Spec Squad built on the Claude Agent SDK, eleven skill manifests, and scheduled git sync across machines.

**Project page:** https://teddashh.github.io/clawd-lobster/

> **Status: experimental, not maintained.** 136 commits between April 1 and April 9, 2026, then cleanup and security fixes in October 2026. No tagged releases and no PyPI package. The package version is 0.6.0; see [CHANGELOG.md](CHANGELOG.md) and [Status and limits](#status-and-limits).

---

## Why it exists

A new Claude Code session does not know what the last one decided unless you paste it in or keep it in CLAUDE.md, and each machine keeps its own copy. Decisions, open TODOs, and lessons from failed attempts end up scattered across chat logs. A spec written and approved by the same session carries its gaps straight into the code.

Clawd-Lobster does not replace Claude Code. It adds memory, reviewed specs, scheduling, and a setup wizard around it, through the extension points Claude Code already has: MCP servers, CLAUDE.md, settings.json hooks, and the Claude Agent SDK.

- **Claude Code CLI and Agent SDK only.** No custom agent loop and no patched Claude Code, so most Claude Code updates need no changes here.
- **Small enough to read.** About 25,800 lines of Python, shell, PowerShell, and JavaScript, including about 3,000 lines of older Spec Squad versions in `scripts/legacy/`.
- **Setup in the browser.** `clawd-lobster serve` opens a setup wizard, and a Claude Code session can drive the same wizard from the terminal.

```
  You describe the project
       |
       v
  Discovery: Claude asks follow-up questions
       |
       v
  +--------------------------------------+
  |              SPEC SQUAD              |
  |                                      |
  |  [A] Architect   writes the spec     |
  |  [R] Reviewer    challenges it       |
  |  [C] Coder       builds from tasks   |
  |  [T] Tester      checks each item    |
  |                                      |
  |  Every turn is a fresh Agent SDK     |
  |  session. The Reviewer never sees    |
  |  the Architect's prompt and can      |
  |  only read files.                    |
  +--------------------------------------+
       |
       v
  Spec, code, and test results in the workspace
```

---

## Quick start

```bash
git clone https://github.com/teddashh/clawd-lobster
cd clawd-lobster
pip install -e ".[agent]"
clawd-lobster serve
```

`serve` starts the dashboard on 127.0.0.1:3333 and opens your browser at the setup wizard (`--no-open` skips the browser, `--port` changes the port). Pick a language (English, 繁體中文, 简体中文, 日本語, or 한국어), then work through four foundations (language, Claude Code sign-in, GitHub Hub, workspace root) and six required skills. The [onboarding guide](docs/onboarding-guide.html) covers the same steps.

Spec Squad needs the `agent` extra, which installs `claude-agent-sdk`. A plain `pip install -e .` installs everything else.

### Terminal only

```bash
clawd-lobster setup        # terminal onboarding
clawd-lobster squad start  # run Spec Squad in the current folder
```

### Install scripts

```powershell
# Windows
.\install.ps1
```

```bash
# macOS / Linux
chmod +x install.sh && ./install.sh
```

The scripts run nine steps: prerequisites, authentication, Hub setup, configuration, the memory server, CLAUDE.md and settings (CLAUDE.md is backed up before anything is appended), workspaces, the scheduler (sync and heartbeat every 30 minutes) with machine registration, and migration from an older setup.

---

## What you get

### 1. Spec Squad

You describe what you want, and four roles take it from there.

The **Architect** writes OpenSpec files with SHALL/MUST requirements and Gherkin scenarios. The **Reviewer**, a separate session that never sees the Architect's instructions and can only read files, challenges the spec. They loop until the Reviewer approves, for up to five rounds. If the Reviewer still has not approved after the fifth round, the spec is approved anyway so the pipeline can go on, but it is recorded as forced: `.spec-squad.json` says `"approval": "round_limit"` instead of `"reviewer"`, the turn log gets a `FORCED_APPROVAL` entry, and the terminal and the web view both say that the round limit approved it. The **Coder** builds from `tasks.md`, and the **Tester** checks each requirement. Only the Coder and Tester can run shell commands.

Each role works in its own context: the Reviewer is not working from the Architect's reasoning, and the Tester does not know which shortcuts the Coder took.

Two interfaces, same engine:
- **Web:** a discovery chat asks follow-up questions until there is enough to start, then a live view shows each phase and turn.
- **Terminal:** type the description and press Enter twice. After the spec is reviewed, it asks before building.

### 2. A brain that doesn't forget: the Thin Ledger

| Layer | What | Role |
|-------|------|------|
| **SQLite (the Ledger)** | Decisions, TODOs, audit log, salience scores, provenance | Operational record, one database per workspace |
| **Git wiki (the Library)** | Markdown pages under `knowledge/wiki/` with an index | Compiled knowledge, readable and synced through git |
| **Oracle (the Vault)** | Embeddings and cross-machine semantic search | Optional; needs an Oracle database and an embedding endpoint |

The memory server is a FastMCP server with 27 tools ([skills/memory-server](skills/memory-server/README.md)). Knowledge records carry provenance: the source agent, a confidence score, and a lifecycle state (raw, extracted, synthesized, accepted, or superseded).

**Three operations keep it healthy:**
- **Ingest:** the absorb skill reads repositories, folders, files, and web pages and stores what it finds as knowledge.
- **Query:** `memory_search` ranks results by salience and falls back to local text search when the Oracle search returns nothing.
- **Lint:** evolve-tick checks each wiki for broken index links, orphan pages, pages untouched for 90 days, and pending corrections.

**Correction workflow:** agents do not edit wiki pages directly. `memory_propose_correction` files a challenge for review (plus a note in `knowledge/.pending/` when that folder exists), so disputed claims get resolved instead of silently overwritten.

Items gain salience when they are used and lose it when they are not, so the decisions that matter stay near the top of search results.

*Architecture ideas from [MemPalace](https://github.com/MemPalace/mempalace) (spatial structure) and [Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (ingest, query, lint). Concepts only; neither is installed as a dependency.*

### 3. Heartbeat

The heartbeat runs from the OS scheduler (Task Scheduler, cron, or launchd) every 30 minutes instead of as a resident daemon. For each workspace it looks for a running `claude` process by name. If none matches, it opens a terminal in that workspace and runs `claude --resume`, which shows the session picker rather than reattaching a specific session.

### 4. All your machines, one brain

GitHub is the control plane and git is the protocol. Setup creates or joins a private GitHub repository as your Hub. The install scripts schedule `sync-all` every 30 minutes; it pulls, commits, and pushes every git repository under the workspace root, so a pattern learned on one machine reaches the others on their next sync. To add a machine, run the install script and join the existing Hub.

### 5. Self-evolution

Every two hours (the dashboard registers this job when you set up the evolve skill: it adds one line to your crontab and leaves the rest alone, or creates a Task Scheduler task on Windows), evolve-tick collects recently completed TODOs and logged actions from every workspace and asks Claude to save reusable patterns as learned skills. It also decays the salience of unused items and lints the wiki. Improvement ideas are written as proposal files under `openspec/proposals/` and committed for a person to review.

---

## The dashboard

`clawd-lobster serve` runs a standard-library HTTP server on 127.0.0.1:3333.

- **Onboarding:** the setup wizard. Each card lists its steps and stays locked until what it depends on has passed.
- **Workspaces:** each workspace with its path, domain, creation date, and current Squad phase, plus a form to create one.
- **Skills:** the catalog in three tabs (MCP Servers, Prompt Patterns, Cron Jobs), each skill marked Always On, Enabled, or Disabled.
- **Credentials:** Claude Code, GitHub, OpenAI Codex, Google Gemini, Oracle Vault, and Odoo. Sign-in checks exist for Claude Code and GitHub; the Update button is still a placeholder.
- **Spec Squad:** the discovery chat, then a live view of phases and turns.

### Agent-guided setup

This is not a traditional installer. The web dashboard and a Claude Code session work as co-pilots:

```
Web (visual layer)        +   Claude Code (conversation layer)
Shows skill cards             Explains what each skill does
Shows setup progress          Answers your questions
Shows config forms            Runs install commands
Updates in real time          Reads state, advances the flow
```

Neither one is in charge. Both submit intents through a single backend API, and one controller lease keeps them from acting at the same time.

> **Security note:** the dashboard listens on 127.0.0.1 only and checks every request before it does anything else. The Host header must be `127.0.0.1:<port>` or `localhost:<port>`, which stops DNS rebinding. A request with an Origin header must come from the dashboard itself. Every POST must send the per-process token in an `X-Clawd-Token` header, which stops other web pages from sending requests (CSRF). The server makes a new random token each time it starts, puts it in the pages it serves, and writes it to `~/.clawd-lobster/server-<port>.token` (readable only by you) for local scripts; the file is removed when the server stops. Failed checks get 403, CORS preflights always get 403, and no `Access-Control-*` headers are sent. The onboarding API also needs its session token, as before. The token keeps web pages out, not other programs running as you on the same machine, so stop `clawd-lobster serve` when you are done.

---

## Skills

Eleven skill manifests in four kinds, plus a folder for learned skills. Six are required during setup; the rest are optional.

| Skill | Kind | Setup | What it does |
|-------|------|-------|--------------|
| [memory-server](skills/memory-server/README.md) | MCP server | Required | 27 MCP tools for decisions, knowledge, TODOs, learned skills, audit, and search |
| [spec](skills/spec/README.md) | Prompt pattern | Required | Workspace creation, OpenSpec documents, and the Spec Squad pipeline |
| [absorb](skills/absorb/README.md) | Prompt pattern | Required | Reads repositories, folders, files, and web pages into memory, or into the Vault when Oracle is set up |
| [evolve](skills/evolve/README.md) | Cron, every 2 hours | Required | Reviews completed TODOs and recent actions, stores learned skills, decays salience, lints the wiki |
| [heartbeat](skills/heartbeat/README.md) | Cron, every 30 minutes | Required | Runs `claude --resume` for workspaces with no running session |
| [deploy](skills/deploy/README.md) | Prompt pattern | Required | `/deploy` detects the stack and generates Dockerfiles, Compose files, and nginx configs for dev, staging, and prod |
| [migrate](skills/migrate/README.md) | Prompt pattern | Optional | Imports memories and configs from `~/.claude/`, `~/.openclaw/`, and `~/.hermes/` |
| [codex-bridge](skills/codex-bridge/README.md) | Prompt pattern | Optional | Hands bulk or parallel work, or a second review, to the OpenAI Codex CLI |
| [gemini-bridge](skills/gemini-bridge/README.md) | Prompt pattern | Optional | Asks the Gemini CLI for a second opinion on uncertain or complex decisions |
| [notebooklm-bridge](skills/notebooklm-bridge/README.md) | Prompt pattern | Optional | Syncs workspace docs to Google NotebookLM to generate slides, infographics, audio overviews, and reports |
| [connect-odoo](skills/connect-odoo/README.md) | Poller | Optional | Odoo over XML-RPC: 6 MCP tools plus a poller that watches for changes |
| [learned](skills/learned/README.md) | Folder | Automatic | Patterns stored by evolve |

Every skill has a manifest (`skill.json`) with its description, credentials, and health check; required skills also list their setup steps and dependencies. [scripts/skill-manager.py](scripts/skill-manager.py) lists skills and handles enable, disable, config, credentials, health checks, and rebuilding `.mcp.json` and `settings.json` from the registry.

---

## Architecture

```
Skills (the what)      ->  11 skill manifests (skill.json) with instructions
Tools (the how)        ->  27 MCP tools + Claude Code's own tools + the dashboard API
Hooks (the when)       ->  OS scheduler, git, PostToolUse and Stop hooks
Memory (the brain)     ->  SQLite ledger + git wiki + optional Oracle Vault
Operations (the cycle) ->  ingest, query, lint
Dashboard (the eyes)   ->  web UI at 127.0.0.1:3333
```

**Standing on the giant's shoulders.** Clawd-Lobster does not rebuild Claude Code. It uses Claude Code's own extension points (MCP servers, CLAUDE.md, hooks, settings.json) as documented, so there is no adapter layer to update when Claude Code or the model changes.

```
Tracked files:  about 2.6 MB (code, configs, docs)
Code:           about 25,800 lines of Python, shell, PowerShell, JavaScript
Memory server:  about 90 MB resident at idle (Python 3.14, FastMCP 3)
Scheduling:     OS scheduler jobs that run and exit; no resident daemon
```

For the file tree and runtime details, see [ARCHITECTURE.md](ARCHITECTURE.md). Some counts there predate the current code; it lists 32 MCP tools, and the server has 27.

---

## Developer Documentation

For developers looking to integrate with or extend Clawd-Lobster, please refer to the following documentation:

- [API Reference](docs/api-reference.md): Outlines the core HTTP endpoints and internal Python APIs.
- [Developer Guide](docs/developer-guide.md): Provides examples for interacting with core modules programmatically.
- [Architecture & Handlers](docs/architecture-and-handlers.md): Deep dive into the event loop, state intents, and custom handlers.

---

## CLI reference

| Command | What it does |
|---------|--------------|
| `clawd-lobster serve` | Start the dashboard on 127.0.0.1:3333 (`--port`, `--no-open`, `--daemon`) |
| `clawd-lobster setup` | Terminal onboarding wizard |
| `clawd-lobster workspace create <name>` | Create a workspace (`--domain`, `--description`, `--repo`, `--dry-run`) |
| `clawd-lobster squad start` | Run Spec Squad in the terminal (`--workspace` takes a name or path; default is the current folder) |
| `clawd-lobster status` | Show system health |

There is no `clawd-lobster deploy` command; deployment is the `/deploy` prompt pattern inside Claude Code.

---

## Multi-machine setup

```
  clawd-lobster (this repo, the generator)
       |
       |  install once
       v
  clawd-yourname (your private Hub on GitHub)
       |
       +-- Machine A: skills + memory + heartbeat
       +-- Machine B: skills + memory + heartbeat
       +-- Machine C: skills + memory + heartbeat
            |
            Synced through git every 30 minutes.
```

The first machine creates the Hub; the install scripts suggest `clawd-` plus your user name. Every machine after that joins it.

The workspace registry, `workspaces.json`, is per-machine state: this repository does not track it and ships [workspaces.example.json](workspaces.example.json) to show the format, while your private Hub tracks its own copy. Files and commit messages that get pushed name a machine only by the `machine_id` in `~/.clawd-lobster/config.json` (the install scripts suggest a random `machine-` label), never by its host name.

---

## Requirements

- Python 3.10 or newer (3.11 or newer for the memory server)
- Claude Code CLI, installed and signed in ([setup guide](https://code.claude.com/docs/en/setup))
- Git 2.x
- A GitHub account and the gh CLI, for the Hub
- Node.js is optional; the prerequisite check reports it but does not require it
- Optional: an Oracle database and an embedding endpoint (Vault and vector search), the OpenAI Codex CLI, the Gemini CLI, a Google account for NotebookLM, an Odoo server

---

## Status and limits

Experimental. 136 commits between April 1 and April 9, 2026, then cleanup and security fixes in October 2026. No tagged releases.

**Works today**
- `pip install -e .` gives a `clawd-lobster` command with serve, setup, workspace create, squad start, and status
- The tests pass: 89 unit tests (onboarding, scheduler registration, the dashboard's request checks, the Spec Squad approval record, the sync script, and PowerShell encoding) plus a scripted end-to-end run through the HTTP API (rechecked on Python 3.14 in October 2026)
- The memory server runs on SQLite alone, with text search ranked by salience
- Install scripts for Windows (PowerShell), macOS, and Linux
- Spec Squad in the terminal stops after the spec and asks before any code is written

**Limits and not yet**
- No feature work since April 9, 2026, and not checked against later Claude Code or Agent SDK releases
- The dashboard's token keeps other web pages out, but any program running as you on the same machine can read it
- If the Reviewer has not approved after five rounds, the spec is still approved and the web flow goes on to build; the state file, the turn log, and both interfaces mark it as forced by the round limit
- The 30-minute sync commits and pushes every git repository under the workspace root, including new Markdown, JSON, YAML, HTML, and script files, so keep anything you do not want pushed outside that folder
- Heartbeat matches sessions by process name and revives them with a plain `claude --resume`
- Spec Squad needs the `[agent]` extra; vector search and the Vault need an Oracle database; the memory server needs Python 3.11 or newer

---

## Philosophy

**1. Amplify, don't rebuild.**
Claude Code does the agent work. This adds a nervous system around it and leaves the brain alone.

**2. When the giant grows taller, you grow taller.**
Nothing here patches Claude Code, so its updates rarely need changes here.

**3. The plan is the product.**
Spec Squad does not write code first. It writes a spec, has a separate session review it, then builds to the spec. The spec is the contract.

---

## Contributing

PRs welcome. Read [ARCHITECTURE.md](ARCHITECTURE.md) before contributing.

## Other languages

[简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md). These describe an earlier version; this README and the [project page](https://teddashh.github.io/clawd-lobster/) are current.

## License

MIT. See [LICENSE](LICENSE).
