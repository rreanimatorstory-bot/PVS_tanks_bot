import os      
 
print("PROCESS ID:", os.getpid())

import requests
from datetime import datetime

def format_number(number):
    return f"{number:,}".replace(",", " ")

from flask import Flask
from threading import Thread
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram import BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ChatMemberHandler,
)


from database import (
    check_history_columns,
    init_db,
    add_clan_id_to_history,
    save_clan,
    get_clan,
    get_all_clans,
    save_player_history,
    get_player_history,
    set_last_update,
    clean_history_duplicates,
    save_user,
    get_user
)

from keyboard import main_menu

load_dotenv()

# Состояния ConversationHandler
WAIT_STATS_NICK = 1
WAIT_HISTORY_NICK = 2
WAIT_CLAN_TAG = 3
WAIT_WOT_NICK = 4

init_db()
check_history_columns()
add_clan_id_to_history()

BOT_TOKEN = os.getenv("BOT_TOKEN")

WG_APP_ID = os.getenv("WG_APP_ID")

DEVELOPER_ID = 356966584


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    if is_developer(user_id):
        await update.message.reply_text(
            "🤖 BlitzClanBot\n\n"
            "Выберите действие:",
            reply_markup=main_menu()
        )
        return

    await update.message.reply_text(
        "🤖 Добро пожаловать в BlitzClanBot!\n\n"
        "Я помогу следить за статистикой World of Tanks Blitz.\n\n"
        "Что умею:\n"
        "📊 Статистика игроков\n"
        "🏆 Рейтинг участников\n"
        "📈 Отчёты клана\n"
        "👥 Состав и активность игроков\n\n"
        "🚀 Вы можете проверить статистику игроков прямо сейчас.\n\n"
        "Для работы с функциями клана добавьте меня в групповой чат "
        "и выполните настройку клана.\n\n"
        "Выберите нужный раздел в меню ниже 👇\n\n"
        "👨‍💻 Разработчик: @Eodreid",
        reply_markup=main_menu()
    )

async def bot_added_to_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):

    print("🔥 BOT ADDED TO CHAT EVENT", flush=True)

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Да, права выданы",
                callback_data="admin_rights_yes"
            )
        ],
        [
            InlineKeyboardButton(
                "❌ Нет, ещё не выдал",
                callback_data="admin_rights_no"
            )
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "✅ BlitzClanBot добавлен в чат! 🏰\n\n"
            "Отлично! Давайте настроим меня для работы.\n\n"
            "Для полноценной работы мне нужны права администратора:\n\n"
            "☑️ Удаление сообщений\n"
            "☑️ Закрепление сообщений\n"
            "☑️ Управление сообщениями\n\n"
            "Без этих прав некоторые функции могут работать некорректно.\n\n"
            "Вы уже выдали мне права администратора?"
        ),
        reply_markup=reply_markup
    )  

async def receive_wot_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):

    print("RECEIVE WOT NICK STARTED", flush=True)

    nickname = update.message.text.strip()

    await update.message.reply_text(
        f"🔎 Проверяю игрока {nickname}..."
    )

    # пока только проверка через API
    response = requests.get(
        "https://api.wotblitz.eu/wotb/account/list/",
        params={
            "application_id": WG_APP_ID,
            "search": nickname
        },
        timeout=10
    )

    data = response.json()

    if data.get("status") != "ok" or not data.get("data"):
        await update.message.reply_text(
            "❌ Игрок не найден. Проверь ник."
        )
        return ConversationHandler.END


    account_id = None

    for player in data["data"]:
        if player["nickname"].lower() == nickname.lower():
            account_id = player["account_id"]
            nickname = player["nickname"]
            break


    if account_id is None:
        await update.message.reply_text(
            "❌ Точный ник не найден."
        )
        return ConversationHandler.END


    user = update.effective_user


    save_user(
        user.id,
        user.username,
        user.first_name,
        nickname,
        account_id
    )
    


    await update.message.reply_text(
        f"✅ Готово!\n\n"
        f"👤 {user.first_name}\n"
        f"🎮 {nickname}\n\n"
        f"Теперь я буду использовать этот аккаунт."
    )


    return ConversationHandler.END    

