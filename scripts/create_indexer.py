import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexerClient
from azure.search.documents.indexes.models import (
    SearchIndexer,
    FieldMapping,
    IndexingParameters,
    IndexingParametersConfiguration
)

load_dotenv('.env')

search_endpoint = os.getenv("SEARCH_ENDPOINT")
search_key = os.getenv("SEARCH_ADMIN_KEY")
indexer_client = SearchIndexerClient(search_endpoint, AzureKeyCredential(search_key))

indexer_name = "documents-indexer"
data_source_name = "documents-datasource"
skillset_name = "documents-skillset"
index_name = "documents-index"

# Then use this for output_field_mappings:
indexer = SearchIndexer(
    name=indexer_name,
    description="Indexer for processing documents",
    data_source_name=data_source_name,
    target_index_name=index_name,
    skillset_name=skillset_name,
    field_mappings=[
        FieldMapping(source_field_name="metadata_storage_name", target_field_name="title")
    ],
    output_field_mappings=[
        FieldMapping(source_field_name="/document/pages/*/contentVector", target_field_name="contentVector"),
        FieldMapping(source_field_name="/document/pages/*", target_field_name="content")
    ]
)

result = indexer_client.create_or_update_indexer(indexer)
print(f"✅ Indexer '{indexer_name}' created/updated")
print("Running indexer...")

# Run the indexer
indexer_client.run_indexer(indexer_name)
print("✅ Indexer is running. Check status in Azure Portal.")