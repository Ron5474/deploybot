import chromadb
from pathlib import Path

from db.db import setup_db

client = chromadb.PersistentClient(path="rag/chroma_db")
docs_collection = client.get_or_create_collection("app_docs")
app_collection = client.get_or_create_collection("app_catalog")

README_DIR = Path("data/readme_cache")
BATCH_SIZE = 256

def chunk_by_heading(content):
    current_heading = ""
    current_lines = []
    chunks = []

    for line in content.splitlines():
        if line.startswith("##"):
            if current_heading != "":
                chunks.append((current_heading, "\n".join(current_lines)))
            current_heading = line
            current_lines = []
        current_lines.append(line)

    if current_heading:
        chunks.append((current_heading, "\n".join(current_lines)))

    return chunks


def read_and_embed_chunks():
    documents, metadatas, ids = [], [], []

    def flush():
        if not documents:
            return
        docs_collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
        documents.clear()
        metadatas.clear()
        ids.clear()

    for j, file in enumerate(README_DIR.glob("*.md")):
        app_name = file.stem
        content = file.read_text(encoding="utf-8")

        print(f"Reading file {app_name} ---- {j}")
        chunks = chunk_by_heading(content)

        for i, (section, text) in enumerate(chunks):
            documents.append(text)
            metadatas.append({"app_name": app_name, "section": section})
            ids.append(f"{app_name}_{i}")

            if len(documents) >= BATCH_SIZE:
                flush()

    flush()
    print("Embedded all chunks")

"""
id
name
category
description
github_url
docker_image
license
language
"""
def read_and_embed_app_catalog():
    conn, cursor = setup_db()
    query = """
        SELECT name, category, description FROM apps;
    """
    cursor.execute(query)
    rows = cursor.fetchall()

    documents = [f"{name} {category} {desc}" for name, category, desc in rows]
    metadatas = [{"name": name, "category": category} for name, category, _ in rows]
    ids = [name for name, _, _ in rows]

    if documents:
        app_collection.upsert(documents=documents, metadatas=metadatas, ids=ids)

    conn.close()
    print("Embedded all App Catalog")
    
    


read_and_embed_chunks()
read_and_embed_app_catalog()
