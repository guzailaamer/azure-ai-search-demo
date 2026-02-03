# azure-ai-search-demo

Small RAG demo: frontend chat UI, Azure Function + FastAPI query backends, Azure Cognitive Search index & ingestion scripts.

## Contents
- `frontend.html` — browser chat UI (points to deployed function by default).
- `backend/backend_api.py` — FastAPI query implementation (alternative to Functions).
- `backend-function/function_app.py` — Azure Function implementation of `/query` and `/health`.
- `scripts/` — index creation, datasource/indexer/skillset creation, and `process_documents.py` for local ingestion.
- `backend-function/local.settings.json` — local Function settings (contains secrets for dev).

## Prerequisites
- Python 3.9+
- pip
- Azure Functions Core Tools (to run Functions locally) OR use FastAPI + `uvicorn`
- (Optional) Git Bash / WSL for POSIX `curl`, or use PowerShell with `curl.exe` / `Invoke-RestMethod`

## Install
```bash
pip install -r backend-function/requirements.txt
```

## Configuration
1. Copy `.env.example` → `.env` and fill values.
2. For Azure Functions local testing, ensure `backend-function/local.settings.json` has correct dev values (this repo currently includes a local file — rotate any exposed keys).
3. For ingestion with `scripts/*`, set `STORAGE_CONNECTION_STRING`, `CONTAINER_NAME`, etc.

## Running locally

### Azure Function
```powershell
cd backend-function
func start
# Function host will typically be at http://localhost:7071
```

### FastAPI (alternative)
```bash
# from repo root
uvicorn backend.backend_api:app --reload --port 8000
# or
python backend/backend_api.py
```

## Indexing / Ingestion
Two approaches:
- Use the Azure indexer + skillset (see `scripts/create_index.py`, `create_skillset.py`, `create_datasource.py`, `create_indexer.py`) — this lets Search call Azure OpenAI to create embeddings.
- Or run local ingestion to compute embeddings and upload docs: 
```bash
python scripts/process_documents.py
```

## Test the query endpoint

- PowerShell (recommended):
```powershell
Invoke-RestMethod -Uri 'http://localhost:7071/api/query' -Method Post -ContentType 'application/json' -Body '{"query":"What motorcycles are in the documents?"}'
```

- curl.exe in PowerShell (escape quotes):
```powershell
curl.exe -X POST "http://localhost:7071/api/query" -H "Content-Type: application/json" -d "{\"query\":\"What motorcycles are in the documents?\"}"
```

- Bash / WSL / Git Bash:
```bash
curl -X POST http://localhost:7071/api/query \
  -H "Content-Type: application/json" \
  -d '{"query":"What motorcycles are in the documents?"}'
```

## Troubleshooting
- If CORS errors occur, confirm the Function responses include `Access-Control-Allow-Origin` headers (they do in `backend-function/function_app.py`).
- If your query returns no documents, check that `contentVector` is populated in the index (either via indexer or `process_documents.py`).
- Confirm embedding & chat deployments and API version match the values used in code (`OPENAI_API_KEY`, `OPENAI_ENDPOINT`, `api_version` in clients).

## Security notes
- Rotate any keys accidentally committed.
- Do not commit `.env` or secrets; use Azure Key Vault for production secrets and managed identity where possible.
