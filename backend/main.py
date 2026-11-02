import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from google.genai import errors as genai_errors
from pydantic import BaseModel, Field, field_validator

from src.agent import responder
from src.knowledge_base import KnowledgeBase, initialize_knowledge_base

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.knowledge_base = initialize_knowledge_base()
    yield


app = FastAPI(
    title="Empório da Música API",
    description="API de atendimento da Empório da Música.",
    lifespan=lifespan,
)


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1)
    message: str = Field(min_length=1)

    @field_validator("session_id", "message")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O campo não pode ficar vazio.")
        return value


class ToolUsage(BaseModel):
    name: str
    args: dict[str, str]


class ChatResponse(BaseModel):
    reply: str
    tools_used: list[ToolUsage]


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "API da Empório da Música",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    knowledge_base: KnowledgeBase = app.state.knowledge_base
    try:
        reply = responder(request.message, knowledge_base)
    except genai_errors.APIError as error:
        logger.exception("Falha ao consultar o Gemini.")
        if error.code in (400, 401, 403):
            detail = (
                "O Gemini recusou a chave configurada. "
                "Verifique GEMINI_API_KEY no arquivo backend/.env."
            )
        elif error.code == 429:
            detail = (
                "A cota gratuita do Gemini foi atingida ou está temporariamente "
                "indisponível. Confira os limites do projeto no Google AI Studio."
            )
        elif error.code in (500, 502, 503, 504):
            detail = (
                "O Gemini está temporariamente indisponível, mesmo após tentar "
                "o modelo alternativo. Tente novamente em instantes."
            )
        else:
            detail = "Falha ao consultar o Gemini. Tente novamente mais tarde."
        raise HTTPException(
            status_code=503
            if error.code in (400, 401, 403, 429, 500, 502, 503, 504)
            else 502,
            detail=detail,
        ) from error

    return ChatResponse(
        reply=reply,
        tools_used=[
            ToolUsage(
                name="buscar_base_conhecimento",
                args={"query": request.message},
            )
        ],
    )