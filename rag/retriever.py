import chromadb
from langchain_core.tools import tool
# Some comment

client = chromadb.PersistentClient(path="rag/chroma_db")
docs_collection = client.get_or_create_collection("app_docs")
app_collection = client.get_or_create_collection("app_catalog")


@tool
def get_info_from_vector_db(query):
    """
    Retrieve relevant documentation and information about self-hosted applications from the local knowledge base. 
    Use this for setup guides, configuration details, environment variables, docker-compose help, 
    or any app-specific technical information
    """

    doc_results = docs_collection.query(query_texts=[query], n_results=4)
    documents = doc_results["documents"][0]

    app_catalog_results = app_collection.query(query_texts=[query], n_results=4)
    app_catalogs = app_catalog_results["documents"][0]

    return "\n\n".join(documents + app_catalogs)
