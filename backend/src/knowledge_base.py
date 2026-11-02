import json
import os
from pathlib import Path
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection
from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors, types

BACKEND_DIR = Path(__file__).resolve().parents[1]
DOCUMENTS_PATH = BACKEND_DIR / "processed" / "agent_documents.jsonl"
CHROMA_PATH = BACKEND_DIR / "processed" / "chroma"
DEFAULT_EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768
EMBEDDING_BATCH_SIZE = 32

load_dotenv(BACKEND_DIR / ".env")


class KnowledgeBase:
    """Semantic search over the prepared public catalog and policy documents."""

    def __init__(
        self, collection: Collection, client: genai.Client, embedding_model: str
    ) -> None:
        self._collection = collection
        self._client = client
        self._embedding_model = embedding_model

    def search(self, question: str, limit: int = 4) -> list[str]:
        if not question.strip():
            raise ValueError("A pergunta para busca não pode estar vazia.")
        if limit < 1:
            raise ValueError("O limite da busca deve ser maior que zero.")

        query_embedding = _embed_texts(
            self._client,
            [question],
            self._embedding_model,
            "RETRIEVAL_QUERY",
        )[0]
        results = self._collection.query(
            query_embeddings=[query_embedding], n_results=limit
        )
        document_groups = results.get("documents")
        if not document_groups or not document_groups[0]:
            return []
        return [document for document in document_groups[0] if document]


def _read_documents() -> list[dict[str, Any]]:
    if not DOCUMENTS_PATH.is_file():
        raise FileNotFoundError(
            f"Base preparada não encontrada em {DOCUMENTS_PATH}. "
            "Execute 'python prepare_data.py' dentro da pasta backend."
        )

    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        DOCUMENTS_PATH.read_text(encoding="utf-8").splitlines(), start=1
    ):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"{DOCUMENTS_PATH.name}, linha {line_number}: JSON inválido."
            ) from error

        if (
            not isinstance(record, dict)
            or not isinstance(record.get("id"), str)
            or not isinstance(record.get("content"), str)
            or not isinstance(record.get("metadata"), dict)
        ):
            raise ValueError(
                f"{DOCUMENTS_PATH.name}, linha {line_number}: "
                "esperados id, content e metadata válidos."
            )
        records.append(record)

    if not records:
        raise ValueError(f"A base preparada está vazia: {DOCUMENTS_PATH}")
    return records


def _embed_texts(
    client: genai.Client,
    texts: list[str],
    model: str,
    task_type: str,
) -> list[list[float]]:
    vectors: list[list[float]] = []
    for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[start : start + EMBEDDING_BATCH_SIZE]
        response = client.models.embed_content(
            model=model,
            contents=batch,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=EMBEDDING_DIMENSIONS,
            ),
        )
        if (
            response.embeddings is None
            or len(response.embeddings) != len(batch)
            or any(
                embedding.values is None for embedding in response.embeddings
            )
        ):
            raise RuntimeError(
                f"O Gemini não retornou todos os embeddings para a tarefa "
                f"{task_type}."
            )
        vectors.extend(
            [float(value) for value in embedding.values]
            for embedding in response.embeddings
            if embedding.values is not None
        )
    return vectors


def initialize_knowledge_base() -> KnowledgeBase:
    """Load prepared documents into Chroma, updating only changed records."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY não configurada. Preencha backend/.env com uma chave "
            "do Google AI Studio antes de iniciar."
        )

    records = _read_documents()
    embedding_model = os.getenv("GEMINI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
    google_client = genai.Client(api_key=api_key)
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection_name = (
        f"emporio_knowledge_{embedding_model.replace('-', '_').replace('.', '_')}"
    )
    collection = client.get_or_create_collection(
        name=collection_name,
    )

    stored = collection.get(include=["documents"])
    stored_documents = {
        record_id: document
        for record_id, document in zip(
            stored["ids"], stored.get("documents") or [], strict=False
        )
        if document is not None
    }
    current_documents = {record["id"]: record["content"] for record in records}
    changed_records = [
        record
        for record in records
        if stored_documents.get(record["id"]) != record["content"]
    ]
    if changed_records:
        try:
            embeddings = _embed_texts(
                google_client,
                [record["content"] for record in changed_records],
                embedding_model,
                "RETRIEVAL_DOCUMENT",
            )
        except genai_errors.APIError as error:
            if error.code == 429:
                message = (
                    "A cota gratuita do Gemini foi atingida ou está "
                    "temporariamente indisponível ao criar embeddings. Confira "
                    "os limites do projeto no Google AI Studio."
                )
            elif error.code in (401, 403):
                message = (
                    "O Gemini recusou a chave ao criar embeddings. Confira "
                    "GEMINI_API_KEY no arquivo backend/.env."
                )
            elif error.code == 404:
                message = (
                    f"Modelo de embeddings '{embedding_model}' não encontrado. "
                    "Confira GEMINI_EMBEDDING_MODEL em backend/.env; os nomes "
                    "válidos incluem gemini-embedding-001 e gemini-embedding-2."
                )
            else:
                message = (
                    "Não foi possível gerar embeddings com o Gemini. "
                    f"Código do provedor: {error.code}."
                )
            raise RuntimeError(message) from None
        collection.upsert(
            ids=[record["id"] for record in changed_records],
            documents=[record["content"] for record in changed_records],
            metadatas=[record["metadata"] for record in changed_records],
            embeddings=embeddings,
        )

    stale_ids = set(stored["ids"]) - set(current_documents)
    if stale_ids:
        collection.delete(ids=sorted(stale_ids))

    return KnowledgeBase(collection, google_client, embedding_model)