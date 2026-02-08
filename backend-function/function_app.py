import azure.functions as func
from azure.storage.blob import BlobServiceClient
import PyPDF2
import io
import uuid
import json
import os
import datetime
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI
import logging

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Initialize clients (these will use environment variables)
def get_search_client():
    search_endpoint = os.environ["SEARCH_ENDPOINT"]
    search_key = os.environ["SEARCH_ADMIN_KEY"]
    return SearchClient(search_endpoint, "documents-index", AzureKeyCredential(search_key))

def get_openai_client():
    return AzureOpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        api_version="2024-02-15-preview",
        azure_endpoint=os.environ["OPENAI_ENDPOINT"]
    )

def get_embedding(text: str, openai_client):
    response = openai_client.embeddings.create(
        input=text,
        model="text-embedding-ada-002"
    )
    return response.data[0].embedding

def search_documents(query: str, search_client, openai_client, top_k: int = 3):
    query_vector = get_embedding(query, openai_client)
    
    vector_query = VectorizedQuery(
        vector=query_vector,
        k_nearest_neighbors=top_k,
        fields="contentVector"
    )
    
    results = search_client.search(
        search_text=query,
        vector_queries=[vector_query],
        select=["content", "title", "metadata_storage_name"],
        top=top_k
    )
    
    return list(results)

def generate_answer(query: str, context_docs: list, openai_client):
    context = "\n\n".join([
        f"[Source: {doc.get('metadata_storage_name', doc.get('title', 'Unknown'))}]\n{doc['content']}"
        for doc in context_docs
    ])
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant that answers questions based on provided context and always cites sources using [Source: filename]."},
        {"role": "user", "content": f"""Answer the question based on the context provided.

Context:
{context}

Question: {query}

Answer:"""}
    ]
    
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.7,
        max_tokens=500
    )
    
    return response.choices[0].message.content

# Common CORS headers to return on responses
DEFAULT_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS, GET",
    "Access-Control-Allow-Headers": "Content-Type",
}

@app.route(route="query", methods=["OPTIONS"])
def query_options(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        status_code=200,
        headers=DEFAULT_CORS_HEADERS
    )

@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Health check endpoint hit.')
    body = json.dumps({"status": "healthy"})
    return func.HttpResponse(
        body,
        mimetype="application/json",
        status_code=200,
        headers=DEFAULT_CORS_HEADERS
    )

@app.route(route="query", methods=["POST"])
def query(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Query endpoint hit.')
    
    try:
        req_body = req.get_json()
        user_query = req_body.get('query', '')
        
        if not user_query:
            body = json.dumps({"error": "No query provided"})
            return func.HttpResponse(
                body,
                mimetype="application/json",
                status_code=400,
                headers=DEFAULT_CORS_HEADERS
            )
        
        # Initialize clients
        search_client = get_search_client()
        openai_client = get_openai_client()
        
        # Search documents
        search_results = search_documents(user_query, search_client, openai_client)
        
        # Generate answer
        answer = generate_answer(user_query, search_results, openai_client)
        
        # Prepare citations
        citations = [
            {
                "source": doc.get('metadata_storage_name', doc.get('title', 'Unknown')),
                "content": doc['content'][:200] + "..."
            }
            for doc in search_results
        ]
        
        response = {
            "answer": answer,
            "citations": citations
        }

        return func.HttpResponse(
            json.dumps(response),
            mimetype="application/json",
            status_code=200,
            headers=DEFAULT_CORS_HEADERS
        )
    
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        body = json.dumps({"error": str(e)})
        return func.HttpResponse(
            body,
            mimetype="application/json",
            status_code=500,
            headers=DEFAULT_CORS_HEADERS
        )
    
# ─── Reindexing helpers ───────────────────────────────────────────

def extract_text_from_pdf(blob_data: bytes) -> str:
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(blob_data))
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks

def make_safe_id(blob_name: str, chunk_index: int) -> str:
    safe_name = blob_name.replace('.', '_').replace(' ', '_')
    return f"{safe_name}_{chunk_index}"

def delete_existing_chunks(search_client, blob_name: str):
    """Delete all existing chunks for a document before reindexing"""
    safe_name = blob_name.replace('.', '_').replace(' ', '_')
    results = search_client.search(
        search_text="*",
        filter=f"metadata_storage_name eq '{blob_name}'",
        select=["id"]
    )
    ids_to_delete = [{"id": doc["id"]} for doc in results]
    if ids_to_delete:
        search_client.delete_documents(documents=ids_to_delete)
        logging.info(f"Deleted {len(ids_to_delete)} old chunks for {blob_name}")

def reindex_document(blob_name: str):
    """Process a single blob and reindex it"""
    openai_client = get_openai_client()
    search_client = get_search_client()

    # Connect to Blob Storage
    storage_connection = os.environ["STORAGE_CONNECTION_STRING"]
    container_name = os.environ.get("CONTAINER_NAME", "documents")
    blob_service = BlobServiceClient.from_connection_string(storage_connection)
    container_client = blob_service.get_container_client(container_name)
    blob_client = container_client.get_blob_client(blob_name)

    # Download and extract text
    blob_data = blob_client.download_blob().readall()
    if blob_name.endswith('.pdf'):
        text = extract_text_from_pdf(blob_data)
    else:
        text = blob_data.decode('utf-8')

    # Chunk text
    chunks = chunk_text(text)

    # Delete old chunks
    delete_existing_chunks(search_client, blob_name)

    # Generate embeddings and index new chunks
    documents = []
    for i, chunk in enumerate(chunks):
        embedding = get_embedding(chunk, openai_client)
        documents.append({
            "id": make_safe_id(blob_name, i),
            "content": chunk,
            "title": blob_name,
            "metadata_storage_name": blob_name,
            "contentVector": embedding
        })

    search_client.upload_documents(documents)
    logging.info(f"✅ Reindexed {len(documents)} chunks from {blob_name}")

# ─── Event Grid trigger ──────────────────────────────────────────

@app.route(route="reindex", methods=["POST"])
def reindex(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Reindex endpoint hit.")
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }

    try:
        events = req.get_json()

        # Event Grid sends array of events
        if not isinstance(events, list):
            events = [events]

        for event in events:
            # Event Grid validation handshake
            if event.get("eventType") == "Microsoft.EventGrid.SubscriptionValidationEvent":
                validation_code = event["data"]["validationCode"]
                logging.info("Validating Event Grid subscription...")
                return func.HttpResponse(
                    json.dumps({"validationResponse": validation_code}),
                    mimetype="application/json",
                    status_code=200
                )

            # Blob created/updated event
            if event.get("eventType") in [
                "Microsoft.Storage.BlobCreated",
                "Microsoft.Storage.BlobDeleted"
            ]:
                # Extract blob name from URL
                url = event["data"]["url"]
                blob_name = url.split("/")[-1]

                logging.info(f"Processing blob: {blob_name}")

                # Skip non-PDF files
                if not blob_name.endswith('.pdf'):
                    logging.info(f"Skipping non-PDF file: {blob_name}")
                    continue

                # Skip if blob was deleted
                if event["eventType"] == "Microsoft.Storage.BlobDeleted":
                    search_client = get_search_client()
                    delete_existing_chunks(search_client, blob_name)
                    logging.info(f"Deleted chunks for {blob_name}")
                    continue

                # Reindex the document
                reindex_document(blob_name)

        return func.HttpResponse(
            json.dumps({"message": "Reindexing complete"}),
            mimetype="application/json",
            status_code=200,
            headers=headers
        )

    except Exception as e:
        logging.error(f"Reindex error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500,
            headers=headers
        )