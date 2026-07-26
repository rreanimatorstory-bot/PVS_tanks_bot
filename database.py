import sqlite3


DB_NAME = "clans.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS clans (
        chat_id INTEGER PRIMARY KEY,
        clan_id INTEGER,
        clan_tag TEXT,
        clan_name TEXT
    )
    """)

    conn.commit()
    conn.close()


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
  
