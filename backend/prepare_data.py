"""Prepare CSV and PDF source files for the agent knowledge base."""

from pathlib import Path

from src.data_processing import (
    build_agent_documents,
    load_store_data,
    write_agent_documents,
)

DEFAULT_OUTPUT = Path(__file__).resolve().parent / "processed" / "agent_documents.jsonl"


def main() -> None:
    data = load_store_data()
    documents = build_agent_documents(data)
    write_agent_documents(documents, DEFAULT_OUTPUT)
    print(
        f"Base preparada: {len(documents)} documentos em {DEFAULT_OUTPUT}. "
        f"{len(data.customers)} clientes e {len(data.orders)} pedidos foram "
        "validados e permanecem disponíveis apenas como dados estruturados."
    )


if __name__ == "__main__":
    main()
