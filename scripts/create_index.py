import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
    SemanticConfiguration,
    SemanticSearch,
    SemanticField,
    SemanticPrioritizedFields
)

load_dotenv('.env')

search_endpoint = os.getenv("SEARCH_ENDPOINT")
search_key = os.getenv("SEARCH_ADMIN_KEY")
index_client = SearchIndexClient(search_endpoint, AzureKeyCredential(search_key))

index_name = "documents-index"

# Define fields
fields = [
    SimpleField(name="id", type="Edm.String", key=True),
    SearchableField(name="content", type="Edm.String", analyzer_name="en.microsoft"),
    SearchableField(name="title", type="Edm.String"),
    SimpleField(name="metadata_storage_name", type="Edm.String", filterable=True, facetable=True),
    SimpleField(name="metadata_storage_path", type="Edm.String"),
    SearchField(
    name="contentVector",
    type="Collection(Edm.Single)",  # Changed from Edm.Single
    searchable=True,
    vector_search_dimensions=1536,
    vector_search_profile_name="myHnswProfile"
    )
]

# Vector search config
vector_search = VectorSearch(
    profiles=[
        VectorSearchProfile(
            name="myHnswProfile",
            algorithm_configuration_name="myHnsw"
        )
    ],
    algorithms=[
        HnswAlgorithmConfiguration(name="myHnsw")
    ]
)

# Semantic search config
semantic_config = SemanticConfiguration(
    name="my-semantic-config",
    prioritized_fields=SemanticPrioritizedFields(
        title_field=SemanticField(field_name="title"),
        content_fields=[SemanticField(field_name="content")]
    )
)

semantic_search = SemanticSearch(configurations=[semantic_config])

# Create index
index = SearchIndex(
    name=index_name,
    fields=fields,
    vector_search=vector_search,
    semantic_search=semantic_search
)

result = index_client.create_or_update_index(index)
print(f"✅ Index '{index_name}' created/updated")