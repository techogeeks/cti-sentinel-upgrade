"""Offline tests for the shard-key scoring logic; MongoDB integration not covered."""
import ast
from pathlib import Path
import unittest

SERVICE = Path(__file__).resolve().parents[1] / "backend" / "services" / "lab_10_12.py"


class ShardKeyDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = ast.parse(SERVICE.read_text(encoding="utf-8"))
        nodes = [node for node in source.body if
                 (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "CANDIDATES" for t in node.targets)) or
                 (isinstance(node, ast.FunctionDef) and node.name == "shard_key_evaluation")]
        namespace = {}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SERVICE), "exec"), namespace)
        cls.run_lab = staticmethod(namespace["shard_key_evaluation"])

    def test_ranking_and_count(self):
        output = self.run_lab()
        self.assertTrue(output["passed"])
        self.assertTrue(output["simulation_only"])
        self.assertEqual(len(output["ranking"]), 4)
        self.assertEqual(output["ranking"][0]["candidate"], "user_id (hashed)")
        self.assertEqual(output["ranking"][0]["score"], 4)


if __name__ == "__main__":
    unittest.main()
