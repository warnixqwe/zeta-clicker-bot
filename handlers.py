import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import CommandStart
from config import BOT_TOKEN, ADMIN_ID
import json
from aiogram.types import WebAppData

router = Router()
bot = Bot(token=BOT_TOKEN)

# ==================== СОСТОЯНИЯ ДЛЯ АДМИНКИ ====================

class BroadcastState(StatesGroup):
    waiting_for_message = State()

# ==================== КОМАНДЫ ПОЛЬЗОВАТЕЛЯ ====================

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    
    # Реферальная система
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        referrer_id = int(args[1].split("_")[1])
        if referrer_id != user_id:
            conn = sqlite3.connect("zeta_clicker.db")
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (referrer_id, user_id))
                cursor.execute("UPDATE users SET balance = balance + 1000 WHERE user_id = ?", (referrer_id,))
                conn.commit()
            except:
                pass
            conn.close()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🎮 Войти в игру", 
            web_app=WebAppInfo(url=f"https://zeta-clicker-bot-production-3a3b.up.railway.app/?user_id={user_id}")
        )]
    ])
    
    await message.answer(
        "🦆 **Добро пожаловать в Zeta Clicker!**\n\n"
        "💰 Кликай по утке, зарабатывай монеты, открывай кейсы, покупай скины и улучшай прибыль!\n\n"
        "👇 **Нажми на кнопку ниже, чтобы начать игру!**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@router.message(Command("game"))
async def cmd_game(message: types.Message):
    user_id = message.from_user.id
    base_url = "https://zeta-clicker-bot-production-3a3b.up.railway.app"
    web_app_url = f"{base_url}/?user_id={user_id}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Играть в Zeta Clicker! 🦆", web_app=WebAppInfo(url=web_app_url))]
    ])
    
    await message.answer(
        "🦆 **Zeta Clicker — Mini App версия!**\n\nНажми на кнопку ниже, чтобы открыть игру!",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# ==================== АДМИН-ПАНЕЛЬ ====================

def get_admin_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")
    )
    keyboard.add(
        InlineKeyboardButton(text="💰 Добавить монеты", callback_data="admin_add_clicks"),
        InlineKeyboardButton(text="💎 Добавить алмазы", callback_data="admin_add_gems")
    )
    keyboard.add(
        InlineKeyboardButton(text="🎁 Награда админа", callback_data="admin_reward"),
        InlineKeyboardButton(text="📋 Список пользователей", callback_data="admin_users")
    )
    keyboard.add(
        InlineKeyboardButton(text="◀️ На главную", callback_data="main_menu")
    )
    return keyboard

