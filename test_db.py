import sqlite3

conn = sqlite3.connect("codebase.db")
cursor = conn.cursor()

cursor.execute("SELECT * FROM chunks")

for row in cursor.fetchall():
    print(f"{row} \n")

conn.close()