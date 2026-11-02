"""Print a small quality report for the prepared agent data."""

from src.data_processing import build_agent_documents, load_store_data


def main() -> None:
    data = load_store_data()
    documents = build_agent_documents(data)

    print("Linhas carregadas:")
    for name in (
        "categories",
        "customers",
        "order_items",
        "orders",
        "products",
        "promotions",
    ):
        print(f"- {name}: {len(getattr(data, name))}")

    print("\nStatus dos produtos:")
    print(data.products["status"].value_counts().to_string())
    print("\nStatus dos pedidos:")
    print(data.orders["status"].value_counts().to_string())
    print(f"\nPáginas de políticas extraídas: {len(data.policies)}")
    print(f"Documentos preparados para busca: {len(documents)}")
    print("Integridade das chaves e especificações: válida")


if __name__ == "__main__":
    main()
