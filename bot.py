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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 BlitzClanBot запущен!\n\n"
        "Команды:\n"
        "/stats ник — статистика игрока"
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
        await update.message.reply_text("❌ Игрок не найден")
        return

    account_id = data["data"][0]["account_id"]
    player_name = data["data"][0]["nickname"]

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
            "❌ Не удалось получить статистику"
        )
        return

    player = stats_data["data"][str(account_id)]["statistics"]["all"]

   battles = player.get("battles", 0)
   wins = player.get("wins", 0)

   damage = player.get("damage_dealt", 0)
   xp = player.get("xp", 0)

   avg_damage = round(
   damage / battles
   ) if battles else 0

avg_xp = round(
    xp / battles
) if battles else 0

winrate = round(
    (wins / battles) * 100, 2
) if battles else 0

    await update.message.reply_text(
        f"🎮 {player_name}\n\n"
        f"⚔️ Бои: {battles}\n"
        f"🏆 Победы: {wins}\n"
        f"📊 Винрейт: {winrate}%"
    )
# Flask для Render

web = Flask(__name__)

@web.route("/")
def home():
    return "BlitzClanBot is running!"

def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))

    print("Bot started")
    app.run_polling(stop_signals=None)


thread = Thread(target=run_bot)
thread.start()

print("Starting Flask...")

web.run(
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 10000))
)
