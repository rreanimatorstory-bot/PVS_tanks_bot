from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu():

    keyboard = [
        [
            InlineKeyboardButton(
                "➕ Добавить бота в чат",
                url="https://t.me/PVS_tanks_bot?startgroup=true"
            )
        ],
        [
            InlineKeyboardButton("🏰 Привязать клан", callback_data="setclan"),
        ],
        [
            InlineKeyboardButton("📊 Статистика игрока", callback_data="stats"),
            InlineKeyboardButton("📜 История игрока", callback_data="history")
        ],
        [
            InlineKeyboardButton("👥 Состав клана", callback_data="members"),
            InlineKeyboardButton("🏆 ТОП игроков", callback_data="top")
        ],
        [
            InlineKeyboardButton("📈 Отчёт клана TEST", callback_data="test_report"),
            InlineKeyboardButton("🏰 Мой клан", callback_data="myclan")
        ],
        [
            InlineKeyboardButton("⚙️ Настройки", callback_data="settings")
        ]
    ]

    return InlineKeyboardMarkup(keyboard)

    

def user_menu():

    keyboard = [
        [
            InlineKeyboardButton(
                "🎮 Привязать WoT ник",
                callback_data="link_wot"
            )
        ],
        [
            InlineKeyboardButton(
                "📊 Статистика игрока",
                callback_data="stats"
            ),
            InlineKeyboardButton(
                "📜 История игрока",
                callback_data="history"
            )
        ],
        [
            InlineKeyboardButton(
                "👥 Состав клана",
                callback_data="members"
            ),
            InlineKeyboardButton(
                "🏆 ТОП игроков",
                callback_data="top"
            )
        ],
        [
            InlineKeyboardButton(
                "📈 Отчёт клана",
                callback_data="report"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)