async def receive_stats_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):

    nickname = update.message.text.strip()

    context.args = [nickname]

    await stats(update, context)

    return ConversationHandler.END

async def receive_clan_tag(update: Update, context: ContextTypes.DEFAULT_TYPE):

    clan_tag = update.message.text.strip()

    print("RECEIVED CLAN TAG:", clan_tag, flush=True)

    context.args = [clan_tag]

    await setclan(update, context)

    return ConversationHandler.END

async def receive_history_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):

    nickname = update.message.text.strip()

    context.args = [nickname]

    await history(update, context)

    return ConversationHandler.END
    

async def myclan(update: Update, context: ContextTypes.DEFAULT_TYPE):

    

    clan = get_clan(update.effective_chat.id)


    if clan is None:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            message_thread_id=update.callback_query.message.message_thread_id,
            text=(
                "🏰 Клан ещё не привязан.\n\n"
                "Чтобы настроить функции клана:\n"
                "1️⃣ Добавьте бота в групповой чат.\n"
                "2️⃣ Выдайте боту права администратора:\n"
                "☑️ Удаление сообщений\n"
                "☑️ Закрепление сообщений\n"
                "☑️ Управление темами\n\n"
                "После этого администратор чата сможет выполнить привязку клана."
            )
        )
        return

    clan_id, clan_tag, clan_name = clan

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=update.callback_query.message.message_thread_id,
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
        
            f"🎮 *{player_name}*\n\n"
            f"🏰 Клан: {clan_name}\n"
            
            f"⚔️ Боёв: {f'{battles:,}'.replace(',', ' ')}\n"
            f"🏆 Победы: {f'{wins:,}'.replace(',', ' ')} ({winrate}%)\n\n"
            
            f"💥 Средний урон: {f'{avg_damage:,}'.replace(',', ' ')}\n"
            f"💀 Фраги: {f'{frags:,}'.replace(',', ' ')} ({avg_frags}/бой)\n"
            f"🎯 Точность: {accuracy}%\n\n"
            
            f"⭐ Средний опыт: {f'{avg_xp:,}'.replace(',', ' ')}\n"
            f"👁 Обнаружено: {f'{spotted:,}'.replace(',', ' ')}\n"
            f"🛡 Выжил в боях: {f'{survived:,}'.replace(',', ' ')}",
            
            parse_mode="Markdown"
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

    thread_id = None

    if update.message:
        thread_id = update.message.message_thread_id

    elif update.callback_query:
        thread_id = update.callback_query.message.message_thread_id

    

    clan = get_clan(update.effective_chat.id)

    if clan is None:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "❌ Клан ещё не привязан.\n\n"
                "Добавьте бота в групповой чат и выполните настройку клана."
            )
        )
        return

    clan_id, clan_tag, clan_name = clan

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=thread_id,
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
            message_thread_id=thread_id,
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
                    "damage": avg_damage,
                    "winrate": round(player.get("wins", 0) / battles * 100, 2) if battles else 0,
                    "battles": battles
                }
            )


    results.sort(
        key=lambda x: x["damage"],
        reverse=True
    )


    text = (
        "🏆 ТОП КЛАНА\n\n"
    )

    for i, player in enumerate(results[:5], start=1):

        if i == 1:
            icon = "🥇"
        elif i == 2:
            icon = "🥈"
        elif i == 3:
            icon = "🥉"
        else:
            icon = "🎮"
    
        text += (
            f"{icon} {player['name']}\n"
            f"💥{format_number(player['damage'])} | 🏆{player['winrate']}% | ⚔️{format_number(player['battles'])}\n\n"
        )


    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=thread_id,
        text=text
    )

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):

    print("🔥 REPORT FUNCTION START", flush=True)
    

    if not can_use_bot(update):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "⚠️ Для работы с ботом сначала добавьте его в групповой чат.\n\n"
                "После добавления бот станет доступен для работы с вашим кланом."
            )
        )
        return
    

    thread_id = None

    if update.message:
        thread_id = update.message.message_thread_id

    elif update.callback_query:
        thread_id = update.callback_query.message.message_thread_id


    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=thread_id,
        text="⏳ Собираю отчёт клана...\nЭто может занять немного времени."
    )

    clan_url = "https://api.wotblitz.eu/wotb/clans/info/"

    clan = get_clan(update.effective_chat.id)

    if clan is None:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            message_thread_id=thread_id,
            text=(
                "❌ Клан ещё не привязан.\n\n"
                "Добавьте бота в групповой чат и выполните настройку клана."
            )
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
            message_thread_id=thread_id,
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
            f"\n• {p['name']} — {format_number(p['battles'])} боёв"
        )

    if not low_text:
        low_text = "\nНет игроков"  

    text = (
        f"📊 Отчёт клана {clan_tag}\n\n"
        f"👥 Участников: {len(members_ids)}\n\n"
        f"⚔️ Всего боёв: {format_number(total_battles)}\n"
        f"🏆 Побед: {format_number(total_wins)}\n"
        f"📊 Средний WR: {winrate}%\n"
        f"💥 Средний урон: {format_number(avg_damage_clan)}\n\n"
        f"🥇 Лучший урон:\n"
        f"{best_damage['name']} — {best_damage['damage']}\n\n"
        f"🔥 ТОП по боям:\n"
        + "\n".join(
            [
                f"{i}. {p['name']} — {format_number(p['battles'])}"
                for i, p in enumerate(players_activity[:3], start=1)
            ]
        )
        + "\n\n"
        f"⚠️ Мало боёв:"
        f"{low_text}"
    )


    send_params = {
        "chat_id": update.effective_chat.id,
        "text": text
    }

    if thread_id:
        send_params["message_thread_id"] = thread_id

    await context.bot.send_message(
        **send_params
    )

