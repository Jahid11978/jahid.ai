import ast
import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from scripts import jahids


class JahidsCliTests(unittest.TestCase):
    def test_demo_prints_successful_agent_result(self):
        output = io.StringIO()

        with redirect_stdout(output):
            jahids.demo()

        result = ast.literal_eval(output.getvalue().strip())
        self.assertEqual(
            result,
            {
                "state": "succeeded",
                "output": {"value": 42},
                "worker_id": "worker-demo-1",
            },
        )

    def test_main_runs_agent_demo_command(self):
        with patch.object(sys, "argv", ["jahids", "agent-demo"]), patch.object(
            jahids, "demo"
        ) as demo:
            jahids.main()

        demo.assert_called_once_with()

    def test_main_rejects_unknown_command(self):
        stderr = io.StringIO()

        with patch.object(sys, "argv", ["jahids", "unknown"]), redirect_stderr(
            stderr
        ), self.assertRaises(SystemExit) as raised:
            jahids.main()

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("invalid choice: 'unknown'", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
