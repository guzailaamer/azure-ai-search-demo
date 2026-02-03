import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI

load_dotenv()

app = FastAPI(title="RAG Query API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients
search_endpoint = os.getenv("SEARCH_ENDPOINT")
search_key = os.getenv("SEARCH_ADMIN_KEY")
search_client = SearchClient(search_endpoint, "documents-index", AzureKeyCredential(search_key))

openai_client = AzureOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    api_version="2024-02-15-preview",
    azure_endpoint=os.getenv("OPENAI_ENDPOINT")
)

class QueryRequest(BaseModel):
    query: str

class Citation(BaseModel):
    source: str
    content: str

class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]

def get_embedding(text: str):
    response = openai_client.embeddings.create(
        input=text,
        model="text-embedding-ada-002"
    )
    return response.data[0].embedding

def search_documents(query: str, top_k: int = 3):
    query_vector = get_embedding(query)
    
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

def generate_answer(query: str, context_docs: list):
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

@app.get("/")
async def root():
    return {"message": "RAG API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    if not request.query:
        raise HTTPException(status_code=400, detail="No query provided")
    
    try:
        # Search documents
        search_results = search_documents(request.query)
        
        # Generate answer
        answer = generate_answer(request.query, search_results)
        
        # Prepare citations
        citations = [
            Citation(
                source=doc.get('metadata_storage_name', doc.get('title', 'Unknown')),
                content=doc['content'][:200] + "..."
            )
            for doc in search_results
        ]
        
        return QueryResponse(answer=answer, citations=citations)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)