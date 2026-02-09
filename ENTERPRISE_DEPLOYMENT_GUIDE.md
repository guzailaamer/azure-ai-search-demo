# Enterprise RAG System Deployment Guide

## Complete Guide to Deploying a Production-Ready RAG System with Azure AI Search

**Version:** 1.0  
**Last Updated:** February 2026   
**Prerequisites:** Azure Contributor access to a Resource Group

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites & Access Requirements](#prerequisites--access-requirements)
3. [**Azure Portal Quick Reference**](#azure-portal-quick-reference) 
4. [Phase 0: Environment Setup](#phase-0-environment-setup)
5. [Phase 1: Azure Resource Provisioning](#phase-1-azure-resource-provisioning)
6. [Phase 2: Code Deployment](#phase-2-code-deployment)
7. [Phase 3: Document Ingestion](#phase-3-document-ingestion)
8. [Phase 4: Query Pipeline Setup](#phase-4-query-pipeline-setup)
9. [Phase 5: Frontend Deployment](#phase-5-frontend-deployment)
10. [Phase 6: Auto-Reindexing with Event Grid](#phase-6-auto-reindexing-with-event-grid)
11. [Policy Document Considerations](#policy-document-considerations)
12. [Common Errors & Troubleshooting](#common-errors--troubleshooting)
13. [Production Refinements](#production-refinements)
14. [Testing Checklist](#testing-checklist)
15. [Appendix: Scripts & Templates](#appendix-scripts--templates)

---

## Azure Portal Quick Reference

**New to Azure Portal?** This section provides a visual guide to help you navigate.

### Accessing Azure Portal

1. **URL:** [https://portal.azure.com](https://portal.azure.com)
2. **Sign in** with your organization credentials
3. **Home page** shows:
   - Recent resources
   - Azure services menu
   - Search bar (top)

### Key Portal Navigation

**Finding Resources:**
- **Search bar** (top): Type resource name or service (fastest method)
- **All resources**: See everything in your subscription
- **Resource groups**: View resources organized by group
- **Favorites** (left sidebar): Pin frequently used services

**Common Actions:**
- **Create a resource**: Big blue button (top left) or search "+ Create"
- **Notifications**: Bell icon (top right) - shows deployment status
- **Cloud Shell**: Terminal icon (top right) - built-in CLI
- **Settings**: Gear icon (top right) - portal preferences

### Resource Group Navigation

Your company resource group contains all RAG system resources:

1. Navigate to **Resource groups** (search or left menu)
2. Click your resource group name
3. See all resources in one place:
   - Storage accounts
   - AI Search
   - OpenAI
   - Function App
   - Event Grid subscriptions

### Getting Connection Strings & Keys

**Storage Account:**
- Storage Account → **Access keys** → Show keys → Copy **Connection string**

**AI Search:**
- AI Search → **Keys** → Copy **Primary admin key**
- URL shown at top of Overview page

**Azure OpenAI:**
- Azure OpenAI → **Keys and Endpoint** → Copy **KEY 1** and **Endpoint**

**Function App:**
- Function App → **Overview** → URL shown at top
- For function keys: Functions → Select function → **Function Keys**

### Monitoring & Logs

**Function App Logs (Real-time):**
- Function App → **Log stream** (left sidebar)
- Shows live execution logs

**Function App Monitoring:**
- Function App → **Monitor** tab → See invocation history
- Click invocation → See detailed logs and errors

**Application Insights (Advanced):**
- Function App → **Application Insights** → Logs
- Run KQL queries for deep analysis

**Event Grid Metrics:**
- Storage Account → Events → Event Subscriptions → Click subscription → **Metrics** tab
- See delivery success/failure rates

### Common Portal Tasks

**Upload files to Blob Storage:**
1. Storage Account → Containers
2. Click container name
3. Click **Upload** button
4. Select files → Upload

**View Search Index:**
1. AI Search → Indexes
2. Click index name
3. Click **Search explorer**
4. Enter search query or `*` for all

**Test Function:**
1. Function App → Functions
2. Click function name
3. Click **Code + Test** tab
4. Click **Test/Run**
5. Enter test body → Run

**View Function Environment Variables:**
1. Function App → **Environment variables** (or Configuration)
2. See all application settings
3. Click "Show values" to reveal secrets (if permitted)

### Troubleshooting in Portal

**Resource creation failed:**
- Click **Notifications** (bell icon)
- Click failed deployment
- Click **Error details** for specific error

**Function not working:**
- Function App → **Diagnose and solve problems**
- Run built-in diagnostics
- Check "Function Execution Errors"

**Can't find resource:**
- Use **Search bar** (top) - searches across all subscriptions
- Check correct **subscription** is selected (top right, next to your name)
- Verify resource is in expected **resource group**

### Portal vs CLI - When to Use Each

**Use Portal when:**
- ✅ Learning Azure for the first time
- ✅ Creating resources (visual, guided)
- ✅ Troubleshooting (rich diagnostics)
- ✅ Viewing metrics and logs
- ✅ One-time setup tasks

**Use CLI when:**
- ✅ Automating repetitive tasks
- ✅ Scripting deployments
- ✅ Batch operations (e.g., uploading 100 files)
- ✅ Infrastructure as Code
- ✅ CI/CD pipelines

**This guide provides both methods** - use whichever you're more comfortable with!

---

## Architecture Overview

### System Flow
```
User → Frontend (HTML/React) 
  ↓
Azure Function (Query API)
  ↓
Azure AI Search (Hybrid Vector + Keyword Search)
  ↓
Azure OpenAI (GPT-4o for answers, text-embedding-ada-002 for embeddings)
  ↓
Return: Answer + Citations

Background Process:
Policy PDFs → Blob Storage 
  ↓
Event Grid (detects changes)
  ↓
Azure Function (Reindex)
  ↓
Process → Chunk → Embed → Index
```

### Components
- **Azure Blob Storage**: Stores policy documents (PDFs, DOCX)
- **Azure AI Search**: Hybrid search index (vector + keyword)
- **Azure OpenAI**: Embeddings and chat completion
- **Azure Functions**: Query API and reindexing logic
- **Azure Event Grid**: Auto-triggers reindexing on document changes
- **Frontend**: HTML/JavaScript chat interface

---

## Prerequisites & Access Requirements

### Azure Access
✅ **Required:**
- Contributor role on Resource Group
- Ability to create resources (Storage, AI Search, OpenAI, Functions)
- Azure CLI installed and authenticated

❌ **NOT Required:**
- RBAC role assignment permissions (we'll use API keys instead of Managed Identity)
- Subscription Owner access

### Development Environment
- **Python**: 3.11 or higher
- **Node.js**: v18+ (for Azure Functions Core Tools)
- **Azure CLI**: Latest version
- **Git**: For cloning the repository
- **VS Code**: Recommended (with Live Server extension)
- **PowerShell** or **Bash**: For running commands

### Cost Estimate (Monthly)
- Azure AI Search (Basic): ~$75
- Azure OpenAI (Pay-as-you-go): ~$20-100 depending on usage
- Azure Functions (Consumption): ~$0-5
- Blob Storage: ~$1-5
- Event Grid: Free tier covers most usage
- **Total: ~$100-200/month**

---

## Phase 0: Environment Setup

### Step 0.1: Install Required Tools (15 min)

#### Azure CLI
**Windows:**
```powershell
winget install Microsoft.AzureCLI
```

**Mac:**
```bash
brew install azure-cli
```

**Linux:**
```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

**Verify:**
```bash
az --version
```

#### Azure Functions Core Tools
**Windows:**
```powershell
npm install -g azure-functions-core-tools@4 --unsafe-perm true
```

**Mac:**
```bash
brew tap azure/functions
brew install azure-functions-core-tools@4
```

**Verify:**
```bash
func --version
# Should show 4.x.x
```

#### Python 3.11+
Download from [python.org](https://python.org) or:
```bash
# Windows (via winget)
winget install Python.Python.3.11

# Mac
brew install python@3.11
```

**Verify:**
```bash
python --version
# Should show 3.11.x or higher
```

#### Git
```bash
# Windows
winget install Git.Git

# Mac
brew install git
```

**Verify:**
```bash
git --version
```

### Step 0.2: Azure Authentication (5 min)

```bash
# Login to Azure
az login

# If you have multiple subscriptions, list them
az account list --output table

# Set the subscription for your company resource group
az account set --subscription "<subscription-id-or-name>"

# Verify you're in the right subscription
az account show
```

**Checkpoint Test:**
```bash
# Verify you can see your resource group
az group show --name <your-company-resource-group>
```

Expected output: Resource group details including location and provisioning state.

---

## Phase 1: Azure Resource Provisioning

### Step 1.1: Define Variables (5 min)

Create a file `deployment-config.env`:

```bash
# Resource Group (provided by your company)
RESOURCE_GROUP="your-company-rg"
LOCATION="eastus"  # or your preferred region

# Resource Names (must be globally unique)
STORAGE_ACCOUNT="companyragstore$(date +%s)"
SEARCH_SERVICE="company-ai-search"
OPENAI_SERVICE="company-openai-rag"
FUNCTION_APP="company-rag-function"

# Container for documents
CONTAINER_NAME="policy-documents"

# Index name
INDEX_NAME="policy-index"
```

**Important:** Storage account names must be:
- 3-24 characters
- Lowercase letters and numbers only
- Globally unique

Load variables:
```bash
source deployment-config.env  # Linux/Mac
# or
. .\deployment-config.env  # PowerShell
```

### Step 1.2: Create Azure Blob Storage (10 min)

#### Option A: Azure Portal (Recommended for Beginners)

1. **Navigate to Storage Accounts**
   - Go to [Azure Portal](https://portal.azure.com)
   - Click "Create a resource" or search for "Storage accounts"
   - Click "Create"

2. **Configure Basics**
   - **Subscription:** Select your subscription
   - **Resource group:** Select your company resource group
   - **Storage account name:** `companyragstore001` (must be globally unique, 3-24 chars, lowercase/numbers only)
   - **Region:** East US (or your preferred region)
   - **Performance:** Standard
   - **Redundancy:** Locally-redundant storage (LRS)

3. **Advanced Settings** (keep defaults)
   - Click "Next: Advanced"
   - Keep defaults, click "Next: Networking"

4. **Networking** (keep defaults)
   - Keep "Enable public access from all networks" selected
   - Click "Next: Data protection"

5. **Review + Create**
   - Click "Review + create"
   - Click "Create"
   - Wait for deployment to complete (1-2 minutes)

6. **Get Connection String**
   - Go to your Storage Account
   - Left sidebar → **Access keys**
   - Click "Show keys"
   - Copy **Connection string** (key1)
   - Save in your `.env` file as `STORAGE_CONNECTION_STRING`

7. **Create Container**
   - Left sidebar → **Containers**
   - Click "+ Container"
   - **Name:** `policy-documents`
   - **Public access level:** Private (no anonymous access)
   - Click "Create"

#### Option B: Azure CLI

```bash
# Create storage account
az storage account create \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS \
  --kind StorageV2

# Get connection string
STORAGE_CONNECTION_STRING=$(az storage account show-connection-string \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --query connectionString \
  --output tsv)

echo "Storage Connection String: $STORAGE_CONNECTION_STRING"

# Create container for documents
az storage container create \
  --name $CONTAINER_NAME \
  --account-name $STORAGE_ACCOUNT \
  --connection-string "$STORAGE_CONNECTION_STRING"
```

**Checkpoint Test:**

**Portal:**
- Navigate to Storage Account → Containers
- Verify `policy-documents` container exists

**CLI:**
```bash
# Verify container exists
az storage container list \
  --account-name $STORAGE_ACCOUNT \
  --connection-string "$STORAGE_CONNECTION_STRING" \
  --output table
```

Expected output: Table showing your container name.

**Common Errors:**
- **Error: "Storage account name already exists"** → Try a different name (must be globally unique)
- **Error: "Authorization failed"** → Verify Contributor permissions on resource group
- **Portal shows "Deployment failed"** → Check Notifications (bell icon) for specific error message

### Step 1.3: Create Azure AI Search (15 min)

#### Option A: Azure Portal (Recommended)

1. **Navigate to AI Search**
   - In Azure Portal, click "Create a resource"
   - Search for "Azure AI Search"
   - Click "Create"

2. **Configure Basics**
   - **Subscription:** Your subscription
   - **Resource group:** Your company resource group
   - **Service name:** `company-ai-search` (must be globally unique)
   - **Region:** East US (same as your storage account)

3. **Pricing Tier**
   - Click "Change pricing tier"
   - Select **Basic** ($75/month)
   - Click "Select"
   - ⚠️ **Note:** Free tier exists but has severe limitations (50MB storage, 3 indexes)

4. **Scale** (keep defaults)
   - Replicas: 1
   - Partitions: 1
   - Click "Next: Networking"

5. **Networking** (keep defaults)
   - Public endpoint: All networks
   - Click "Next: Tags"

6. **Review + Create**
   - Click "Review + create"
   - Click "Create"
   - Wait for deployment (5-10 minutes)

7. **Get Admin Key**
   - Go to your AI Search service
   - Left sidebar → **Keys**
   - Copy **Primary admin key**
   - Save in `.env` as `SEARCH_ADMIN_KEY`
   - Note the **URL** (e.g., `https://company-ai-search.search.windows.net`)
   - Save in `.env` as `SEARCH_ENDPOINT`

#### Option B: Azure CLI

```bash
# Create AI Search service
az search service create \
  --name $SEARCH_SERVICE \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku basic

# Get admin key
SEARCH_ADMIN_KEY=$(az search admin-key show \
  --service-name $SEARCH_SERVICE \
  --resource-group $RESOURCE_GROUP \
  --query primaryKey \
  --output tsv)

# Construct endpoint
SEARCH_ENDPOINT="https://${SEARCH_SERVICE}.search.windows.net"

echo "Search Endpoint: $SEARCH_ENDPOINT"
echo "Search Admin Key: $SEARCH_ADMIN_KEY"
```

**Checkpoint Test:**

**Portal:**
- Navigate to AI Search service → Overview
- Status should show "Running"
- Click on "Keys" to verify admin key is accessible

**CLI:**
```bash
# Test API access
curl -X GET "$SEARCH_ENDPOINT/indexes?api-version=2024-07-01" \
  -H "api-key: $SEARCH_ADMIN_KEY" \
  -H "Content-Type: application/json"
```

Expected output: `{"@odata.context":"...","value":[]}`

**Common Errors:**
- **Error: "Search service name already exists"** → Try a different name (globally unique)
- **Error: "Quota exceeded"** → Your subscription may have limits; contact Azure support or try different region
- **Error: "Location not available"** → Try westus2, northeurope, or uksouth
- **Portal error: "Pricing tier not available"** → Basic tier requires certain subscription types; try Standard if needed

### Step 1.4: Create Azure OpenAI (20 min)

**Prerequisites:** Azure OpenAI requires special access approval. 

**Request Access (if needed):**
1. Go to [https://aka.ms/oai/access](https://aka.ms/oai/access)
2. Fill out the access request form
3. Wait for approval (usually 1-2 business days)
4. You'll receive email confirmation when approved

#### Option A: Azure Portal (Recommended)

1. **Create Azure OpenAI Resource**
   - In Azure Portal, click "Create a resource"
   - Search for "Azure OpenAI"
   - Click "Create"

2. **Configure Basics**
   - **Subscription:** Your subscription
   - **Resource group:** Your company resource group
   - **Region:** **East US** (critical - not all regions support all models)
   - **Name:** `company-openai-rag`
   - **Pricing tier:** Standard S0

3. **Network** (keep defaults)
   - All networks can access
   - Click "Next: Tags"

4. **Review + Create**
   - Click "Review + create"
   - Click "Create"
   - Wait for deployment (2-3 minutes)

5. **Get Keys and Endpoint**
   - Go to your Azure OpenAI resource
   - Left sidebar → **Keys and Endpoint**
   - Copy **KEY 1** → Save as `OPENAI_KEY` in `.env`
   - Copy **Endpoint** → Save as `OPENAI_ENDPOINT` in `.env`

6. **Deploy Embedding Model**
   - Left sidebar → **Model deployments**
   - Click "Create new deployment" or "Manage Deployments" → Opens Azure AI Studio
   - In Azure AI Studio:
     - Click "+ Create new deployment"
     - **Select model:** text-embedding-ada-002
     - **Deployment name:** `text-embedding-ada-002` (use exact name)
     - **Model version:** Default (2)
     - **Deployment type:** Standard
     - **Tokens per Minute Rate Limit:** 120K (default)
     - Click "Create"
     - Wait for deployment (1-2 minutes)

7. **Deploy GPT-4o Model**
   - Still in Azure AI Studio → Deployments
   - Click "+ Create new deployment"
   - **Select model:** gpt-4o
   - **Deployment name:** `gpt-4o` (use exact name)
   - **Model version:** Latest (2024-08-06 or newer)
   - **Deployment type:** Standard
   - **Tokens per Minute Rate Limit:** 80K (default)
   - Click "Create"
   - Wait for deployment (1-2 minutes)

8. **Verify Deployments**
   - In Deployments tab, you should see:
     - ✅ text-embedding-ada-002 (Status: Succeeded)
     - ✅ gpt-4o (Status: Succeeded)

#### Option B: Azure CLI

```bash
# Create Azure OpenAI resource
az cognitiveservices account create \
  --name $OPENAI_SERVICE \
  --resource-group $RESOURCE_GROUP \
  --location eastus \
  --kind OpenAI \
  --sku S0 \
  --yes

# Get endpoint and key
OPENAI_ENDPOINT=$(az cognitiveservices account show \
  --name $OPENAI_SERVICE \
  --resource-group $RESOURCE_GROUP \
  --query properties.endpoint \
  --output tsv)

OPENAI_KEY=$(az cognitiveservices account keys list \
  --name $OPENAI_SERVICE \
  --resource-group $RESOURCE_GROUP \
  --query key1 \
  --output tsv)

echo "OpenAI Endpoint: $OPENAI_ENDPOINT"
echo "OpenAI Key: $OPENAI_KEY"

# Deploy embedding model
az cognitiveservices account deployment create \
  --name $OPENAI_SERVICE \
  --resource-group $RESOURCE_GROUP \
  --deployment-name text-embedding-ada-002 \
  --model-name text-embedding-ada-002 \
  --model-version "2" \
  --model-format OpenAI \
  --sku-capacity 120 \
  --sku-name "Standard"

# Deploy GPT-4o model
az cognitiveservices account deployment create \
  --name $OPENAI_SERVICE \
  --resource-group $RESOURCE_GROUP \
  --deployment-name gpt-4o \
  --model-name gpt-4o \
  --model-version "2024-08-06" \
  --model-format OpenAI \
  --sku-capacity 80 \
  --sku-name "Standard"
```

**Checkpoint Test:**

**Portal:**
- Navigate to Azure OpenAI → Model deployments
- Verify both deployments show "Succeeded" status
- Click on each deployment to see details and test in playground

**CLI:**
```bash
# Test embedding deployment
curl -X POST "$OPENAI_ENDPOINT/openai/deployments/text-embedding-ada-002/embeddings?api-version=2024-02-15-preview" \
  -H "api-key: $OPENAI_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input": "test"}'
```

Expected output: JSON with embedding array (1536 dimensions).

**Common Errors:**
- **Error: "Access denied"** → Request Azure OpenAI access at aka.ms/oai/access and wait for approval
- **Portal error: "Azure OpenAI not available"** → Access not yet granted; check email for approval
- **Error: "Deployment already exists"** → Delete existing deployment or use unique name
- **Error: "Quota exceeded"** → Reduce token limits (try 60K for gpt-4o, 80K for embeddings) or request quota increase
- **Error: "Model not available in region"** → Use East US; if still failing, try Sweden Central or West Europe
- **Portal: Can't find "Azure OpenAI"** → May be listed as "OpenAI" or "Cognitive Services - OpenAI"

### Step 1.5: Create Azure Function App (15 min)

#### Option A: Azure Portal (Recommended)

1. **Create Storage for Function App**
   - Search for "Storage accounts" → Create
   - **Name:** `funcstore001` (unique name)
   - **Resource group:** Your company resource group
   - **Region:** Same as other resources
   - **Performance:** Standard
   - **Redundancy:** LRS
   - Click "Review + create" → Create

2. **Create Function App**
   - Search for "Function App" → Create
   - Click "Create"

3. **Configure Basics**
   - **Subscription:** Your subscription
   - **Resource group:** Your company resource group
   - **Function App name:** `company-rag-function` (globally unique)
   - **Publish:** Code
   - **Runtime stack:** Python
   - **Version:** 3.11
   - **Region:** Same as other resources (East US)
   - **Operating System:** Linux (required for Python)

4. **Hosting**
   - **Storage account:** Select the `funcstore001` you just created
   - **Plan type:** Consumption (Serverless)
   - Click "Next: Networking"

5. **Networking** (keep defaults)
   - Enable public access
   - Click "Next: Monitoring"

6. **Monitoring**
   - **Enable Application Insights:** Yes (recommended)
   - **Application Insights:** Create new (or select existing)
   - Click "Next: Deployment"

7. **Deployment** (optional, skip for now)
   - GitHub Actions: Disable
   - Click "Next: Tags"

8. **Review + Create**
   - Click "Review + create"
   - Click "Create"
   - Wait for deployment (5-7 minutes)

9. **Verify Function App**
   - Go to Function App resource
   - Overview should show "Running"
   - Note the **URL:** `https://company-rag-function.azurewebsites.net`

#### Option B: Azure CLI

```bash
# Create storage account for Function App
FUNC_STORAGE="funcstore$(date +%s)"
az storage account create \
  --name $FUNC_STORAGE \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS

# Create Function App (Linux, Python 3.11)
az functionapp create \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --storage-account $FUNC_STORAGE \
  --consumption-plan-location $LOCATION \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --os-type Linux
```

**Checkpoint Test:**

**Portal:**
- Navigate to Function App → Overview
- **Status:** Should show "Running"
- **URL:** Click to open (should show default Azure Functions page)

**CLI:**
```bash
# Verify function app is running
az functionapp show \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --query state
```

Expected output: `"Running"`

**Common Errors:**
- **Error: "Function App name not available"** → Try different name (globally unique)
- **Portal: "Python 3.11 not available"** → Select Python 3.10 or 3.9 as fallback
- **Error: "Consumption plan not available in region"** → Try different region
- **Portal: Can't find storage account in dropdown** → Ensure storage account is in same resource group and region

### Step 1.6: Save Configuration (5 min)

Create `.env` file for local development:

```bash
cat > .env << EOF
# Storage
STORAGE_CONNECTION_STRING=$STORAGE_CONNECTION_STRING
STORAGE_ACCOUNT_NAME=$STORAGE_ACCOUNT
CONTAINER_NAME=$CONTAINER_NAME

# Azure AI Search
SEARCH_ENDPOINT=$SEARCH_ENDPOINT
SEARCH_ADMIN_KEY=$SEARCH_ADMIN_KEY

# Azure OpenAI
OPENAI_ENDPOINT=$OPENAI_ENDPOINT
OPENAI_KEY=$OPENAI_KEY
OPENAI_API_KEY=$OPENAI_KEY
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-15-preview
EOF

echo ".env file created successfully"
```

**⚠️ IMPORTANT:** Add `.env` to `.gitignore` to prevent committing secrets!

---

## Phase 2: Code Deployment

### Step 2.1: Clone Repository (5 min)

```bash
# Clone the reference repository
git clone https://github.com/guzailaamer/azure-ai-search-demo.git
cd azure-ai-search-demo

# Create a new branch for your company
git checkout -b company-deployment
```

### Step 2.2: Setup Python Environment (10 min)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows PowerShell:
venv\Scripts\Activate.ps1
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r backend-function/requirements.txt

# Also install development dependencies
pip install azure-storage-blob PyPDF2 pycryptodome python-dotenv
```

**Checkpoint Test:**
```bash
# Verify imports work
python -c "import azure.search.documents; import openai; print('All imports successful')"
```

Expected output: `All imports successful`

### Step 2.3: Configure Local Settings (10 min)

Copy your `.env` values into `backend-function/local.settings.json`:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "STORAGE_CONNECTION_STRING": "<from .env>",
    "STORAGE_ACCOUNT_NAME": "<from .env>",
    "CONTAINER_NAME": "<from .env>",
    "SEARCH_ENDPOINT": "<from .env>",
    "SEARCH_ADMIN_KEY": "<from .env>",
    "OPENAI_ENDPOINT": "<from .env>",
    "OPENAI_KEY": "<from .env>",
    "OPENAI_API_KEY": "<from .env>"
  },
  "Host": {
    "CORS": "*",
    "CORSCredentials": false
  }
}
```

### Step 2.4: Test Function Locally (15 min)

```bash
cd backend-function
func start
```

**Expected Output:**
```
Functions:
  health: [GET] http://localhost:7071/api/health
  query: [POST] http://localhost:7071/api/query
  query_options: [OPTIONS] http://localhost:7071/api/query
  reindex: [POST] http://localhost:7071/api/reindex
```

**Checkpoint Test:**
```powershell
# Test health endpoint
Invoke-WebRequest -Uri "http://localhost:7071/api/health" -UseBasicParsing

# Expected: {"status": "healthy"}
```

**Common Errors:**
- **Error: "Python worker failed to start"** → Verify Python 3.11 is installed and in PATH
- **Error: "Module not found"** → Run `pip install -r requirements.txt` again
- **Error: "Port 7071 already in use"** → Kill existing func.exe process or use different port

Press `Ctrl+C` to stop the function when done testing.

---

## Phase 3: Document Ingestion

### Step 3.1: Create Search Index (10 min)

Navigate to the scripts directory and create the index:

```bash
cd ../scripts  # From backend-function
python create_index.py
```

**Expected Output:**
```
✅ Index 'policy-index' created/updated
```

**What This Does:**
- Creates index schema with vector and keyword fields
- Configures hybrid search (HNSW algorithm for vectors)
- Sets up semantic search capabilities

**Checkpoint Test:**
```bash
# Verify index exists
curl -X GET "$SEARCH_ENDPOINT/indexes/policy-index?api-version=2024-07-01" \
  -H "api-key: $SEARCH_ADMIN_KEY"
```

Expected: JSON schema of your index.

**Common Errors:**
- **Error: "Index already exists"** → Either delete and recreate, or ignore (it will update)
- **Error: "Invalid vector dimensions"** → Ensure you're using text-embedding-ada-002 (1536 dimensions)

### Step 3.2: Upload Policy Documents (10 min)

#### Option A: Azure Portal (Easiest for Small Batches)

1. **Navigate to Storage Account**
   - Go to your Storage Account
   - Left sidebar → **Containers**
   - Click on `policy-documents` container

2. **Upload Files**
   - Click **Upload** button (top toolbar)
   - Click **Browse for files** or drag-and-drop PDFs
   - Select your policy documents (PDF files)
   - **Advanced options** (optional):
     - Blob type: Block blob (default)
     - Block size: Default
   - Click **Upload**
   - Wait for upload to complete
   - You'll see files listed in the container

3. **Verify Upload**
   - Files should appear in the container with "Modified" timestamp
   - Click on a file to see details (size, content type, etc.)

**Tips:**
- Upload up to 200 files at once
- Supported formats: PDF (recommended), DOCX, TXT
- Max file size: 50GB per file
- Organize with folder prefixes if needed (e.g., `HR/policy.pdf`)

#### Option B: Azure CLI (Best for Bulk Upload)

```bash
# Upload a single file
az storage blob upload \
  --account-name $STORAGE_ACCOUNT \
  --container-name $CONTAINER_NAME \
  --name "employee-handbook.pdf" \
  --file "/path/to/employee-handbook.pdf" \
  --connection-string "$STORAGE_CONNECTION_STRING"

# Upload multiple files from a directory
for file in /path/to/policies/*.pdf; do
  filename=$(basename "$file")
  az storage blob upload \
    --account-name $STORAGE_ACCOUNT \
    --container-name $CONTAINER_NAME \
    --name "$filename" \
    --file "$file" \
    --connection-string "$STORAGE_CONNECTION_STRING"
done
```

#### Option C: Azure Storage Explorer (Best for Large Batches)

1. **Download Azure Storage Explorer**
   - Download from: https://azure.microsoft.com/features/storage-explorer/
   - Install and launch

2. **Connect to Your Storage Account**
   - Click "Add an account" or connection icon
   - Select "Storage account or service"
   - Choose "Connection string"
   - Paste your storage connection string
   - Click "Next" → "Connect"

3. **Upload Files**
   - Navigate to your storage account → Blob Containers → `policy-documents`
   - Click "Upload" → "Upload Files"
   - Select multiple files (supports 1000+ files)
   - Click "Upload"
   - Monitor progress in Activities panel

**Checkpoint Test:**

**Portal:**
- Navigate to Storage Account → Containers → `policy-documents`
- Verify all files are listed
- Check file count matches what you uploaded

**CLI:**
```bash
# List uploaded files
az storage blob list \
  --account-name $STORAGE_ACCOUNT \
  --container-name $CONTAINER_NAME \
  --connection-string "$STORAGE_CONNECTION_STRING" \
  --output table
```

**Common Errors:**
- **Portal: "Upload failed"** → Check file size (<50GB), network connection
- **Error: "Authentication failed"** → Verify connection string is correct
- **Files don't appear** → Refresh browser; check you're in correct container
- **Large files timing out** → Use Azure Storage Explorer or AzCopy for files >1GB

### Step 3.3: Index Documents (20-60 min depending on size)

```bash
cd scripts
python process_documents.py
```

**Expected Output:**
```
Processing employee-handbook.pdf...
✅ Indexed 245 chunks from employee-handbook.pdf
Processing benefits-policy.pdf...
✅ Indexed 128 chunks from benefits-policy.pdf
...
✅ All documents indexed!
```

**What This Does:**
- Reads PDFs from Blob Storage
- Extracts text using PyPDF2
- Chunks text (1000 chars, 100 char overlap)
- Generates embeddings via Azure OpenAI
- Uploads to Azure AI Search index

**Performance:**
- ~10-15 chunks per minute
- 1000-page document ≈ 1500 chunks ≈ 2 hours

**Checkpoint Test:**
```bash
# Check index document count via API
curl -X GET "$SEARCH_ENDPOINT/indexes/policy-index/stats?api-version=2024-07-01" \
  -H "api-key: $SEARCH_ADMIN_KEY"
```

Expected: `"documentCount": <number>` matching your chunks.

**Common Errors:**
- **Error: "PyCryptodome required"** → `pip install pycryptodome`
- **Error: "Rate limit exceeded"** → Slow down embedding requests (add sleep)
- **Error: "Invalid document key"** → Ensure IDs don't contain `.` or special chars
- **Error: "Timeout"** → Large documents may time out; process in batches

---

## Phase 4: Query Pipeline Setup

### Step 4.1: Deploy Function to Azure (15 min)

```bash
cd ../backend-function
func azure functionapp publish $FUNCTION_APP
```

**Expected Output:**
```
Deployment successful.
Functions in <your-function-app>:
    health - [httpTrigger]
        Invoke url: https://<function-app>.azurewebsites.net/api/health
    query - [httpTrigger]
        Invoke url: https://<function-app>.azurewebsites.net/api/query
    reindex - [httpTrigger]
        Invoke url: https://<function-app>.azurewebsites.net/api/reindex
```

### Step 4.2: Configure Function App Settings (10 min)

After deploying your function code, you need to add environment variables (application settings) to the Function App in Azure.

#### Option A: Azure Portal (Recommended)

1. **Navigate to Function App**
   - Go to your Function App resource
   - Left sidebar → **Environment variables** (or **Configuration** in older portal)

2. **Add Application Settings**
   - Click **+ Add** (or **+ New application setting**)
   - Add each setting below:

   | Name | Value (from your .env file) |
   |------|----------------------------|
   | `STORAGE_CONNECTION_STRING` | Your storage connection string |
   | `STORAGE_ACCOUNT_NAME` | Your storage account name |
   | `CONTAINER_NAME` | `policy-documents` |
   | `SEARCH_ENDPOINT` | `https://your-search.search.windows.net` |
   | `SEARCH_ADMIN_KEY` | Your search admin key |
   | `OPENAI_ENDPOINT` | Your OpenAI endpoint |
   | `OPENAI_KEY` | Your OpenAI key |
   | `OPENAI_API_KEY` | Same as OPENAI_KEY |

3. **Save Changes**
   - Click **Apply** at the bottom
   - Click **Confirm** when prompted
   - Wait for settings to apply (30-60 seconds)
   - Function app will restart automatically

4. **Verify Settings**
   - Settings should now appear in the list
   - ⚠️ **Security:** Keys are hidden by default (shown as `****`)
   - Click "Show values" to verify if needed

**Tips:**
- Copy-paste carefully to avoid trailing spaces
- Use "Bulk edit" if you prefer JSON format
- Settings are encrypted at rest automatically

#### Option B: Azure CLI

```bash
az functionapp config appsettings set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --settings \
    STORAGE_CONNECTION_STRING="$STORAGE_CONNECTION_STRING" \
    STORAGE_ACCOUNT_NAME="$STORAGE_ACCOUNT" \
    CONTAINER_NAME="$CONTAINER_NAME" \
    SEARCH_ENDPOINT="$SEARCH_ENDPOINT" \
    SEARCH_ADMIN_KEY="$SEARCH_ADMIN_KEY" \
    OPENAI_ENDPOINT="$OPENAI_ENDPOINT" \
    OPENAI_KEY="$OPENAI_KEY" \
    OPENAI_API_KEY="$OPENAI_KEY"
```

**Checkpoint Test:**

**Portal:**
- Navigate to Function App → Environment variables
- Verify all 8 settings are present
- Click "Show values" and spot-check one value matches your .env

**CLI:**
```bash
# List all settings (values will be shown)
az functionapp config appsettings list \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --output table
```

**Common Errors:**
- **Function fails after adding settings** → Check for typos in setting names (case-sensitive)
- **Portal: "Failed to update settings"** → Refresh and try again; may be temporary
- **Environment variables not working** → Ensure function app restarted (stop/start if needed)

### Step 4.3: Configure CORS (5 min)

CORS (Cross-Origin Resource Sharing) allows your frontend to call the Function API from a different domain/origin.

#### Option A: Azure Portal (Recommended)

1. **Navigate to CORS Settings**
   - Go to your Function App
   - Left sidebar → **CORS** (under API section)

2. **Add Allowed Origins**
   
   **For Development/Testing:**
   - Click in the "Allowed Origins" text box
   - Add: `*` (allows all origins)
   - Click **Save**
   
   **For Production (Recommended):**
   - Remove `*` if present
   - Add specific origins:
     - `https://company.com`
     - `https://intranet.company.com`
     - `http://localhost:5500` (for local testing)
     - `http://127.0.0.1:5500` (for local testing)
   - Click **Save**

3. **Verify Settings**
   - Allowed origins should be listed
   - "Enable Access-Control-Allow-Credentials" should be unchecked (unless you need it)

**Important Security Notes:**
- ⚠️ `*` (wildcard) allows ANY website to call your API
- ✅ For production, use specific domains only
- ✅ Always use HTTPS in production origins

#### Option B: Azure CLI

**For Development (allow all):**
```bash
az functionapp cors add \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --allowed-origins "*"
```

**For Production (specific domains):**
```bash
# Remove all origins first
az functionapp cors remove \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --allowed-origins "*"

# Add specific origins
az functionapp cors add \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --allowed-origins \
    "https://company.com" \
    "https://intranet.company.com" \
    "http://localhost:5500"
```

**Checkpoint Test:**

**Portal:**
- Navigate to Function App → CORS
- Verify allowed origins are listed
- Test by opening frontend and making a query

**CLI:**
```bash
# Show CORS settings
az functionapp cors show \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP
```

Expected output: JSON with `allowedOrigins` array.

**Test CORS is Working:**
1. Open frontend in browser (via Live Server)
2. Open browser console (F12)
3. Send a test query
4. Should NOT see CORS errors
5. If you see "CORS policy" error → check origins match exactly (including http/https)

**Common Errors:**
- **Error: "CORS policy blocked"** → Ensure frontend origin is in allowed origins list
- **Portal: Changes not applying** → Wait 30 seconds and refresh; may need function restart
- **localhost vs 127.0.0.1** → Add both to allowed origins; browsers treat them differently
- **http vs https mismatch** → Ensure protocol matches (use https in production)

**Checkpoint Test:**
```bash
# Get Function URL
FUNCTION_URL=$(az functionapp function show \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --function-name query \
  --query invokeUrlTemplate \
  --output tsv)

# Test query endpoint
curl -X POST "$FUNCTION_URL" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the vacation policy?"}'
```

Expected: JSON response with answer and citations.

**Common Errors:**
- **Error: "500 Internal Server Error"** → Check Function logs in Portal
- **Error: "Module not found"** → Ensure requirements.txt includes all dependencies
- **Error: "CORS blocked"** → Verify CORS settings are applied

---

## Phase 5: Frontend Deployment

### Step 5.1: Update Frontend Configuration (5 min)

Edit `frontend.html`:

```javascript
// Change this line to your deployed function URL
const API_URL = 'https://<your-function-app>.azurewebsites.net/api/query';
```

Replace `<your-function-app>` with your actual function app name.

### Step 5.2: Test Frontend Locally (10 min)

**Using VS Code Live Server:**
1. Install "Live Server" extension in VS Code
2. Right-click `frontend.html`
3. Select "Open with Live Server"
4. Opens at `http://127.0.0.1:5500/frontend.html`

**Using Python:**
```bash
cd ..  # Back to repo root
python -m http.server 8000
# Open http://localhost:8000/frontend.html
```

**Checkpoint Test:**
- Ask: "What is our company's remote work policy?"
- Verify you get an answer with citations

### Step 5.3: Deploy Frontend to Azure Static Web Apps (Optional, 20 min)

For a production deployment:

```bash
# Create Static Web App
az staticwebapp create \
  --name company-rag-frontend \
  --resource-group $RESOURCE_GROUP \
  --location eastus2 \
  --source https://github.com/your-org/your-repo \
  --branch main \
  --app-location "/" \
  --output-location "/" \
  --login-with-github
```

**Alternative:** Host on company intranet/SharePoint.

---

## Phase 6: Auto-Reindexing with Event Grid

### Step 6.1: Create Event Grid Subscription (10 min)

Event Grid will automatically trigger reindexing whenever a document is added, modified, or deleted in Blob Storage.

#### Option A: Azure Portal (Recommended - Visual & Easier)

1. **Navigate to Storage Account Events**
   - Go to your **Storage Account** resource
   - Left sidebar → **Events**
   - You'll see the Events overview page

2. **Create Event Subscription**
   - Click **+ Event Subscription** (top toolbar)

3. **Configure Event Subscription - Basics Tab**
   
   **Event Subscription Details:**
   - **Name:** `policy-reindex-subscription`
   - **Event Schema:** Event Grid Schema (default)
   - **System Topic Name:** `storage-events-topic` (will be created automatically)
   
   **Event Types:**
   - Scroll down to "Filter to Event Types"
   - **Check these boxes:**
     - ☑️ Blob Created
     - ☑️ Blob Deleted (optional - to clean up deleted docs from index)
   - Uncheck all others

4. **Configure Endpoint**
   
   Scroll to "Endpoint Details" section:
   - **Endpoint Type:** Select **Web Hook** from dropdown
   - Click **Select an endpoint**
   
   In the "Select Web Hook" panel:
   - **Subscriber Endpoint:** Paste your function URL:
     ```
     https://<your-function-app>.azurewebsites.net/api/reindex
     ```
     Replace `<your-function-app>` with your actual function app name
   - Click **Confirm Selection**

5. **Configure Filters (Optional but Recommended)**
   
   Click **Filters** tab:
   
   **Subject Filters:**
   - **Subject Begins With:** `/blobServices/default/containers/policy-documents/`
     - This ensures only events from your policy container trigger the function
   - **Subject Ends With:** `.pdf`
     - This ensures only PDF files trigger reindexing (optional)
   
   **Advanced Filters:** (skip for now)

6. **Review and Create**
   - Click **Create** button at bottom
   - Wait for deployment (30-60 seconds)

7. **Validation Process**
   - Event Grid will send a validation request to your function
   - Your function will respond automatically
   - Status will change from "Creating" to "Provisioning" to **"Succeeded"**
   - This may take 1-2 minutes

8. **Verify Subscription**
   - Go back to Storage Account → Events
   - Click on **Event Subscriptions** tab
   - You should see `policy-reindex-subscription`
   - **Provisioning state:** Should show **Succeeded** (green checkmark)
   - **Active:** Should show **Yes**

**Troubleshooting Validation:**

If status shows "AwaitingManualAction":
1. Go to Function App → Log stream (left sidebar)
2. Check for validation errors
3. Common fix: Delete subscription and recreate
4. Ensure function is deployed and running

#### Option B: Azure CLI

First, get your subscription ID:
```bash
SUBSCRIPTION_ID=$(az account show --query id --output tsv)
```

Create Event Grid subscription:
```bash
# Get Function URL
REINDEX_URL="https://${FUNCTION_APP}.azurewebsites.net/api/reindex"

# Create Event Grid subscription
az eventgrid event-subscription create \
  --name policy-reindex-subscription \
  --source-resource-id "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT" \
  --endpoint-type webhook \
  --endpoint $REINDEX_URL \
  --included-event-types Microsoft.Storage.BlobCreated Microsoft.Storage.BlobDeleted \
  --subject-begins-with /blobServices/default/containers/$CONTAINER_NAME/ \
  --subject-ends-with .pdf
```

**Checkpoint Test:**

**Portal Method:**
1. Wait 1-2 minutes after creation
2. Navigate to Storage Account → Events → Event Subscriptions
3. Check status:
   - ✅ **Provisioning State:** Succeeded
   - ✅ **Active:** Yes
4. Click on subscription name to see details

**CLI Method:**
```bash
# Check subscription status
az eventgrid event-subscription show \
  --name policy-reindex-subscription \
  --source-resource-id "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT" \
  --query provisioningState
```

Expected output: `"Succeeded"`

**Visual Verification in Portal:**
- Storage Account → Events → Event Subscriptions
- Should see your subscription with green checkmark
- Click on it to see:
  - Endpoint URL (your function)
  - Event types (BlobCreated, BlobDeleted)
  - Filters configured
  - Delivery metrics (after testing)

**Common Errors:**

| Error | Cause | Solution (Portal) | Solution (CLI) |
|-------|-------|------------------|----------------|
| "AwaitingManualAction" | Validation failed | Check Function logs; delete & recreate subscription | Check endpoint URL is correct |
| "Endpoint not found" | Wrong URL | Verify function deployed; check URL has `/api/reindex` | Verify `$FUNCTION_APP` variable |
| "No events firing" | Wrong filters | Remove subject filters temporarily | Check `--subject-begins-with` path |
| Can't find Function in dropdown | Using wrong endpoint type | Use "Web Hook" not "Azure Function" | N/A - use webhook endpoint type |
| "Forbidden" error | Function auth issue | Ensure function allows anonymous access | Check function auth settings |

**Next:** Test the auto-reindexing in Step 6.2

### Step 6.2: Test Auto-Reindexing (10 min)

Now let's verify that Event Grid automatically triggers reindexing when you upload a document.

#### Test via Azure Portal

1. **Open Function Logs (First)**
   - Go to your **Function App** resource
   - Left sidebar → **Log stream**
   - Keep this window open (you'll see live logs)
   - Wait for "Connected!" message

2. **Upload a Test Document**
   - Open a **new browser tab/window**
   - Navigate to **Storage Account → Containers → policy-documents**
   - Click **Upload** button
   - Select a PDF file (use a small test file for faster processing)
   - Click **Upload**
   - Wait for upload to complete

3. **Monitor Function Logs**
   - Switch back to the **Log stream** tab
   - Within 30-60 seconds, you should see:
   
   ```
   [timestamp] Executing 'Functions.reindex'
   [timestamp] Reindex endpoint hit.
   [timestamp] Processing blob: your-test-file.pdf
   [timestamp] Deleted X old chunks for your-test-file.pdf
   [timestamp] ✅ Reindexed Y chunks from your-test-file.pdf
   [timestamp] Executed 'Functions.reindex' (Succeeded, Duration=XYZms)
   ```

4. **Verify in AI Search**
   - Go to **AI Search** resource
   - Left sidebar → **Indexes**
   - Click on `policy-index`
   - Click **Search explorer** button
   - Search for: `your-test-file` (without .pdf extension)
   - You should see chunks from your newly uploaded document

5. **Test in Frontend**
   - Open your frontend (via Live Server)
   - Ask a question about the content in the test document
   - Verify you get an answer with citations showing your document

#### Test Document Deletion

1. **Delete Test Document**
   - Go to Storage Account → Containers → policy-documents
   - Find your test document
   - Click the **...** (more options) menu
   - Click **Delete**
   - Confirm deletion

2. **Check Function Logs**
   - Should see:
   ```
   [timestamp] Processing blob: your-test-file.pdf
   [timestamp] Deleted chunks for your-test-file.pdf
   [timestamp] Executed 'Functions.reindex' (Succeeded)
   ```

3. **Verify in AI Search**
   - Search explorer → search for your test file
   - Should return 0 results (chunks removed)

#### Troubleshooting - No Events Firing

**Check Event Grid Metrics:**
1. Go to **Storage Account → Events → Event Subscriptions**
2. Click on `policy-reindex-subscription`
3. Look at **Metrics** tab:
   - **Publish Succeeded:** Should increase when you upload
   - **Delivery Succeeded:** Should increase if function processed it
   - **Delivery Failed:** Investigate if this increases

**Check Function Invocations:**
1. Go to **Function App → Functions**
2. Click on `reindex` function
3. Click **Monitor** tab
4. Look for recent invocations
5. Click on an invocation to see details/logs

**Common Issues:**

| Symptom | Cause | Fix |
|---------|-------|-----|
| No logs appear at all | Event Grid not triggering | Check subscription status is "Succeeded"; verify filters |
| Logs show "Reindex endpoint hit" but error | Missing env variables | Check Function App environment variables |
| "Processing blob" but then error | Issue with document or code | Check full error in logs; verify PDF is valid |
| Works for first upload, not subsequent | Duplicate event handling issue | This is normal; function handles duplicates |
| Event Grid shows "Delivery Failed" | Function returned error | Check function logs for specific error |

**Detailed Logging:**

For more detailed debugging, view **Application Insights:**
1. Go to Function App → Application Insights
2. Click on **Logs** (left sidebar)
3. Run query:
   ```kusto
   traces
   | where timestamp > ago(1h)
   | where message contains "reindex"
   | order by timestamp desc
   ```

#### Performance Metrics

**Expected timing:**
- Event Grid latency: 30-60 seconds from upload to trigger
- Small PDF (10 pages): ~30 seconds to reindex
- Medium PDF (100 pages): ~3-5 minutes to reindex
- Large PDF (500 pages): ~15-25 minutes to reindex

**Monitor in Portal:**
- Function App → Overview → Shows invocation count
- AI Search → Overview → Shows document count (updates after reindex)
- Storage Account → Metrics → Monitor blob operations

**Success Indicators:**
- ✅ Function logs show "✅ Reindexed X chunks"
- ✅ AI Search document count increased by X
- ✅ Frontend returns answers about new document
- ✅ Event Grid metrics show delivery succeeded

---

## Policy Document Considerations

### Document Format Requirements

**Supported Formats:**
- ✅ PDF (preferred for policies)
- ✅ DOCX (requires additional code - see Appendix)
- ✅ TXT

**PDF Best Practices:**
- ✅ **Text-based PDFs** (not scanned images)
- ✅ Well-structured with headings
- ✅ Searchable text
- ❌ Avoid password-protected PDFs (requires extra handling)
- ❌ Avoid image-only PDFs (requires OCR - see Production Refinements)

### Content Structure

**For Best Results:**
1. **Clear Headings:** Use H1, H2 hierarchy
2. **Section Numbers:** "5.2.1 Remote Work Eligibility"
3. **Metadata:** Include policy version, effective date
4. **Consistent Formatting:** Use templates

### Chunking Strategy for Policies

Current default: 1000 characters with 100-character overlap.

**Policy-Specific Tuning:**

```python
# In process_documents.py or reindex function
def chunk_text(text: str, chunk_size: int = 1500, overlap: int = 200):
    # Larger chunks preserve policy context
    # More overlap prevents losing cross-references
```

**Recommended for Policies:**
- **Short policies (<10 pages):** 1500 chars, 200 overlap
- **Long policies (>50 pages):** 1000 chars, 150 overlap
- **Legal documents:** 2000 chars, 300 overlap (preserve legal context)

### Metadata Extraction

**Enhanced Indexing for Policies:**

Add custom fields to index schema:

```python
# In create_index.py
fields = [
    SimpleField(name="id", type="Edm.String", key=True),
    SearchableField(name="content", type="Edm.String"),
    SearchableField(name="title", type="Edm.String"),
    SimpleField(name="metadata_storage_name", type="Edm.String", filterable=True),
    
    # Policy-specific fields
    SimpleField(name="policy_version", type="Edm.String", filterable=True),
    SimpleField(name="effective_date", type="Edm.DateTimeOffset", filterable=True, sortable=True),
    SimpleField(name="department", type="Edm.String", filterable=True, facetable=True),
    SimpleField(name="policy_type", type="Edm.String", filterable=True, facetable=True),
    
    SearchField(name="contentVector", type="Collection(Edm.Single)", ...),
]
```

Extract from filename or PDF metadata:
```python
# Example: "HR-Remote-Work-Policy-v2.1-2025-01-15.pdf"
def extract_policy_metadata(filename):
    parts = filename.replace('.pdf', '').split('-')
    return {
        "department": parts[0],  # "HR"
        "policy_type": parts[1],  # "Remote"
        "policy_version": parts[-2],  # "v2.1"
        "effective_date": parts[-1]  # "2025-01-15"
    }
```

### Access Control & Security

**Current Implementation:** No access control (all indexed documents visible to all users)

**For Production (see Refinements):**

1. **Azure Entra ID Authentication:**
   - Require login to access frontend
   - Pass user identity to query function

2. **Document-Level Security:**
   ```python
   # Add security field to index
   SimpleField(name="allowed_groups", type="Collection(Edm.String)", filterable=True)
   
   # Filter queries by user's group membership
   filter=f"allowed_groups/any(g: g eq '{user_group}')"
   ```

3. **Audit Logging:**
   - Log all queries with user ID and timestamp
   - Track document access patterns

### Compliance Considerations

**Data Residency:**
- Choose Azure region matching your compliance requirements
- EU data: West Europe or North Europe
- US data: East US, West US
- Configure region when creating resources

**Data Retention:**
- Policy documents in Blob Storage: Set lifecycle policies
- Search index: No automatic deletion - manage manually
- Function logs: Default 30 days (configure in Application Insights)

**Sensitive Data:**
- ⚠️ Current implementation indexes ALL text
- ⚠️ No PII redaction or masking
- **For Production:** Implement PII detection and redaction (see Refinements)

---

## Common Errors & Troubleshooting

### Azure Resource Provisioning

| Error | Cause | Solution |
|-------|-------|----------|
| "Resource name already exists" | Name is taken globally | Add unique suffix: `company-rag-$(date +%s)` |
| "Authorization failed" | Insufficient permissions | Verify Contributor role on resource group |
| "Quota exceeded" | Subscription limits | Request quota increase via Azure Support |
| "Region not available" | Service not in region | Try eastus, westus2, or northeurope |
| "OpenAI access denied" | No Azure OpenAI access | Request at aka.ms/oai/access |

### Document Indexing

| Error | Cause | Solution |
|-------|-------|----------|
| "PyCryptodome required" | Encrypted PDF | `pip install pycryptodome` |
| "Invalid document key" | Key contains `.` | Replace dots: `filename.replace('.', '_')` |
| "Rate limit exceeded" | Too many API calls | Add `time.sleep(0.1)` between embeddings |
| "Timeout" | Large document | Process in smaller batches |
| "ModuleNotFoundError" | Missing dependency | `pip install -r requirements.txt` |
| "Collection(Edm.Double) mismatch" | Type error in skillset | Use manual Python ingestion instead |

### Query Function

| Error | Cause | Solution |
|-------|-------|----------|
| "500 Internal Server Error" | Missing env variable | Check Function App Settings in Portal |
| "DeploymentNotFound" | Wrong model name | Verify deployment name matches code |
| "CORS blocked" | CORS not configured | Run `az functionapp cors add` |
| "No module named 'azure.storage'" | Missing in requirements.txt | Add `azure-storage-blob` to requirements.txt |
| "OpenAI API error" | Wrong API key or endpoint | Verify OPENAI_KEY and OPENAI_ENDPOINT |

### Event Grid

| Error | Cause | Solution |
|-------|-------|----------|
| "AwaitingManualAction" | Validation failed | Check function logs; ensure validation response is correct |
| "No events firing" | Wrong event types | Verify "Microsoft.Storage.BlobCreated" is selected |
| "403 Forbidden" | Authentication issue | Ensure function allows anonymous access |
| "Endpoint not reachable" | Function not deployed | Deploy function first, then create subscription |

### Frontend

| Error | Cause | Solution |
|-------|-------|----------|
| "Failed to fetch" | CORS issue | Use Live Server, not direct file open; check CORS config |
| "404 Not Found" | Wrong API URL | Verify API_URL in frontend.html matches deployed function |
| "No response" | Function not running | Check function status in Azure Portal |

---

## Production Refinements

### 1. Enhanced Document Processing

#### OCR for Scanned PDFs

```python
# Add to requirements.txt
# azure-ai-vision==0.15.0

from azure.ai.vision import VisionServiceOptions, VisionSource
from azure.ai.vision.imageanalysis import ImageAnalyzer

def extract_text_from_scanned_pdf(pdf_path):
    # Use Azure Computer Vision OCR
    vision_service = VisionServiceOptions(
        os.getenv("VISION_ENDPOINT"),
        os.getenv("VISION_KEY")
    )
    
    # Process each page as image
    # Extract text with OCR
    # Combine into full text
    pass
```

#### Multi-Format Support

```python
def extract_text(blob_name: str, blob_data: bytes) -> str:
    if blob_name.endswith('.pdf'):
        return extract_text_from_pdf(blob_data)
    elif blob_name.endswith('.docx'):
        return extract_text_from_docx(blob_data)
    elif blob_name.endswith('.txt'):
        return blob_data.decode('utf-8')
    elif blob_name.endswith('.html'):
        return extract_text_from_html(blob_data)
    else:
        raise ValueError(f"Unsupported format: {blob_name}")

def extract_text_from_docx(blob_data: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(blob_data))
    return "\n".join([para.text for para in doc.paragraphs])
```

### 2. Improved Search Quality

#### Semantic Ranker

Enable in AI Search (requires Standard tier or higher):

```python
# In search query
results = search_client.search(
    search_text=query,
    vector_queries=[vector_query],
    query_type="semantic",
    semantic_configuration_name="my-semantic-config",
    top=10
)
```

#### Query Expansion

```python
def expand_query(original_query: str) -> str:
    """Use GPT to generate related search terms"""
    prompt = f"Given this query: '{original_query}', list 3-5 related search terms."
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=50
    )
    expanded = response.choices[0].message.content
    return f"{original_query} {expanded}"
```

#### Re-ranking

```python
def rerank_results(query: str, results: list) -> list:
    """Re-rank search results based on relevance"""
    # Use a cross-encoder model or GPT-4o to score relevance
    for result in results:
        score_prompt = f"Rate relevance of this text to query '{query}': {result['content'][:500]}"
        # Get score from model
        # Sort by new scores
    return sorted_results
```

### 3. Authentication & Authorization

#### Azure Entra ID (formerly Azure AD)

**Frontend:**
```javascript
// Use MSAL.js for authentication
import { PublicClientApplication } from "@azure/msal-browser";

const msalConfig = {
    auth: {
        clientId: "<your-app-id>",
        authority: "https://login.microsoftonline.com/<tenant-id>",
        redirectUri: window.location.origin
    }
};

const msalInstance = new PublicClientApplication(msalConfig);

// Get token
const tokenResponse = await msalInstance.acquireTokenSilent({
    scopes: ["<api-scope>"]
});

// Include in API call
fetch(API_URL, {
    headers: {
        'Authorization': `Bearer ${tokenResponse.accessToken}`
    }
});
```

**Backend:**
```python
# In function_app.py
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureSasCredential

def validate_token(req: func.HttpRequest):
    auth_header = req.headers.get('Authorization')
    if not auth_header:
        return None
    
    token = auth_header.replace('Bearer ', '')
    # Validate token against Azure AD
    # Extract user claims
    return user_info
```

#### Row-Level Security

```python
# Add user groups to index
SimpleField(name="allowed_users", type="Collection(Edm.String)", filterable=True),
SimpleField(name="allowed_groups", type="Collection(Edm.String)", filterable=True),

# Filter search by user permissions
def search_documents(query: str, user_id: str, user_groups: list):
    filter_clause = f"allowed_users/any(u: u eq '{user_id}') or allowed_groups/any(g: search.in(g, '{','.join(user_groups)}'))"
    
    results = search_client.search(
        search_text=query,
        filter=filter_clause,
        ...
    )
```

### 4. Monitoring & Analytics

#### Application Insights

```bash
# Create Application Insights
az monitor app-insights component create \
  --app company-rag-insights \
  --location $LOCATION \
  --resource-group $RESOURCE_GROUP

# Get instrumentation key
APPINSIGHTS_KEY=$(az monitor app-insights component show \
  --app company-rag-insights \
  --resource-group $RESOURCE_GROUP \
  --query instrumentationKey \
  --output tsv)

# Configure Function App
az functionapp config appsettings set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --settings APPINSIGHTS_INSTRUMENTATIONKEY=$APPINSIGHTS_KEY
```

**Custom Metrics:**
```python
from applicationinsights import TelemetryClient

telemetry = TelemetryClient(os.getenv('APPINSIGHTS_INSTRUMENTATIONKEY'))

# Track custom events
telemetry.track_event('QueryProcessed', {
    'query': user_query,
    'user_id': user_id,
    'results_count': len(search_results),
    'latency_ms': latency
})

# Track metrics
telemetry.track_metric('SearchLatency', latency)
telemetry.flush()
```

#### Query Analytics Dashboard

Create custom queries in Application Insights:

```kusto
// Most common queries
customEvents
| where name == "QueryProcessed"
| summarize count() by tostring(customDimensions.query)
| top 20 by count_

// Average latency by hour
customMetrics
| where name == "SearchLatency"
| summarize avg(value) by bin(timestamp, 1h)

// User engagement
customEvents
| where name == "QueryProcessed"
| summarize users=dcount(customDimensions.user_id) by bin(timestamp, 1d)
```

### 5. Cost Optimization

#### Caching Frequent Queries

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
def cached_search(query_hash: str, query: str):
    return search_documents(query)

def query_with_cache(query: str):
    query_hash = hashlib.md5(query.encode()).hexdigest()
    return cached_search(query_hash, query)
```

Or use Azure Redis Cache:

```python
import redis

cache = redis.Redis(
    host=os.getenv('REDIS_HOST'),
    port=6380,
    password=os.getenv('REDIS_KEY'),
    ssl=True
)

def search_with_redis_cache(query: str):
    cached = cache.get(f"query:{query}")
    if cached:
        return json.loads(cached)
    
    results = search_documents(query)
    cache.setex(f"query:{query}", 3600, json.dumps(results))  # Cache for 1 hour
    return results
```

#### Reduce Embedding Costs

```python
# Only re-embed changed chunks
def get_chunk_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()

def reindex_document_optimized(blob_name: str):
    # Download and chunk document
    new_chunks = chunk_text(text)
    
    # Get existing chunks
    existing = search_client.search(filter=f"metadata_storage_name eq '{blob_name}'")
    existing_hashes = {doc['id']: get_chunk_hash(doc['content']) for doc in existing}
    
    # Only embed new/changed chunks
    for i, chunk in enumerate(new_chunks):
        chunk_id = make_safe_id(blob_name, i)
        chunk_hash = get_chunk_hash(chunk)
        
        if chunk_id in existing_hashes and existing_hashes[chunk_id] == chunk_hash:
            # Chunk unchanged, skip embedding
            continue
        
        # Generate embedding only for new/changed chunks
        embedding = get_embedding(chunk)
        # Index
```

### 6. Advanced Features

#### Conversation Memory

```python
# Store conversation history in session
conversation_history = []

def query_with_context(user_query: str, conversation_history: list):
    # Include previous Q&A in context
    context = "\n".join([
        f"Q: {item['query']}\nA: {item['answer']}"
        for item in conversation_history[-3:]  # Last 3 turns
    ])
    
    enhanced_prompt = f"""Previous conversation:
{context}

Current question: {user_query}
"""
    
    # Search and generate answer
    answer = generate_answer(enhanced_prompt, search_results)
    
    # Store in history
    conversation_history.append({
        'query': user_query,
        'answer': answer
    })
    
    return answer
```

#### Multi-Modal Search

```python
# Search by uploading an image of a policy document page
from azure.ai.vision import ImageAnalyzer

def search_by_image(image_data: bytes):
    # Extract text from image using OCR
    vision_analyzer = ImageAnalyzer(...)
    extracted_text = vision_analyzer.analyze(image_data)
    
    # Use extracted text as search query
    return search_documents(extracted_text)
```

#### Follow-Up Questions

```python
def generate_followup_questions(query: str, answer: str) -> list:
    prompt = f"""Based on this Q&A, suggest 3 follow-up questions:
Question: {query}
Answer: {answer}

Suggested questions:"""
    
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150
    )
    
    suggestions = response.choices[0].message.content.split('\n')
    return [q.strip() for q in suggestions if q.strip()]
```

---

## Testing Checklist

### Pre-Deployment Testing

- [ ] All Azure resources created successfully
- [ ] Connection strings and keys saved in `.env`
- [ ] Python environment activated with all dependencies
- [ ] Local function starts without errors
- [ ] Health endpoint returns 200
- [ ] Sample document uploaded to Blob Storage
- [ ] Index created in AI Search
- [ ] Document processed and indexed successfully
- [ ] Local query test returns results
- [ ] Frontend loads without errors
- [ ] Query from frontend returns answer with citations

### Post-Deployment Testing

- [ ] Function deployed to Azure successfully
- [ ] Function environment variables configured
- [ ] CORS configured and working
- [ ] Health endpoint accessible via public URL
- [ ] Query endpoint returns correct responses
- [ ] Frontend deployed and accessible
- [ ] End-to-end query test from deployed frontend
- [ ] Event Grid subscription created
- [ ] Event Grid validation completed (status: Succeeded)
- [ ] Upload test document triggers reindexing
- [ ] Reindex function logs show successful processing
- [ ] New document searchable in frontend
- [ ] Delete document removes chunks from index

### Performance Testing

- [ ] Query latency < 3 seconds for typical queries
- [ ] Indexing rate meets requirements (chunks/min)
- [ ] Concurrent users supported (test with load tool)
- [ ] No timeout errors under load
- [ ] Cost per query within budget

### Security Testing

- [ ] No secrets in source code or logs
- [ ] `.env` file in `.gitignore`
- [ ] Function keys rotated from defaults
- [ ] CORS configured for specific origins (production)
- [ ] Authentication enabled (if applicable)
- [ ] Access control working (if applicable)

---

## Appendix: Scripts & Templates

### A. Batch Document Upload Script

Save as `upload_policies.sh`:

```bash
#!/bin/bash

# Configuration
STORAGE_ACCOUNT="your-storage-account"
CONTAINER_NAME="policy-documents"
DOCS_DIRECTORY="/path/to/policies"

# Get connection string
CONNECTION_STRING=$(az storage account show-connection-string \
  --name $STORAGE_ACCOUNT \
  --query connectionString \
  --output tsv)

# Upload all PDFs
echo "Uploading policy documents..."
count=0

for file in "$DOCS_DIRECTORY"/*.pdf; do
  if [ -f "$file" ]; then
    filename=$(basename "$file")
    echo "Uploading: $filename"
    
    az storage blob upload \
      --account-name $STORAGE_ACCOUNT \
      --container-name $CONTAINER_NAME \
      --name "$filename" \
      --file "$file" \
      --connection-string "$CONNECTION_STRING" \
      --overwrite
    
    ((count++))
  fi
done

echo "✅ Uploaded $count documents"
```

Make executable: `chmod +x upload_policies.sh`

### B. Environment Validation Script

Save as `validate_environment.py`:

```python
import os
import sys
from dotenv import load_dotenv

load_dotenv()

REQUIRED_VARS = [
    'STORAGE_CONNECTION_STRING',
    'SEARCH_ENDPOINT',
    'SEARCH_ADMIN_KEY',
    'OPENAI_ENDPOINT',
    'OPENAI_KEY',
]

def validate():
    missing = []
    for var in REQUIRED_VARS:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print("❌ Missing environment variables:")
        for var in missing:
            print(f"  - {var}")
        sys.exit(1)
    
    print("✅ All required environment variables set")
    
    # Test imports
    try:
        import azure.search.documents
        import azure.storage.blob
        import openai
        print("✅ All required packages installed")
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        sys.exit(1)

if __name__ == "__main__":
    validate()
```

Run: `python validate_environment.py`

### C. Index Statistics Script

Save as `check_index_stats.py`:

```python
import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

load_dotenv()

search_endpoint = os.getenv("SEARCH_ENDPOINT")
search_key = os.getenv("SEARCH_ADMIN_KEY")
index_name = "policy-index"

client = SearchClient(search_endpoint, index_name, AzureKeyCredential(search_key))

# Get document count
results = client.search(search_text="*", include_total_count=True, top=0)
total_docs = results.get_count()

print(f"📊 Index Statistics")
print(f"Total documents: {total_docs}")

# Count by source
sources = {}
for doc in client.search(search_text="*", select=["metadata_storage_name"]):
    source = doc.get("metadata_storage_name", "unknown")
    sources[source] = sources.get(source, 0) + 1

print("\n📄 Documents by source:")
for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
    print(f"  {source}: {count} chunks")
```

Run: `python check_index_stats.py`

### D. Query Testing Script

Save as `test_queries.py`:

```python
import os
import requests
from dotenv import load_dotenv

load_dotenv()

FUNCTION_URL = os.getenv("FUNCTION_URL") or "http://localhost:7071/api/query"

TEST_QUERIES = [
    "What is the vacation policy?",
    "How many days of sick leave do I get?",
    "What is the remote work policy?",
    "Who should I contact for benefits questions?",
    "What is the dress code?",
]

def test_query(query):
    print(f"\n❓ Query: {query}")
    response = requests.post(
        FUNCTION_URL,
        json={"query": query},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Answer: {data['answer'][:200]}...")
        print(f"📚 Citations: {len(data['citations'])} sources")
    else:
        print(f"❌ Error {response.status_code}: {response.text}")

if __name__ == "__main__":
    for query in TEST_QUERIES:
        test_query(query)
```

Run: `python test_queries.py`

### E. Cleanup Script

Save as `cleanup_resources.sh`:

```bash
#!/bin/bash

# WARNING: This will delete all resources!
read -p "Are you sure you want to delete all resources? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

RESOURCE_GROUP="your-company-rg"

echo "Deleting Event Grid subscriptions..."
az eventgrid event-subscription list --source-resource-id "/subscriptions/<sub-id>/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/<storage-account>" \
  | jq -r '.[].name' \
  | xargs -I {} az eventgrid event-subscription delete --name {}

echo "Deleting Function App..."
az functionapp delete --name <function-app> --resource-group $RESOURCE_GROUP

echo "Deleting AI Search..."
az search service delete --name <search-service> --resource-group $RESOURCE_GROUP

echo "Deleting OpenAI..."
az cognitiveservices account delete --name <openai-service> --resource-group $RESOURCE_GROUP

echo "Deleting Storage Accounts..."
az storage account delete --name <storage-account> --resource-group $RESOURCE_GROUP

echo "✅ Cleanup complete"
```

---

## Summary

You now have a complete, production-ready RAG system deployed on Azure with:

✅ **Automated ingestion** - Event Grid triggers reindexing on document changes  
✅ **Hybrid search** - Vector + keyword search for best results  
✅ **Citations** - Every answer includes source references  
✅ **Scalable architecture** - Azure Functions auto-scale with demand  
✅ **Policy-optimized** - Chunking and indexing tuned for policy documents  

### Next Steps for Your Organization:

1. **Security Review:** Implement authentication and authorization
2. **Compliance Check:** Verify data residency and retention policies
3. **User Testing:** Gather feedback from policy consumers
4. **Performance Tuning:** Optimize chunk size and search parameters
5. **Integration:** Embed into existing intranet or portal
6. **Training:** Document for internal IT team

### Getting Help

- **Azure Documentation:** https://docs.microsoft.com/azure
- **Azure OpenAI:** https://learn.microsoft.com/azure/ai-services/openai
- **Azure AI Search:** https://learn.microsoft.com/azure/search
- **GitHub Repository:** https://github.com/guzailaamer/azure-ai-search-demo

---

**Document Version:** 1.0  
**Last Updated:** 09 February 2026  
**Maintained By:** Guzail Aamer
