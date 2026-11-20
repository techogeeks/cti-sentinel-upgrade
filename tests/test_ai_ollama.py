"""Isolated API tests: no real Ollama or MongoDB instance is needed."""
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from flask import Flask
from backend.route.ai import bp


class OllamaRouteTests(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.register_blueprint(bp, url_prefix="/api")
        app.testing = True
        self.client = app.test_client()

    @patch("backend.route.ai._installed_models", side_effect=URLError("connection refused"))
    def test_status_reports_unavailable_service(self, _):
        response = self.client.get("/api/ai/status")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["provider"], "OLLAMA")
        self.assertFalse(response.json["configured"])

    @patch("backend.route.ai._installed_models", return_value=["qwen2.5:3b"])
    def test_status_reports_local_model(self, _):
        response = self.client.get("/api/ai/status")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["configured"])
        self.assertIn("qwen2.5:3b", response.json["models"])

    @patch.dict("os.environ", {"ENABLE_LAB_RUNNER": "1"})
    @patch("backend.route.ai._installed_models")
    def test_explicit_lab_command_runs_without_ollama(self, models):
        response = self.client.post("/api/ai/chat", json={"message": "run lab 11.1"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["lab_result"]["passed"])
        self.assertEqual(len(response.json["lab_result"]["ranking"]), 4)
        models.assert_not_called()

    @patch.dict("os.environ", {"ENABLE_LAB_RUNNER": "0"})
    def test_chat_command_respects_runner_opt_in(self):
        response = self.client.post("/api/ai/chat", json={"message": "/run 10.1"})
        self.assertEqual(response.status_code, 403)

    @patch.dict("os.environ", {"ENABLE_LAB_RUNNER": "1"})
    def test_chat_command_rejects_remote_caller(self):
        response = self.client.post("/api/ai/chat", json={"message": "/run 11.1"},
                                    environ_overrides={"REMOTE_ADDR": "192.0.2.1"})
        self.assertEqual(response.status_code, 403)

    @patch("backend.route.ai._installed_models", return_value=[])
    def test_chat_requires_installed_model(self, _):
        response = self.client.post("/api/ai/chat", json={"message": "Hello"})
        self.assertEqual(response.status_code, 503)
        self.assertIn("pull", response.json["error"])

    def test_rejects_cloud_provider(self):
        response = self.client.post("/api/ai/chat", json={"message": "Hello", "provider": "nvidia"})
        self.assertEqual(response.status_code, 400)

    @patch("backend.route.ai._installed_models", return_value=["qwen2.5:3b"])
    def test_rejects_uninstalled_model(self, _):
        response = self.client.post("/api/ai/chat", json={"message": "Hello", "model": "missing:latest"})
        self.assertEqual(response.status_code, 400)

    @patch("backend.route.ai._installed_models", return_value=["qwen2.5:3b"])
    @patch("backend.route.ai._generate", return_value="Replication keeps data copies in sync.")
    @patch("backend.route.ai.get_db")
    def test_chat_returns_local_response_and_saves_messages(self, db_fn, generate, _):
        mock_db = MagicMock()
        db_fn.return_value = mock_db
        mock_db.ai_messages.find.return_value.sort.return_value.limit.return_value = []
        response = self.client.post("/api/ai/chat", json={"message": "Explain replication"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["provider"], "ollama")
        self.assertEqual(response.json["model"], "qwen2.5:3b")
        self.assertEqual(response.json["answer"], "Replication keeps data copies in sync.")
        self.assertTrue(response.json["conversation_id"])
        generate.assert_called_once()
        saved = mock_db.ai_messages.insert_many.call_args.args[0]
        self.assertEqual(len(saved), 2)
        self.assertTrue(all(msg["provider"] == "ollama" for msg in saved))


if __name__ == "__main__":
    unittest.main()
