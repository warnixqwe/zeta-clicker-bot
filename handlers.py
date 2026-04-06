import asyncio
import sqlite3
from datetime import datetime, timedelta
from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import BOT_TOKEN, ADMIN_ID

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
    
    # Кнопка для входа в Mini App
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🎮 Войти в игру", 
            web_app=WebAppInfo(url=f"https://zeta-clicker-bot-production-3a3b.up.railway.app/?user_id={user_id}")
        )]
    ])
    
    await message.answer(
        "🦆 **Добро пожаловать в Zeta Clicker!**\n\n"
        "💰 Кликай по утке, зарабатывай монеты, открывай кейсы, покупай скины и улучшай прибыль!\n\n"
        "🔥 **Что тебя ждёт:**\n"
        "• 🦆 Кликай по утке и зарабатывай\n"
        "• 📦 Открывай кейсы с крутыми наградами\n"
        "• 👕 Покупай скины для утки\n"
        "• ⚡ Активируй бустеры для удвоения прибыли\n"
        "• 👥 Приглашай друзей и получай бонусы\n"
        "• 🏆 Соревнуйся в топе игроков\n\n"
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
        "🦆 **Zeta Clicker — Mini App версия!**\n\n"
        "Нажми на кнопку ниже, чтобы открыть игру с живыми анимациями!\n\n"
        "🚀 **Погнали!**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await message.answer("⛔ **У тебя нет прав администратора!**", parse_mode="Markdown")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="💰 Добавить монеты", callback_data="admin_add_clicks")],
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
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(lambda c: c.data == "admin_broadcast")
async def admin_broadcast_start(callback: types.CallbackQuery, state: FSMContext):
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
    await state.set_state(BroadcastState.waiting_for_message)
    await callback.answer()

@router.message(Command("cancel"))
async def cancel_broadcast(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено.", reply_markup=get_main_keyboard())

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
        "💰 **Добавление монет**\n\n"
        "Отправь ID пользователя и количество монет через пробел.\n"
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
        "🦆 **Zeta Clicker**\n\n"
        "👇 **Выбери действие:**",
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
        "🦆 **Zeta Clicker — Mini App версия!**\n\n"
        "Нажми на кнопку ниже, чтобы открыть игру с живыми анимациями!\n\n"
        "🚀 **Погнали!**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )