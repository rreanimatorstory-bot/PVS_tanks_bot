import sqlite3
import os

DB_NAME = os.path.join(os.path.dirname(__file__), "clans.db")


def init_db():
    print("INIT_DB CALLED")
    
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

    # Таблица истории игроков
    cur.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER,
        nickname TEXT,
        battles INTEGER,
        damage INTEGER,
        date TEXT
    )
    """)

    conn.commit()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    print("DATABASE TABLES:", cur.fetchall())
    
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
  
