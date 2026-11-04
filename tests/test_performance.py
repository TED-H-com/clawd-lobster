import unittest
import time
import json
import re
from pathlib import Path
from clawd_lobster.squad import extract_json_signal, extract_discovery_data
from scripts.agent_dispatch import _extract_json_blocks

class TestPerformance(unittest.TestCase):
    def test_extract_json_signal_perf(self):
        # Create a large string
        large_text = "some text\n" * 10000 + "```json\n{\"status\": \"done\"}\n```\n" + "more text\n" * 10000
        start = time.time()
        res = extract_json_signal(large_text)
        duration = time.time() - start
        self.assertIsNotNone(res)
        self.assertLess(duration, 5.0)

    def test_extract_discovery_data_perf(self):
        large_text = "DISCOVERY_COMPLETE\n" + "some text\n" * 10000 + "```json\n{\"what\": \"app\"}\n```\n" + "more text\n" * 10000
        start = time.time()
        res = extract_discovery_data(large_text)
        duration = time.time() - start
        self.assertIsNotNone(res)
        self.assertLess(duration, 5.0)

    def test_agent_dispatch_json_extraction_perf(self):
        large_text = "some text\n" * 1000000
        start = time.perf_counter()
        res = _extract_json_blocks(large_text)
        duration = time.perf_counter() - start
        self.assertEqual(res, [])
        self.assertLess(duration, 5.0)

if __name__ == '__main__':
    unittest.main()
