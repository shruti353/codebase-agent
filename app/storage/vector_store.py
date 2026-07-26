import requests
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

COLLECTION_NAME = "code_chunks"
EMBED_DIM= 768
OLLAMA_URL= "http://localhost:11434/api/embeddings"

def get_embeddings(text: str) -> list[float]:
    response= requests.post(
        OLLAMA_URL,
        json={ "model": "nomic-embed-text", "prompt": text}
    )
    response.raise_for_status()
    return response.json()["embedding"]


def build_embedding_text(chunk: dict) -> str:
    first_line= chunk["source_code"].split("\n")[0] if chunk["source_code"] else ""
    docstring= chunk["docstring"] or ""
    return f"{chunk['name']}\n{first_line}\n{docstring}"


def init_collection(client: QdrantClient):
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name= COLLECTION_NAME,
            vectors_config= VectorParams(size=EMBED_DIM, distance=Distance.COSINE ),
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


