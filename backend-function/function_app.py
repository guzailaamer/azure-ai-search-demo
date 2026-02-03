import azure.functions as func
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