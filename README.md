# azure-ai-search-demo

A RAG (Retrieval Augmented Generation) demo built with Azure AI Search, Azure OpenAI, and Azure Functions. Includes a frontend chat UI, query backend, and document ingestion pipeline.

## Architecture
```
User → frontend.html → Azure Function (query) → Azure AI Search (hybrid search) → Azure OpenAI (GPT-4o) → Answer + Citations
                                                        ↑
Documents (PDFs) → Blob Storage → process_documents.py → Azure AI Search Index (embeddings via text-embedding-ada-002)
```

## Contents
- `frontend.html` — Browser chat UI (points to deployed Azure Function).
- `backend/backend_api.py` — FastAPI query implementation (local development/alternative).
- `backend-function/function_app.py` — Azure Function implementation of `/query`, `/health`, and CORS preflight `/query OPTIONS`.
- `scripts/` — Index creation, datasource/indexer/skillset creation, and `process_documents.py` for manual ingestion.
- `backend-function/local.settings.json` — Local Function settings (contains secrets for dev only).

## Prerequisites
- Python 3.11+
- pip
- Azure CLI (`az login`)
- Azure Functions Core Tools v4 (`func --version`)
- VS Code with **Live Server** extension (recommended for running frontend locally)
- (Optional) Git Bash / WSL for POSIX `curl`, or use PowerShell with `Invoke-WebRequest` / `Invoke-RestMethod`

## Install
```bash
pip install -r backend-function/requirements.txt
```

For document ingestion also install:
```bash
pip install PyPDF2 pycryptodome azure-storage-blob
```

## Configuration
1. Copy `.env.example` → `.env` and fill in values:
```env
STORAGE_CONNECTION_STRING=<from Storage Account → Access Keys>
STORAGE_ACCOUNT_NAME=storageragdemo001
CONTAINER_NAME=documents
SEARCH_ENDPOINT=https://<your-search-service>.search.windows.net
SEARCH_ADMIN_KEY=<from AI Search → Keys>
OPENAI_ENDPOINT=<from Azure OpenAI → Keys and Endpoint>
OPENAI_KEY=<from Azure OpenAI → Keys and Endpoint>
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```
2. For Azure Functions local testing, copy values into `backend-function/local.settings.json`.
3. **Rotate any keys that were accidentally committed.**

## Running Locally

### Azure Function (Recommended)
```powershell
cd backend-function
func start
# Health: http://localhost:7071/api/health
# Query: http://localhost:7071/api/query
```

### FastAPI (Alternative)
```powershell
cd backend
python backend_api.py
# Docs: http://localhost:8000/docs
# Query: http://localhost:8000/query
```

### Frontend
- Open `frontend.html` using **VS Code → Live Server** (right-click → "Go Live")
- Opens at `http://127.0.0.1:5500/frontend.html`
- **Do not** open `frontend.html` by double-clicking — CORS will block requests

## Indexing / Ingestion

### Option A: Manual Python Ingestion (Recommended)
Reads PDFs from Blob Storage, chunks text, generates embeddings, and uploads to the search index:
```powershell
python scripts/process_documents.py
```
- Processes all PDFs in your Blob Storage container
- Chunks text into 1000-char pieces with 100-char overlap
- Generates embeddings using `text-embedding-ada-002`
- Uploads to Azure AI Search index

**To reindex after document changes:** Simply re-upload the PDF to Blob Storage and re-run the script.

### Option B: Azure Indexer + Skillset
Uses Azure-native indexer pipeline:
```powershell
python scripts/create_datasource.py
python scripts/create_index.py
python scripts/create_skillset.py
python scripts/create_indexer.py
```
> **Note:** This approach may encounter a `Collection(Edm.Double)` vs `Collection(Edm.Single)` type mismatch with `AzureOpenAIEmbeddingSkill`. Option A is more reliable.

## Testing the Query Endpoint

### PowerShell (Recommended)
```powershell
# Local
Invoke-WebRequest -Uri "http://localhost:7071/api/query" -Method POST -ContentType "application/json" -Body '{"query":"What motorcycles are in the documents?"}' -UseBasicParsing

# Deployed
Invoke-WebRequest -Uri "https://<your-function-app>.azurewebsites.net/api/query" -Method POST -ContentType "application/json" -Body '{"query":"What motorcycles are in the documents?"}' -UseBasicParsing
```

### Bash / WSL / Git Bash
```bash
curl -X POST http://localhost:7071/api/query \
  -H "Content-Type: application/json" \
  -d '{"query":"What motorcycles are in the documents?"}'
```

### FastAPI Interactive Docs
```
http://localhost:8000/docs
```
- Click **POST /query** → **Try it out** → Enter query → **Execute**

## Deployment

### Azure Function
```powershell
cd backend-function
func azure functionapp publish <your-function-app-name>
```

### Set Environment Variables
```powershell
az functionapp config appsettings set `
  --name <your-function-app-name> `
  --resource-group rg-rag-demo `
  --settings `
    SEARCH_ENDPOINT="<your-endpoint>" `
    SEARCH_ADMIN_KEY="<your-key>" `
    OPENAI_ENDPOINT="<your-endpoint>" `
    OPENAI_KEY="<your-key>"
```

### CORS Configuration
```powershell
az functionapp cors add `
  --name <your-function-app-name> `
  --resource-group rg-rag-demo `
  --origins "http://127.0.0.1:5500"
```

## Monitoring
In Azure Portal → **Function App**:
- **Monitor → Metrics** — Invocations, execution time, errors
- **Monitor → Logs** — Real-time execution logs
- **Overview** — Invocation count and error summary

Also check:
- **Azure OpenAI → Usage** — Token usage and costs
- **AI Search → Usage** — Query counts

## Troubleshooting

| Issue | Fix |
|-------|-----|
| CORS errors | Ensure `Access-Control-Allow-Origin` headers are in responses. Run frontend via Live Server, not directly. |
| `failed to fetch` in frontend | Open via Live Server (`http://127.0.0.1:5500`), not double-click. Add origin to CORS in Portal. |
| No documents returned | Run `process_documents.py` to index. Check `contentVector` is populated in AI Search index. |
| `DeploymentNotFound` | Verify deployment names in Azure OpenAI match values in code (e.g., `gpt-4o` not `gpt-4`). |
| `PyCryptodome required` | Run `pip install pycryptodome` — needed for encrypted PDFs. |
| `InvalidDocumentKey` | Document IDs cannot contain `.` — use `blob_name.replace('.', '_')`. |
| `proxies` keyword error | Run `pip install --upgrade openai`. |
| `Collection(Edm.Double)` mismatch | Use manual ingestion (`process_documents.py`) instead of Azure Skillset indexer. |

## Security Notes
- **Rotate any keys accidentally committed.**
- Do not commit `.env` or `local.settings.json` with real secrets — add to `.gitignore`.
- Use **Azure Key Vault** and **Managed Identity** for production deployments.

## Future Improvements
- Add **Event Grid** trigger to auto-reindex when documents change in Blob Storage
- Add **conversation history** to maintain context across messages
- Deploy frontend to **Azure Static Web Apps**
- Add **Azure Entra ID** authentication for user-level access control
- Add **ACL filtering** for document-level security