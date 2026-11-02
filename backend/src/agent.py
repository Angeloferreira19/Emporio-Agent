import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors, types

from src.prompts import SYSTEM_PROMPT

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

logger = logging.getLogger(__name__)
DEFAULT_FALLBACK_MODEL = "gemini-3.5-flash"
TRANSIENT_ERROR_CODES = {500, 502, 503, 504}


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

    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=30_000,
            retry_options=types.HttpRetryOptions(
                attempts=2,
                initial_delay=0.5,
                max_delay=1.0,
            ),
        ),
    )


def responder(pergunta: str, knowledge_base: KnowledgeSearcher) -> str:
    trechos = knowledge_base.search(pergunta)
    if not trechos:
        return (
            "Não encontrei essa informação no catálogo ou nas políticas disponíveis. "
            "Entre em contato com a loja para confirmar."
        )

    contexto = "\n\n---\n\n".join(trechos)
    client = _get_llm()
    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    contents = f"Trechos encontrados:\n{contexto}\n\nPergunta: {pergunta}"
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=0.2,
    )
    try:
        resposta = client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )
    except genai_errors.APIError as error:
        fallback_model = os.getenv(
            "GEMINI_FALLBACK_MODEL", DEFAULT_FALLBACK_MODEL
        ).strip()
        if error.code not in TRANSIENT_ERROR_CODES or not fallback_model or fallback_model == model:
            raise

        logger.warning(
            "Modelo Gemini %s indisponível (HTTP %s); tentando o fallback %s.",
            model,
            error.code,
            fallback_model,
        )
        resposta = client.models.generate_content(
            model=fallback_model,
            contents=contents,
            config=config,
        )

    texto = resposta.text
    if not texto:
        raise RuntimeError("O modelo retornou uma resposta vazia.")
    return texto