from qdrant_client import QdrantClient
from app.parser.ast_parser import parse_repo
from app.storage.db import init_db, insert_chunks, insert_calls
from app.storage.vector_store import init_collection, index_chunks, search_code

def index_repository(repo_path:str):
    chunks, calls= parse_repo(repo_path)
    print(f"Parsed {len(chunks)} chunks and {len(calls)} calls")

    conn= init_db()
    chunks_with_id= insert_chunks(conn,chunks)
    insert_calls(conn, calls)
    print("Inserted into SQLite")

    qdrant= QdrantClient(host="localhost", port=6333)
    init_collection(qdrant)
    counts=index_chunks(qdrant, chunks_with_id)
    print(f"Indexed {counts} vectors into Qdrant")

    return conn, qdrant


if __name__ == "__main__":
    conn, qdrant= index_repository(".")

    query = "divide two numbers together"
    results= search_code(qdrant, query, top_k=3)
    print(f"\nSearch results for: '{query}'")

    for r in results:
        print(f" score: {r.score: .3f}, name: {r.payload['name']}, file: {r.payload['file']}")