async def members(update: Update, context: ContextTypes.DEFAULT_TYPE):

    print("🔥🔥🔥 MEMBERS FUNCTION ENTERED 🔥🔥🔥", flush=True)

    print("🚀🚀🚀 MEMBERS TEST 777 🚀🚀🚀", flush=True)
    print("🔥🔥🔥 I AM HERE MEMBERS BUTTON 🔥🔥🔥", flush=True)

    print("🔥🔥🔥 NEW MEMBERS CODE STARTED 🔥🔥🔥", flush=True)

    

    print("MEMBERS START", flush=True)

    thread_id = None

    if update.message:
        thread_id = update.message.message_thread_id

    elif update.callback_query:
        thread_id = update.callback_query.message.message_thread_id



    print("MEMBERS THREAD:", thread_id, flush=True)


    

    # Получаем привязанный клан из базы
    clan = get_clan(update.effective_chat.id)

    print("MEMBERS CLAN:", clan, flush=True)

    if clan is None:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            message_thread_id=thread_id,
            text=(
                "❌ Клан ещё не привязан.\n\n"
                "Добавьте бота в групповой чат и выполните настройку клана."
            )    
        )
        return

    loading_message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            message_thread_id=thread_id,
            text="⏳ Загружаю состав клана..."
    )


    clan_id, clan_tag, clan_name = clan
    print(
        "DEBUG CURRENT CLAN:",
        clan_id,
        clan_tag,
        clan_name,
        flush=True
    )

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

    print("MEMBERS API STATUS:", data.get("status"), flush=True)

    print("MEMBERS: clan API response received", flush=True)
    print(data, flush=True)


    if data.get("status") != "ok":
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            message_thread_id=thread_id,
            text="❌ Не удалось получить данные клана"
        )
        return


    members_ids = data["data"][str(clan_id)]["members_ids"]

    print(
        "DEBUG MEMBERS IDS COUNT:",
        len(members_ids),
        flush=True
    )
    
    clan_info = data["data"][str(clan_id)]

    leader_id = clan_info.get("leader_id")
    
    print("MEMBERS: players count", len(members_ids))
    print("MEMBERS: leader id", leader_id, flush=True)


    # Один запрос вместо 50 запросов
    members = []

    players_url = "https://api.wotblitz.eu/wotb/account/info/"


    # запрашиваем игроков группами по 10

    print("MEMBERS: START PLAYERS REQUEST", flush=True)
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

        print("MEMBERS: players response received", flush=True)
        print(players_response.status_code, flush=True)


        players_data = players_response.json()

        print("MEMBERS: json parsed", flush=True)
        print(players_data.get("status"), flush=True)

        print("MEMBERS: batch received", batch, flush=True)
        print("MEMBERS: players count in batch", len(players_data.get("data", {})), flush=True)
        print("MEMBERS PLAYERS STATUS:", players_data.get("status"), flush=True)
        print("MEMBERS: players API response received")


        if players_data.get("status") != "ok":
            continue


        for player in players_data["data"].values():

            print("MEMBERS: processing player", flush=True)
   

            if player is None:
                continue

            is_leader = player["account_id"] == leader_id
        
            stats = player.get("statistics", {}).get("all", {})
        
            battles = stats.get("battles", 0)
            wins = stats.get("wins", 0)
            damage = stats.get("damage_dealt", 0)
        
            winrate = round(wins / battles * 100, 2) if battles else 0
        
            avg_damage = round(damage / battles) if battles else 0
        
            members.append({
                "nickname": player["nickname"],
                "leader": is_leader,
                "battles": battles,
                "winrate": winrate,
                "avg_damage": avg_damage
            
            })

    print("MEMBERS: sorting", len(members), flush=True)

    members.sort(key=lambda x: not x["leader"])    
            
    text = (
        f"👥 Состав клана {clan_tag}\n\n"
        f"Всего игроков: {len(members)}\n\n"
    )
        
        
    for i, player in enumerate(members, start=1):

        crown = "👑 " if player["leader"] else ""
    
        text += (
            f"{i}. {crown}{player['nickname']}\n"
            f"⚔️ {player['battles']} боёв | 🏆 {player['winrate']}%\n"
            f"💥 {player['avg_damage']} С/У\n\n"
        )   
   


    message = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=thread_id,
        text=text
    )

    print("MEMBERS TEST MESSAGE SENT", message.message_id, flush=True)

