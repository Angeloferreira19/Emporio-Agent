# Empório da Música — Customer Support

## Local environment

The backend requires Python 3.11 or later. To create a virtual environment and install its dependencies:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

On Windows, activate the environment with `.venv\Scripts\activate`.

## Run the API

From `backend/`, start the development server:

```bash
uvicorn main:app --reload
```

The API is available at <http://127.0.0.1:8000>. The `GET /` route lists useful links, `GET /health` checks whether the service is running, and interactive API documentation is available at <http://127.0.0.1:8000/docs>. The chat endpoint is `POST /api/chat`.

## Configure the model

Copy `backend/.env.example` to `backend/.env` and set `GEMINI_API_KEY` to a key created in [Google AI Studio](https://aistudio.google.com/api-keys). `GEMINI_MODEL` selects the primary model. If it is temporarily unavailable, the agent tries `GEMINI_FALLBACK_MODEL` (default: `gemini-3.5-flash`). You can also adjust `GEMINI_EMBEDDING_MODEL`. The `.env` file is ignored by Git.

## Prepare the agent data

With the virtual environment activated, run this command from `backend/`:

```bash
python prepare_data.py
```

This command validates relationships between the CSV files, parses product specifications stored as JSON, reads the PDF store policies, and generates `backend/processed/agent_documents.jsonl`. At startup, the backend creates Gemini embeddings and synchronizes the documents with Chroma in `backend/processed/chroma`, updating only changed records. Customer and order files are validated but are not added to the semantic index, avoiding the indexing of personal information. To inspect file counts and integrity, run `python explore.py`.

The Gemini API offers free quotas for some models, subject to rate limits and model or regional availability; see the [pricing and rate limits page](https://ai.google.dev/gemini-api/docs/pricing). Under the free tier, Google may use submitted content to improve its products, according to its terms of service. Avoid sending personal or sensitive data.

## Technical decisions

- **Language and API:** Python is required by the challenge. FastAPI provides a small HTTP interface between the agent and the web frontend, with request validation and interactive API documentation.
- **Agent architecture and retrieval:** I chose retrieval-augmented generation (RAG) because it is familiar from my previous projects and lets me build on an approach I know well. The agent retrieves relevant product catalog or policy passages from a Chroma collection and provides them to the model as context. This keeps answers grounded in the supplied materials without adding a separate orchestration framework.
- **Model provider:** I chose Gemini because, among the widely used hosted LLM providers I considered, its free quota was the best fit for a prototype with limited resources. The provider is configurable, and a fallback model is attempted when generation fails due to transient server errors. This is a practical trade-off, not a claim that Gemini is universally the best model.
- **Frontend:** I chose React for its flexibility in building and customizing the chat experience. The browser stores conversation history for display, but previous messages are not sent as context to the backend.
- **Data preparation:** Product specifications are parsed from JSON, CSV relationships are validated, and store policy text is extracted from the supplied PDF. Customer and order tables are validated but excluded from the semantic index to avoid indexing personal information.

## Example conversations

The agent is configured to respond in Portuguese. These examples show how it uses the supplied catalog and store policies; the illustrative transcripts are in English for the submission:

- **Product availability and prices:** “Which nylon-string guitars are available for under R$1,000?” The agent lists matching products with catalog prices and stock. ([Transcript](./examples/01-product-catalog.md))
- **Return policy:** “I bought an instrument online and changed my mind. Can I return it?” The agent explains the return window and conditions from the policy. ([Transcript](./examples/02-return-policy.md))
- **Store information:** “Where is the store, and when are you open?” The agent answers with the address and opening hours. ([Transcript](./examples/03-store-information.md))

## Run the frontend

The frontend uses React and Vite and requires Node.js 20.19 or later. In another terminal, install the dependencies and start the UI:

```bash
cd frontend
npm install
npm run dev
```

Open the address printed by Vite. During development, `/api` and `/health` requests are proxied to the backend at `http://localhost:8000`; keep the API running to chat with the agent. The frontend stores a local conversation list in the browser. Users can switch between conversations or delete them from the sidebar. This history is not sent to the agent as context or synchronized with the backend. The UI supports light and dark themes, saves the selected theme in the browser, and follows the system preference on the first visit. To validate the frontend, run `npm run lint` and `npm run build` from `frontend/`.

## Known limitations and future improvements

- **Provider availability and quotas:** Generation and embedding depend on the Gemini API. A fallback model helps with temporary generation outages, but it does not remove provider, quota, or embedding-service dependency.
- **Catalog freshness:** Product prices and stock reflect the supplied CSV snapshot, not a live inventory system.
- **Order support:** Customer and order data are validated but are not queried by the agent. With more time, I would add a secure, structured order lookup with customer verification instead of exposing those records through semantic search.
- **No conversational context:** Although the frontend saves conversation history locally, each request is answered from the current message and retrieved documents; prior turns are not included in the model prompt.
- **Evaluation and automation:** The prototype uses a straightforward retrieval-and-generation flow. With more time, I would automate more of the agent's decision-making with structured tools, and add an evaluation set for retrieval relevance, factual accuracy, and out-of-scope questions.
- **Frontend polish:** Given more time, I would continue refining the interface and testing it with users.

## AI coding assistant usage

I used GitHub Copilot as a coding assistant during development. It helped me explore implementation options, get unstuck, and move faster, especially while building and refining the frontend. I used it as support rather than as a substitute for project decisions: I chose the overall direction based on the challenge requirements and my experience, then reviewed and tested the resulting changes. With more time, I would aim to rely less on AI assistance and implement more of the work independently.

## Dependencies

- **FastAPI and Uvicorn:** HTTP API and local server.
- **Google Gen AI SDK:** Gemini integration for responses and embeddings.
- **Pydantic Settings and python-dotenv:** environment-based configuration.
- **pandas:** CSV loading and processing.
- **pypdf:** text extraction from the store policies PDF.
