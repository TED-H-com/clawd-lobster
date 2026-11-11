# API Reference

This document outlines the core HTTP endpoints and internal Python APIs in Clawd-Lobster.

## HTTP API Endpoints (`clawd_lobster/server.py`)

All state-mutating requests (POST) must carry an `X-Clawd-Token` header for CSRF protection.
Auth endpoints require a token either as a `?token=` query parameter or a `Bearer` token in the `Authorization` header.

### Onboarding API (Sole State Authority)

*   **`POST /api/onboarding/session`**: Create a new onboarding session. Returns a session ID and token.
*   **`GET /api/onboarding/state`**: Get current onboarding state. Requires `session_id`.
*   **`POST /api/onboarding/intent`**: Apply a state mutation intent (e.g., `set_status`, `set_foundation`).
*   **`GET /api/onboarding/health`**: Run and return health probes for system dependencies.
*   **`GET /api/onboarding/manifest`**: Get the current onboarding manifest.
*   **`GET /api/onboarding/events`**: Retrieve the audit trail (events log).
*   **`POST /api/onboarding/reconcile`**: Reconcile state drift with actual system configuration.
*   **`POST /api/onboarding/handoff-gen`**: Generate `CLAUDE.md` instructions for handoff to the CLI.
*   **`POST /api/onboarding/detect`**: Detect handoff state from CLI.

### Controller Lease API

Ensures single-writer mutations between Web UI and Claude CLI.

*   **`POST /api/controller/acquire`**: Acquire the controller lease.
*   **`POST /api/controller/renew`**: Renew the lease.
*   **`POST /api/controller/release`**: Release the lease.
*   **`POST /api/controller/handoff`**: Transfer the lease from web to claude.

### System & Workspaces API

*   **`GET /api/status`**: Return system status, Python version, and first-time flag.
*   **`GET /api/workspaces`**: List all registered workspaces.
*   **`POST /api/workspaces/create`**: Create a new workspace (params: `name`, `domain`, `description`).

### Squad API

*   **`POST /api/squad/chat`**: Submit a discovery turn message (Terminal/Web shared).
*   **`POST /api/squad/start`**: Launch the Spec Squad agents.
*   **`GET /api/squad/state`**: Get current squad state for a given workspace.

### Skills & Jobs API

*   **`GET /api/skills/catalog`**: List the skills catalog.
*   **`GET /api/jobs/status`**: Return status of registered background jobs.
*   **`POST /api/jobs/register`**: Register cron jobs for a skill.
*   **`POST /api/skills/<skill_id>/install`**: Install a skill.
*   **`POST /api/skills/<skill_id>/verify`**: Verify a skill's health.

### Vault API

*   **`POST /api/vault/test`**: Test connection to Oracle Vault.
*   **`POST /api/vault/save`**: Save Vault credentials to config.

---

## Internal Python API

### Agent Dispatch (`scripts/agent_dispatch.py`)

A wrapper around the Claude Agent SDK for executing sub-agents natively without shelling out to the CLI.

#### `async def dispatch(prompt: str, **kwargs) -> DispatchResult`

Dispatches a task to a Claude sub-agent.

**Arguments:**
*   `prompt` (str): Task instruction.
*   `cwd` (str|Path): Working directory for the agent.
*   `system_prompt` (str): Role-specific prompt instructions.
*   `tools` (list[str]): Names of tools to enable. Defaults to `["Read", "Glob", "Grep"]`.
*   `permission_mode` (str): `"default"`, `"acceptEdits"`, or `"bypassPermissions"`.
*   `max_turns` (int): Maximum agent iterations (default 30).
*   `vault` (bool): Attach Vault MCP tools if True.
*   `timeout_seconds` (int): Hard timeout (default 600s).

**Returns:** `DispatchResult` containing text, tool usage stats, and JSON blocks.

#### `def dispatch_sync(prompt: str, **kwargs) -> DispatchResult`

Synchronous wrapper for `dispatch()`. Spawns a localized event loop. Will raise `RuntimeError` if called from within an existing event loop.

### Vault API (`scripts/vault_api.py`)

Provides the semantic memory layer and Oracle database interactions.

#### `class Vault`

*   `__init__(self, wallet_dir="", dsn="", user="", password="")`: Initialize connection pool to Oracle DB.
*   `ingest(self, content: str, doc_type: str, meta: dict = None, original_path: str = None)`: Ingest a document and chunk/embed it.
*   `bulk_ingest(self, items: list[dict])`: Optimized fast-path for bulk data insertion.
*   `search(self, query: str, doc_type: str = None, limit: int = 5, threshold: float = 0.5)`: Semantic vector search.
*   `add_entity(self, entity_type: str, canonical_name: str, aliases: list = None)`: Create or update a knowledge entity.
*   `add_relation(self, subject_type, subject_id, relation_type, target_type, target_id)`: Link entities in the knowledge graph.
*   `merge_entities(self, source_id: int, target_id: int)`: Merge two entities (e.g. "JS" and "JavaScript").
*   `gdpr_erase(self, entity_id: int, reason: str)`: Hard delete an entity and its associated memories.
