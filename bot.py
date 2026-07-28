import os
import sqlite3
from datetime import datetime
from threading import Thread

# Печатаем ID процесса для контроля в логах
print("PROCESS ID:", os.getpid())

import httpx
from flask import Flask
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Импорт ваших функций из соседнего файла базы данных
from database import init_db, save_clan, get_clan

# Загружаем переменные окружения и инициализируем БД
load_dotenv()
init_db()

# Константы из настроек среды
BOT_TOKEN = os.getenv("BOT_TOKEN")
WG_APP_ID = os.getenv("WG_APP_ID")
DB_NAME = "database.db"  # Убедитесь, что имя совпадает с вашей БД в database.py

# Создаем один глобальный клиент для асинхронных HTTP-запросов к API Wargaming
http_client = httpx.AsyncClient(timeout=10.0)

# Инициализируем Flask-сервер для прохождения Health Check на Render
app = Flask(__name__)

@app.route('/')
def home():
    """Эндпоинт, который Render будет пинговать для проверки работоспособности"""
    return "Bot is alive and running!", 200

def run_flask():
    """Функция для запуска веб-сервера в отдельном потоке"""
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


def save_player_history(account_id, nickname, battles, damage):
    """Сохранение истории игрока в локальную БД SQLite"""
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
    """Отображение главного меню команд"""
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
    """Вывод информации о текущем привязанном к чату клане"""
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
    """Получение подробной статистики конкретного игрока"""
    if not context.args:
        await update.message.reply_text("Использование:\n/stats ник")
        return

    nickname = context.args[0]
    await update.message.reply_text(f"🔎 Ищу игрока {nickname}...")

    try:
        # ---------- 1. Поиск ID игрока по никнейму ----------
        search_response = await http_client.get(
            "https://wotblitz.eu",
            params={"application_id": WG_APP_ID, "search": nickname}
        )
        search_data = search_response.json()

        if search_data.get("status") != "ok" or not search_data.get("data"):
            await update.message.reply_text("❌ Игрок не найден")
            return

        account_id = search_data["data"][0]["account_id"]

        # ---------- 2. Запрос общей боевой статистики ----------
        info_response = await http_client.get(
            "https://wotblitz.eu",
            params={"application_id": WG_APP_ID, "account_id": account_id}
        )
        info_data = info_response.json()

        if info_data.get("status") != "ok" or not info_data["data"].get(str(account_id)):
            await update.message.reply_text("❌ Не удалось получить статистику")
            return

        account = info_data["data"][str(account_id)]
        
        # Проверка скрытого (приватного) аккаунта
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
        
        # ---------- 3. Запрос клана игрока (исправленный эндпоинт) ----------
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
                    
        # ---------- 4. Математические расчеты эффективности ----------
        winrate = round(wins / battles * 100, 2) if battles else 0
        avg_damage = round(damage / battles) if battles else 0
        avg_frags = round(frags / battles, 2) if battles else 0
        accuracy = round(hits / shots * 100, 2) if shots else 0
        avg_xp = round(xp / battles) if battles else 0

        # Сохранение среза данных в историю для графиков/отчетов
        try:
            save_player_history(account_id, player_name, battles, damage)
        except Exception as db_err:
            print(f"Ошибка сохранения истории в БД: {db_err}")

        # ---------- 5. Отправка итогового сообщения ----------
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
    """Построение таблицы лидеров клана по среднему урону"""
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
        # ---------- 1. Получаем список ID всех участников клана ----------
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
            await update.message.reply_text("🏰 В клане отсутствуют участники.")
            return

        # ---------- 2. Оптимизированный пакетный запрос статистики ----------
        # Передаем массив ID строкой через запятую (например: "135,246,357")
        account_ids_str = ",".join(map(str, members_ids))
        
        stats_res = await http_client.get(
            "https://wotblitz.eu",
            params={"application_id": WG_APP_ID, "account_id": account_ids_str}
        )
        stats_data = stats_res.json()

        if stats_data.get("status") != "ok":
            await update.message.reply_text("❌ Не удалось пакетно получить статистику игроков.")
            return

        players_stats = stats_data["data"]
        leaderboard = []

        # ---------- 3. Сбор и обработка профилей участников ----------
        for p_id_str, p_data in players_stats.items():
            if not p_data or p_data.get("private") or not p_data.get("statistics"):
                continue  # Игнорируем закрытые аккаунты
            

