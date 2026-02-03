import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexerClient
from azure.search.documents.indexes.models import (
    SearchIndexerDataSourceConnection,
    SearchIndexerDataContainer
)

load_dotenv('.env')

# Initialize client
search_endpoint = os.getenv("SEARCH_ENDPOINT")
search_key = os.getenv("SEARCH_ADMIN_KEY")
indexer_client = SearchIndexerClient(search_endpoint, AzureKeyCredential(search_key))

# Create data source
data_source_name = "documents-datasource"
connection_string = os.getenv("STORAGE_CONNECTION_STRING")
container_name = os.getenv("CONTAINER_NAME")

data_source = SearchIndexerDataSourceConnection(
    name=data_source_name,
    type="azureblob",
    connection_string=connection_string,
    container=SearchIndexerDataContainer(name=container_name)
)

# Create or update
result = indexer_client.create_or_update_data_source_connection(data_source)
print(f"✅ Data source '{data_source_name}' created/updated")