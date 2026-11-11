# Developer Guide

This guide provides examples of how to interact programmatically with the core modules in Clawd-Lobster.

## 1. Invoking Sub-Agents via `agent_dispatch.py`

The `agent_dispatch` module provides a bridge to the Claude Agent SDK without shelling out to the `claude` executable.

### Example: Async Dispatch (Preferred)

When running within an `asyncio` context, use the native `dispatch` method.

```python
import asyncio
from pathlib import Path
from scripts.agent_dispatch import dispatch

async def main():
    workspace = Path("/tmp/my-workspace")
    prompt = "Create a hello world python script in this folder."

    # Run the agent with custom permissions and timeout
    result = await dispatch(
        prompt=prompt,
        cwd=workspace,
        system_prompt="You are a helpful Python developer.",
        tools=["Write", "Read", "Bash"], # Grant bash access
        permission_mode="acceptEdits",
        timeout_seconds=300
    )

    print(f"Agent finished in {result.elapsed_seconds}s")
    print(f"Final output: {result.text}")
    print(f"Tools used: {len(result.tool_calls)}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Example: Sync Dispatch

If you are inside a synchronous context (e.g., standard HTTP request handlers), use `dispatch_sync`.

```python
from scripts.agent_dispatch import dispatch_sync

def handle_request():
    result = dispatch_sync(
        "Analyze the logs in ./app.log",
        cwd=".",
        tools=["Read", "Grep"]
    )
    return result.text
```

**Note:** `dispatch_sync` will throw a `RuntimeError` if called from within an existing event loop.

## 2. Authoring a Custom State Intent

State mutations in the Onboarding and Setup flows strictly follow a single-writer Intent system.

### Step 1: Define the Intent Function

Create a handler function in `clawd_lobster/onboarding/intents.py`. It must accept the state, target item ID, payload, and actor string. It returns a status dictionary.

```python
def _intent_mark_tested(
    state: dict, item_id: str | None, payload: dict, actor: str,
) -> dict:
    """Handle an intent to mark a feature as tested."""
    if not item_id:
        return {"ok": False, "error": "item_id required"}

    test_result = payload.get("test_result")
    if not test_result:
        return {"ok": False, "error": "payload.test_result required"}

    # Find the item in state
    item = state_store.find_item(state, item_id)
    if item is None:
        return {"ok": False, "error": f"Item not found: {item_id}"}

    # Apply mutation
    item["facts"]["tested"] = True
    item["facts"]["test_result"] = test_result
    item["last_actor"] = actor

    return {"ok": True, "message": f"{item_id}: successfully marked as tested"}
```

### Step 2: Register the Intent

Add your new function to the `handlers` dictionary inside `apply_intent()` in the same file.

```python
    handlers = {
        "set_status": _intent_set_status,
        "set_foundation": _intent_set_foundation,
        "mark_tested": _intent_mark_tested, # <--- Register here
    }
```

Clients can now hit `POST /api/onboarding/intent` with `"intent": "mark_tested"`. The backend will securely increment the revision, broadcast changes, and append to the audit log `events.jsonl`.

## 3. Adding a New HTTP Handler

The thin server (`clawd_lobster/server.py`) relies on `http.server` to stay dependency-free.

### Step 1: Create the Handler Method

Inside the `_Handler` class in `server.py`, add a new method using the `_api_` prefix convention. Use helper functions like `_send_json()` or `_read_body()`.

```python
    def _api_system_metrics(self, query: dict) -> None:
        """
        Return system metrics.
        URL: GET /api/system/metrics?detailed=true
        """
        # query parameters are parsed as lists: {'detailed': ['true']}
        detailed = "detailed" in query and query["detailed"][0] == "true"

        metrics = {
            "status": "healthy",
            "cpu": get_cpu() if detailed else None
        }

        self._send_json({"ok": True, "metrics": metrics})
```

### Step 2: Register the Route

Map the URL to your method in the appropriate HTTP method function (e.g., `do_GET` or `do_POST`). If your endpoint returns sensitive data or modifies state, ensure it goes through the `_require_auth` check block if placed under `/api/`.

```python
    def do_GET(self) -> None:
        # ... validation ...
        routes = {
            "/api/system/metrics": self._api_system_metrics,
            # ... existing routes ...
        }
```
