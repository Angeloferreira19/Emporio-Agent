import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from google.genai import errors as genai_errors

from main import app


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.initializer = patch(
            "main.initialize_knowledge_base", return_value=object()
        )
        self.responder = patch("main.responder", return_value="Resposta do agente.")
        self.initializer.start()
        self.responder.start()
        self.addCleanup(self.responder.stop)
        self.addCleanup(self.initializer.stop)
        self.client_context = TestClient(app)
        self.client = self.client_context.__enter__()
        self.addCleanup(self.client_context.__exit__, None, None, None)

    def test_root_and_health_routes(self) -> None:
        root = self.client.get("/")
        health = self.client.get("/health")

        self.assertEqual(root.status_code, 200)
        self.assertEqual(root.json()["docs"], "/docs")
        self.assertEqual(health.json(), {"status": "ok"})

    def test_chat_route_preserves_frontend_contract(self) -> None:
        response = self.client.post(
            "/api/chat",
            json={"session_id": "session-1", "message": "  Oi  "},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "reply": "Resposta do agente.",
                "tools_used": [
                    {
                        "name": "buscar_base_conhecimento",
                        "args": {"query": "Oi"},
                    }
                ],
            },
        )

    def test_chat_rejects_blank_messages(self) -> None:
        response = self.client.post(
            "/api/chat",
            json={"session_id": "session-1", "message": "   "},
        )

        self.assertEqual(response.status_code, 422)

    def test_chat_reports_gemini_free_tier_quota_errors(self) -> None:
        with patch(
            "main.responder",
            side_effect=genai_errors.APIError(
                429, {"message": "quota exhausted"}
            ),
        ):
            response = self.client.post(
                "/api/chat",
                json={"session_id": "session-1", "message": "Oi"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertIn("cota gratuita", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
