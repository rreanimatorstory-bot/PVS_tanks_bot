import os
import sqlite3
from datetime import datetime
from threading import Thread

# Вывод ID процесса для контроля старта в консоли Render
print("PROCESS ID:", os.getpid())

import httpx
from flask import Flask
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Импорт ваших функций для работы с базой данных
from database import init_db, save_clan, get_clan

# Загрузка переменных среды и первичная настройка БД
load_dotenv()
init_db()

# Конфигурационные константы
BOT_TOKEN = os.getenv("BOT_TOKEN")
WG_APP_ID = os.getenv("WG_APP_ID")
DB_NAME = "database.db"

# Инициализация единого асинхронного HTTP-клиента
http_client = httpx.AsyncClient(timeout=10.0)

# Инициализация веб-сервера Flask для прохождения Health Check на Render
app = Flask(__name__)

@app.route('/')
def home():
    """Простейший эндпоинт, подтверждающий работоспособность сервиса."""
    return "Bot is alive and running!", 200

def run_flask():
    """Запуск веб-сервера на порту, предоставленном платформой Render."""
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


def save_player_history(account_id, nickname, battles, damage):
    """Запись текущего среза статистики игрока в историю."""
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
    """Вывод списка доступных команд."""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=update.message.message_thread_id if update.message.message_thread_id else None,
        text=(
             "🤖 BlitzClanBot\n\n"
             "📋 Доступные команды:\n\n"
             "📊 /stats <ник> — статистика игрока\n"
             "🏆 /top — ТОП клана по среднему урону\n"
             "📈 /clanreport — отчёт клана\n"
             "👥 /members — список игроков клана\n"
             "⚙️ /setclan [тег] — привязать клан\n"
             "     Пример: /setclan 1PVS\n"
             "📋 /menu — это меню"
        )
    )  


async def myclan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка текущего клана, закрепленного за данным чатом."""
    clan = get_clan(update.effective_chat.id)

    if clan is None:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            message_thread_id=update.message.message_thread_id if update.message.message_thread_id else None,
            text="🏰 Для этого чата клан пока не настроен."
        )
        return

    clan_id, clan_tag, clan_name = clan

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=update.message.message_thread_id if update.message.message_thread_id else None,
        text=(
            f"🏰 Текущий клан\n\n"
            f"Название: {clan_name}\n"
            f"Тег: {clan_tag}\n"
            f"ID: {clan_id}"
        )
    )
    

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поиск и вывод подробной статистики игрока по его никнейму."""
    if not context.args:
        await update.message.reply_text("Использование:\n/stats ник")
        return

    nickname = context.args[0]
    await update.message.reply_text(f"🔎 Ищу игрока {nickname}...")

    try:
        # ---------- 1. Определение Account ID по нику ----------
        search_response = await http_client.get(
            "https://wotblitz.eu",
            params={"application_id": WG_APP_ID, "search": nickname}
        )
        search_data = search_response.json()

        if search_data.get("status") != "ok" or not search_data.get("data"):
            await update.message.reply_text("❌ Игрок не найден")
            return

        account_id = search_data["data"][0]["account_id"]

        # ---------- 2. Запрос статистики аккаунта ----------
        info_response = await http_client.get(
            "https://wotblitz.eu",
            params={"application_id": WG_APP_ID, "account_id": account_id}
        )
        info_data = info_response.json()

        if info_data.get("status") != "ok" or not info_data["data"].get(str(account_id)):
            await update.message.reply_text("❌ Не удалось получить статистику")
            return

        account = info_data["data"][str(account_id)]
        
        if account.get("private") or not account.get("statistics"):
            await update.message.reply_text("🔒 Профиль игрока скрыт настройками приватности.")
            return

        player_name = account["nickname"]
        player_stats = account["statistics"]["all"]

        battles = player_stats.get("battles", 0)
        wins = player_stats.get("wins", 0)
        damage = player_stats.get("damage_dealt", 0)
        frags = player_stats.get("frags", 0)
        shots = player_stats.get("shots", 0)
        hits = player_stats.get("hits", 0)
        xp = player_stats.get("xp", 0)
        spotted = player_stats.get("spotted", 0)
        survived = player_stats.get("survived_battles", 0)
        
        # ---------- 3. Определение клана игрока через accountinfo ----------
        clan_text = "Без клана"
        clan_response = await http_client.get(
            "https://wotblitz.eu",
            params={"application_id": WG_APP_ID, "account_id": account_id}
        )
        clan_data = clan_response.json()
        
        if clan_data.get("status") == "ok" and clan_data["data"].get(str(account_id)):
            player_clan_info = clan_data["data"][str(account_id)]
            if player_clan_info and player_clan_info.get("clan"):
                clan_text = f"[{player_clan_info['clan']['tag']}]"
                    
        # ---------- 4. Расчет средних показателей ----------
        winrate = round(wins / battles * 100, 2) if battles else 0
        avg_damage = round(damage / battles) if battles else 0
        avg_frags = round(frags / battles, 2) if battles else 0
        accuracy = round(hits / shots * 100, 2) if shots else 0
        avg_xp = round(xp / battles) if battles else 0

        try:
            save_player_history(account_id, player_name, battles, damage)
        except Exception as db_err:
            print(f"Ошибка сохранения в локальную БД: {db_err}")

        # ---------- 5. Отправка ответа в чат ----------
        await update.message.reply_text(
            f"🎮 {player_name}\n\n"
            f"⚔️ Бои: {battles:,}\n"
            f"🏆 Победы: {wins:,}\n"
            f"📊 Винрейт: {winrate}%\n"
            f"🏰 Клан: {clan_text}\n\n"
            f"💥 Средний урон: {avg_damage:,}\n"
            f"💀 Уничтожено: {frags:,} ({avg_frags}/бой)\n"
            f"🎯 Точность: {accuracy}%\n"
            f"⭐ Средний опыт: {avg_xp:,}\n"
            f"👁 Обнаружено: {spotted:,}\n"
            f"🛡 Выжил в боях: {survived:,}"
        )

    except httpx.TimeoutException:
        await update.message.reply_text("⌛ Сервер Wargaming не ответил вовремя. Попробуйте позже.")
    except Exception as e:
        print(f"Ошибка в функции stats: {e}")
        await update.message.reply_text("❌ Произошла ошибка при получении статистики.")


