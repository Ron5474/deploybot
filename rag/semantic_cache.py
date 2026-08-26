import uuid

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction


client = chromadb.PersistentClient(path="rag/chroma_db")
cache_collection = client.get_or_create_collection(
        name="response_cache",
        embedding_function=DefaultEmbeddingFunction()
)

def get_cached_response(query, threshold = 0.15):
        results = cache_collection.query(query_texts=[query], n_results=1)
        if results["ids"][0]:
                distance = results["distances"][0][0]
                if distance < threshold:
                        return results["metadatas"][0][0]["response"]
        return None

def cache_response(query, response):
        cache_collection.upsert(
                ids=[query],
                documents=[query],
                metadatas=[{"response": response}]
        )

def get_response(query):
        cached = get_cached_response(query)
        if cached:
                return cached, True

        from agent.agent import agent
        result = agent.invoke(
                {"messages": [("human", query)]},
                config={"configurable": {"thread_id": f"semcache-{uuid.uuid4().hex[:8]}"}},
        )
        response = result["messages"][-1].content
        cache_response(query, response)
        return response, False


def clear_cache():
        """Drop every cached response so a benchmark can measure a true cold pass.
        Only the response_cache collection is recreated — the RAG index
        (app_docs / app_catalog) in the same store is left untouched."""
        global cache_collection
        client.delete_collection("response_cache")
        cache_collection = client.get_or_create_collection(
                name="response_cache",
                embedding_function=DefaultEmbeddingFunction(),
        )
