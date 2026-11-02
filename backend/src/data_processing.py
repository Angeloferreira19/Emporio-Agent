"""Load and prepare the Empório da Música source data for an agent."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

import pandas as pd
from pypdf import PdfReader

Record: TypeAlias = dict[str, object]

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
POLICY_FILENAME = "políticas_da_loja.pdf"
POLICY_CHUNK_SIZE = 1800
POLICY_CHUNK_OVERLAP = 180

CSV_FILES = {
    "categories": "desafio_tecnico_ai_eng - categories.csv",
    "customers": "desafio_tecnico_ai_eng - customers.csv",
    "order_items": "desafio_tecnico_ai_eng - order_items.csv",
    "orders": "desafio_tecnico_ai_eng - orders.csv",
    "products": "desafio_tecnico_ai_eng - products.csv",
    "promotions": "desafio_tecnico_ai_eng - promotions.csv",
}

REQUIRED_COLUMNS = {
    "categories": {"category_id", "name", "description"},
    "customers": {"customer_id", "name", "phone", "email", "city"},
    "order_items": {"order_id", "quantity", "product_id"},
    "orders": {
        "order_id",
        "customer_id",
        "order_date",
        "status",
        "total_brl",
        "payment_method",
        "tracking_code",
        "estimated_delivery",
        "notes",
    },
    "products": {
        "product_id",
        "price_brl",
        "name",
        "category_id",
        "description",
        "stock_quantity",
        "status",
        "specs",
        "created_at",
    },
    "promotions": {
        "promotion_id",
        "product_id",
        "discount_percent",
        "description",
        "is_active",
    },
}


@dataclass(frozen=True)
class AgentDocument:
    """A text document and metadata ready to serialize or embed."""

    id: str
    content: str
    metadata: dict[str, str | int | float | bool]

    def to_dict(self) -> dict[str, object]:
        return {"id": self.id, "content": self.content, "metadata": self.metadata}


@dataclass(frozen=True)
class StoreData:
    """Normalized source tables; orders and customers remain structured data."""

    categories: pd.DataFrame
    customers: pd.DataFrame
    order_items: pd.DataFrame
    orders: pd.DataFrame
    products: pd.DataFrame
    promotions: pd.DataFrame
    policies: tuple[str, ...]


def _read_csv(data_dir: Path, table: str) -> pd.DataFrame:
    path = data_dir / CSV_FILES[table]
    if not path.is_file():
        raise FileNotFoundError(f"Arquivo de dados não encontrado: {path}")

    frame = pd.read_csv(path, encoding="utf-8-sig")
    missing_columns = REQUIRED_COLUMNS[table] - set(frame.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"{path.name}: colunas obrigatórias ausentes: {missing}")
    if frame.empty:
        raise ValueError(f"{path.name}: o arquivo não contém registros.")

    for column in frame.select_dtypes(include=["object", "str"]).columns:
        frame[column] = frame[column].map(
            lambda value: value.strip() if isinstance(value, str) else value
        )
    return frame


def _validate_unique_ids(frame: pd.DataFrame, table: str, column: str) -> None:
    if frame[column].isna().any():
        raise ValueError(f"{table}.{column}: há identificadores vazios.")
    if frame[column].duplicated().any():
        raise ValueError(f"{table}.{column}: há identificadores duplicados.")


def _validate_reference(
    child: pd.DataFrame,
    child_table: str,
    child_column: str,
    parent: pd.DataFrame,
    parent_table: str,
    parent_column: str,
) -> None:
    missing = child.loc[~child[child_column].isin(parent[parent_column]), child_column]
    if not missing.empty:
        ids = ", ".join(str(value) for value in missing.drop_duplicates().tolist())
        raise ValueError(
            f"{child_table}.{child_column}: referências inexistentes em "
            f"{parent_table}.{parent_column}: {ids}"
        )


def _parse_product_specs(products: pd.DataFrame, filename: str) -> None:
    parsed_specs: list[dict[str, object]] = []
    for row_number, value in enumerate(products["specs"], start=2):
        try:
            specs = json.loads(value)
        except (json.JSONDecodeError, TypeError) as error:
            raise ValueError(
                f"{filename}, linha {row_number}: 'specs' não contém JSON válido."
            ) from error
        if not isinstance(specs, dict):
            raise ValueError(
                f"{filename}, linha {row_number}: 'specs' precisa ser um objeto JSON."
            )
        parsed_specs.append(specs)
    products["specs"] = parsed_specs


def _extract_policy_pages(pdf_path: Path) -> tuple[str, ...]:
    if not pdf_path.is_file():
        raise FileNotFoundError(f"Arquivo de políticas não encontrado: {pdf_path}")

    reader = PdfReader(pdf_path)
    pages: list[str] = []
    for page_number, page in enumerate(reader.pages, start=1):
        if page_number == 1:
            continue
        text = re.sub(r"\s+", " ", page.extract_text() or "").strip()
        text = re.sub(
            r"^Empório da Música Manual de Políticas e Procedimentos\s*",
            "",
            text,
            count=1,
            flags=re.IGNORECASE,
        ).strip()
        if not text:
            raise ValueError(
                f"{pdf_path.name}, página {page_number}: nenhum texto extraído. "
                "Se o PDF for digitalizado, aplique OCR antes de preparar a base."
            )
        pages.append(text)

    if not pages:
        raise ValueError(f"{pdf_path.name}: o PDF não contém páginas de políticas.")
    return tuple(pages)


def load_store_data(data_dir: Path = DATA_DIR) -> StoreData:
    """Read, normalize, and validate all CSV tables and policy PDF pages."""
    data_dir = Path(data_dir)
    tables = {name: _read_csv(data_dir, name) for name in CSV_FILES}

    primary_keys = {
        "categories": ("categories", "category_id"),
        "customers": ("customers", "customer_id"),
        "orders": ("orders", "order_id"),
        "products": ("products", "product_id"),
        "promotions": ("promotions", "promotion_id"),
    }
    for table, (key_table, key_column) in primary_keys.items():
        _validate_unique_ids(tables[table], key_table, key_column)

    references = (
        ("products", "category_id", "categories", "category_id"),
        ("orders", "customer_id", "customers", "customer_id"),
        ("order_items", "order_id", "orders", "order_id"),
        ("order_items", "product_id", "products", "product_id"),
        ("promotions", "product_id", "products", "product_id"),
    )
    for child_name, child_col, parent_name, parent_col in references:
        _validate_reference(
            tables[child_name],
            child_name,
            child_col,
            tables[parent_name],
            parent_name,
            parent_col,
        )

    products = tables["products"]
    _parse_product_specs(products, CSV_FILES["products"])
    if (products["price_brl"] < 0).any():
        raise ValueError("products.price_brl: valores não podem ser negativos.")
    if (products["stock_quantity"] < 0).any():
        raise ValueError("products.stock_quantity: valores não podem ser negativos.")

    order_items = tables["order_items"]
    if (order_items["quantity"] <= 0).any():
        raise ValueError("order_items.quantity: quantidades devem ser positivas.")

    promotions = tables["promotions"]
    if not promotions["is_active"].isin((0, 1, False, True)).all():
        raise ValueError("promotions.is_active: use somente 0/1 ou true/false.")
    promotions["is_active"] = promotions["is_active"].astype(bool)
    if not promotions["discount_percent"].between(0, 100).all():
        raise ValueError("promotions.discount_percent: use valores entre 0 e 100.")

    orders = tables["orders"]
    if (orders["total_brl"] < 0).any():
        raise ValueError("orders.total_brl: valores não podem ser negativos.")

    return StoreData(
        categories=tables["categories"],
        customers=tables["customers"],
        order_items=order_items,
        orders=orders,
        products=products,
        promotions=promotions,
        policies=_extract_policy_pages(data_dir / POLICY_FILENAME),
    )


def _format_brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _split_policy_text(text: str) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + POLICY_CHUNK_SIZE, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start = max(start + 1, end - POLICY_CHUNK_OVERLAP)
        while start < len(text) and text[start].isspace():
            start += 1
    return chunks


def build_agent_documents(data: StoreData) -> list[AgentDocument]:
    """Build retrieval documents without embedding customer or order records."""
    categories = {
        int(row.category_id): row
        for row in data.categories.itertuples(index=False)
    }
    promotions_by_product: dict[int, list[object]] = {}
    for promotion in data.promotions.itertuples(index=False):
        if promotion.is_active:
            promotions_by_product.setdefault(int(promotion.product_id), []).append(
                promotion
            )

    documents: list[AgentDocument] = []
    for category in data.categories.itertuples(index=False):
        documents.append(
            AgentDocument(
                id=f"category-{category.category_id}",
                content=(
                    f"Categoria: {category.name}. "
                    f"Descrição: {category.description}"
                ),
                metadata={
                    "source": "category",
                    "category_id": int(category.category_id),
                },
            )
        )

    for product in data.products.itertuples(index=False):
        category = categories[int(product.category_id)]
        if product.status == "active" and int(product.stock_quantity) > 0:
            availability = f"disponível, estoque de {product.stock_quantity} unidade(s)"
        elif product.status == "active":
            availability = "sem estoque no momento"
        elif product.status == "coming_soon":
            availability = "em breve"
        else:
            availability = "descontinuado"

        specs = ", ".join(
            f"{key}: {value}" for key, value in product.specs.items()
        ) or "não informadas"
        content = (
            f"Produto: {product.name}. "
            f"Categoria: {category.name}. "
            f"Descrição: {product.description} "
            f"Preço: {_format_brl(float(product.price_brl))}. "
            f"Disponibilidade: {availability}. "
            f"Especificações: {specs}."
        )
        for promotion in promotions_by_product.get(int(product.product_id), []):
            sale_price = float(product.price_brl) * (
                1 - int(promotion.discount_percent) / 100
            )
            content += (
                f" Promoção ativa: {promotion.description}, "
                f"{promotion.discount_percent}% de desconto; "
                f"preço promocional {_format_brl(sale_price)}."
            )
        documents.append(
            AgentDocument(
                id=f"product-{product.product_id}",
                content=content,
                metadata={
                    "source": "product",
                    "product_id": int(product.product_id),
                    "category_id": int(product.category_id),
                    "status": str(product.status),
                    "stock_quantity": int(product.stock_quantity),
                    "price_brl": float(product.price_brl),
                },
            )
        )

    for promotion in data.promotions.itertuples(index=False):
        if not promotion.is_active:
            continue
        product = data.products.loc[
            data.products["product_id"] == promotion.product_id
        ].iloc[0]
        discounted_price = float(product["price_brl"]) * (
            1 - int(promotion.discount_percent) / 100
        )
        documents.append(
            AgentDocument(
                id=f"promotion-{promotion.promotion_id}",
                content=(
                    f"Promoção ativa: {promotion.description}. "
                    f"Produto: {product['name']}. "
                    f"Desconto: {promotion.discount_percent}%. "
                    f"Preço original: {_format_brl(float(product['price_brl']))}; "
                    f"preço promocional: {_format_brl(discounted_price)}."
                ),
                metadata={
                    "source": "promotion",
                    "promotion_id": int(promotion.promotion_id),
                    "product_id": int(promotion.product_id),
                    "discount_percent": int(promotion.discount_percent),
                },
            )
        )

    for page_number, page_text in enumerate(data.policies, start=2):
        for chunk_number, chunk in enumerate(_split_policy_text(page_text), start=1):
            documents.append(
                AgentDocument(
                    id=f"policy-page-{page_number}-chunk-{chunk_number}",
                    content=chunk,
                    metadata={
                        "source": "policy",
                        "page": page_number,
                        "chunk": chunk_number,
                    },
                )
            )

    return documents


def write_agent_documents(
    documents: list[AgentDocument], output_path: Path
) -> None:
    """Write UTF-8 JSONL documents, one retrieval record per line."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
        for document in documents:
            output_file.write(
                json.dumps(document.to_dict(), ensure_ascii=False) + "\n"
            )
