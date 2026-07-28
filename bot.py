import httpx

# Создаем один клиент на все время работы приложения
http_client = httpx.AsyncClient(timeout=10.0)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование:\n/stats ник")
        return

    nickname = context.args[0]
    await update.message.reply_text(f"🔎 Ищу игрока {nickname}...")

    try:
        # ---------- 1. Поиск игрока по нику ----------
        search_res = await http_client.get(
            "https://api.wotblitz.eu/wotb/account/list/",
            params={"application_id": WG_APP_ID, "search": nickname}
        )
        search_data = search_res.json()

        if search_data.get("status") != "ok" or not search_data.get("data"):
            await update.message.reply_text("❌ Игрок не найден")
            return

        account_id = search_data["data"][0]["account_id"]

        # ---------- 2. Получение статистики игрока ----------
        info_res = await http_client.get(
            "https://api.wotblitz.eu/wotb/account/info/",
            params={"application_id": WG_APP_ID, "account_id": account_id}
        )
        info_data = info_res.json()

        if info_data.get("status") != "ok" or not info_data["data"].get(str(account_id)):
            await update.message.reply_text("❌ Не удалось получить статистику")
            return

        account = info_data["data"][str(account_id)]
        
        # Защита от скрытой статистики (приватный профиль)
        if account.get("private") or not account.get("statistics"):
            await update.message.reply_text("🔒 Профиль игрока скрыт настройками приватности.")
            return

        player_name = account["nickname"]
        stats_all = account["statistics"]["all"]

        battles = stats_all.get("battles", 0)
        wins = stats_all.get("wins", 0)
        damage = stats_all.get("damage_dealt", 0)
        frags = stats_all.get("frags", 0)
        shots = stats_all.get("shots", 0)
        hits = stats_all.get("hits", 0)
        xp = stats_all.get("xp", 0)
        spotted = stats_all.get("spotted", 0)
        survived = stats_all.get("survived_battles", 0)

        # ---------- 3. ИСПРАВЛЕНО: Получение клана игрока ----------
        clan_text = "Без клана"
        clan_res = await http_client.get(
            "https://wotblitz.eu",
            params={"application_id": WG_APP_ID, "account_id": account_id}
        )
        clan_data = clan_res.json()

        if clan_data.get("status") == "ok" and clan_data["data"].get(str(account_id)):
            player_clan_data = clan_data["data"][str(account_id)]
            if player_clan_data and player_clan_data.get("clan"):
                clan_text = f"[{player_clan_data['clan']['tag']}]"

        # ---------- 4. Расчеты ----------
        winrate = round(wins / battles * 100, 2) if battles else 0
        avg_damage = round(damage / battles) if battles else 0
        avg_frags = round(frags / battles, 2) if battles else 0
        accuracy = round(hits / shots * 100, 2) if shots else 0
        avg_xp = round(xp / battles) if battles else 0

        # Сохранение в историю (Важно: если ваша БД sqlite3 не асинхронная, 
        # вызов функции заблокирует поток на миллисекунды, но для сохранения 1 записи это не критично)
        try:
            save_player_history(account_id, player_name, battles, damage)
        except Exception as db_err:
            print(f"Ошибка БД: {db_err}")

        # ---------- 5. Ответ ----------
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
        print(f"Ошибка в stats: {e}")
        await update.message.reply_text("❌ Произошла ошибка при получении статистики.")


async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clan = get_clan(update.effective_chat.id)
    if clan is None:
        await update.message.reply_text("❌ Сначала привяжите клан:\n/setclan [TAG]")
        return

    clan_id, clan_tag, clan_name = clan

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=update.message.message_thread_id,
        text=f"⏳ Считаю статистику клана {clan_tag}..."
    )

    try:
        # ---------- 1. Получаем список ID членов клана ----------
        clan_res = await http_client.get(
            "https://api.wotblitz.eu/wotb/clans/info/",
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

        # ---------- 2. ОПТИМИЗАЦИЯ: Один запрос для ВСЕХ игроков ----------
        # Передаем ID через запятую: "123,456,789"
        account_ids_str = ",".join(map(str, members_ids))
        
        stats_res = await http_client.get(
            "https://api.wotblitz.eu/wotb/account/info/",
            params={"application_id": WG_APP_ID, "account_id": account_ids_str}
        )
        stats_data = stats_res.json()

        if stats_data.get("status") != "ok":
            await update.message.reply_text("❌ Не удалось получить статистику участников.")
            return

        players_stats = stats_data["data"]
        leaderboard = []

        # ---------- 3. Сбор и расчет параметров ----------
        for p_id_str, p_data in players_stats.items():
            if not p_data or p_data.get("private") or not p_data.get("statistics"):
                continue  # Пропускаем скрытые профили
            
            nickname = p_data["nickname"]
            all_b = p_data["statistics"]["all"]
            battles = all_b.get("battles", 0)
            damage = all_b.get("damage_dealt", 0)
            
            avg_dmg = round(damage / battles) if battles > 0 else 0
            
            leaderboard.append({
                "nickname": nickname,
                "battles": battles,
                "avg_dmg": avg_dmg
            })

        # Сортируем по среднему урону (от большего к меньшему)
        leaderboard.sort(key=lambda x: x["avg_dmg"], reverse=True)

        # ---------- 4. Формирование вывода (ТОП-15) ----------
        response_text = f"🏆 **ТОП клана {clan_tag} по ср. урону:**\n\n"
        for index, player in enumerate(leaderboard[:15], start=1):
            response_text += f"{index}. `{player['nickname']}` — {player['avg_dmg']:,} СУ ({player['battles']:,} боев)\n"

        await update.message.reply_text(response_text, parse_mode="Markdown")

    except Exception as e:
        print(f"Ошибка в top: {e}")
        await update.message.reply_text("❌ Произошла ошибка при составлении ТОПа.")
