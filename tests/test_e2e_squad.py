import asyncio
import json
import queue
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from clawd_lobster import squad

def signal(data):
    return "```json\n" + json.dumps(data) + "\n```"

def fake_agents_full_pipeline():
    """A stand-in for squad._run_agent that successfully runs the full pipeline."""
    async def run_agent(role, system_prompt, prompt, workspace, allowed_tools=None):
        if role == "architect":
            if "Fix ALL" in prompt:
                return signal({"status": "fixed"})
            return signal({"status": "spec_drafted"})
        elif role == "reviewer":
            return signal({"verdict": "APPROVED", "confidence": 0.95})
        elif role == "coder":
            return signal({"status": "built", "files": ["app.py", "test.py"]})
        elif role == "tester":
            return signal({"status": "tested", "passed": True})
        return signal({"status": "done"})
    return run_agent

def drain_sse():
    events = []
    q = squad.get_sse_queue()
    while True:
        try:
            events.append(json.loads(q.get_nowait()))
        except queue.Empty:
            return events

class TestE2ESquadPipeline(unittest.TestCase):
    def run_squad_pipeline(self):
        drain_sse()
        phases_recorded = []
        def _on_phase(p):
            phases_recorded.append(p)

        with tempfile.TemporaryDirectory() as ws, \
             patch.object(squad, "_run_agent", fake_agents_full_pipeline()):
            asyncio.run(squad._run_squad_async(
                Path(ws), "a test project", plan_only=False, on_phase=_on_phase
            ))
            state = squad.load_state(Path(ws))
        return state, drain_sse(), phases_recorded

    def test_full_pipeline_execution(self):
        state, events, phases = self.run_squad_pipeline()

        # Verify state handoffs (phases)
        self.assertEqual(state["phase"], "done")
        self.assertEqual(phases, ["spec", "review", "code", "test", "done"])

        # Verify 4-role pipeline roles took turns
        roles_in_turns = [turn["role"] for turn in state["turns"]]
        self.assertEqual(roles_in_turns, ["architect", "reviewer", "coder", "tester"])

        # Verify summary reporting / signals
        turns = state["turns"]

        architect_turn = turns[0]
        self.assertEqual(architect_turn["signal"], {"status": "spec_drafted"})

        reviewer_turn = turns[1]
        self.assertEqual(reviewer_turn["signal"], {"verdict": "APPROVED", "confidence": 0.95})

        coder_turn = turns[2]
        self.assertEqual(coder_turn["signal"], {"status": "built", "files": ["app.py", "test.py"]})

        tester_turn = turns[3]
        self.assertEqual(tester_turn["signal"], {"status": "tested", "passed": True})

        # Verify SSE events trace
        sse_phases = [e["phase"] for e in events if e["event"] == "phase"]
        self.assertEqual(sse_phases, ["spec", "review", "code", "test", "done"])

        self.assertTrue(state["approved"])
        self.assertEqual(state["approval"], "reviewer")
        self.assertEqual(state["review_round"], 1)

if __name__ == "__main__":
    unittest.main(verbosity=2)
