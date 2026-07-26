import sqlite3
import os

print("DATABASE.PY LOADED")

DB_NAME = os.path.join(os.path.dirname(__file__), "clans.db")


def init_db():
    print("INIT_DB CALLED")

    print("DB PATH:", DB_NAME)

    conn = sqlite3.connect(DB_NAME, timeout=5)
    print("SQLITE CONNECT OK")

    cur = conn.cursor()
    print("CURSOR CREATED")

    cur.execute("SELECT 1")
    print("SELECT OK")

    conn.close()
    print("DB CLOSED")


def save_clan(chat_id, clan_id, clan_tag, clan_name):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    INSERT OR REPLACE INTO clans
    (chat_id, clan_id, clan_tag, clan_name)
    VALUES (?, ?, ?, ?)
    """,
    (chat_id, clan_id, clan_tag, clan_name))

    conn.commit()
    conn.close()


def get_clan(chat_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute(
        "SELECT clan_id, clan_tag, clan_name FROM clans WHERE chat_id=?",
        (chat_id,)
    )

    result = cur.fetchone()

    conn.close()

    return result
  
