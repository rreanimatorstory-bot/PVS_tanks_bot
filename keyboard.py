from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu():

    keyboard = [
        [
            InlineKeyboardButton("📊 Статистика", callback_data="stats"),
            InlineKeyboardButton("📜 История", callback_data="history")
        ],
        [
            InlineKeyboardButton("👥 Состав клана", callback_data="members"),
            InlineKeyboardButton("🏆 ТОП игроков", callback_data="top")
        ],
        [
            InlineKeyboardButton("📈 Отчёт клана", callback_data="report"),
            InlineKeyboardButton("🏰 Мой клан", callback_data="myclan")
        ],
        [
            InlineKeyboardButton("⚙️ Настройки", callback_data="settings")
        ]
    ]

    return InlineKeyboardMarkup(keyboard)