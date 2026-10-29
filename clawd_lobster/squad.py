"""
clawd_lobster.squad: Unified spec-squad orchestrator.

Terminal and web modes share the same async core (_run_agent).
State persists in <workspace>/.spec-squad.json.
SSE events go to _sse_queue for the web dashboard.
"""
from __future__ import annotations

import json, queue, re, threading, time
from datetime import datetime, timezone
from pathlib import Path

MAX_REVIEW_ROUNDS = 5
SQUAD_STATE_FILE = ".spec-squad.json"

# ── SSE queue (web dashboard) ──────────────────────────────────────────────

_sse_queue: queue.Queue = queue.Queue()

def push_sse(event: str, data: dict) -> None:
    _sse_queue.put(json.dumps({"event": event, **data}, ensure_ascii=False))

def get_sse_queue() -> queue.Queue:
    return _sse_queue

# ── State file I/O ─────────────────────────────────────────────────────────

def load_state(workspace: Path) -> dict:
    f = workspace / SQUAD_STATE_FILE
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}

def save_state(workspace: Path, state: dict) -> None:
    (workspace / SQUAD_STATE_FILE).write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

# ── JSON signal extraction ─────────────────────────────────────────────────

def extract_json_signal(output: str) -> dict | None:
    for pat in (r'```json\s*\n({[^`]*?})\s*\n```', r'({\"(?:status|verdict)\"[^}]*})'):
        m = re.findall(pat, output, re.DOTALL)
        if m:
            try:
                return json.loads(m[-1])
            except json.JSONDecodeError:
                continue
    return None

def extract_discovery_data(response: str) -> dict | None:
    if "DISCOVERY_COMPLETE" not in response:
        return None
    m = re.search(r'```json\s*\n({[^`]*})\s*\n```', response, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    return None

# ── Discovery state (in-memory, per session) ───────────────────────────────

_disc_lock = threading.Lock()
_disc_history: list[dict] = []

def _reset_discovery() -> None:
    with _disc_lock:
        _disc_history.clear()

# ── System prompts ─────────────────────────────────────────────────────────

DISCOVERY_SYSTEM = """\
You are the Discovery Interviewer for Spec Squad, a multi-agent spec development system.

YOUR JOB: Ask the user smart questions to understand what they want to build. \
You are a senior consultant doing requirements gathering.

APPROACH:
- Ask 1-2 questions at a time, conversationally
- Be opinionated: if they say "whatever you think", make a strong recommendation
- Adapt based on their answers
- Cover the 3W1H framework: Why, What, Who, How, Scope, Integrations, Constraints

RULES:
- Do NOT write any code or specs yourself
- Do NOT create files
- Just ask questions and synthesize understanding
- When you have enough context (typically 3-6 exchanges), say EXACTLY:

DISCOVERY_COMPLETE
```json
{"what": "...", "why": "...", "who": "...", "stack": "...", \
"scope": "mvp|standard|enterprise", "integrations": "...", \
"constraints": "...", "workspace_name": "kebab-case-name"}
```

The JSON must contain all fields. workspace_name should be derived from the project (kebab-case).

START by asking what they want to build. Be friendly but efficient."""

ARCHITECT_SYSTEM = """\
You are the ARCHITECT in a Spec Squad. Write a complete OpenSpec.
Generate artifacts in strict DAG order:
1. openspec/project.md (3W1H context)
2. openspec/changes/v1/proposal.md (scope: In Scope / Out of Scope)
3. openspec/changes/v1/design.md (architecture with rationale)
4. openspec/changes/v1/specs/<capability>/spec.md (SHALL/MUST + Gherkin)
5. openspec/changes/v1/tasks.md (phased, file-referenced, 5-30 min tasks)

Requirements MUST use SHALL or MUST. Every requirement needs Gherkin scenarios.
After generating all artifacts, output:
```json
{"status": "spec_complete", "capabilities": N, "tasks": N, "phases": N}
```
Write ALL files now. Do not ask questions."""

REVIEWER_SYSTEM = """\
You are the REVIEWER in a Spec Squad.
Tear apart the Architect's spec. Find gaps, ambiguities, weak decisions.
Read ALL files in openspec/. Challenge architecture, requirements, tasks.

Output verdict:
If issues: ```json {"verdict": "REVISE", "issues": ["..."], "severity": "high|medium|low"} ```
If solid: ```json {"verdict": "APPROVED", "confidence": 0.0-1.0} ```

Be ruthless but fair."""

CODER_SYSTEM = """\
You are the CODER in a Spec Squad.
Execute the approved spec exactly. Read openspec/changes/v1/tasks.md.
Execute tasks phase by phase. Mark done: [ ] to [x] in tasks.md.
After each phase, commit. Skip [codex] tasks.

After all tasks: ```json {"status": "build_complete", "tasks_done": N, "tasks_total": N} ```
The spec is the plan. Follow it. Do not improvise."""

TESTER_SYSTEM = """\
You are the TESTER in a Spec Squad.
Verify code matches the approved spec. Read specs/ requirements and Gherkin scenarios.
Check every SHALL/MUST requirement against the code. Run any tests.

Output:
If issues: ```json {"verdict": "ISSUES", "failures": ["..."], "pass_rate": 0.0-1.0} ```
If pass: ```json {"verdict": "PASSED", "pass_rate": 1.0} ```"""

# ── Async core ─────────────────────────────────────────────────────────────

async def _run_agent(
    role: str, system_prompt: str, prompt: str, workspace: Path,
    allowed_tools: list[str] | None = None,
) -> str:
    """Run one agent via claude_agent_sdk.query(). Lazy import."""
    from claude_agent_sdk import (
        query, ClaudeAgentOptions, AssistantMessage, ResultMessage, TextBlock)

    if allowed_tools is None:
        allowed_tools = ["Read", "Glob", "Grep"]
    push_sse("agent_start", {"role": role})
    text = ""
    t0 = time.time()

    async for msg in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            system_prompt=system_prompt, allowed_tools=allowed_tools,
            permission_mode="acceptEdits" if role in ("architect", "coder") else "default",
            max_turns=30, cwd=str(workspace)),
    ):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, TextBlock):
                    text += b.text
                    push_sse("agent_text", {"role": role, "chunk": b.text[:200]})
        elif isinstance(msg, ResultMessage) and msg.result:
            text += msg.result

    push_sse("agent_done", {"role": role, "elapsed": round(time.time() - t0)})
    return text


