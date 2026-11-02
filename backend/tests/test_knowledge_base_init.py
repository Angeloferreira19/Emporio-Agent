import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from google.genai import errors as genai_errors

from src.knowledge_base import initialize_knowledge_base


class FakeCollection:
    def __init__(self, documents: dict[str, str] | None = None) -> None:
        self.documents = documents or {}
        self.upsert_calls: list[dict[str, list[object]]] = []
        self.deleted_ids: list[str] = []

    def get(self, include: list[str]) -> dict[str, list[object]]:
        return {
            "ids": list(self.documents),
            "documents": list(self.documents.values()),
        }

    def upsert(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, object]],
        embeddings: list[list[float]],
    ) -> None:
        self.upsert_calls.append(
            {
                "ids": ids,
                "documents": documents,
                "metadatas": metadatas,
                "embeddings": embeddings,
            }
        )
        self.documents.update(zip(ids, documents, strict=True))

    def delete(self, ids: list[str]) -> None:
        self.deleted_ids.extend(ids)
        for document_id in ids:
            self.documents.pop(document_id, None)

    def query(
        self, query_embeddings: list[list[float]], n_results: int
    ) -> dict[str, list[list[str]]]:
        return {"documents": [[]]}


class FakeClient:
    def __init__(self, collection: FakeCollection) -> None:
        self.collection = collection
        self.collection_names: list[str] = []

    def get_or_create_collection(
        self, name: str
    ) -> FakeCollection:
        self.collection_names.append(name)
        return self.collection


class FakeGoogleClient:
    def __init__(self) -> None:
        self.models = SimpleNamespace(embed_content=self.embed_content)
        self.embedding_calls: list[dict[str, object]] = []

    def embed_content(
        self, model: str, contents: list[str], config: object
    ) -> SimpleNamespace:
        self.embedding_calls.append(
            {"model": model, "contents": contents, "config": config}
        )
        return SimpleNamespace(
            embeddings=[
                SimpleNamespace(values=[float(index)] * 768)
                for index, _ in enumerate(contents)
            ]
        )


class KnowledgeBaseInitializationTests(unittest.TestCase):
    def test_upserts_only_changes_and_removes_stale_documents(self) -> None:
        records = [
            {
                "id": "product-1",
                "content": "Updated",
                "metadata": {"source": "product"},
            },
            {"id": "policy-1", "content": "New", "metadata": {"source": "policy"}},
        ]
        collection = FakeCollection(
            {"product-1": "Old", "removed-1": "No longer in source"}
        )
        chroma_client = FakeClient(collection)
        google_client = FakeGoogleClient()

        with (
            patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}),
            patch("src.knowledge_base._read_documents", return_value=records),
            patch(
                "src.knowledge_base.chromadb.PersistentClient",
                return_value=chroma_client,
            ),
            patch(
                "src.knowledge_base.genai.Client",
                return_value=google_client,
            ) as genai_client,
        ):
            knowledge_base = initialize_knowledge_base()
            initialize_knowledge_base()

        self.assertEqual(len(collection.upsert_calls), 1)
        self.assertEqual(
            collection.upsert_calls[0]["ids"],
            ["product-1", "policy-1"],
        )
        self.assertEqual(collection.deleted_ids, ["removed-1"])
        self.assertEqual(collection.documents["product-1"], "Updated")
        self.assertEqual(knowledge_base.search("Pergunta"), [])
        self.assertEqual(genai_client.call_count, 2)
        self.assertEqual(len(google_client.embedding_calls), 2)
        self.assertEqual(
            google_client.embedding_calls[0]["contents"],
            ["Updated", "New"],
        )
        self.assertEqual(
            chroma_client.collection_names,
            ["emporio_knowledge_gemini_embedding_001"] * 2,
        )

    def test_requires_api_key(self) -> None:
        with (
            patch.dict(os.environ, {}, clear=True),
            self.assertRaisesRegex(RuntimeError, "GEMINI_API_KEY"),
        ):
            initialize_knowledge_base()

    def test_explains_free_tier_limit_when_embedding_quota_is_exhausted(self) -> None:
        collection = FakeCollection()
        chroma_client = FakeClient(collection)
        google_client = SimpleNamespace(
            models=SimpleNamespace(
                embed_content=Mock(
                    side_effect=genai_errors.APIError(
                        429, {"message": "quota exhausted"}
                    )
                )
            )
        )
        records = [
            {"id": "policy-1", "content": "Policy", "metadata": {"source": "policy"}}
        ]

        with (
            patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}),
            patch("src.knowledge_base._read_documents", return_value=records),
            patch(
                "src.knowledge_base.chromadb.PersistentClient",
                return_value=chroma_client,
            ),
            patch("src.knowledge_base.genai.Client", return_value=google_client),
        ):
            with self.assertRaisesRegex(RuntimeError, "cota gratuita") as error:
                initialize_knowledge_base()

        self.assertNotIn("test-key", str(error.exception))

    def test_explains_unknown_embedding_model(self) -> None:
        collection = FakeCollection()
        chroma_client = FakeClient(collection)
        google_client = SimpleNamespace(
            models=SimpleNamespace(
                embed_content=Mock(
                    side_effect=genai_errors.APIError(
                        404, {"message": "model not found"}
                    )
                )
            )
        )
        records = [
            {"id": "policy-1", "content": "Policy", "metadata": {"source": "policy"}}
        ]

        with (
            patch.dict(
                os.environ,
                {
                    "GEMINI_API_KEY": "test-key",
                    "GEMINI_EMBEDDING_MODEL": "gemini-embedding-002",
                },
            ),
            patch("src.knowledge_base._read_documents", return_value=records),
            patch(
                "src.knowledge_base.chromadb.PersistentClient",
                return_value=chroma_client,
            ),
            patch("src.knowledge_base.genai.Client", return_value=google_client),
        ):
            with self.assertRaisesRegex(
                RuntimeError, "gemini-embedding-002.*não encontrado"
            ):
                initialize_knowledge_base()


if __name__ == "__main__":
    unittest.main()
