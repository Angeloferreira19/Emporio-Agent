# Empório da Música — backend

## Ambiente local

O backend usa Python 3.11 ou superior. Para criar o ambiente virtual e instalar as dependências:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

No Windows, ative o ambiente com `.venv\Scripts\activate`.

## Executar a API

Ainda em `backend/`, inicie o servidor de desenvolvimento:

```bash
uvicorn main:app --reload
```

A API fica disponível em <http://127.0.0.1:8000>. A rota `GET /` mostra os links úteis, `GET /health` verifica se o serviço está ativo, e a documentação interativa fica em <http://127.0.0.1:8000/docs>. O endpoint de conversa é `POST /api/chat`.

## Configuração do modelo

Copie `backend/.env.example` para `backend/.env` e preencha `GEMINI_API_KEY` com uma chave criada no [Google AI Studio](https://aistudio.google.com/api-keys). Ajuste `GEMINI_MODEL` e `GEMINI_EMBEDDING_MODEL` se necessário. O arquivo `.env` é ignorado pelo Git.

## Preparar dados para o agente

Com o ambiente virtual ativado, execute a partir de `backend/`:

```bash
python prepare_data.py
```

O comando valida as relações entre os CSVs, interpreta as especificações JSON dos produtos, lê as políticas em PDF e gera `backend/processed/agent_documents.jsonl`. Na inicialização, o backend gera embeddings com o Gemini e sincroniza os documentos com o Chroma em `backend/processed/chroma`, atualizando apenas registros alterados. Clientes e pedidos são validados, mas não entram no índice semântico; consulte esses dados de forma estruturada para evitar indexar informações pessoais. Para conferir as contagens e a integridade dos arquivos, execute `python explore.py`.

O Gemini API oferece cota gratuita para alguns modelos, sujeita a limites de taxa e disponibilidade por modelo/região; consulte a [página de preços e cotas](https://ai.google.dev/gemini-api/docs/pricing). Na modalidade gratuita, o Google pode usar o conteúdo enviado para melhorar os produtos, conforme os termos do serviço. Evite enviar dados pessoais ou sensíveis.

## Dependências

- **FastAPI e Uvicorn:** API HTTP e servidor local.
- **Google Gen AI SDK:** integração com o Gemini para respostas e embeddings.
- **Pydantic Settings e python-dotenv:** configuração por variáveis de ambiente.
- **pandas:** leitura e tratamento dos arquivos CSV.
- **pypdf:** extração de texto das políticas em PDF.
