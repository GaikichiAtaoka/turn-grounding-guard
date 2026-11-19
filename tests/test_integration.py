import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class IntegrationTests(unittest.TestCase):
    def test_offline_agent_delivers_only_passed_or_corrected_text(self):
        spec = importlib.util.spec_from_file_location("example", ROOT / "examples/agent_integration.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        output = mod.run_demo()
        self.assertEqual([r["status"] for r in output["results"]], ["pass", "corrected", "blocked"])
        self.assertEqual(len(output["delivered_to_ui"]), 2)

    def run_cli(self, obj):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "input.json"
            path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, "-m", "turn_grounding_guard.cli", "--input", str(path)],
                                    capture_output=True, text=True, timeout=10)
            return result.returncode, json.loads(result.stdout)

    def fixture(self):
        return json.loads((ROOT / "examples/synthetic_input.json").read_text(encoding="utf-8"))

    def test_cli_block_does_not_return_original_draft(self):
        code, output = self.run_cli(self.fixture())
        self.assertEqual(code, 2)
        self.assertIsNone(output["reply"])
        self.assertNotIn("おやすみ", json.dumps(output, ensure_ascii=False))

    def test_cli_pass_and_invalid_are_distinct(self):
        data = self.fixture()
        data["reply"] = "またあとでね。"
        self.assertEqual(self.run_cli(data)[0], 0)
        data["reference"] = "invalid"
        code, output = self.run_cli(data)
        self.assertEqual(code, 1)
        self.assertEqual(output["status"], "invalid")


if __name__ == "__main__":
    unittest.main()
