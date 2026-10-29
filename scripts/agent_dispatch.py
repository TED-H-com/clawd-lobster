"""
agent_dispatch.py: Unified sub-agent dispatch using Claude Agent SDK.

Replaces subprocess.run(["claude", "-p", ...]) with native Agent SDK query().
Provides both async and sync interfaces for backward compatibility.

Usage:
    # Async (preferred)
    result = await dispatch(prompt, cwd="/path/to/workspace")

    # Sync (for scripts that can't use async)
    result = dispatch_sync(prompt, cwd="/path/to/workspace")

    # With Vault MCP tools
    result = await dispatch(prompt, cwd=cwd, vault=True)

    # With custom tools and system prompt
    result = await dispatch(prompt, cwd=cwd,
                            system_prompt="You are a code reviewer.",
                            tools=["Read", "Glob", "Grep"],
                            max_turns=10)
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Core dispatch
# ---------------------------------------------------------------------------

async def dispatch(
    prompt: str,
    *,
    cwd: str | Path | None = None,
    system_prompt: str | None = None,
    tools: list[str] | None = None,
    permission_mode: str = "default",
    max_turns: int = 30,
    vault: bool = False,
    timeout_seconds: int = 600,
    on_text: Any = None,
) -> DispatchResult:
    """Dispatch a task to a Claude sub-agent via Agent SDK.

    Args:
        prompt: The task instruction.
        cwd: Working directory for file operations.
        system_prompt: Optional role-specific system prompt.
        tools: List of tool names. Default: ["Read", "Glob", "Grep"].
        permission_mode: "default", "acceptEdits", or "bypassPermissions".
        max_turns: Maximum agent iterations.
        vault: If True, attach Vault MCP tools.
        timeout_seconds: Hard timeout (async cancel after this).
        on_text: Optional callback(role: str, chunk: str) for streaming.

    Returns:
        DispatchResult with text, json_blocks, usage, and metadata.
    """
    from claude_agent_sdk import (
        query, ClaudeAgentOptions, AssistantMessage, ResultMessage,
        SystemMessage, TextBlock, ToolUseBlock,
    )

    if tools is None:
        tools = ["Read", "Glob", "Grep"]

    opts: dict[str, Any] = {
        "allowed_tools": tools,
        "permission_mode": permission_mode,
        "max_turns": max_turns,
    }
    if cwd:
        opts["cwd"] = str(cwd)
    if system_prompt:
        opts["system_prompt"] = system_prompt

    # Attach Vault MCP if requested
    if vault:
        try:
            from vault_mcp_server import create_vault_mcp
            opts["mcp_servers"] = {"vault": create_vault_mcp()}
        except ImportError:
            import logging
            logging.warning("vault=True requested but vault_mcp_server not importable")

    text_parts: list[str] = []
    tool_calls: list[dict] = []
    session_id: str | None = None
    usage_total: dict[str, int] = {"input_tokens": 0, "output_tokens": 0}
    t0 = time.time()

    async def _run_query():
        async for msg in query(
            prompt=prompt,
            options=ClaudeAgentOptions(**opts),
        ):
            if isinstance(msg, SystemMessage) and msg.subtype == "init":
                session_id_holder.append(msg.data.get("session_id"))

            elif isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        text_parts.append(block.text)
                        if on_text:
                            on_text("assistant", block.text)
                    elif isinstance(block, ToolUseBlock):
                        tool_calls.append({"name": block.name, "id": block.id})
                if msg.usage:
                    usage_total["input_tokens"] += msg.usage.get("input_tokens", 0)
                    usage_total["output_tokens"] += msg.usage.get("output_tokens", 0)

            elif isinstance(msg, ResultMessage):
                if msg.result:
                    text_parts.append(msg.result)

    session_id_holder: list[str | None] = []
    try:
        await asyncio.wait_for(_run_query(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        text_parts.append(f"\n[TIMEOUT after {timeout_seconds}s]")
    except asyncio.CancelledError:
        pass

    session_id = session_id_holder[0] if session_id_holder else None

    elapsed = round(time.time() - t0, 1)
    full_text = "\n".join(text_parts)

    # Extract JSON blocks from output (backward compat with evolve-tick pattern)
    json_blocks = _extract_json_blocks(full_text)

    return DispatchResult(
        text=full_text,
        json_blocks=json_blocks,
        tool_calls=tool_calls,
        session_id=session_id,
        usage=usage_total,
        elapsed_seconds=elapsed,
    )


def dispatch_sync(
    prompt: str, **kwargs: Any
) -> DispatchResult:
    """Synchronous wrapper around dispatch(). For scripts without async.

    Note: Cannot be called from within a running event loop (e.g., Jupyter,
    async web frameworks). Use dispatch() directly in those contexts.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is not None:
        raise RuntimeError(
            "dispatch_sync() cannot be called from a running event loop. "
            "Use 'await dispatch(...)' instead."
        )
    return asyncio.run(dispatch(prompt, **kwargs))


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

class DispatchResult:
    """Structured result from a sub-agent dispatch."""

    __slots__ = (
        "text", "json_blocks", "tool_calls",
        "session_id", "usage", "elapsed_seconds",
    )

    def __init__(
        self, text: str, json_blocks: list[dict],
        tool_calls: list[dict], session_id: str | None,
        usage: dict[str, int], elapsed_seconds: float,
    ):
        self.text = text
        self.json_blocks = json_blocks
        self.tool_calls = tool_calls
        self.session_id = session_id
        self.usage = usage
        self.elapsed_seconds = elapsed_seconds

    @property
    def ok(self) -> bool:
        """True if we got any text output."""
        return bool(self.text.strip())

    @property
    def first_json(self) -> dict | None:
        """First JSON block extracted, or None."""
        return self.json_blocks[0] if self.json_blocks else None

    def __repr__(self) -> str:
        return (
            f"DispatchResult(ok={self.ok}, "
            f"len={len(self.text)}, "
            f"json_blocks={len(self.json_blocks)}, "
            f"tools={len(self.tool_calls)}, "
            f"elapsed={self.elapsed_seconds}s)"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_JSON_BLOCK_RE = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)


def _extract_json_blocks(text: str) -> list[dict]:
    """Extract ```json ... ``` blocks from text, parse each as JSON."""
    blocks = []
    for match in _JSON_BLOCK_RE.finditer(text):
        try:
            blocks.append(json.loads(match.group(1)))
        except json.JSONDecodeError:
            continue
    return blocks


# ---------------------------------------------------------------------------
# CLI for testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Agent dispatch test")
    parser.add_argument("prompt", help="Prompt to send")
    parser.add_argument("--cwd", help="Working directory")
    parser.add_argument("--system", help="System prompt")
    parser.add_argument("--tools", nargs="*", default=["Read", "Glob", "Grep"])
    parser.add_argument("--vault", action="store_true", help="Attach Vault MCP")
    parser.add_argument("--max-turns", type=int, default=5)
    args = parser.parse_args()

    result = dispatch_sync(
        args.prompt,
        cwd=args.cwd,
        system_prompt=args.system,
        tools=args.tools,
        vault=args.vault,
        max_turns=args.max_turns,
    )
    print(result)
    print(f"\n--- Output ({len(result.text)} chars) ---")
    print(result.text[:1000])
    if result.json_blocks:
        print(f"\n--- JSON blocks ({len(result.json_blocks)}) ---")
        for b in result.json_blocks:
            print(json.dumps(b, indent=2, ensure_ascii=False))