async def cleanhistory(update: Update, context: ContextTypes.DEFAULT_TYPE):

    clean_history_duplicates()

    await update.message.reply_text(
        "✅ Дубли истории удалены"
    )

  

async def update_history(update: Update, context: ContextTypes.DEFAULT_TYPE):

    print("UPDATE COMMAND RECEIVED", flush=True)

    print("UPDATE_HISTORY START", flush=True)

   

    if update.effective_chat.type != "private":
        if not can_use_bot(update):
            await update.message.reply_text(
                "⚠️ Для работы с ботом сначала добавьте его в групповой чат.\n\n"
                "После добавления бот станет доступен для работы с вашим кланом."
            )
            return

    print("SENDING MESSAGE", flush=True)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=update.message.message_thread_id,
        text="⏳ Обновляю историю игроков..."
    )
    print("MESSAGE SENT", flush=True)

    print("BEFORE GET CLAN", flush=True)

    clan = get_clan(update.effective_chat.id)

    print("AFTER GET CLAN:", clan, flush=True)

    if clan is None:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            message_thread_id=update.message.message_thread_id,
            text="❌ Сначала привяжите клан:\n/setclan [TAG]"
        )
        return


    clan_id, clan_tag, clan_name = clan


    clan_url = "https://api.wotblitz.eu/wotb/clans/info/"

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
            text="❌ Не удалось получить клан"
        )
        return


    members_ids = clan_data["data"][str(clan_id)]["members_ids"]
    print("MEMBERS:", len(members_ids), flush=True)


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
            damage,
            clan_id
        )

        saved += 1

    set_last_update(
        datetime.now().strftime("%Y-%m-%d")
    )    


    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=update.message.message_thread_id,
        text=(
            f"✅ История обновлена\n"
            f"Сохранено игроков: {saved}"
        )
    )

