import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI
import PyPDF2
import io
import uuid
import base64


load_dotenv()

# Initialize clients
storage_connection = os.getenv("STORAGE_CONNECTION_STRING")
blob_service = BlobServiceClient.from_connection_string(storage_connection)

search_endpoint = os.getenv("SEARCH_ENDPOINT")
search_key = os.getenv("SEARCH_ADMIN_KEY")
search_client = SearchClient(search_endpoint, "documents-index", AzureKeyCredential(search_key))

openai_client = AzureOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    api_version="2024-02-15-preview",
    azure_endpoint=os.getenv("OPENAI_ENDPOINT")
)

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
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    return chunks

def get_embedding(text: str):
    response = openai_client.embeddings.create(
        input=text,
        model="text-embedding-ada-002"
    )
    return response.data[0].embedding

# At the top with other functions, add:
def make_safe_id(blob_name: str, chunk_index: int) -> str:
    """Create a safe document ID"""
    safe_name = blob_name.replace('.', '_').replace(' ', '_')
    return f"{safe_name}_{chunk_index}"

def process_blob(blob_name: str, container_name: str):
    print(f"Processing {blob_name}...")
    
    container_client = blob_service.get_container_client(container_name)
    blob_client = container_client.get_blob_client(blob_name)
    blob_data = blob_client.download_blob().readall()
    
    if blob_name.endswith('.pdf'):
        text = extract_text_from_pdf(blob_data)
    else:
        text = blob_data.decode('utf-8')
    
    chunks = chunk_text(text)
    
    documents = []
    for i, chunk in enumerate(chunks):
        embedding = get_embedding(chunk)
        doc = {
            "id": make_safe_id(blob_name, i),
            "content": chunk,
            "title": blob_name,
            "metadata_storage_name": blob_name,
            "metadata_storage_path": f"https://{os.getenv('STORAGE_ACCOUNT_NAME')}.blob.core.windows.net/{container_name}/{blob_name}",
            "contentVector": embedding
        }
        documents.append(doc)
    
    search_client.upload_documents(documents)
    print(f"✅ Indexed {len(documents)} chunks from {blob_name}")

def index_all_documents():
    container_name = os.getenv("CONTAINER_NAME", "documents")
    container_client = blob_service.get_container_client(container_name)
    blobs = container_client.list_blobs()
    
    for blob in blobs:
        process_blob(blob.name, container_name)

if __name__ == "__main__":
    index_all_documents()
    print("✅ All documents indexed!")