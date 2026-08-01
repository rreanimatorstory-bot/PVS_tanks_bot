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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS dashboard_messages (
        chat_id BIGINT,
        dashboard TEXT,
        message_id BIGINT,
        PRIMARY KEY(chat_id, dashboard)
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        telegram_id BIGINT PRIMARY KEY,
        telegram_username TEXT,
        telegram_first_name TEXT,
        wot_nickname TEXT,
        wot_account_id BIGINT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        telegram_id BIGINT PRIMARY KEY,
        telegram_username TEXT,
        telegram_first_name TEXT,
        wot_nickname TEXT,
        wot_account_id BIGINT
    )
    """)

    

    conn.commit()

    cur.close()
    conn.close()

    print("POSTGRES DB READY")

def add_clan_id_to_history():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        ALTER TABLE history
        ADD COLUMN IF NOT EXISTS clan_id BIGINT;
    """)

    conn.commit()

    cur.close()
    conn.close()

    print("HISTORY TABLE UPDATED: clan_id added", flush=True)

def check_history_columns():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name='history'
    """)

    rows = cur.fetchall()

    print("HISTORY COLUMNS:", rows, flush=True)

    cur.close()
    conn.close()        


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

def get_all_clans():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT chat_id, clan_id, clan_tag, clan_name
        FROM clans
        """
    )

    result = cur.fetchall()

    cur.close()
    conn.close()

    return result

def save_dashboard_message(chat_id, dashboard, message_id):
    print(
        "SAVE DASHBOARD:",
        chat_id,
        dashboard,
        message_id,
        flush=True
    )

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO dashboard_messages
    (chat_id, dashboard, message_id)
    VALUES (%s,%s,%s)
    ON CONFLICT (chat_id, dashboard)
    DO UPDATE SET
        message_id = EXCLUDED.message_id
    """,
    (
        chat_id,
        dashboard,
        message_id
    ))

    conn.commit()

    cur.close()
    conn.close()

def delete_dashboard_message(chat_id, dashboard):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    DELETE FROM dashboard_messages
    WHERE chat_id=%s
    AND dashboard=%s
    """,
    (
        chat_id,
        dashboard
    ))

    conn.commit()

    cur.close()
    conn.close()    


def get_dashboard_message(chat_id, dashboard):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT message_id
    FROM dashboard_messages
    WHERE chat_id=%s
    AND dashboard=%s
    """,
    (
        chat_id,
        dashboard
    ))

    row = cur.fetchone()

    cur.close()
    conn.close()

    if row:
        return row[0]

    return None

def save_player_history(account_id, nickname, battles, damage, clan_id):


    conn = get_connection()
    cur = conn.cursor()

    # Проверяем последнюю запись
    cur.execute("""
    SELECT battles, damage, date
    FROM history
    WHERE account_id=%s
    ORDER BY id DESC
    LIMIT 1
    """,
    (account_id,))

    last = cur.fetchone()

    today = datetime.now().strftime("%Y-%m-%d")

    if last:
        last_battles, last_damage, last_date = last

        if str(last_date) == today:
            cur.close()
            conn.close()
            return

    # Сохраняем новый снимок
    cur.execute("""
    INSERT INTO history
    (account_id, nickname, battles, damage, date, clan_id)
    VALUES (%s, %s, %s, %s, %s, %s)
    """,
    (
        account_id,
        nickname,
        battles,
        damage,
        datetime.now().strftime("%Y-%m-%d"),
        clan_id
    ))

    

    conn.commit()

    cur.close()
    conn.close()

def get_player_history(account_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT nickname, battles, damage, date, clan_id
    FROM history
    WHERE account_id=%s
    ORDER BY id DESC
    LIMIT 10
    """,
    (account_id,))

    result = cur.fetchall()

    cur.close()
    conn.close()


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

def clean_history_duplicates():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    DELETE FROM history a
    USING history b
    WHERE a.id > b.id
    AND a.account_id = b.account_id
    AND a.battles = b.battles
    AND a.damage = b.damage
    """)

    deleted = cur.rowcount

    conn.commit()

    cur.close()
    conn.close()

def save_user(
    telegram_id,
    telegram_username,
    telegram_first_name,
    wot_nickname,
    wot_account_id
):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO users
    (
        telegram_id,
        telegram_username,
        telegram_first_name,
        wot_nickname,
        wot_account_id
    )
    VALUES (%s,%s,%s,%s,%s)

    ON CONFLICT (telegram_id)
    DO UPDATE SET
        telegram_username = EXCLUDED.telegram_username,
        telegram_first_name = EXCLUDED.telegram_first_name,
        wot_nickname = EXCLUDED.wot_nickname,
        wot_account_id = EXCLUDED.wot_account_id
    """,
    (
        telegram_id,
        telegram_username,
        telegram_first_name,
        wot_nickname,
        wot_account_id
    ))

    conn.commit()

    cur.close()
    conn.close()


def get_user(telegram_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT
        telegram_id,
        telegram_username,
        telegram_first_name,
        wot_nickname,
        wot_account_id
    FROM users
    WHERE telegram_id=%s
    """,
    (telegram_id,))

    result = cur.fetchone()

    cur.close()
    conn.close()

    return result


    
       
    

   