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

    nickname = context.args[0]

    await update.message.reply_text(
        f"🔎 Ищу игрока {nickname}..."
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
