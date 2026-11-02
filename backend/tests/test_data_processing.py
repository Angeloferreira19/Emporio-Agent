import json
import shutil
import tempfile
import unittest
from pathlib import Path

from src.data_processing import (
    DATA_DIR,
    POLICY_CHUNK_SIZE,
    build_agent_documents,
    load_store_data,
    write_agent_documents,
)


class DataProcessingTests(unittest.TestCase):
    def test_loads_and_normalizes_all_source_tables(self) -> None:
        data = load_store_data()

        self.assertEqual(len(data.categories), 9)
        self.assertEqual(len(data.customers), 50)
        self.assertEqual(len(data.orders), 20)
        self.assertEqual(len(data.products), 65)
        self.assertIsInstance(data.products.iloc[0]["specs"], dict)
        self.assertTrue(data.promotions["is_active"].map(type).eq(bool).all())
        self.assertEqual(len(data.policies), 7)
        self.assertTrue(all(data.policies))

    def test_builds_public_documents_without_order_or_customer_records(self) -> None:
        documents = build_agent_documents(load_store_data())
        sources = {document.metadata["source"] for document in documents}

        self.assertEqual(sources, {"category", "product", "promotion", "policy"})
        self.assertEqual(
            sum(document.metadata["source"] == "product" for document in documents),
            65,
        )
        self.assertEqual(
            sum(document.metadata["source"] == "promotion" for document in documents),
            4,
        )
        self.assertTrue(
            all(
                len(document.content) <= POLICY_CHUNK_SIZE
                for document in documents
                if document.metadata["source"] == "policy"
            )
        )
        self.assertTrue(
            all(
                "Empório da Música Manual de Políticas" not in document.content
                for document in documents
                if document.metadata["source"] == "policy"
            )
        )

    def test_writes_utf8_jsonl_records(self) -> None:
        documents = build_agent_documents(load_store_data())
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "nested" / "documents.jsonl"
            write_agent_documents(documents, output_path)

            records = [
                json.loads(line)
                for line in output_path.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(len(records), len(documents))
        self.assertEqual(records[0]["id"], documents[0].id)
        self.assertIn("Categoria", records[0]["content"])

    def test_rejects_broken_foreign_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data_copy = Path(directory) / "data"
            shutil.copytree(DATA_DIR, data_copy)
            orders_path = data_copy / "desafio_tecnico_ai_eng - orders.csv"
            orders_path.write_text(
                orders_path.read_text(encoding="utf-8").replace(
                    "1,3,2025-10-15", "1,999,2025-10-15", 1
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "orders.customer_id"):
                load_store_data(data_copy)


if __name__ == "__main__":
    unittest.main()
