from dotenv import load_dotenv
load_dotenv()

import sys
from qdrant_client import QdrantClient
from app.parser.ast_parser import parse_repo
from app.storage.db import reset_db, insert_chunks, insert_calls
from app.storage.vector_store import init_collection, index_chunks, search_code
import os


def index_repository(repo_path: str):
    chunks, calls = parse_repo(repo_path)
    print(f"Parsed {len(chunks)} chunks and {len(calls)} calls from {repo_path}")

    conn = reset_db()
    chunks_with_ids = insert_chunks(conn, chunks)
    insert_calls(conn, calls)
    print("Inserted into SQLite")

    qdrant = QdrantClient(
        url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )

    init_collection(qdrant)
    count = index_chunks(qdrant, chunks_with_ids)
    print(f"Indexed {count} vectors into Qdrant")

    return conn, qdrant


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "sample_target"
    conn, qdrant = index_repository(target)

    query = "calculate a value recursively"
    results = search_code(qdrant, query, top_k=3)
    print(f"\nSearch results for: '{query}'")
    for r in results:
        print(f"  score={r.score:.3f}  name={r.payload['name']}  file={r.payload['file']}")