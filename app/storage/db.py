import sqlite3

DB_PATH= "codebase.db"

def init_db(db_path=DB_PATH):
    """
    Connect to the database, create the chunks and calls tables
    if they don't already exist (use CREATE TABLE IF NOT EXISTS),
    and return the connection.
    """

    conn = sqlite3.connect(db_path)
    cursor= conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS chunks")
    cursor.execute("DROP TABLE IF EXISTS calls")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        docstring TEXT,
        source_code TEXT,
        file TEXT NOT NULL,
        start_line INTEGER,
        end_line INTEGER,
        parent_class TEXT
        
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calls(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            caller TEXT NOT NULL,
            callee TEXT NOT NULL
            )
        """)

    conn.commit()
    return conn

    
def insert_chunks(conn, chunks: list[dict]):
    """
    Insert a list of chunk dicts (like the ones your parser produces)
    into the chunks table. Return a dict mapping chunk name -> its new id,
    so insert_calls can look up ids later if needed.
    Hint: conn.cursor(), cursor.execute(), then conn.commit() at the end.
    """

    cursor = conn.cursor()
    name_to_id = {}

    for chunk in chunks:
        cursor.execute("""
            INSERT INTO chunks (name, type, docstring, source_code, file, start_line, end_line, parent_class)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,(
            chunk["name"],
            chunk["type"],
            chunk["docstring"],
            chunk["source_code"],
            chunk["file"],
            chunk["start_line"],
            chunk["end_line"],
            chunk["parent_class"],
        ))
        name_to_id[chunk["name"]]= cursor.lastrowid

    conn.commit()
    return name_to_id


def insert_calls(conn, calls: list[tuple]):
    """
    Insert a list of (caller, callee) tuples into the calls table.
    Hint: cursor.executemany() lets you insert a whole list at once,
    instead of looping and calling execute() one row at a time.
    """

    cursor= conn.cursor()
    cursor.executemany("""
        INSERT INTO calls (caller, callee)
        VALUES(?,?)
    """, calls) 

    conn.commit()


def get_callers(conn, function_name: str) -> list[str]:
    """
    Return every distinct 'caller' where callee == function_name.
    This is the query your Day 5 agent will use for
    "what calls this function?"
    """

    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT caller FROM calls WHERE callee=?
    """, (function_name,))

    return [row[0] for row in cursor.fetchall()]


if __name__== "__main__":
    from app.parser.ast_parser import parse_repo

    chunks, calls= parse_repo(".")
    conn=init_db()
    name_to_id= insert_chunks(conn, chunks)
    insert_calls(conn,calls)

    print(f"Inserted {len(chunks)} chunks and {len(calls)} calls")
    print("Who calls 'append'? ->", get_callers(conn, "append"))