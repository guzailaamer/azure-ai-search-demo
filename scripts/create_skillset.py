import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexerClient
from azure.search.documents.indexes.models import (
    SearchIndexerSkillset,
    SplitSkill,
    AzureOpenAIEmbeddingSkill,
    InputFieldMappingEntry,
    OutputFieldMappingEntry
)

load_dotenv('.env')

search_endpoint = os.getenv("SEARCH_ENDPOINT")
search_key = os.getenv("SEARCH_ADMIN_KEY")
openai_endpoint = os.getenv("OPENAI_ENDPOINT")
openai_key = os.getenv("OPENAI_API_KEY")
embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")

indexer_client = SearchIndexerClient(search_endpoint, AzureKeyCredential(search_key))

skillset_name = "documents-skillset"

# Define skills
skills = [
    # Skill 1: Split text into chunks
    SplitSkill(
        name="split-skill",
        description="Split content into chunks",
        context="/document",
        text_split_mode="pages",
        maximum_page_length=1000,
        page_overlap_length=100,
        inputs=[
            InputFieldMappingEntry(name="text", source="/document/content")
        ],
        outputs=[
            OutputFieldMappingEntry(name="textItems", target_name="pages")
        ]
    ),
    # Skill 2: Generate embeddings
    AzureOpenAIEmbeddingSkill(
        name="embedding-skill",
        description="Generate embeddings using Azure OpenAI",
        context="/document/pages/*",
        resource_url=openai_endpoint,  # Changed from resource_uri
        deployment_name=embedding_deployment,  # Changed from deployment_id
        model_name="text-embedding-ada-002",
        api_key=openai_key,
        inputs=[
            InputFieldMappingEntry(name="text", source="/document/pages/*")
        ],
        outputs=[
            OutputFieldMappingEntry(name="embedding", target_name="contentVector")
        ]
    )
]

# Create skillset
skillset = SearchIndexerSkillset(
    name=skillset_name,
    description="Skillset for document processing",
    skills=skills
)

result = indexer_client.create_or_update_skillset(skillset)
print(f"✅ Skillset '{skillset_name}' created/updated")