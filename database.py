import os 
import psycopg2
from datetime import datetime

print("DATABASE.PY LOADED (POSTGRES)")


DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    print("INIT_DB CALLED")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS clans (
        chat_id BIGINT PRIMARY KEY,
        clan_id BIGINT,
        clan_tag TEXT,
        clan_name TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id SERIAL PRIMARY KEY,
        account_id BIGINT,
        nickname TEXT,
        battles INTEGER,
        damage INTEGER,
        date TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bot_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    

    conn.commit()

    cur.close()
    conn.close()

    print("POSTGRES DB READY")


def save_clan(chat_id, clan_id, clan_tag, clan_name):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO clans
    (chat_id, clan_id, clan_tag, clan_name)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (chat_id)
    DO UPDATE SET
        clan_id = EXCLUDED.clan_id,
        clan_tag = EXCLUDED.clan_tag,
        clan_name = EXCLUDED.clan_name
    """,
    (
        chat_id,
        clan_id,
        clan_tag,
        clan_name
    ))

    conn.commit()

    cur.close()
    conn.close()


def get_clan(chat_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT clan_id, clan_tag, clan_name
        FROM clans
        WHERE chat_id=%s
        """,
        (chat_id,)
    )

    result = cur.fetchone()

    cur.close()
    conn.close()

    return result

def save_player_history(account_id, nickname, battles, damage):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO history
    (account_id, nickname, battles, damage, date)
    VALUES (%s, %s, %s, %s, %s)
    """,
    (
        account_id,
        nickname,
        battles,
        damage,
        datetime.now().strftime("%Y-%m-%d")
    ))

    print(
        "SAVE HISTORY ID:",
        account_id,
        nickname,
        battles,
        damage,
        flush=True
    )

    conn.commit()

    cur.close()
    conn.close()

def get_player_history(account_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT nickname, battles, damage, date
    FROM history
    WHERE account_id=%s
    ORDER BY id DESC
    LIMIT 10
    """,
    (account_id,))

    result = cur.fetchall()

    cur.close()
    conn.close()

    print("GET HISTORY ID:", account_id, flush=True)
    print("GET HISTORY RESULT:", result, flush=True)

    return result

def get_last_update():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT value
    FROM bot_settings
    WHERE key='last_update'
    """)

    row = cur.fetchone()

    cur.close()
    conn.close()

    if row:
        return row[0]

    return None


def set_last_update(date):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO bot_settings (key, value)
    VALUES ('last_update', %s)
    ON CONFLICT (key)
    DO UPDATE SET value = EXCLUDED.value
    """, (date,))

    conn.commit()

    cur.close()
    conn.close()