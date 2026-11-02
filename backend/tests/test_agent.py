import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from google.genai import errors as genai_errors

from src.agent import _get_llm, responder
from src.knowledge_base import KnowledgeBase


class FakeKnowledgeBase:
    def __init__(self, documents: list[str]) -> None:
        self.documents = documents
        self.question = ""

    def search(self, question: str) -> list[str]:
        self.question = question
        return self.documents


class AgentTests(unittest.TestCase):
    def test_responds_using_retrieved_context(self) -> None:
        knowledge_base = FakeKnowledgeBase(["Prazo de devolução: 7 dias corridos."])
        completion = SimpleNamespace(text="O prazo é de 7 dias corridos.")
        llm = Mock()
        llm.models.generate_content.return_value = completion

        with patch("src.agent._get_llm", return_value=llm):
            reply = responder("Qual é o prazo?", knowledge_base)

        self.assertEqual(reply, "O prazo é de 7 dias corridos.")
        self.assertEqual(knowledge_base.question, "Qual é o prazo?")
        self.assertIn(
            "Prazo de devolução: 7 dias corridos.",
            llm.models.generate_content.call_args.kwargs["contents"],
        )

    def test_uses_fallback_model_when_primary_is_temporarily_unavailable(self) -> None:
        knowledge_base = FakeKnowledgeBase(["A loja abre às 9h."])
        completion = SimpleNamespace(text="A loja abre às 9h.")
        llm = Mock()
        llm.models.generate_content.side_effect = [
            genai_errors.APIError(503, {"message": "model overloaded"}),
            completion,
        ]

        with (
            patch("src.agent._get_llm", return_value=llm),
            patch.dict(
                "os.environ",
                {
                    "GEMINI_MODEL": "primary-model",
                    "GEMINI_FALLBACK_MODEL": "fallback-model",
                },
            ),
        ):
            reply = responder("Qual é o horário?", knowledge_base)

        self.assertEqual(reply, "A loja abre às 9h.")
        self.assertEqual(
            [call.kwargs["model"] for call in llm.models.generate_content.call_args_list],
            ["primary-model", "fallback-model"],
        )

    def test_does_not_use_fallback_for_nontransient_provider_errors(self) -> None:
        knowledge_base = FakeKnowledgeBase(["A loja abre às 9h."])
        llm = Mock()
        llm.models.generate_content.side_effect = genai_errors.APIError(
            400, {"message": "invalid request"}
        )

        with (
            patch("src.agent._get_llm", return_value=llm),
            patch.dict(
                "os.environ",
                {
                    "GEMINI_MODEL": "primary-model",
                    "GEMINI_FALLBACK_MODEL": "fallback-model",
                },
            ),
            self.assertRaises(genai_errors.APIError),
        ):
            responder("Qual é o horário?", knowledge_base)

        llm.models.generate_content.assert_called_once()

    def test_returns_fallback_without_calling_model_when_search_is_empty(self) -> None:
        knowledge_base = FakeKnowledgeBase([])

        with patch("src.agent._get_llm") as get_llm:
            reply = responder("Pergunta sem resultado", knowledge_base)

        self.assertIn("Não encontrei essa informação", reply)
        get_llm.assert_not_called()

    def test_requires_gemini_key(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            _get_llm.cache_clear()
            try:
                with self.assertRaisesRegex(RuntimeError, "GEMINI_API_KEY"):
                    _get_llm()
            finally:
                _get_llm.cache_clear()


class KnowledgeBaseTests(unittest.TestCase):
    @staticmethod
    def _client(embedding_values: list[float]) -> SimpleNamespace:
        return SimpleNamespace(
            models=SimpleNamespace(
                embed_content=Mock(
                    return_value=SimpleNamespace(
                        embeddings=[SimpleNamespace(values=embedding_values)]
                    )
                )
            )
        )

    def test_search_returns_matching_documents(self) -> None:
        collection = Mock()
        collection.query.return_value = {
            "documents": [["Política de troca", "Prazo de devolução"]]
        }
        client = self._client([0.1] * 768)
        knowledge_base = KnowledgeBase(collection, client, "test-embedding-model")

        self.assertEqual(
            knowledge_base.search("Como faço uma troca?"),
            ["Política de troca", "Prazo de devolução"],
        )
        client.models.embed_content.assert_called_once()
        collection.query.assert_called_once_with(
            query_embeddings=[[0.1] * 768], n_results=4
        )

    def test_search_returns_empty_list_when_there_are_no_matches(self) -> None:
        collection = Mock()
        collection.query.return_value = {"documents": [[]]}

        knowledge_base = KnowledgeBase(
            collection, self._client([0.1] * 768), "test-embedding-model"
        )
        self.assertEqual(knowledge_base.search("Pergunta"), [])

    def test_search_rejects_empty_question_and_nonpositive_limit(self) -> None:
        knowledge_base = KnowledgeBase(
            Mock(), self._client([0.1] * 768), "test-embedding-model"
        )

        with self.assertRaisesRegex(ValueError, "pergunta"):
            knowledge_base.search("  ")
        with self.assertRaisesRegex(ValueError, "limite"):
            knowledge_base.search("Pergunta", limit=0)


if __name__ == "__main__":
    unittest.main()
