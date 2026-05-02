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
        result = agent.invoke({"messages": [("human", query)]})
        response = result["messages"][-1].content
        cache_response(query, response)
        return response, False
