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
uvicorn app.main:app --reload
```

A API fica disponível em <http://127.0.0.1:8000>. A rota `GET /health` verifica se o serviço está ativo, e a documentação interativa fica em <http://127.0.0.1:8000/docs>.

## Configuração do modelo

Copie `backend/.env.example` para `backend/.env` e preencha as credenciais e o nome do modelo escolhido. O arquivo `.env` é ignorado pelo Git. As variáveis serão utilizadas quando a integração com o modelo for implementada.

## Dependências

- **FastAPI e Uvicorn:** API HTTP e servidor local.
- **OpenAI SDK:** integração com a API OpenAI ou provedores compatíveis.
- **Pydantic Settings e python-dotenv:** configuração por variáveis de ambiente.
- **pandas:** leitura e tratamento dos arquivos CSV.
- **pypdf:** extração de texto das políticas em PDF.