async def run_discovery_turn(user_message: str, workspace: Path | None) -> str:
    """Single discovery chat turn. Returns Claude's response."""
    from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage

    with _disc_lock:
        _disc_history.append({"role": "user", "content": user_message})
        history = list(_disc_history)

    parts = [f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
             for m in history]
    response = ""
    async for msg in query(
        prompt="\n\n".join(parts),
        options=ClaudeAgentOptions(
            system_prompt=DISCOVERY_SYSTEM, allowed_tools=[],
            max_turns=1, cwd=str(workspace) if workspace else None),
    ):
        if isinstance(msg, ResultMessage) and msg.result:
            response = msg.result
            break

    with _disc_lock:
        _disc_history.append({"role": "assistant", "content": response})
    return response

# ── Squad pipeline ─────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _append_turn(sq: dict, role: str, phase: str, signal, **extra) -> None:
    sq["turns"].append({"role": role, "phase": phase, "time": _now(),
                         "signal": signal, **extra})

def approval_source(state: dict) -> str | None:
    """How the spec got approved: "reviewer", "round_limit", or None if it is not.

    State files written before the "approval" field existed are classified
    from the last Reviewer verdict.
    """
    if not state.get("approved"):
        return None
    source = state.get("approval")
    if source in ("reviewer", "round_limit"):
        return source
    reviews = [t for t in state.get("turns", []) if t.get("role") == "reviewer"]
    last = (reviews[-1].get("signal") or {}) if reviews else {}
    return "reviewer" if last.get("verdict") == "APPROVED" else "round_limit"

def approval_label(state: dict) -> str:
    """One-line approval status that tells the two kinds of approval apart."""
    source = approval_source(state)
    if source is None:
        return "not approved"
    if source == "round_limit":
        return (f"approved by the round limit (the Reviewer did not approve within "
                f"{MAX_REVIEW_ROUNDS} rounds)")
    return "approved by the Reviewer"

