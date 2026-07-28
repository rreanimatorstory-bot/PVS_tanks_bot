import os

print("PROCESS ID:", os.getpid())

import requests
import sqlite3
from datetime import datetime

from flask import Flask
from threading import Thread
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from database import init_db, save_clan, get_clan

load_dotenv()

init_db()

BOT_TOKEN = os.getenv("BOT_TOKEN")


WG_APP_ID = os.getenv("WG_APP_ID")
    
def save_player_history(account_id, nickname, battles, damage):

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO history
    (account_id, nickname, battles, damage, date)
    VALUES (?, ?, ?, ?, ?)
    """,
    (
        account_id,
        nickname,
        battles,
        damage,
        datetime.now().strftime("%Y-%m-%d")
    ))

    conn.commit()
    conn.close()



async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 Добро пожаловать в BlitzClanBot!\n\n"
        "Я помогу следить за статистикой вашего клана.\n\n"
        "📌 Сначала привяжите клан:\n"
        "/setclan [TAG]\n\n"
        "Команды:\n\n"
        "📊 /stats ник — статистика любого игрока\n"
        "🏆 /top — ТОП вашего клана\n"
        "📈 /clanreport — отчёт клана\n"
        "👥 /members — список игроков клана\n"
        "🏰 /myclan — текущий клан"
    )

async def myclan(update: Update, context: ContextTypes.DEFAULT_TYPE):

    

    clan = get_clan(update.effective_chat.id)


    if clan is None:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            message_thread_id=update.message.message_thread_id,
            text="🏰 Для этого чата клан пока не настроен."
        )
        return

    clan_id, clan_tag, clan_name = clan

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=update.message.message_thread_id,
        text=(
            f"🏰 Текущий клан\n\n"
            f"Название: {clan_name}\n"
            f"Тег: {clan_tag}\n"
            f"ID: {clan_id}"
        )
    )
    

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        await update.message.reply_text(
            "Использование:\n/stats ник"
        )
        return

    nickname = context.args[0]

    await update.message.reply_text(
        f"🔎 Ищу игрока {nickname}..."
    )

    try:
  
        # ---------- Поиск игрока ----------
        search_response = requests.get(
            "https://api.wotblitz.eu/wotb/account/list/",
            params={
                "application_id": WG_APP_ID,
                "search": nickname
            },
            timeout=10
        )

        search_data = search_response.json()

        print("SEARCH DATA:")
        print(search_data)

        if search_data.get("status") != "ok" or not search_data.get("data"):
            await update.message.reply_text("❌ Игрок не найден")
            return

        account_id = None

        for acc in search_data["data"]:
            if acc["nickname"].lower() == nickname.lower():
                account_id = acc["account_id"]
                break
        
        if account_id is None:
            account_id = search_data["data"][0]["account_id"]

        print("SELECTED ACCOUNT:", account_id, flush=True)

            
        # ---------- Статистика игрока ----------
        info_response = requests.get(
            "https://api.wotblitz.eu/wotb/account/info/",
            params={
                "application_id": WG_APP_ID,
                "account_id": account_id
            },
            timeout=10
        )

        print("STATUS CODE:", info_response.status_code, 
        flush=True)
        print("RAW RESPONSE:", info_response.text, flush=True)
        
        info_data = info_response.json()


        if info_data.get("status") != "ok":
            await update.message.reply_text(
                "❌ Не удалось получить статистику"
            )
            return

        account = info_data["data"].get(str(account_id))

        print("ACCOUNT DATA:",flush=True)
        print(account, flush=True)
        
        print("ACCOUNT CLAN:", flush=True)
        print(account.get("clan_id"), flush=True)

        # ---------- Проверка клана игрока ----------
        clan_id = account.get("clan_id")

        print("CLAN ID:", flush=True)
        print(clan_id, flush=True)

        clan_text = "Без клана"
        
        if clan_id:
            clan_response = requests.get(
                "https://api.wotblitz.eu/wotb/clans/info/",
                params={
                    "application_id": WG_APP_ID,
                    "clan_id": clan_id
                },
                timeout=10
            )
        
            clan_data = clan_response.json()
        
            print("CLAN DATA:", flush=True)
            print(clan_data, flush=True)
        
            if clan_data.get("status") == "ok":
                clan_info = clan_data["data"].get(str(clan_id))
        
                if clan_info:
                    clan_text = clan_info.get("tag", "Без клана")
            
        if account is None:
             await update.message.reply_text(
                "❌ В ответе API нет данных игрока"
             )
             return

        player_name = account["nickname"]

        stats = account["statistics"]["all"]

        battles = stats.get("battles", 0)
        wins = stats.get("wins", 0)
        damage = stats.get("damage_dealt", 0)
        frags = stats.get("frags", 0)
        shots = stats.get("shots", 0)
        hits = stats.get("hits", 0)
        xp = stats.get("xp", 0)
        spotted = stats.get("spotted", 0)
        survived = stats.get("survived_battles", 0)
        
        # ---------- Клан игрока ----------
        clan_response = requests.get(
            "https://api.wotblitz.eu/wotb/clans/accountinfo/",
            params={
                "application_id": WG_APP_ID,
                "account_id": account_id
            },
            timeout=10
        )
        
        clan_data = clan_response.json()
         
        
        clan_name = "Без клана"
        
        if clan_data.get("status") == "ok":
        
            player_clan = clan_data.get("data", {}).get(str(account_id))
        
            if player_clan:
        
                player_clan_id = player_clan.get("clan_id")
        
                if player_clan_id:
        
                    clan_response = requests.get(
                        "https://api.wotblitz.eu/wotb/clans/info/",
                        params={
                            "application_id": WG_APP_ID,
                            "clan_id": player_clan_id
                        },
                        timeout=10
                    )
        
                    clan_info_data = clan_response.json()
        
                    if clan_info_data.get("status") == "ok":
        
                        clan_info = clan_info_data.get("data", {}).get(str(player_clan_id))
        
                        if clan_info:
                            clan_name = f"[{clan_info.get('tag')}]"
                    
        # ---------- Расчеты ----------
        winrate = round(
            wins / battles * 100,
            2
        ) if battles else 0

        avg_damage = round(
            damage / battles
        ) if battles else 0

        avg_frags = round(
            frags / battles,
            2
        ) if battles else 0

        accuracy = round(
            hits / shots * 100,
            2
        ) if shots else 0

        avg_xp = round(
            xp / battles
        ) if battles else 0

        # ---------- Ответ ----------
        await update.message.reply_text(

            f"🎮 {player_name}\n\n"

            f"⚔️ Бои: {battles:,}\n"
            f"🏆 Победы: {wins:,}\n"
            f"📊 Винрейт: {winrate}%\n"
            f"🏰 Клан: {clan_name}\n\n"

            f"💥 Средний урон: {avg_damage:,}\n"
            f"💀 Уничтожено: {frags:,} ({avg_frags}/бой)\n"
            f"🎯 Точность: {accuracy}%\n"
            f"⭐ Средний опыт: {avg_xp:,}\n"
            f"👁 Обнаружено: {spotted:,}\n"
            f"🛡 Выжил в боях: {survived:,}"

        )

    except requests.exceptions.Timeout:

        await update.message.reply_text(
            "⌛ Сервер Wargaming не ответил вовремя. Попробуйте позже."
        )

    except Exception as e:
        print("STATS ERROR:", e, flush=True)
        await update.message.reply_text(
        f"❌ Ошибка: {e}"
    )

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):

    clan = get_clan(update.effective_chat.id)

    if clan is None:
        await update.message.reply_text(
            "❌ Сначала привяжите клан:\n/setclan [TAG]"
        )
        return

    clan_id, clan_tag, clan_name = clan

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=update.message.message_thread_id,
        text=f"⏳ Считаю статистику клана {clan_tag}..."
    )

    clan_url = "https://api.wotblitz.eu/wotb/clans/info/"

    clan_params = {
        "application_id": WG_APP_ID,
        "clan_id": clan_id
    }

    clan_response = requests.get(
        clan_url,
        params=clan_params
    )

    clan_data = clan_response.json()

    if clan_data.get("status") != "ok":
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            message_thread_id=update.message.message_thread_id,
            text="❌ Не удалось получить клан"
        )
        return


    members_ids = clan_data["data"][str(clan_id)]["members_ids"]


    results = []

    for account_id in members_ids:



        stats_url = "https://api.wotblitz.eu/wotb/account/info/"

        stats_params = {
            "application_id": WG_APP_ID,
            "account_id": account_id
        }

        stats_response = requests.get(
            stats_url,
            params=stats_params
        )

        stats_data = stats_response.json()

        if stats_data.get("status") != "ok":
            continue


        player = stats_data["data"][str(account_id)]["statistics"]["all"]

        battles = player.get("battles", 0)
        damage = player.get("damage_dealt", 0)

        if battles:
            avg_damage = round(damage / battles)

            nickname = stats_data["data"][str(account_id)]["nickname"]

            results.append(
                {
                    "name": nickname,
                    "damage": avg_damage
                }
            )


    results.sort(
        key=lambda x: x["damage"],
        reverse=True
    )


    text = "🏆 ТОП КЛАНА\n\n"

    for i, player in enumerate(results[:10], start=1):

        text += (
            f"{i}. 🎮 {player['name']}\n"
            f"💥 Средний урон: {player['damage']}\n\n"
        )


    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=update.message.message_thread_id,
        text=text
    )

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):

    print("REPORT START", flush=True)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=update.message.message_thread_id,
        text="⏳ Собираю отчёт клана...\nЭто может занять немного времени."
    )

    clan_url = "https://api.wotblitz.eu/wotb/clans/info/"

    clan = get_clan(update.effective_chat.id)

    if clan is None:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            message_thread_id=update.message.message_thread_id,
            text="❌ Сначала привяжите клан:\n/setclan [TAG]"
        )
        return
    
    clan_id, clan_tag, clan_name = clan

    clan_params = {
        "application_id": WG_APP_ID,
        "clan_id": clan_id
    }

    clan_response = requests.get(
        clan_url,
        params=clan_params,
        timeout=10
    )

    clan_data = clan_response.json()

    if clan_data.get("status") != "ok":
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            message_thread_id=update.message.message_thread_id,
            text="❌ Не удалось получить данные клана"
        )
        return


    members_ids = clan_data["data"][str(clan_id)]["members_ids"]


    total_battles = 0
    total_wins = 0
    total_damage = 0

    best_damage = {
        "name": "",
        "damage": 0
    }

    most_active = {
        "name": "",
        "battles": 0
    }

    players_activity = []
    low_activity = []


    for index, account_id in enumerate(members_ids, start=1):

        print(f"REPORT: processing {index}/{len(members_ids)}")

        stats_url = "https://api.wotblitz.eu/wotb/account/info/"

        stats_params = {
            "application_id": WG_APP_ID,
            "account_id": account_id
        }


        stats_response = requests.get(
            stats_url,
            params=stats_params,
            timeout=10
        )

        stats_data = stats_response.json()


        if stats_data.get("status") != "ok":
            continue


        account = stats_data["data"][str(account_id)]

        nickname = account["nickname"]

        player = account["statistics"]["all"]


        battles = player.get("battles", 0)
        wins = player.get("wins", 0)
        damage = player.get("damage_dealt", 0)


        if battles:

            avg_damage = round(
                damage / battles
            )

            players_activity.append(
                {
                    "name": nickname,
                    "battles": battles
                }
            )
            
            if battles < 1000:
                low_activity.append(
                    {
                        "name": nickname,
                        "battles": battles
                    }
                )
            

            total_battles += battles
            total_wins += wins
            total_damage += damage


            if avg_damage > best_damage["damage"]:
                best_damage["name"] = nickname
                best_damage["damage"] = avg_damage


            if battles > most_active["battles"]:
                most_active["name"] = nickname
                most_active["battles"] = battles



    winrate = round(
        total_wins / total_battles * 100,
        2
    ) if total_battles else 0


    avg_damage_clan = round(
        total_damage / total_battles
    ) if total_battles else 0

    players_activity.sort(
        key=lambda x: x["battles"],
        reverse=True
    )

    low_activity.sort(
        key=lambda x: x["battles"]
    )


    low_text = ""

    for p in low_activity[:5]:
        low_text += (
            f"\n• {p['name']} — {p['battles']:,} боёв"
        )

    if not low_text:
        low_text = "\nНет игроков"

    text = (
        "📊 Отчёт клана P=V=S\n\n"
        f"👥 Участников: {len(members_ids)}\n\n"
        f"⚔️ Всего боёв: {total_battles:,}\n"
        f"🏆 Побед: {total_wins:,}\n"
        f"📊 Средний WR: {winrate}%\n"
        f"💥 Средний урон: {avg_damage_clan:,}\n\n"
        f"🥇 Лучший урон:\n"
        f"{best_damage['name']} — {best_damage['damage']}\n\n"
        f"🔥 ТОП по боям:\n"
        f"1. {players_activity[0]['name']} — {players_activity[0]['battles']:,}\n"
        f"2. {players_activity[1]['name']} — {players_activity[1]['battles']:,}\n"
        f"3. {players_activity[2]['name']} — {players_activity[2]['battles']:,}\n\n"
        f"⚠️ Мало боёв:"
        f"{low_text}"
    )


    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=update.message.message_thread_id,
        text=text
    )

async def members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    print("MEMBERS START", flush=True)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=update.message.message_thread_id,
        text="⏳ Загружаю состав клана..."
    )

    # Получаем привязанный клан из базы
    clan = get_clan(update.effective_chat.id)

    if clan is None:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            message_thread_id=update.message.message_thread_id,
            text="❌ Сначала привяжите клан:\n/setclan [TAG]"
        )
        return


    clan_id, clan_tag, clan_name = clan

    print("MEMBERS: clan from database", clan_id, clan_tag)


    # Получаем список игроков клана
    clan_url = "https://api.wotblitz.eu/wotb/clans/info/"

    clan_params = {
        "application_id": WG_APP_ID,
        "clan_id": clan_id
    }


    response = requests.get(
        clan_url,
        params=clan_params,
        timeout=10
    )

    data = response.json()

    print("MEMBERS: clan API response received")


    if data.get("status") != "ok":
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            message_thread_id=update.message.message_thread_id,
            text="❌ Не удалось получить данные клана"
        )
        return


    members_ids = data["data"][str(clan_id)]["members_ids"]
    print("MEMBERS: players count", len(members_ids))


    # Один запрос вместо 50 запросов
    names = []

    players_url = "https://api.wotblitz.eu/wotb/account/info/"


    # запрашиваем игроков группами по 10
    for i in range(0, len(members_ids), 10):

        batch = members_ids[i:i+10]

        ids = ",".join(map(str, batch))


        players_params = {
            "application_id": WG_APP_ID,
            "account_id": ids
        }

        print("MEMBERS: requesting players info")
        players_response = requests.get(
            players_url,
            params=players_params,
            timeout=10
        )


        players_data = players_response.json()
        print("MEMBERS: players API response received")


        if players_data.get("status") != "ok":
            continue


        for player in players_data["data"].values():
            names.append(player["nickname"])

    names.sort()


    text = (
        f"👥 Состав клана {clan_tag}\n\n"
        f"Всего игроков: {len(names)}\n\n"
    )


    for i, name in enumerate(names, start=1):
        text += f"{i}. {name}\n"


    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=update.message.message_thread_id,
        text=text
    )

async def update_history(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=update.message.message_thread_id,
        text="⏳ Обновляю историю игроков..."
    )

    clan_url = "https://api.wotblitz.eu/wotb/clans/info/"

    clan_params = {
        "application_id": WG_APP_ID,
        "clan_id": CLAN_ID
    }

    clan_response = requests.get(
        clan_url,
        params=clan_params,
        timeout=10
    )

    clan_data = clan_response.json()

    if clan_data.get("status") != "ok":
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            message_thread_id=update.message.message_thread_id,
            text="❌ Не удалось получить клан"
        )
        return


    members_ids = clan_data["data"][str(CLAN_ID)]["members_ids"]


    saved = 0


    for index, account_id in enumerate(members_ids, start=1):

        if index % 10 == 0:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                message_thread_id=update.message.message_thread_id,
                text=f"⏳ Обработано {index}/{len(members_ids)} участников..."
            )

        stats_url = "https://api.wotblitz.eu/wotb/account/info/"

        stats_params = {
            "application_id": WG_APP_ID,
            "account_id": account_id
        }


        try:
            stats_response = requests.get(
                stats_url,
                params=stats_params,
                timeout=10
            )

            stats_data = stats_response.json()

        except:
            continue


        if stats_data.get("status") != "ok":
            continue


        account = stats_data["data"][str(account_id)]

        nickname = account["nickname"]

        player = account["statistics"]["all"]


        battles = player.get("battles", 0)
        damage = player.get("damage_dealt", 0)


        save_player_history(
            account_id,
            nickname,
            battles,
            damage
        )

        saved += 1


    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=update.message.message_thread_id,
        text=(
            f"✅ История обновлена\n"
            f"Сохранено игроков: {saved}"
        )
    )

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        await update.message.reply_text(
            "Использование:\n/history ник"
        )
        return

    nickname = context.args[0]

    # Поиск игрока
    url = "https://api.wotblitz.eu/wotb/account/list/"

    params = {
        "application_id": WG_APP_ID,
        "search": nickname
    }

    response = requests.get(url, params=params)
    data = response.json()

    if data.get("status") != "ok" or not data.get("data"):
        await update.message.reply_text("❌ Игрок не найден")
        return

    player = data["data"][0]
    account_id = player["account_id"]

    # Получение статистики
    url = "https://api.wotblitz.eu/wotb/account/info/"

    params = {
        "application_id": WG_APP_ID,
        "account_id": account_id
    }

    response = requests.get(url, params=params)
    data = response.json()

    if data.get("status") != "ok":
        await update.message.reply_text("❌ Ошибка получения статистики")
        return

    player = list(data["data"].values())[0]

    stats = player["statistics"]["all"]

    nickname = player["nickname"]
    battles = stats["battles"]
    wins = stats["wins"]
    damage = stats["damage_dealt"]
    frags = stats["frags"]

    winrate = round(wins / battles * 100, 1) if battles else 0

    text = (
        f"📜 История игрока\n\n"
        f"👤 {nickname}\n\n"
        f"⚔️ Бои: {battles:,}\n"
        f"🏆 Победы: {wins:,}\n"
        f"📊 Винрейт: {winrate}%\n"
        f"💥 Урон: {damage:,}\n"
        f"☠️ Фраги: {frags:,}"
    )

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=update.message.message_thread_id,
        text=text
    )

# Flask для Render

web = Flask(__name__)


@web.route("/")
def home():
    return "BlitzClanBot is running!"
    
async def setclan(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id

    if not context.args:
        await update.message.reply_text(
            "Использование:\n"
            "/setclan [ТЕГ]\n\n"
            "Пример:\n"
            "/setclan [1PVS]"
        )
        return

    clan_tag = context.args[0].upper().replace("[", "").replace("]", "")

    url = "https://api.wotblitz.eu/wotb/clans/list/"

    params = {
        "application_id": WG_APP_ID,
        "search": clan_tag
    }

    response = requests.get(url, params=params)
    data = response.json()


    if data.get("status") != "ok" or not data.get("data"):
        await update.message.reply_text(
            "❌ Клан с таким тегом не найден"
        )
        return

    clan = data["data"][0]

    clan_id = clan["clan_id"]
    clan_name = clan["name"]
    clan_tag = clan["tag"]

    save_clan(
        chat_id,
        clan_id,
        clan_tag,
        clan_name
    )

    await update.message.reply_text(
        f"✅ Клан настроен:\n"
        f"🏰 {clan_name}\n"
        f"🔖 {clan_tag}\n"
        f"ID: {clan_id}"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 Добро пожаловать в BlitzClanBot!\n\n"
        "Я помогу следить за статистикой вашего клана.\n\n"
        "📌 Сначала привяжите клан:\n"
        "/setclan [TAG]\n\n"
        "Команды:\n\n"
        "📊 /stats ник — статистика любого игрока\n"
        "🏆 /top — ТОП вашего клана\n"
        "📈 /clanreport — отчёт клана\n"
        "👥 /members — список игроков клана\n"
        "🏰 /myclan — текущий клан"
    )
    
def run_bot():

    print("RUN_BOT STARTED")

    print("CREATING TELEGRAM APP")

    print("TOKEN EXISTS:", bool(BOT_TOKEN))
    print("TOKEN LENGTH:", len(BOT_TOKEN) if BOT_TOKEN else 0)
    print("TOKEN START:", BOT_TOKEN[:10])
    print("TOKEN END:", BOT_TOKEN[-10:])

    app = Application.builder().token(BOT_TOKEN).build()

    print("TELEGRAM APP CREATED")

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setclan", setclan))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("myclan", myclan))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("clanreport", report))
    app.add_handler(CommandHandler("members", members))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CommandHandler("update", update_history))

    print("BOT STARTED")
    print("STARTING POLLING")

    
    app.run_polling(
        drop_pending_updates=True,
        stop_signals=None
    ) 


print("START BOT THREAD")

thread = Thread(target=run_bot)
thread.start()

print("Starting Flask...")

web.run(
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 10000))
)