async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пакетный сбор данных участников привязанного клана и вывод ТОП-15 по урону."""
    clan = get_clan(update.effective_chat.id)

    if clan is None:
        await update.message.reply_text("❌ Сначала привяжите клан:\n/setclan [TAG]")
        return

    clan_id, clan_tag, clan_name = clan

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=update.message.message_thread_id if update.message.message_thread_id else None,
        text=f"⏳ Считаю статистику клана {clan_tag}..."
    )

    try:
        # ---------- 1. Получение ID всех участников клана ----------
        clan_res = await http_client.get(
            "https://wotblitz.eu",
            params={"application_id": WG_APP_ID, "clan_id": clan_id}
        )
        clan_data = clan_res.json()

        if clan_data.get("status") != "ok" or not clan_data["data"].get(str(clan_id)):
            await update.message.reply_text("❌ Не удалось получить данные клана.")
            return

        members_ids = clan_data["data"][str(clan_id)]["members_ids"]
        if not members_ids:
            await update.message.reply_text("🏰 В клане нет игроков.")
            return

        # ---------- 2. Оптимизированный запрос всей группы игроков за один раз ----------
        account_ids_str = ",".join(map(str, members_ids))
        
        stats_res = await http_client.get(
            "https://wotblitz.eu",
            params={"application_id": WG_APP_ID, "account_id": account_ids_str}
        )
        stats_data = stats_res.json()

        if stats_data.get("status") != "ok":
            await update.message.reply_text("❌ Не удалось получить групповую статистику.")
            return

        players_stats = stats_data["data"]
        leaderboard = []

        # ---------- 3. Вычисление среднего урона ----------
        for p_id_str, p_data in players_stats.items():
            if not p_data or p_data.get("private") or not p_data.get("statistics"):
                continue
            
            nickname = p_data["nickname"]
            all_b = p_data["statistics"]["all"]
            battles = all_b.get("battles", 0)
            damage = all_b.get("damage_dealt", 0)
            
            avg_dmg = round(damage / battles) if battles > 0 else 0
            