async def _run_squad_async(
    workspace: Path, project_desc: str,
    plan_only: bool = False, on_phase=None,
) -> None:
    """Architect -> Reviewer -> Coder -> Tester pipeline."""
    sq: dict = {"phase": "spec", "review_round": 0, "approved": False,
                "approval": None, "started": _now(), "turns": []}
    save_state(workspace, sq)
    def _notify(p: str):
        push_sse("phase", {"phase": p})
        if on_phase: on_phase(p)

    # Phase 1: Architect
    _notify("spec")
    out = await _run_agent("architect", ARCHITECT_SYSTEM,
        f"Write a complete OpenSpec for this project:\n\n{project_desc}",
        workspace, ["Read", "Write", "Edit", "Glob", "Grep"])
    _append_turn(sq, "architect", "spec", extract_json_signal(out))
    sq["phase"] = "review"
    save_state(workspace, sq)

    # Phase 2: Review loop
    _notify("review")
    while sq["review_round"] < MAX_REVIEW_ROUNDS:
        sq["review_round"] += 1
        rn = sq["review_round"]
        rev = await _run_agent("reviewer", REVIEWER_SYSTEM,
            f"Review round {rn}. Read ALL files in openspec/ and challenge the spec.",
            workspace)
        rs = extract_json_signal(rev)
        _append_turn(sq, "reviewer", "review", rs, round=rn)
        save_state(workspace, sq)
        if rs and rs.get("verdict") == "APPROVED":
            sq["approved"] = True
            sq["approval"] = "reviewer"
            save_state(workspace, sq)
            break
        issues = rs.get("issues", ["Reviewer requested revisions"]) if rs else ["Review completed"]
        fix = await _run_agent("architect", ARCHITECT_SYSTEM,
            "The REVIEWER found these issues. Fix ALL of them:\n"
            + "\n".join(f"- {i}" for i in issues) + "\n\nRead and update the openspec/ files.",
            workspace, ["Read", "Write", "Edit", "Glob", "Grep"])
        _append_turn(sq, "architect", "revision", extract_json_signal(fix), round=rn)
        save_state(workspace, sq)

    if not sq["approved"]:
        # Round limit reached without an APPROVED verdict. The spec still
        # counts as approved so the pipeline can go on, but the state, the
        # turn log and the SSE stream all record that the limit forced it.
        sq["approved"] = True
        sq["approval"] = "round_limit"
        _append_turn(sq, "system", "review",
                     {"verdict": "FORCED_APPROVAL", "reason": "round_limit",
                      "rounds": sq["review_round"], "max_rounds": MAX_REVIEW_ROUNDS})
        save_state(workspace, sq)
        push_sse("forced_approval", {"rounds": sq["review_round"],
                                     "max_rounds": MAX_REVIEW_ROUNDS})

    if plan_only:
        sq["phase"] = "done"; save_state(workspace, sq); _notify("done"); return

    # Phase 3: Coder
    sq["phase"] = "code"; save_state(workspace, sq); _notify("code")
    cout = await _run_agent("coder", CODER_SYSTEM,
        "Read the approved spec in openspec/changes/v1/tasks.md and build everything.",
        workspace, ["Read", "Write", "Edit", "Bash", "Glob", "Grep"])
    _append_turn(sq, "coder", "code", extract_json_signal(cout))
    save_state(workspace, sq)

    # Phase 4: Tester
    sq["phase"] = "test"; save_state(workspace, sq); _notify("test")
    tout = await _run_agent("tester", TESTER_SYSTEM,
        "Read the specs in openspec/changes/v1/specs/ and verify the code matches every requirement.",
        workspace, ["Read", "Bash", "Glob", "Grep"])
    _append_turn(sq, "tester", "test", extract_json_signal(tout))
    sq["phase"] = "done"; save_state(workspace, sq); _notify("done")

# ── Threading helpers ──────────────────────────────────────────────────────

def _run_async_sync(async_fn, *args, timeout: float = 300):
    """Run async function synchronously via anyio in a worker thread."""
    import anyio
    result, error = [None], [None]
    def worker():
        try:
            async def w(): return await async_fn(*args)
            result[0] = anyio.run(w)
        except Exception as e:
            error[0] = e
    t = threading.Thread(target=worker, daemon=True); t.start(); t.join(timeout=timeout)
    if error[0]: raise error[0]
    return result[0]