@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await message.answer("⛔ **У тебя нет прав администратора!**", parse_mode="Markdown")
        return
    
    await message.answer(
        "👑 **Админ-панель**\n\nВыбери действие:",
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(lambda c: c.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет прав", show_alert=True)
        return
    
    conn = sqlite3.connect("zeta_clicker.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(total_clicks) FROM users")
    total_clicks = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(balance) FROM users")
    total_balance = cursor.fetchone()[0] or 0
    conn.close()
    
    text = (
        f"📊 **Статистика бота**\n\n"
        f"👥 Всего пользователей: `{total_users}`\n"
        f"💎 Всего кликов: `{total_clicks}`\n"
        f"💰 Всего монет: `{total_balance}`\n"
    )
    
    await callback.message.edit_text(text, reply_markup=get_admin_keyboard(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(lambda c: c.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет прав!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📢 **Рассылка**\n\nОтправь сообщение для рассылки.\nДля отмены отправь `/cancel`",
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(BroadcastState.waiting_for_message)
    await callback.answer()

@router.message(Command("cancel"))
async def cancel_broadcast(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено.")

@router.message(BroadcastState.waiting_for_message)
async def process_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await state.clear()
        return
    
    await message.answer("⏳ **Начинаю рассылку...**", parse_mode="Markdown")
    
    conn = sqlite3.connect("zeta_clicker.db")
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
    
    await state.clear()
    await message.answer(
        f"✅ **Рассылка завершена!**\n✅ Успешно: `{success}`\n❌ Ошибок: `{fail}`",
        parse_mode="Markdown"
    )

@router.callback_query(lambda c: c.data == "admin_add_gems")
async def admin_add_clicks(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет прав!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "💎 **Добавление алмазов**\n\n"
        "Отправь ID пользователя и количество алмазов через пробел.\n"
        "Пример: `123456789 100`\n\n"
        "Для отмены отправь `/cancel`",
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(lambda message: message.from_user.id == ADMIN_ID and not message.text.startswith('/'))
async def admin_add_gems_process(message: types.Message):
    parts = message.text.split()
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        await message.answer("❌ Неверный формат! Используй: `ID количество`\nПример: `123456789 100`", parse_mode="Markdown")
        return
    
    user_id = int(parts[0])
    amount = int(parts[1])
    
    conn = sqlite3.connect("zeta_clicker.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        await message.answer(f"❌ Пользователь с ID `{user_id}` не найден!", parse_mode="Markdown")
        conn.close()
        return
    
    cursor.execute("UPDATE users SET gems = gems + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()
    
    await message.answer(f"✅ Пользователю `{user_id}` начислено `{amount}` алмазов!", parse_mode="Markdown")

@router.callback_query(lambda c: c.data == "admin_add_clicks")
async def admin_add_clicks(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет прав!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "💰 **Добавление монет**\n\nОтправь ID пользователя и количество монет через пробел.\nПример: `123456789 1000`\n\nДля отмены отправь `/cancel`",
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(lambda message: message.from_user.id == ADMIN_ID and not message.text.startswith('/'))
async def admin_add_clicks_process(message: types.Message):
    parts = message.text.split()
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        await message.answer("❌ Неверный формат! Используй: `ID количество`", parse_mode="Markdown")
        return
    
    user_id = int(parts[0])
    amount = int(parts[1])
    
    conn = sqlite3.connect("zeta_clicker.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        await message.answer(f"❌ Пользователь с ID `{user_id}` не найден!", parse_mode="Markdown")
        conn.close()
        return
    cursor.execute("UPDATE users SET balance = balance + ?, total_clicks = total_clicks + ? WHERE user_id = ?", (amount, amount, user_id))
    conn.commit()
    conn.close()
    
    await message.answer(f"✅ Пользователю `{user_id}` начислено `{amount}` монет!", parse_mode="Markdown")

@router.callback_query(lambda c: c.data == "admin_reward")
async def admin_reward(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет прав!", show_alert=True)
        return
    
    conn = sqlite3.connect("zeta_clicker.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + 100000, total_clicks = total_clicks + 100000 WHERE user_id = ?", (ADMIN_ID,))
    conn.commit()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (ADMIN_ID,))
    new_balance = cursor.fetchone()[0]
    conn.close()
    
    await callback.message.edit_text(
        f"✅ **Награда получена!**\n\n💰 Тебе начислено `100000` монет!\n💎 Твой баланс: `{new_balance}` монет",
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "admin_users")
async def admin_users(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет прав!", show_alert=True)
        return
    
    conn = sqlite3.connect("zeta_clicker.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, balance, total_clicks, profit_per_tap, gems FROM users ORDER BY balance DESC LIMIT 10")
    users = cursor.fetchall()
    conn.close()
    
    if not users:
        text = "📋 **Список пользователей**\n\nПока никого нет"
    else:
        text = "📋 **Топ-10 пользователей**\n\n"
        for i, (user_id, balance, clicks, tap_power, gems) in enumerate(users, 1):
            # Пробуем получить username через API бота
            username = str(user_id)
            try:
                user = await bot.get_chat(user_id)
                if user.username:
                    username = f"@{user.username}"
                elif user.first_name:
                    username = user.first_name
            except:
                pass
            
            text += f"{i}. {username}\n"
            text += f"   🆔 ID: `{user_id}`\n"
            text += f"   💰 Баланс: `{balance}`\n"
            text += f"   💎 Алмазы: `{gems}`\n"
            text += f"   📊 Кликов: `{clicks}`\n"
            text += f"   💪 Сила: `+{tap_power}`\n\n"
    
    await callback.message.edit_text(text, reply_markup=get_admin_keyboard(), parse_mode="Markdown")
    await callback.answer()

@router.message(lambda message: message.text == ".з")
async def dot_z_command(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await message.answer("⛔ Нет прав!")
        return
    await cmd_admin(message)

# ==================== КЛАВИАТУРЫ ====================

def get_main_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(text="🦆 Играть", callback_data="game"),
        InlineKeyboardButton(text="📊 Профиль", callback_data="profile")
    )
    return keyboard

def get_back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    ])

# ==================== ОСНОВНЫЕ ОБРАБОТЧИКИ ====================

@router.callback_query(lambda c: c.data == "main_menu")
async def back_to_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🦆 **Zeta Clicker**\n\n👇 **Выбери действие:**",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(lambda c: c.data == "profile")
async def handle_profile(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    conn = sqlite3.connect("zeta_clicker.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance, profit_per_tap, profit_per_hour, gems, total_clicks FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        balance, profit_per_tap, profit_per_hour, gems, total_clicks = result
    else:
        balance, profit_per_tap, profit_per_hour, gems, total_clicks = 0, 1, 0, 0, 0
    
    profile_text = (
        f"🦆 **Профиль игрока**\n\n"
        f"💰 Баланс: `{balance}`\n"
        f"💪 Сила тапа: `+{profit_per_tap}`\n"
        f"⏱️ Прибыль в час: `+{profit_per_hour}`\n"
        f"💎 Алмазы: `{gems}`\n"
        f"📊 Всего кликов: `{total_clicks}`\n"
    )
    
    await callback.message.edit_text(profile_text, reply_markup=get_back_keyboard(), parse_mode="Markdown")

@router.callback_query(lambda c: c.data == "game")
async def handle_game(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    base_url = "https://zeta-clicker-bot-production-3a3b.up.railway.app"
    web_app_url = f"{base_url}/?user_id={user_id}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Играть в Zeta Clicker! 🦆", web_app=WebAppInfo(url=web_app_url))]
    ])
    
    await callback.message.edit_text(
        "🦆 **Zeta Clicker — Mini App версия!**\n\nНажми на кнопку ниже, чтобы открыть игру!",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@router.message(lambda message: message.web_app_data is not None)
async def handle_share(message: types.Message):
    data = json.loads(message.web_app_data.data)
    if data.get('action') == 'share':
        user_id = data.get('user_id')
        # Генерируем ссылку на картинку
        image_url = f"https://zeta-clicker-bot-production-3a3b.up.railway.app/api/share_image?user_id={user_id}"
        
        # Отправляем картинку с подписью
        await message.answer_photo(
            photo=image_url,
            caption=f"🦆 Я накликал {data.get('balance', 0)} монет в Zeta Clicker!\nПрисоединяйся: t.me/ZetaClickerRobot?start=ref_{user_id}"
        )

@router.pre_checkout_query()
async def process_pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)

@router.message(lambda msg: msg.successful_payment)
async def on_successful_payment(message: types.Message):
    user_id = message.from_user.id
    stars = message.successful_payment.total_amount
    # Начисляем бонус: например, 1000 монет за 1 звезду
    bonus = stars * 1000
    conn = await get_connection()
    await conn.execute("UPDATE users SET balance = balance + $1 WHERE user_id = $2", bonus, user_id)
    await conn.close()
    await message.answer(f"✅ Спасибо за поддержку! Ты получил {bonus} монет.")

    # Кнопка в главном меню
@router.callback_query(lambda c: c.data == "gems_shop")
async def gems_shop(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    conn = await get_connection()
    gems = await conn.fetchval("SELECT gems FROM users WHERE user_id = $1", user_id)
    await conn.close()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Алмазная утка (+20 к силе) — 50💎", callback_data="buy_skin_gems_6")],
        [InlineKeyboardButton(text="⚡ Бустер x2 на 1 час — 30💎", callback_data="buy_booster_gems_2")],
        [InlineKeyboardButton(text="🎁 10 000 монет — 10💎", callback_data="buy_clicks_gems")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(
        f"💎 **Магазин алмазов**\nУ тебя: {gems} 💎\n\n"
        "✨ **Предложения:**\n"
        "• Алмазная утка +20 к силе (50💎)\n"
        "• Бустер x2 на 1 час (30💎)\n"
        "• 10 000 монет (10💎)",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

    @router.callback_query(lambda c: c.data == "buy_skin_gems_6")
async def buy_skin_gems(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    conn = await get_connection()
    gems = await conn.fetchval("SELECT gems FROM users WHERE user_id = $1", user_id)
    
    if gems >= 50:
        new_gems = gems - 50
        # Добавляем скин (id=6 — алмазная утка)
        await conn.execute("UPDATE users SET gems = $1 WHERE user_id = $2", new_gems, user_id)
        await conn.execute("INSERT INTO user_skins (user_id, skin_id) VALUES ($1, 6) ON CONFLICT DO NOTHING", user_id)
        await callback.answer("✅ Ты купил Алмазную утку! Теперь экипируй её в магазине скинов.", show_alert=True)
    else:
        await callback.answer(f"❌ Не хватает алмазов! Нужно 50, у тебя {gems}", show_alert=True)
    await conn.close()
    await gems_shop(callback)

@router.callback_query(lambda c: c.data == "buy_booster_gems_2")
async def buy_booster_gems(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    conn = await get_connection()
    gems = await conn.fetchval("SELECT gems FROM users WHERE user_id = $1", user_id)
    
    if gems >= 30:
        new_gems = gems - 30
        expires_at = datetime.now() + timedelta(hours=1)
        await conn.execute("UPDATE users SET gems = $1 WHERE user_id = $2", new_gems, user_id)
        await conn.execute("""
            INSERT INTO user_boosters (user_id, booster_id, expires_at) 
            VALUES ($1, 1, $2) 
            ON CONFLICT (user_id, booster_id) DO UPDATE SET expires_at = EXCLUDED.expires_at
        """, user_id, expires_at)
        await callback.answer("✅ Бустер x2 активирован на 1 час!", show_alert=True)
    else:
        await callback.answer(f"❌ Не хватает алмазов! Нужно 30, у тебя {gems}", show_alert=True)
    await conn.close()
    await gems_shop(callback)

@router.callback_query(lambda c: c.data == "buy_clicks_gems")
async def buy_clicks_gems(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    conn = await get_connection()
    gems = await conn.fetchval("SELECT gems FROM users WHERE user_id = $1", user_id)
    
    if gems >= 10:
        new_gems = gems - 10
        await conn.execute("UPDATE users SET gems = $1, balance = balance + 10000 WHERE user_id = $2", new_gems, user_id)
        await callback.answer("✅ +10 000 монет зачислено!", show_alert=True)
    else:
        await callback.answer(f"❌ Не хватает алмазов! Нужно 10, у тебя {gems}", show_alert=True)
    await conn.close()
    await gems_shop(callback)

@router.message(lambda message: message.web_app_data is not None)
async def handle_web_app_data(message: types.Message):
    data = json.loads(message.web_app_data.data)
    if data.get('action') == 'share':
        user_id = data.get('user_id')
        image_url = f"https://zeta-clicker-bot-production-3a3b.up.railway.app/api/share_image?user_id={user_id}"
        await message.answer_photo(
            photo=image_url,
            caption=f"🦆 Присоединяйся к Zeta Clicker!\nhttps://t.me/ZetaClickerRobot?start=ref_{user_id}"
        )