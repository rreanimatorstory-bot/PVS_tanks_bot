import os
import requests
from flask import Flask
from threading import Thread
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WG_APP_ID = os.getenv("WG_APP_ID")
CLAN_ID = "1336303"



async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 BlitzClanBot\n\n"
        "📋 Доступные команды:\n\n"
        "📊 /stats <ник> — статистика игрока\n"
        "🏆 /top — ТОП клана по среднему урону\n"
        "📈 /clanreport — отчёт клана\n"
        "📋 /menu — это меню"
    )



async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        await update.message.reply_text(
            "Использование:\n/stats ник"
        )
        return


    nickname = " ".join(context.args)

    await update.message.reply_text(
        f"🔎 Ищу игрока {nickname}..."
    )


    # поиск игрока
    url = "https://api.wotblitz.eu/wotb/account/list/"

    params = {
        "application_id": WG_APP_ID,
        "search": nickname,
        "type": "exact",
        "limit": 1
    }


    response = requests.get(url, params=params)
    data = response.json()


    if data.get("status") != "ok" or not data.get("data"):
        await update.message.reply_text(
            "❌ Игрок не найден"
        )
        return


    account_id = data["data"][0]["account_id"]
    player_name = data["data"][0]["nickname"]


    # получение статистики
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
        await update.message.reply_text(
            "❌ Ошибка получения статистики"
        )
        return


    player = stats_data["data"][str(account_id)]["statistics"]["all"]
    account = stats_data["data"][str(account_id)]

    rating = account.get("global_rating", 0)
    clan_id = account.get("clan_id", "нет")
    
    
    battles = player.get("battles", 0)
    wins = player.get("wins", 0)

    damage = player.get("damage_dealt", 0)
    frags = player.get("frags", 0)
    shots = player.get("shots", 0)
    hits = player.get("hits", 0)
    xp = player.get("xp", 0)
    spotted = player.get("spotted", 0)
    survived = player.get("survived_battles", 0)


    winrate = round(
        wins / battles * 100, 2
    ) if battles else 0


    avg_damage = round(
        damage / battles
    ) if battles else 0


    avg_frags = round(
        frags / battles, 2
    ) if battles else 0


    accuracy = round(
        hits / shots * 100, 2
    ) if shots else 0


    avg_xp = round(
        xp / battles
    ) if battles else 0


    await update.message.reply_text(
        f"🎮 {player_name}\n\n"
        f"⚔️ Бои: {battles:,}\n"
        f"🏆 Победы: {wins:,}\n"
        f"📊 Винрейт: {winrate}%\n"
        f"🏅 Рейтинг: {rating}\n"
        f"🏰 Клан ID: {clan_id}\n\n"
        f"💥 Средний урон: {avg_damage:,}\n"
        f"💀 Уничтожено: {frags:,} ({avg_frags}/бой)\n"
        f"🎯 Точность: {accuracy}%\n"
        f"⭐ Средний опыт: {avg_xp:,}\n"
        f"👁 Обнаружено: {spotted:,}\n"
        f"🛡 Выжил в боях: {survived:,}"
    )

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
    "⏳ Считаю статистику 49 игроков клана..."
    )

    clan_url = "https://api.wotblitz.eu/wotb/clans/info/"

    clan_params = {
        "application_id": WG_APP_ID,
        "clan_id": CLAN_ID
    }

    clan_response = requests.get(
        clan_url,
        params=clan_params
    )

    clan_data = clan_response.json()

    if clan_data.get("status") != "ok":
        await update.message.reply_text(
            "❌ Не удалось получить клан"
        )
        return


    members_ids = clan_data["data"][CLAN_ID]["members_ids"]


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


    await update.message.reply_text(text)

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "⏳ Собираю отчёт клана...\nЭто может занять немного времени."
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
        await update.message.reply_text(
            "❌ Не удалось получить данные клана"
        )
        return


    members_ids = clan_data["data"][str(CLAN_ID)]["members_ids"]


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


    for account_id in members_ids:

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
        f"3. {players_activity[2]['name']} — {players_activity[2]['battles']:,}"

        f"⚠️ Мало боёв:"
        f"{low_text}"
    )


    await update.message.reply_text(text)

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):

    account_id = 726737026  # сюда потом поставим ID игрока

    url = "https://api.wotblitz.eu/wotb/account/info/"

    params = {
        "application_id": WG_APP_ID,
        "account_id": account_id
    }

    response = requests.get(url, params=params)

    await update.message.reply_text(
        str(response.json())[:4000]
    )


    

# Flask для Render

web = Flask(__name__)


@web.route("/")
def home():
    return "BlitzClanBot is running!"



def run_bot(): 
    
    print("RUN_BOT START")

    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("clanreport", report))
    app.add_handler(CommandHandler("history", history))


    print("Bot started")

    app.run_polling(
        stop_signals=None
    )



thread = Thread(target=run_bot)
thread.start()


print("Starting Flask...")


web.run(
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 10000))
)
