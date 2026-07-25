import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

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


app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("stats", stats))

print("Bot started")

app.run_polling()
