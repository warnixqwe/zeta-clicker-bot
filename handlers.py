import asyncio
import sqlite3
from datetime import datetime
from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery, WebAppInfo

from database import *
from keyboards import *
from config import BOT_TOKEN, ADMIN_ID

router = Router()
bot = Bot(token=BOT_TOKEN)

# ==================== КОМАНДЫ ПОЛЬЗОВАТЕЛЯ ====================

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    
    # Реферальная система
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        referrer_id = int(args[1].split("_")[1])
        if referrer_id != user_id:
            add_referral(referrer_id, user_id)
            await bot.send_message(referrer_id, f"🎉 Новый реферал! ID: {user_id}")
    
    init_db()
    get_user_stats(user_id)
    
    await message.answer(
        f"🦆 **Добро пожаловать в Zeta Clicker!**\n\n"
        f"💰 **Кликай по кнопке КВАК, зарабатывай клики и прокачивай свою утку!**\n\n"
        f"📊 **Твой ID:** `{user_id}`\n"
        f"🎮 **Мини-игра:** `/game`\n\n"
        f"👇 **Жми на кнопки и становись лучшим!**",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@router.message(Command("game"))
async def cmd_game(message: types.Message):
    user_id = message.from_user.id
    base_url = "https://zeta-clicker-bot-2.up.railway.app"
    web_app_url = f"{base_url}/?user_id={user_id}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Играть в Zeta Clicker! 🦆", web_app=WebAppInfo(url=web_app_url))]
    ])
    
    await message.answer(
        "🦆 **Zeta Clicker — Mini App версия!**\n\n"
        "Нажми на кнопку ниже, чтобы открыть игру с живыми анимациями!\n\n"
        "🚀 **Погнали!**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@router.message(Command("donate"))
async def cmd_donate(message: types.Message):
    parts = message.text.split()
    
    if len(parts) < 2:
        await message.answer("❌ Используй: `/donate <количество звезд>`\nПример: `/donate 100`", parse_mode="Markdown")
        return
    
    if not parts[1].isdigit():
        await message.answer("❌ Сумма должна быть числом!\nПример: `/donate 100`", parse_mode="Markdown")
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
            f"🌟 **Поддержи проект!**\n\n"
            f"Сумма: `{amount} ⭐️`\n"
            f"Награда: `{amount * 1000} кликов`\n\n"
            f"Нажми на кнопку ниже для оплаты.",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

# ==================== АДМИН-ПАНЕЛЬ ====================

@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await message.answer("⛔ **У тебя нет прав администратора!**", parse_mode="Markdown")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="💰 Добавить клики", callback_data="admin_add_clicks")],
        [InlineKeyboardButton(text="◀️ На главную", callback_data="main_menu")]
    ])
    
    await message.answer(
        "👑 **Админ-панель**\n\nВыбери действие:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@router.callback_query(lambda c: c.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет прав!", show_alert=True)
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(total_clicks) FROM users")
    total_clicks = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(clicks) FROM users")
    available_clicks = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM referrals")
    total_refs = cursor.fetchone()[0]
    conn.close()
    
    text = (
        f"📊 **Статистика бота**\n\n"
        f"👥 Всего пользователей: `{total_users}`\n"
        f"💎 Всего накликано: `{total_clicks}`\n"
        f"💰 Доступно кликов: `{available_clicks}`\n"
        f"👥 Всего рефералов: `{total_refs}`\n"
    )
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(lambda c: c.data == "admin_broadcast")
async def admin_broadcast_start(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет прав!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📢 **Рассылка**\n\n"
        "Отправь сообщение для рассылки (текст, фото, видео).\n"
        "Для отмены отправь `/cancel`",
        reply_markup=get_back_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(Command("cancel"))
async def cancel_broadcast(message: types.Message):
    await message.answer("❌ Действие отменено.", reply_markup=get_main_keyboard())

@router.message(lambda message: message.from_user.id == ADMIN_ID)
async def process_broadcast(message: types.Message):
    if message.text and message.text.startswith('/'):
        return
    
    await message.answer("⏳ **Начинаю рассылку...**", parse_mode="Markdown")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()
    
    success = 0
    fail = 0
    
    for user in users:
        try:
            if message.photo:
                await bot.send_photo(user[0], message.photo[-1].file_id, caption=message.caption)
            elif message.video:
                await bot.send_video(user[0], message.video.file_id, caption=message.caption)
            elif message.text:
                await bot.send_message(user[0], message.text)
            success += 1
        except:
            fail += 1
        await asyncio.sleep(0.05)
    
    await message.answer(
        f"✅ **Рассылка завершена!**\n"
        f"✅ Успешно: `{success}`\n"
        f"❌ Ошибок: `{fail}`",
        parse_mode="Markdown"
    )

@router.callback_query(lambda c: c.data == "admin_add_clicks")
async def admin_add_clicks_start(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет прав!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "💰 **Добавление кликов**\n\n"
        "Отправь ID пользователя и количество кликов через пробел.\n"
        "Пример: `123456789 1000`\n\n"
        "Для отмены отправь `/cancel`",
        reply_markup=get_back_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(lambda message: message.from_user.id == ADMIN_ID and not message.text.startswith('/'))
async def admin_add_clicks_process(message: types.Message):
    parts = message.text.split()
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        await message.answer("❌ Неверный формат! Используй: `ID количество`\nПример: `123456789 1000`", parse_mode="Markdown")
        return
    
    user_id = int(parts[0])
    amount = int(parts[1])
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        await message.answer(f"❌ Пользователь с ID `{user_id}` не найден!", parse_mode="Markdown")
        conn.close()
        return
    conn.close()
    
    add_clicks(user_id, amount)
    await message.answer(f"✅ Пользователю `{user_id}` начислено `{amount}` кликов!", parse_mode="Markdown")

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
        f"💰 Баланс пополнен на `{bonus_clicks} кликов`!",
        parse_mode="Markdown"
    )

# ==================== ОСНОВНЫЕ ОБРАБОТЧИКИ ====================

@router.callback_query(lambda c: c.data == "tap")
async def handle_tap(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    clicks, level, energy, tap_power, passive_income, _, current_skin, total_clicks, _ = get_user_stats(user_id)
    
    if energy <= 0:
        await callback.answer("😫 Нет энергии! Подожди, она восстановится.", show_alert=True)
        return
    
    # Получаем бонус от скина
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
        f"📊 Клики: `{new_clicks}`\n"
        f"🏆 Уровень: `{new_level}`\n"
        f"⚡ Энергия: `{new_energy}/1000`\n"
        f"💪 Сила тапа: `+{tap_power + skin_bonus}`\n\n"
        f"👇 **Жми дальше!**",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(lambda c: c.data == "main_menu")
async def back_to_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    clicks, level, energy, tap_power, passive_income, _, _, _, _ = get_user_stats(user_id)
    
    await callback.message.edit_text(
        f"🦆 **Zeta Clicker**\n\n"
        f"📊 Клики: `{clicks}`\n"
        f"🏆 Уровень: `{level}`\n"
        f"⚡ Энергия: `{energy}/1000`\n"
        f"💪 Сила тапа: `+{tap_power}`\n\n"
        f"👇 **Выбери действие:**",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(lambda c: c.data == "profile")
async def handle_profile(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    clicks, level, energy, tap_power, passive_income, premium_until, current_skin, total_clicks, daily_streak = get_user_stats(user_id)
    referral_count = get_referral_count(user_id)
    rank = get_user_rank(user_id)
    is_prem = is_premium(user_id)
    
    premium_status = "✅ Активна" if is_prem else "❌ Неактивна"
    
    profile_text = (
        f"🦆 **Профиль игрока**\n\n"
        f"📊 Всего кликов: `{total_clicks}`\n"
        f"💰 Доступно: `{clicks}`\n"
        f"🏆 Уровень: `{level}`\n"
        f"⚡ Энергия: `{energy}/1000`\n"
        f"💪 Сила тапа: `+{tap_power}`\n"
        f"👕 Текущий скин: `{current_skin}`\n"
        f"👥 Приглашено друзей: `{referral_count}`\n"
        f"⭐ Премиум: {premium_status}\n"
        f"📅 Серия входов: `{daily_streak} дней`\n"
        f"🏅 Место в рейтинге: `{rank}`\n"
    )
    
    await callback.message.edit_text(profile_text, reply_markup=get_back_keyboard(), parse_mode="Markdown")

@router.callback_query(lambda c: c.data == "daily")
async def handle_daily(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    bonus, streak = claim_daily_bonus(user_id)
    
    if bonus == 0:
        await callback.answer("🎁 Ты уже забирал бонус сегодня! Возвращайся завтра!", show_alert=True)
        return
    
    await callback.answer(f"🎁 +{bonus} кликов! Серия: {streak} дней!", show_alert=True)
    await back_to_menu(callback)

@router.callback_query(lambda c: c.data == "referrals")
async def handle_referrals(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    count = get_referral_count(user_id)
    unclaimed = 0
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND reward_claimed = 0", (user_id,))
    unclaimed = cursor.fetchone()[0]
    conn.close()
    
    bot_username = (await callback.bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    
    text = (
        f"👥 **Реферальная система**\n\n"
        f"👥 Приглашено друзей: `{count}`\n"
        f"🎁 Неполученных наград: `{unclaimed}`\n"
        f"💰 За каждого друга: `1000` кликов\n\n"
        f"🔗 **Твоя реферальная ссылка:**\n"
        f"`{referral_link}`\n\n"
        f"👇 Отправь её друзьям и получай награду!"
    )
    
    await callback.message.edit_text(text, reply_markup=get_referral_keyboard(), parse_mode="Markdown")

@router.callback_query(lambda c