import asyncio
import sys
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.agent_dispatch import dispatch, dispatch_sync, DispatchResult, _extract_json_blocks

class TestAgentDispatch(unittest.IsolatedAsyncioTestCase):
    def test_extract_json_blocks(self):
        text = "Here is some text.\n```json\n{\"key\": \"value\"}\n```\nMore text.\n```json\n{\"another\": \"value\"}\n```"
        blocks = _extract_json_blocks(text)
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0], {"key": "value"})
        self.assertEqual(blocks[1], {"another": "value"})

    def test_extract_invalid_json(self):
        text = "```json\n{\"key\": \"value\"\n```"
        blocks = _extract_json_blocks(text)
        self.assertEqual(len(blocks), 0)

    @patch("claude_agent_sdk.query")
    async def test_dispatch(self, mock_query):
        from claude_agent_sdk import AssistantMessage, TextBlock, SystemMessage

        async def mock_query_gen(*args, **kwargs):
            yield SystemMessage(subtype="init", data={"session_id": "test_session_123"})
            yield AssistantMessage(content=[TextBlock(text="This is a test response.")], model="test-model")

        mock_query.side_effect = mock_query_gen

        result = await dispatch("test prompt")
        self.assertTrue(result.ok)
        self.assertEqual(result.text, "This is a test response.")
        self.assertEqual(result.session_id, "test_session_123")
        self.assertEqual(result.usage, {"input_tokens": 0, "output_tokens": 0})
        self.assertEqual(result.tool_calls, [])
        self.assertEqual(result.json_blocks, [])

    @patch("claude_agent_sdk.query")
    def test_dispatch_sync(self, mock_query):
        from claude_agent_sdk import AssistantMessage, TextBlock, SystemMessage

        async def mock_query_gen(*args, **kwargs):
            yield SystemMessage(subtype="init", data={"session_id": "test_session_sync"})
            yield AssistantMessage(content=[TextBlock(text="Sync test response.\n```json\n{\"foo\": \"bar\"}\n```")], model="test-model")

        mock_query.side_effect = mock_query_gen

        result = dispatch_sync("sync prompt")
        self.assertTrue(result.ok)
        self.assertIn("Sync test response.", result.text)
        self.assertEqual(result.session_id, "test_session_sync")
        self.assertEqual(len(result.json_blocks), 1)
        self.assertEqual(result.json_blocks[0], {"foo": "bar"})

    @patch("claude_agent_sdk.query")
    async def test_dispatch_with_tools(self, mock_query):
        from claude_agent_sdk import AssistantMessage, ToolUseBlock, TextBlock, ResultMessage

        async def mock_query_gen(*args, **kwargs):
            yield AssistantMessage(content=[ToolUseBlock(name="Glob", id="tool_1", input={"pattern": "*.py"})], model="test-model")
            yield ResultMessage(
                subtype="tool_result",
                result="Found 3 files",
                duration_ms=10,
                duration_api_ms=5,
                is_error=False,
                num_turns=1,
                session_id="test_session_123"
            )
            yield AssistantMessage(content=[TextBlock(text="Done.")], model="test-model")

        mock_query.side_effect = mock_query_gen

        result = await dispatch("find files", tools=["Glob"])
        self.assertTrue(result.ok)
        self.assertIn("Done.", result.text)
        self.assertIn("Found 3 files", result.text)
        self.assertEqual(len(result.tool_calls), 1)
        self.assertEqual(result.tool_calls[0]["name"], "Glob")
        self.assertEqual(result.tool_calls[0]["id"], "tool_1")

    @patch("claude_agent_sdk.query")
    async def test_dispatch_timeout(self, mock_query):
        async def mock_query_gen(*args, **kwargs):
            await asyncio.sleep(0.5)
            yield None

        mock_query.side_effect = mock_query_gen

        result = await dispatch("timeout prompt", timeout_seconds=0.1)
        self.assertIn("[TIMEOUT after 0.1s]", result.text)

    @patch("claude_agent_sdk.query")
    async def test_initialization_latency(self, mock_query):
        from claude_agent_sdk import AssistantMessage, TextBlock
        import time

        async def mock_query_gen(*args, **kwargs):
            # Fast mock generation
            yield AssistantMessage(content=[TextBlock(text="Benchmarking latency.")], model="test-model")

        mock_query.side_effect = mock_query_gen

        # We measure the time dispatch() takes when the query executes instantly.
        # This isolates the initialization and dispatch setup overhead.
        start = time.perf_counter()
        result = await dispatch("latency check prompt")
        duration = time.perf_counter() - start

        self.assertTrue(result.ok)
        self.assertLess(duration, 5.0, f"Initialization latency {duration:.4f}s exceeds 5.0s")

    @patch("claude_agent_sdk.query")
    async def test_transcript_tailing_performance(self, mock_query):
        from claude_agent_sdk import AssistantMessage, TextBlock
        import time

        async def mock_query_gen(*args, **kwargs):
            for i in range(1000):
                yield AssistantMessage(content=[TextBlock(text=f"Chunk {i} ")], model="test-model")

        mock_query.side_effect = mock_query_gen

        start = time.perf_counter()
        result = await dispatch("tailing prompt")
        duration = time.perf_counter() - start

        self.assertTrue(result.ok)
        self.assertEqual(len(result.text.split("Chunk")), 1001)
        self.assertLess(duration, 5.0, f"Transcript tailing performance {duration:.4f}s exceeds 5.0s")

if __name__ == "__main__":
    unittest.main()
