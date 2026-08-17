import requests
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
import os
from google import genai

COLLECTION_NAME = "code_chunks"
EMBED_DIM= 1024

import os
import requests
import cohere

EMBED_PROVIDER = os.getenv("EMBED_PROVIDER", "ollama")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/embed")

_cohere_client = None
if EMBED_PROVIDER == "cohere":
    _cohere_client = cohere.ClientV2(api_key=os.environ["COHERE_API_KEY"])


def get_embeddings(text: str) -> list[float]:
    if EMBED_PROVIDER == "cohere":
        result = _cohere_client.embed(
            texts=[text],
            model="embed-english-v3.0",
            input_type="search_document",
            embedding_types=["float"],
        )
        return result.embeddings.float[0]
    else:
        response = requests.post(OLLAMA_URL, json={"model": "nomic-embed-text", "input": text})
        response.raise_for_status()
        return response.json()["embeddings"][0]
    
    

def build_embedding_text(chunk: dict) -> str:
    first_line= chunk["source_code"].split("\n")[0] if chunk["source_code"] else ""
    docstring= chunk["docstring"] or ""
    return f"{chunk['name']}\n{first_line}\n{docstring}"

def init_collection(client: QdrantClient):
    if client.collection_exists(COLLECTION_NAME):
        info = client.get_collection(COLLECTION_NAME)
        existing_dim = info.config.params.vectors.size
        if existing_dim != EMBED_DIM:
            print(f"Collection dim mismatch ({existing_dim} vs {EMBED_DIM}), recreating...")
            client.delete_collection(COLLECTION_NAME)
        else:
            return

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
    )
    
    

def index_chunks(client: QdrantClient, chunks_with_id: list[tuple[int, dict]]):
    points=[]

    for chunk_id, chunk in chunks_with_id:
        text= build_embedding_text(chunk)
        vector= get_embeddings(text)

        points.append(PointStruct(
            id=chunk_id,
            vector=vector,
            payload={
                "name": chunk["name"],
                "type": chunk["type"],
                "file": chunk["file"],
                "parent_class": chunk["parent_class"],
            }
        )
        )

    client.upsert(collection_name=COLLECTION_NAME, points=points)
    return len(points)


def search_code(client: QdrantClient, query: str, top_k: int = 5):
    query_vector = get_embeddings(query)

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=top_k,
    )
    return results.points