async def auto_update_history(context: ContextTypes.DEFAULT_TYPE):

    print("AUTO UPDATE: START", flush=True)

    clans = get_all_clans()

    print("AUTO UPDATE CLANS:", clans, flush=True)


    if not clans:
        print("AUTO UPDATE: NO CLANS FOUND", flush=True)
        return


    for chat_id, clan_id, clan_tag, clan_name in clans:

        print(
            "AUTO UPDATE CLAN:",
            clan_tag,
            clan_id,
            flush=True
        )


        clan_url = "https://api.wotblitz.eu/wotb/clans/info/"

        clan_params = {
            "application_id": WG_APP_ID,
            "clan_id": clan_id
        }


        try:

            clan_response = requests.get(
                clan_url,
                params=clan_params,
                timeout=10
            )

            clan_data = clan_response.json()

        except Exception as e:

            print(
                "AUTO UPDATE CLAN ERROR:",
                e,
                flush=True
            )

            continue


        if clan_data.get("status") != "ok":

            print(
                "AUTO UPDATE: CLAN API ERROR",
                clan_tag,
                flush=True
            )

            continue


        members_ids = clan_data["data"][str(clan_id)]["members_ids"]


        print(
            "AUTO UPDATE MEMBERS:",
            clan_tag,
            len(members_ids),
            flush=True
        )


        saved = 0


        for account_id in members_ids:


            print(
                "AUTO CHECK PLAYER:",
                account_id,
                flush=True
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

                if stats_data.get("status") != "ok":
                    continue

                account = stats_data["data"].get(str(account_id))

                if not account:
                    continue

                nickname = account["nickname"]

                player = account.get(
                    "statistics",
                    {}
                ).get(
                    "all",
                    {}
                )

                battles = player.get(
                    "battles",
                    0
                )

                damage = player.get(
                    "damage_dealt",
                    0
                )

                print(
                    "SAVING HISTORY:",
                    nickname,
                    flush=True
                )

                save_player_history(
                    account_id,
                    nickname,
                    battles,
                    damage,
                    clan_id
                )

                print(
                    "HISTORY SAVED:",
                    nickname,
                    flush=True
                )

                saved += 1

            except Exception as e:
                print(
                    "PLAYER ERROR:",
                    account_id,
                    e,
                    flush=True
                )
                continue


        print(
            "AUTO UPDATE CLAN DONE:",
            clan_tag,
            "SAVED:",
            saved,
            flush=True
        )



    set_last_update(
        datetime.now().strftime("%Y-%m-%d")
    )


    print(
        "AUTO UPDATE FINISHED",
        flush=True
    )    

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):

    

    if not context.args:
        await update.message.reply_text(
            "Использование:\n/history ник"
        )
        return

    nickname = context.args[0]

    # Поиск игрока через WG API
    url = "https://api.wotblitz.eu/wotb/account/list/"

    params = {
        "application_id": WG_APP_ID,
        "search": nickname
    }

    response = requests.get(
        url,
        params=params,
        timeout=10
    )

    data = response.json()

    if data.get("status") != "ok" or not data.get("data"):
        await update.message.reply_text(
            "❌ Игрок не найден"
        )
        return


    account_id = data["data"][0]["account_id"]


    # Берём историю из PostgreSQL
    history_data = get_player_history(account_id)

    print("HISTORY ACCOUNT ID:", account_id, flush=True)
    print("HISTORY DATA:", history_data, flush=True)


    if not history_data:
        await update.message.reply_text(
            "📭 Истории пока нет.\n"
            "Используйте /update для сохранения статистики."
        )
        return


    text = (
        f"📜 История игрока\n\n"
        f"👤 {nickname}\n\n"
    )


    for row in reversed(history_data):

        name, battles, damage, date = row

        text += (
            f"📅 {date}\n"
            f"⚔️ Бои: {format_number(battles)}\n"
            f"💥 Урон: {format_number(damage)}\n\n"
      )


    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text
    )
        


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    print("🔥🔥🔥 BUTTON HANDLER START 🔥🔥🔥", flush=True)

    query = update.callback_query

    await query.answer()

    user_id = update.effective_user.id

    print("BUTTON PRESSED:", query.data, flush=True)
    print("USER ID:", user_id, flush=True)
    print("CHAT TYPE:", update.effective_chat.type, flush=True)
    print("IS DEVELOPER:", is_developer(user_id), flush=True)



    # ====== СЮДА ВОЗВРАЩАЕМ ЛОГИКУ КНОПОК ======

    print("BUTTON:", query.data, flush=True)

    if query.data == "admin_rights_no":

        await query.message.reply_text(
            "⚠️ Для полноценной работы мне нужны права администратора:\n\n"
            "☑️ Удаление сообщений\n"
            "☑️ Закрепление сообщений\n"
            "☑️ Управление сообщениями\n\n"
            "После выдачи прав нажмите:\n"
            "✅ Да, права выданы"
        )

        return


    elif query.data == "admin_rights_yes":

        keyboard = [
            [
                InlineKeyboardButton(
                    "🏰 Привязать клан",
                    callback_data="setclan"
                )
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.reply_text(
            "🎉 Отлично!\n\n"
            "Теперь осталось привязать ваш клан.\n\n"
            "👇 Нажмите кнопку:",
            reply_markup=reply_markup
        )

        return

    if query.data == "link_wot":

        await query.message.reply_text(
            "🎮 Введите ваш ник в WoT Blitz:"
        )

        return WAIT_WOT_NICK


    if query.data == "stats":

        await query.message.reply_text(
            "📊 Введите ник игрока:"
        )

        return WAIT_STATS_NICK


    elif query.data == "history":

        await query.message.reply_text(
            "📜 Введите ник игрока для истории:"
        )

        return WAIT_HISTORY_NICK


    elif query.data == "members":

        await members(update, context)


    elif query.data == "top":

        await top(update, context)


      
    elif query.data == "report":

        print("🔥 REPORT BUTTON PRESSED", flush=True)

        await report(update, context)


    elif query.data == "myclan":

        await myclan(update, context)


    elif query.data == "setclan":

        if is_developer(user_id):
            pass

        else:

            member = await context.bot.get_chat_member(
                chat_id=update.effective_chat.id,
                user_id=user_id
            )

            if member.status not in ["administrator", "creator"]:
                await query.message.reply_text(
                    "❌ Только администраторы группы могут привязать клан.\n\n"
                    "Попросите администратора выполнить настройку клана."
                )
                return

        await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "🏰 Введите тег вашего клана.\n\n"
            "Например: [1PVS]\n\n"
            "⚠️ Введите только тег клана, без названия."
        )
    )

        return WAIT_CLAN_TAG


    elif query.data == "settings":

        await query.message.reply_text(
            "⚙️ Настройки пока в разработке"
        )    

