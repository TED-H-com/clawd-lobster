import unittest
import json
import jsonschema
from pathlib import Path
import sys
import tempfile
import os
import subprocess
import shutil
import asyncio
import queue
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from clawd_lobster import squad

def signal(data):
    return "```json\n" + json.dumps(data) + "\n```"

def fake_agents_with_revision():
    """A stand-in for squad._run_agent that forces a revision round."""
    review_calls = 0

    async def run_agent(role, system_prompt, prompt, workspace, allowed_tools=None):
        nonlocal review_calls
        if role == "architect":
            if "Fix ALL" in prompt:
                return signal({"status": "fixed"})
            return signal({"status": "spec_drafted"})
        elif role == "reviewer":
            review_calls += 1
            if review_calls == 1:
                return signal({"verdict": "REVISE", "issues": ["Architecture gap", "Missing tests"], "severity": "high"})
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

class TestE2ESpecSquadFlow(unittest.TestCase):

    def test_squad_manifest_schema_validation(self):
        manifest_path = Path(__file__).resolve().parent.parent / "skills" / "spec" / "skill.json"
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        config_schema = manifest.get("configSchema", {})

        # Valid config
        valid_config = {
            "default_depth": "standard",
            "auto_create_github": True,
            "blitz_auto_approve": False
        }
        jsonschema.validate(instance=valid_config, schema=config_schema)

        # Invalid configs
        invalid_configs = [
            {"default_depth": "invalid_depth"},
            {"auto_create_github": "not_a_boolean"},
            {"blitz_auto_approve": "not_a_boolean"}
        ]

        for invalid_config in invalid_configs:
            with self.assertRaises(jsonschema.exceptions.ValidationError):
                jsonschema.validate(instance=invalid_config, schema=config_schema)

    def test_role_assignment_transitions(self):
        drain_sse()

        with tempfile.TemporaryDirectory() as ws, \
             patch.object(squad, "_run_agent", fake_agents_with_revision()):
            asyncio.run(squad._run_squad_async(
                Path(ws), "a test project with revisions", plan_only=False
            ))
            state = squad.load_state(Path(ws))

        roles_in_turns = [turn["role"] for turn in state["turns"]]
        self.assertEqual(roles_in_turns, ["architect", "reviewer", "architect", "reviewer", "coder", "tester"])
        self.assertEqual(state["review_round"], 2)
        self.assertTrue(state["approved"])
        self.assertEqual(state["approval"], "reviewer")

    def test_git_sync_commit_flow(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            wrapper = root / "wrapper"
            wrapper.mkdir()

            # Init wrapper git
            subprocess.run(["git", "init", "-b", "master", str(wrapper)], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(wrapper), "config", "user.name", "Test User"], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(wrapper), "config", "user.email", "test@example.com"], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(wrapper), "config", "commit.gpgsign", "false"], check=True, capture_output=True)

            test_file = wrapper / "test.json"
            test_file.write_text('{"initial": true}')

            subprocess.run(["git", "-C", str(wrapper), "add", "."], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(wrapper), "commit", "-m", "initial commit"], check=True, capture_output=True)

            # Setup a remote so we don't get push errors
            remote = root / "remote.git"
            subprocess.run(["git", "init", "--bare", "-b", "master", str(remote)], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(wrapper), "remote", "add", "origin", str(remote)], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(wrapper), "push", "-u", "origin", "master"], check=True, capture_output=True)

            # Edit file to trigger sync
            test_file.write_text('{"initial": false, "updated": true}')

            # Create a mock wrapper for the sync script to operate on
            # and a config so it finds our wrapper as WS_ROOT
            env = os.environ.copy()
            env["HOME"] = str(root)
            config_dir = root / ".clawd-lobster"
            config_dir.mkdir()
            config_file = config_dir / "config.json"
            config_file.write_text(json.dumps({"workspace_root": str(root)}))

            # Run the sync script
            sync_script = Path(__file__).resolve().parent.parent / "scripts" / "sync-all.sh"

            temp_script_dir = root / "scripts"
            temp_script_dir.mkdir()
            shutil.copy(sync_script, temp_script_dir / "sync-all.sh")

            result = subprocess.run(
                ["bash", str(temp_script_dir / "sync-all.sh")],
                env=env,
                capture_output=True,
                text=True
            )

            # Verify the commit message in the wrapper repo
            log_result = subprocess.run(
                ["git", "-C", str(wrapper), "log", "-1", "--format=%s"],
                check=True,
                capture_output=True,
                text=True
            )
            commit_msg = log_result.stdout.strip()

            import re
            self.assertTrue(re.match(r"^auto-sync \d{4}-\d{2}-\d{2} \d{2}:\d{2}$", commit_msg), f"Commit message didn't match: {commit_msg}")

if __name__ == "__main__":
    unittest.main(verbosity=2)
