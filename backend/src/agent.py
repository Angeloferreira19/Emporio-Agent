import os
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from dotenv import load_dotenv
from google import genai
from google.genai import types

from src.prompts import SYSTEM_PROMPT

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class KnowledgeSearcher(Protocol):
    def search(self, question: str, limit: int = 4) -> list[str]: ...


@lru_cache(maxsize=1)
def _get_llm() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY não configurada. Preencha backend/.env com uma chave "
            "do Google AI Studio antes de iniciar."
        )

    return genai.Client(api_key=api_key)


def responder(pergunta: str, knowledge_base: KnowledgeSearcher) -> str:
    trechos = knowledge_base.search(pergunta)
    if not trechos:
        return (
            "Não encontrei essa informação no catálogo ou nas políticas disponíveis. "
            "Entre em contato com a loja para confirmar."
        )

    contexto = "\n\n---\n\n".join(trechos)
    resposta = _get_llm().models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        contents=f"Trechos encontrados:\n{contexto}\n\nPergunta: {pergunta}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
        ),
    )

    texto = resposta.text
    if not texto:
        raise RuntimeError("O modelo retornou uma resposta vazia.")
    return texto