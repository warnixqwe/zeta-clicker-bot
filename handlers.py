import sqlite3
import os
import asyncio
from datetime import datetime
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery

from database import *
from keyboards import *
from config import BOT_TOKEN, ADMIN_ID

router = Router()
DB_PATH = os.path.join(os.path.dirname(__file__), "zeta_clicker.db")

# ==================== ОСНОВНЫЕ КОМАНДЫ ====================

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    parts = message.text.split()
    if len(parts) > 1 and parts[1].startswith("ref_"):
        referrer_id = int(parts[1].split("_")[1])
        if referrer_id != user_id:
            add_referral(referrer_id, user_id)
    init_db()
    get_user_stats(user_id)
    await message.answer(
        f"🦆 **Добро пожаловать в Zeta Clicker!**\n\n"
        f"Жми на кнопку ниже, чтобы зарабатывать клики.\n"
        f"Твой ID: `{user_id}`",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@router.message(Command("donate"))
async def cmd_donate(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("❌ Используй: `/donate <количество звезд>`\nПример: `/donate 100`", parse_mode="Markdown")
        return
    amount = int(parts[1])
    if amount < 1 or amount > 2500:
        await message.answer("❌ Сумма должна быть от 1 до 2500 звезд")
        return
    payload = f"donate_{message.from_user.id}_{amount}_{int(datetime.now().timestamp())}"
    try:
        invoice_link = await message.bot.create_invoice_link(
            title="Поддержка проекта 💫",
            description=f"Донат {amount} Telegram Stars",
            payload=payload,
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="XTR", amount=amount)],
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"💎 Оплатить {amount} ⭐️", url=invoice_link)]
        ])
        await message.answer(
            f"🌟 Поддержи проект за {amount} ⭐️!\nНажми на кнопку ниже.",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@router.message(Command("game"))
async def cmd_game(message: types.Message):
    user_id = message.from_user.id
    base_url = os.environ.get("PUBLIC_URL", "https://zeta-clicker-bot-2.up.railway.app")
    web_app_url = f"{base_url}/?user_id={user_id}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Играть в Zeta Clicker! 🦆", web_app=types.WebAppInfo(url=web_app_url))]
    ])
    await message.answer(
        "🦆 **Zeta Clicker — Mini App версия!**\n\n"
        "Нажми на кнопку ниже, чтобы открыть игру с живыми анимациями!\n\n"
        "✨ **Фичи:**\n"
        "• Живая анимация клика\n"
        "• Система энергии\n"
        "• Уровни и прокачка\n"
        "• Всплывающие числа\n\n"
        "Погнали! 🚀",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# ==================== CALLBACK-ЗАПРОСЫ ====================

@router.callback_query(lambda c: c.data == "tap")
async def handle_tap(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    clicks, level, energy, tap_power, passive_income, _, current_skin, total_clicks, _ = get_user_stats(user_id)
    if energy <= 0:
        await callback.answer("😫 Нет энергии!", show_alert=True)
        return
    skin_bonus = 0
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT tap_bonus FROM skins WHERE emoji = ?", (current_skin,))
    result = cursor.fetchone()
    if result:
        skin_bonus = result[0]
    conn.close()
    new_clicks, new_level, new_energy = update_tap(user_id, 1, skin_bonus)
    await callback.answer("🦆 КВАК!", show_alert=False)
    await callback.message.edit_text(
        f"🦆 **Zeta Clicker**\n\n"
        f"📊 Клики: {new_clicks}\n"
        f"🏆 Уровень: {new_level}\n"
        f"⚡ Энергия: {new_energy}/1000\n"
        f"💪 Сила тапа: +{tap_power + skin_bonus}\n\n"
        f"👇 Жми дальше!",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(lambda c: c.data == "main_menu")
async def back_to_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    clicks, level, energy, tap_power, passive_income, _, _, _, _ = get_user_stats(user_id)
    await callback.message.edit_text(
        f"🦆 **Zeta Clicker**\n\n"
        f"📊 Клики: {clicks}\n"
        f"🏆 Уровень: {level}\n"
        f"⚡ Энергия: {energy}/1000\n"
        f"💪 Сила тапа: +{tap_power}",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(lambda c: c.data == "profile")
async def handle_profile(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    clicks, level, energy, tap_power, passive_income, premium_until, current_skin, total_clicks, daily_streak = get_user_stats(user_id)
    profile_text = (
        f"🦆 **Профиль игрока**\n\n"
        f"📊 Всего кликов: `{total_clicks}`\n"
        f"💎 Доступно: `{clicks}`\n"
        f"🏆 Уровень: `{level}`\n"
        f"💪 Сила тапа: `+{tap_power}`\n"
        f"👕 Текущий скин: `{current_skin}`\n"
        f"📅 Серия: `{daily_streak} дней`"
    )
    await callback.message.edit_text(profile_text, reply_markup=get_back_keyboard(), parse_mode="Markdown")

@router.callback_query(lambda c: c.data == "daily")
async def handle_daily(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    bonus, streak = claim_daily_bonus(user_id)
    if bonus == 0:
        await callback.answer("🎁 Ты уже забирал бонус сегодня!", show_alert=True)
        return
    await callback.answer(f"🎁 +{bonus} кликов! Серия: {streak} дней!", show_alert=True)
    await back_to_menu(callback)

@router.callback_query(lambda c: c.data == "shop")
async def handle_shop(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    skins = get_skins_list()
    user_skins = get_user_skins(user_id)
    _, _, _, _, _, _, current_skin, _, _ = get_user_stats(user_id)
    await callback.message.edit_text(
        "👕 **Магазин скинов**\nВыбери скин для своей утки:",
        reply_markup=get_shop_keyboard(skins, user_skins, current_skin),
        parse_mode="Markdown"
    )

@router.callback_query(lambda c: c.data.startswith("buy_skin_"))
async def handle_buy_skin(callback: types.CallbackQuery):
    skin_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    if buy_skin(user_id, skin_id):
        await callback.answer("✅ Скин куплен!", show_alert=True)
    else:
        await callback.answer("❌ Не хватает кликов или уже есть", show_alert=True)
    await handle_shop(callback)

@router.callback_query(lambda c: c.data.startswith("equip_skin_"))
async def handle_equip_skin(callback: types.CallbackQuery):
    skin_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    if equip_skin(user_id, skin_id):
        await callback.answer("✅ Скин экипирован!", show_alert=True)
    else:
        await callback.answer("❌ Ошибка", show_alert=True)
    await handle_shop(callback)

@router.callback_query(lambda c: c.data == "referrals")
async def handle_referrals(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    count = get_referral_count(user_id)
    bot_username = (await callback.bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    text = (
        f"👥 **Реферальная система**\n\n"
        f"Ты пригласил: `{count}` друзей\n"
        f"За каждого друга ты получишь `1000` кликов!\n\n"
        f"🔗 **Твоя реферальная ссылка:**\n"
        f"`{referral_link}`\n\n"
        f"👇 Отправь её друзьям и получай награду!"
    )
    await callback.message.edit_text(text, reply_markup=get_referral_keyboard(), parse_mode="Markdown")

@router.callback_query(lambda c: c.data == "claim_referral")
async def handle_claim_referral(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    reward = claim_referral_reward(user_id)
    if reward == 0:
        await callback.answer("😢 Нет новых рефералов для награды!", show_alert=True)
        return
    await callback.answer(f"🎉 +{reward} кликов за рефералов!", show_alert=True)
    await back_to_menu(callback)

@router.callback_query(lambda c: c.data == "quests")
async def handle_quests(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    quests = get_daily_quests(user_id)
    text = "📋 **Ежедневные задания**\n\n"
    for q in quests:
        status = "✅" if q['completed'] else "🔄"
        text += f"{status} **{q['name']}**\n"
        text += f"   {q['description']}\n"
        text += f"   Прогресс: {q['progress']}/{q['target']}\n"
        text += f"   Награда: +{q['reward']} кликов\n\n"
    await callback.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="Markdown")

@router.callback_query(lambda c: c.data == "upgrades")
async def handle_upgrades(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    clicks, level, energy, tap_power, passive_income, _, _, _, _ = get_user_stats(user_id)
    tap_price = tap_power * 100
    energy_price = (energy // 100) * 100
    passive_price = 500 + passive_income * 100
    text = (
        f"💎 **Прокачка**\n\n"
        f"💪 Сила тапа: +{tap_power} (след. уровень: {tap_price} кликов)\n"
        f"⚡ Энергия: {energy}/1000 (след. уровень: {energy_price} кликов)\n"
        f"💰 Пассивный доход: +{passive_income}/час (след. уровень: {passive_price} кликов)\n"
    )
    await callback.message.edit_text(text, reply_markup=get_upgrades_keyboard(tap_price, energy_price, passive_price), parse_mode="Markdown")

@router.callback_query(lambda c: c.data == "upgrade_tap")
async def handle_upgrade_tap(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    success, new_power, price = upgrade_tap_power(user_id)
    if success:
        await callback.answer(f"✅ Сила тапа увеличена до +{new_power}!", show_alert=True)
    else:
        await callback.answer(f"❌ Не хватает кликов! Нужно: {price}", show_alert=True)
    await handle_upgrades(callback)

@router.callback_query(lambda c: c.data == "upgrade_energy")
async def handle_upgrade_energy(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    success, new_energy, price = upgrade_energy(user_id)
    if success:
        await callback.answer(f"✅ Энергия увеличена до {new_energy}!", show_alert=True)
    else:
        await callback.answer(f"❌ Не хватает кликов! Нужно: {price}", show_alert=True)
    await handle_upgrades(callback)

@router.callback_query(lambda c: c.data == "upgrade_passive")
async def handle_upgrade_passive(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    success, new_income, price = upgrade_passive_income(user_id)
    if success:
        await callback.answer(f"✅ Пассивный доход увеличен до +{new_income}/час!", show_alert=True)
    else:
        await callback.answer(f"❌ Не хватает кликов! Нужно: {price}", show_alert=True)
    await handle_upgrades(callback)

@router.callback_query(lambda c: c.data == "premium")
async def handle_premium(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    is_prem = is_premium(user_id)
    if is_prem:
        text = f"⭐ **Премиум активен!**\n\nБонусы:\n✅ +50% к пассивному доходу\n✅ Ускоренное восстановление энергии\n✅ Эксклюзивные скины"
        await callback.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="Markdown")
    else:
        text = "⭐ **Премиум подписка**\n\nБонусы:\n✅ +50% к пассивному доходу\n✅ Ускоренное восстановление энергии\n✅ Эксклюзивные скины\n\n💰 Цена: 5000 кликов за 30 дней"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 Купить премиум (5000 кликов)", callback_data="buy_premium")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

@router.callback_query(lambda c: c.data == "buy_premium")
async def handle_buy_premium(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if buy_premium(user_id, 30):
        await callback.answer("✅ Премиум подписка активирована на 30 дней!", show_alert=True)
    else:
        await callback.answer("❌ Не хватает кликов! Нужно 5000", show_alert=True)
    await handle_premium(callback)

@router.callback_query(lambda c: c.data == "leaderboard")
async def handle_leaderboard(callback: types.CallbackQuery):
    leaderboard = get_leaderboard(10)
    if not leaderboard:
        text = "🏆 **Топ-10 игроков**\n\nПока никого нет, будь первым!"
    else:
        text = "🏆 **Топ-10 игроков**\n\n"
        for i, (user_id, total_clicks) in enumerate(leaderboard, 1):
            text += f"{i}. `{user_id}` — {total_clicks} кликов\n"
    await callback.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="Markdown")

@router.callback_query(lambda c: c.data == "collect_passive")
async def handle_collect_passive(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    earned = collect_passive_income(user_id)
    if earned > 0:
        await callback.answer(f"💰 +{earned} кликов от пассивного дохода!", show_alert=True)
    else:
        await callback.answer("😴 Пассивный доход ещё не накоплен. Подожди немного или улучши доход!", show_alert=True)
    await back_to_menu(callback)

# ==================== ПЛАТЕЖИ ====================

@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@router.message(lambda message: message.successful_payment is not None)
async def process_successful_payment(message: types.Message):
    user_id = message.from_user.id
    amount = message.successful_payment.total_amount
    bonus_clicks = amount * 1000
    add_clicks(user_id, bonus_clicks)
    await message.answer(
        f"✅ **Спасибо за донат!**\n\n"
        f"Ты перевел `{amount} ⭐️`\n"
        f"Баланс пополнен на `{bonus_clicks} кликов`!",
        parse_mode="Markdown"
    )

# ==================== АДМИН-ПАНЕЛЬ ====================

@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа к админ-панели!")
        return
    await message.answer("👑 **Админ-панель Zeta Clicker**\n\nВыбери действие:", reply_markup=get_admin_keyboard(), parse_mode="Markdown")

@router.callback_query(lambda c: c.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа!", show_alert=True)
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(total_clicks) FROM users")
    total_clicks = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM users WHERE premium_until > datetime('now')")
    premium_users = cursor.fetchone()[0]
    today = datetime.now().date().isoformat()
    cursor.execute("SELECT COUNT(*) FROM users WHERE last_daily = ?", (today,))
    active_today = cursor.fetchone()[0]
    conn.close()
    text = f"📊 **Статистика бота**\n\n👥 Всего пользователей: `{total_users}`\n💰 Всего кликов: `{total_clicks}`\n⭐ Премиум пользователей: `{premium_users}`\n📅 Активных сегодня: `{active_today}`"
    await callback.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(lambda c: c.data == "admin_users")
async def admin_users(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа!", show_alert=True)
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, total_clicks, level FROM users ORDER BY total_clicks DESC LIMIT 20")
    users = cursor.fetchall()
    conn.close()
    if not users:
        text = "👥 **Пользователи**\n\nПока никого нет"
    else:
        text = "👥 **Топ-20 пользователей**\n\n"
        for i, (uid, clicks, lvl) in enumerate(users, 1):
            text += f"{i}. ID: `{uid}` | Уровень: {lvl} | Кликов: {clicks}\n"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✉️ Отправить сообщение пользователю", callback_data="admin_send_message")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(lambda c: c.data == "admin_send_message")
async def admin_send_message_prompt(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа!", show_alert=True)
        return
    await callback.message.edit_text(
        "✉️ **Отправка сообщения пользователю**\n\n"
        "Введите команду в формате:\n"
        "`/send user_id текст сообщения`\n\n"
        "Пример: `/send 123456789 Привет! Это админ`\n\n"
        "Или нажмите кнопку ниже для отмены.",
        reply_markup=get_back_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(Command("send"))
async def admin_send_message(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("❌ Формат: `/send user_id текст`", parse_mode="Markdown")
        return
    try:
        target_user_id = int(parts[1])
        text_to_send = parts[2]
        await message.bot.send_message(target_user_id, f"📨 **Сообщение от администратора:**\n\n{text_to_send}", parse_mode="Markdown")
        await message.answer(f"✅ Сообщение отправлено пользователю `{target_user_id}`", parse_mode="Markdown")
    except ValueError:
        await message.answer("❌ Неверный формат user_id")
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке: {e}")

@router.callback_query(lambda c: c.data == "admin_top_donors")
async def admin_top_donors(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа!", show_alert=True)
        return
    donors = get_top_donors(10)
    if not donors:
        text = "💰 **Топ-10 донатеров**\n\nПока никого нет"
    else:
        text = "💰 **Топ-10 донатеров**\n\n"
        for i, (uid, clicks) in enumerate(donors, 1):
            text += f"{i}. ID: `{uid}` — {clicks} кликов\n"
    await callback.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(lambda c: c.data == "admin_mailing")
async def admin_mailing_prompt(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа!", show_alert=True)
        return
    await callback.message.edit_text(
        "📨 **Рассылка**\n\n"
        "Введите команду в формате:\n"
        "`/mail текст сообщения`\n\n"
        "Пример: `/mail Всем привет! Обновление бота!`",
        reply_markup=get_back_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(Command("mail"))
async def admin_mailing(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ Формат: `/mail текст`", parse_mode="Markdown")
        return
    text_to_mail = parts[1]
    users = get_all_users()
    success = 0
    fail = 0
    await message.answer(f"📨 Начинаю рассылку для {len(users)} пользователей...")
    for uid in users:
        try:
            await message.bot.send_message(uid, f"📢 **Массовая рассылка:**\n\n{text_to_mail}", parse_mode="Markdown")
            success += 1
        except:
            fail += 1
        await asyncio.sleep(0.05)
    await message.answer(f"✅ Рассылка завершена!\nУспешно: {success}\nОшибок: {fail}")

@router.callback_query(lambda c: c.data == "admin_give_clicks")
async def admin_give_clicks_prompt(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа!", show_alert=True)
        return
    await callback.message.edit_text(
        "🎁 **Выдача кликов пользователю**\n\n"
        "Введите команду в формате:\n"
        "`/give_clicks user_id количество`\n\n"
        "Пример: `/give_clicks 123456789 5000`",
        reply_markup=get_back_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(Command("give_clicks"))
async def admin_give_clicks(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 3 or not parts[2].isdigit():
        await message.answer("❌ Формат: `/give_clicks user_id количество`", parse_mode="Markdown")
        return
    try:
        target_user_id = int(parts[1])
        amount = int(parts[2])
        add_clicks(target_user_id, amount)
        await message.answer(f"✅ Пользователю `{target_user_id}` выдано `{amount}` кликов!", parse_mode="Markdown")
        await message.bot.send_message(target_user_id, f"🎁 Администратор выдал вам `{amount}` кликов!", parse_mode="Markdown")
    except ValueError:
        await message.answer("❌ Неверный формат user_id или количества")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@router.callback_query(lambda c: c.data == "admin_give_premium")
async def admin_give_premium_prompt(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа!", show_alert=True)
        return
    await callback.message.edit_text(
        "⭐ **Выдача премиума пользователю**\n\n"
        "Введите команду в формате:\n"
        "`/give_premium user_id дни`\n\n"
        "Пример: `/give_premium 123456789 30`",
        reply_markup=get_back_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(Command("give_premium"))
async def admin_give_premium(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 3 or not parts[2].isdigit():
        await message.answer("❌ Формат: `/give_premium user_id дни`", parse_mode="Markdown")
        return
    try:
        target_user_id = int(parts[1])
        days = int(parts[2])
        success = buy_premium(target_user_id, days)
        if success:
            await message.answer(f"✅ Пользователю `{target_user_id}` выдан премиум на `{days}` дней!", parse_mode="Markdown")
            await message.bot.send_message(target_user_id, f"⭐ Администратор выдал вам премиум на `{days}` дней!", parse_mode="Markdown")
        else:
            await message.answer(f"❌ Не удалось выдать премиум пользователю `{target_user_id}`", parse_mode="Markdown")
    except ValueError:
        await message.answer("❌ Неверный формат user_id или дней")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@router.callback_query(lambda c: c.data == "admin_logs")
async def admin_logs(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа!", show_alert=True)
        return
    await callback.message.edit_text(
        "📋 **Просмотр логов**\n\n"
        "Логи доступны в панели Railway:\n"
        "1. Зайди в свой проект на railway.app\n"
        "2. Выбери сервис `bot`\n"
        "3. Открой вкладку `Logs`\n\n"
        "Или используй команду `/deploy_logs` для получения последних логов (если настроено).",
        reply_markup=get_back_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "admin_reset_quests")
async def admin_reset_quests(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа!", show_alert=True)
        return
    reset_all_quests()
    await callback.message.edit_text(
        "✅ **Все задания сброшены!**\n\n"
        "Все пользователи теперь могут выполнять задания заново.",
        reply_markup=get_back_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()