# Flask для Render

web = Flask(__name__)


@web.route("/")
def home():
    return "BlitzClanBot is running!"
    
async def setclan(update: Update, context: ContextTypes.DEFAULT_TYPE):

    print("🔥 SETCLAN CALLED", flush=True)

    chat_id = update.effective_chat.id

    user_id = update.effective_user.id

    if not is_developer(user_id):

        member = await context.bot.get_chat_member(
            chat_id=update.effective_chat.id,
            user_id=user_id
        )

        if member.status not in ["administrator", "creator"]:
            await update.message.reply_text(
                "❌ Только администраторы группы могут привязать клан.\n\n"
                "Попросите администратора выполнить настройку клана."
            )
            return

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

    found_clan = None

    for clan in data["data"]:
        if clan["tag"].upper() == clan_tag:
            found_clan = clan
            break


    if found_clan is None:
        await update.message.reply_text(
            "❌ Клан с таким тегом не найден"
        )
        return


    clan_id = found_clan["clan_id"]
    clan_name = found_clan["name"]
    clan_tag = found_clan["tag"]

    save_clan(
        chat_id,
        clan_id,
        clan_tag,
        clan_name
    )

    await update.message.reply_text(
        "🎉 Настройка завершена!\n\n"
        f"🏰 Клан успешно привязан: {clan_tag}\n\n"
        "BlitzClanBot готов к работе.",
    )

    

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    if update.effective_chat.type != "private":
        return

    if is_developer(user_id):
        await update.message.reply_text(
            "🤖 BlitzClanBot\n\n"
            "Выберите действие:",
            reply_markup=main_menu()
        )
        return

    await update.message.reply_text(
        "🤖 Добро пожаловать в BlitzClanBot!\n\n"
        "Я помогу следить за статистикой World of Tanks Blitz.\n\n"
        "Что умею:\n"
        "📊 Статистика игроков\n"
        "🏆 Рейтинг участников\n"
        "📈 Отчёты клана\n"
        "👥 Состав и активность игроков\n\n"
        "Для начала необходимо добавить меня в групповой чат.\n\n"
        "👇 Нажмите кнопку ниже.",
        reply_markup=main_menu()
    )

