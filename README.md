# Edson IT AI Support Platform

Shared AI support backend and Chrome extension for the ServiceNow AI Ticket Assistant.

The first supported workflow is AI-assisted ServiceNow ticket field generation and one-field-at-a-time revision. The backend is organized so later channels, such as an IT Help Chatbot, can use the same user profiles, prompt engine, CreateAI provider, safety rules, memory, and PostgreSQL/pgvector database.

## Project Layout

```text
backend/
  app/
    api/                  FastAPI route modules
    ai/                   CreateAI provider, prompt engine, validators, safety
    core/                 settings, logging, security helpers
    db/                   database setup, models, SQL migrations
    domains/servicenow/   ServiceNow schemas, prompts, service logic
    domains/it_support/   future chatbot placeholder
    memory/               local user/team/session/example memory
    retrieval/            future embeddings and vector search placeholders

extension/
  src/                    Vite React Chrome extension content script
```

## Backend Quick Start

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

The backend defaults to `CREATEAI_MOCK=true`, which returns deterministic local output for development. Set `CREATEAI_MOCK=false`, `CREATEAI_QUERY_URL`, and any required CreateAI auth values when you are ready to call the real Query endpoint.

The CreateAI provider sends this MVP payload shape:

```json
{
  "action": "query",
  "model_provider": "openai",
  "model_name": "gpt4o",
  "model_params": {
    "temperature": 0.1,
    "top_p": 0.01,
    "system_prompt": "..."
  },
  "enable_search": false,
  "enable_history": false,
  "response_format": {
    "type": "json"
  }
}
```

## Database

PostgreSQL/pgvector is included through `docker-compose.yml`.

```bash
docker compose up -d postgres
docker compose exec -T postgres psql -U edson_it_ai -d edson_it_ai < backend/app/db/migrations/001_initial.sql
```

By default, Docker publishes PostgreSQL on host port `5433` to avoid colliding with a local Postgres on `5432`. Use this backend setting:

```env
DATABASE_URL=postgresql+psycopg://edson_it_ai:edson_it_ai@localhost:5433/edson_it_ai
```

Override the published host port with `POSTGRES_HOST_PORT` if needed. When `DATABASE_URL` is configured, the backend persists generations, revisions, field statuses, and accepted examples. Without `DATABASE_URL`, the app still runs in local in-memory mode.

## Extension Quick Start

```bash
cd extension
npm install
npm run build
```

Then load `extension/dist` as an unpacked extension in Chrome.

Set `VITE_BACKEND_URL` in `extension/.env` if the backend is not running at `http://localhost:8000`.

## MVP Endpoints

- `POST /api/servicenow/generate-fields`
- `POST /api/servicenow/revise-field`
- `POST /api/servicenow/save-field-status`

The extension does not auto-submit, close, or resolve ServiceNow tickets. It fills fields and leaves the Update action to the user.