# ── Terminal mode ──────────────────────────────────────────────────────────

def run_squad_terminal(workspace: Path | str | None = None) -> None:
    """Interactive terminal: describe project -> spec -> review -> build."""
    import anyio
    if workspace is None: workspace = Path.cwd()
    workspace = Path(workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "openspec").mkdir(exist_ok=True)

    print("=" * 60)
    print("  Spec Squad  --  Terminal Mode")
    print("=" * 60)
    print(f"  Workspace: {workspace}\n")
    print("Describe your project (press Enter twice to finish):")
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line == "" and lines and lines[-1] == "":
            lines.pop(); break
        lines.append(line)
    desc = "\n".join(lines).strip()
    if not desc:
        print("No description provided. Exiting."); return

    print("\n" + "-" * 60)
    def _on_phase(p: str):
        labels = {"spec": "Architect is writing the spec...", "review": "Review loop starting...",
                  "code": "Coder is building...", "test": "Tester is verifying...",
                  "done": "All phases complete."}
        print(f"\n>> [{p.upper()}] {labels.get(p, p)}")

    # Spec + review only
    print("\nPhase 1: Generating spec...")
    anyio.run(lambda: _run_squad_async(workspace, desc, plan_only=True, on_phase=_on_phase))

    st = load_state(workspace)
    print(f"\nSpec complete: {len(st.get('turns',[]))} turns, "
          f"{st.get('review_round',0)} review rounds, {approval_label(st)}")
    if approval_source(st) == "round_limit":
        print("Warning: the Reviewer never approved this spec. Read the last review "
              "in .spec-squad.json before building.")
    print(f"Files in: {workspace / 'openspec'}\n")

    try:
        ans = input("Build now? (y/n): ").strip().lower()
    except EOFError:
        ans = "n"
    if ans not in ("y", "yes"):
        print("Spec saved. Run again to build later."); return

    # Code + test
    print("\nPhase 2: Building and testing...")
    async def _build():
        sq = load_state(workspace)
        sq["phase"] = "code"; save_state(workspace, sq); _on_phase("code")
        cout = await _run_agent("coder", CODER_SYSTEM,
            "Read the approved spec in openspec/changes/v1/tasks.md and build everything.",
            workspace, ["Read", "Write", "Edit", "Bash", "Glob", "Grep"])
        _append_turn(sq, "coder", "code", extract_json_signal(cout))
        sq["phase"] = "test"; save_state(workspace, sq); _on_phase("test")
        tout = await _run_agent("tester", TESTER_SYSTEM,
            "Read the specs in openspec/changes/v1/specs/ and verify the code matches every requirement.",
            workspace, ["Read", "Bash", "Glob", "Grep"])
        _append_turn(sq, "tester", "test", extract_json_signal(tout))
        sq["phase"] = "done"; save_state(workspace, sq); _on_phase("done")
    anyio.run(_build)

    final = load_state(workspace)
    last = final["turns"][-1].get("signal", {}) if final.get("turns") else {}
    v = last.get("verdict", last.get("status", "unknown"))
    print(f"\n{'=' * 60}\n  Done!  {len(final.get('turns',[]))} total turns  |  Final: {v}")
    print(f"  Workspace: {workspace}\n{'=' * 60}")

# ── Web mode ───────────────────────────────────────────────────────────────

def run_squad_web(workspace: Path, project_desc: str, plan_only: bool = False) -> None:
    """Launch squad in a background daemon thread. Pushes SSE events."""
    import anyio
    def _worker():
        try:
            anyio.run(lambda: _run_squad_async(workspace, project_desc, plan_only=plan_only))
        except Exception as e:
            push_sse("error", {"message": str(e)})
    threading.Thread(target=_worker, daemon=True, name="squad-web").start()

def discovery_turn_sync(user_message: str, workspace: Path | None) -> str:
    """Synchronous wrapper around run_discovery_turn for HTTP handlers."""
    return _run_async_sync(run_discovery_turn, user_message, workspace)