async def set_commands(app):

    commands = [
        BotCommand("stats", "📊 Статистика игрока"),
        BotCommand("clanreport", "🏰 Отчет клана"),
        BotCommand("history", "📈 История игрока"),
        BotCommand("members", "👥 Состав клана"),
        BotCommand("top", "🏆 Топ игроков клана"),
        BotCommand("update", "🔄 Обновить историю"),
        BotCommand("menu", "📋 Меню бота"),
    ]

    await app.bot.set_my_commands(commands)

def is_developer(user_id):
    return user_id == DEVELOPER_ID 

def can_use_bot(update):
    user_id = update.effective_user.id
    chat_type = update.effective_chat.type

    # Разработчик имеет полный доступ
    if is_developer(user_id):
        return True

    # В группах бот работает
    if chat_type in ["group", "supergroup"]:
        return True

    # В личке обычным пользователям нельзя
    return False   


    
def run_bot():

    print("RUN_BOT STARTED")

    print("CREATING TELEGRAM APP")

    

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )
    app.post_init = set_commands

    print("TELEGRAM APP CREATED", flush=True)

    app.job_queue.run_repeating(
        auto_update_history,
        interval=86400,
        first=30
    )

    print("AUTO UPDATE SCHEDULER ENABLED", flush=True)

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
            ChatMemberHandler(
                bot_added_to_chat,
                ChatMemberHandler.MY_CHAT_MEMBER
            )
        )
    
    app.add_handler(CommandHandler("setclan", setclan))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("myclan", myclan))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CommandHandler("update", update_history))
    print("UPDATE HANDLER REGISTERED", flush=True)
    app.add_handler(
        ConversationHandler(
            entry_points=[

                CallbackQueryHandler(
                    button_handler,
                    pattern="^(stats|history|setclan|link_wot)$"
                )

            ],
        per_message=False,

        states={
            WAIT_STATS_NICK: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_stats_nick
                )
            ],

            WAIT_WOT_NICK: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_wot_nick
                )
            ],

            WAIT_HISTORY_NICK: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_history_nick
                )
           ],

           WAIT_CLAN_TAG: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_clan_tag
                )
            ]
        },
        fallbacks=[]
    )
)

    app.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

   
    
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("clanreport", report))
    app.add_handler(CommandHandler("members", members))
    app.add_handler(CommandHandler("cleanhistory", cleanhistory))
    

        
    print("BOT STARTED")
    print("STARTING POLLING")
    print("STARTING TELEGRAM POLLING", flush=True)
    
    app.run_polling(
        drop_pending_updates=True,
        stop_signals=None
    ) 


print("START BOT THREAD")

thread = Thread(target=run_bot, daemon=True)
thread.start()

print("Starting Flask...")

web.run(
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 10000))
)
