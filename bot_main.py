import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import LabeledPrice, PreCheckoutQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_TOKEN, ADMIN_ID

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DB_PATH = "zeta_clicker.db"

# ==================== КОМАНДА /START ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    
    # Регистрируем пользователя в БД (если его нет)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, clicks, level, energy, tap_power, passive_income, current_skin, total_clicks, daily_streak, gems) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (user_id, 0, 1, 1000, 1, 0, "🦆", 0, 0, 0))
        conn.commit()
    conn.close()
    
    await message.answer(
        f"🦆 **Добро пожаловать в Zeta Clicker!**\n\n"
        f"💰 **Кликай по утке в Mini App и становись лучшим!**\n\n"
        f"🎮 **Mini App:** `/game`\n"
        f"📊 Твой ID: `{user_id}`",
        parse_mode="Markdown"
    )


# ==================== КОМАНДА /GAME ====================

@dp.message(Command("game"))
async def cmd_game(message: types.Message):
    user_id = message.from_user.id
    base_url = "https://zeta-clicker-bot-production-3a3b.up.railway.app"
    web_app_url = f"{base_url}/?user_id={user_id}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Играть в Zeta Clicker! 🦆", web_app=types.WebAppInfo(url=web_app_url))]
    ])
    
    await message.answer(
        "🦆 **Zeta Clicker — Mini App версия!**\n\n"
        "Нажми на кнопку ниже, чтобы открыть игру с живыми анимациями!\n\n"
        "🚀 **Погнали!**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


# ==================== ДОНАТ ЧЕРЕЗ TELEGRAM STARS ====================

@dp.message(Command("donate"))
async def cmd_donate(message: types.Message):
    args = message.text.split()
    
    if len(args) < 2:
        await message.answer(
            "❌ **Неправильный формат!**\n"
            "Используй: `/donate <количество звезд>`\n"
            "Пример: `/donate 100`\n\n"
            "💰 **Доступные суммы:**\n"
            "• 100 Stars — 1000 кликов + 1💎\n"
            "• 500 Stars — 6000 кликов + 5💎\n"
            "• 1000 Stars — 15000 кликов + 15💎",
            parse_mode="Markdown"
        )
        return
    
    if not args[1].isdigit():
        await message.answer("❌ Сумма должна быть числом!\nПример: `/donate 100`", parse_mode="Markdown")
        return
    
    amount = int(args[1])
    
    allowed_amounts = [100, 500, 1000]
    if amount not in allowed_amounts:
        await message.answer(
            f"❌ Сумма `{amount}` недоступна!\n"
            f"Доступные суммы: {', '.join(map(str, allowed_amounts))} Stars",
            parse_mode="Markdown"
        )
        return
    
    reward_clicks = amount * 10
    reward_gems = amount // 20
    
    payload = f"donate_{message.from_user.id}_{amount}_{int(asyncio.get_event_loop().time())}"
    
    try:
        invoice_link = await message.bot.create_invoice_link(
            title="Поддержка Zeta Clicker 💫",
            description=f"Донат {amount} Telegram Stars\nНаграда: +{reward_clicks} кликов + {reward_gems}💎",
            payload=payload,
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="⭐ Telegram Stars", amount=amount)],
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"💎 Оплатить {amount} ⭐️", url=invoice_link)]
        ])
        
        await message.answer(
            f"🌟 **Поддержи проект!**\n\n"
            f"💰 Сумма: `{amount} ⭐️`\n"
            f"🎁 Награда: `+{reward_clicks}` кликов + `{reward_gems}`💎\n\n"
            f"👇 Нажми на кнопку ниже для оплаты.",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_q: PreCheckoutQuery):
    await pre_checkout_q.answer(ok=True)


@dp.message(lambda message: message.successful_payment is not None)
async def success_payment_handler(message: types.Message):
    user_id = message.from_user.id
    payment = message.successful_payment
    amount = payment.total_amount
    
    reward_clicks = amount * 10
    reward_gems = amount // 20
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT clicks, gems FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    if result:
        new_clicks = result[0] + reward_clicks
        new_gems = result[1] + reward_gems
        cursor.execute("UPDATE users SET clicks = ?, gems = ? WHERE user_id = ?", 
                       (new_clicks, new_gems, user_id))
        conn.commit()
    
    conn.close()
    
    await message.answer(
        f"✅ **Спасибо за донат!**\n\n"
        f"⭐ Ты перевел `{amount}` Telegram Stars\n"
        f"💰 Награда: `+{reward_clicks}` кликов\n"
        f"💎 Алмазы: `+{reward_gems}`\n\n"
        f"🔥 Продолжай кликать!",
        parse_mode="Markdown"
    )


# ==================== АДМИН-ПАНЕЛЬ ====================

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    user_id = message.from_user.id
    
    if user_id != ADMIN_ID:
        await message.answer("⛔ **У тебя нет прав администратора!**", parse_mode="Markdown")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="💰 Добавить клики", callback_data="admin_add_clicks")],
        [InlineKeyboardButton(text="💎 Добавить алмазы", callback_data="admin_add_gems")],
        [InlineKeyboardButton(text="◀️ На главную", callback_data="back_to_start")]
    ])
    
    await message.answer(
        "👑 **Админ-панель**\n\nВыбери действие:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@dp.callback_query(lambda c: c.data == "admin_stats")
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
    
    cursor.execute("SELECT SUM(gems) FROM users")
    total_gems = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT SUM(clicks) FROM users")
    available_clicks = cursor.fetchone()[0] or 0
    
    conn.close()
    
    await callback.message.edit_text(
        f"📊 **Статистика бота**\n\n"
        f"👥 Всего пользователей: `{total_users}`\n"
        f"💎 Всего накликано: `{total_clicks}`\n"
        f"💰 Доступно кликов: `{available_clicks}`\n"
        f"💎 Всего алмазов: `{total_gems}`",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data == "back_to_admin")
async def back_to_admin(callback: types.CallbackQuery):
    await cmd_admin(callback.message)


@dp.callback_query(lambda c: c.data == "admin_broadcast")
async def admin_broadcast_start(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет прав!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📢 **Рассылка**\n\n"
        "Отправь сообщение для рассылки (текст, фото, видео).\n"
        "Для отмены отправь `/cancel`",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Отмена", callback_data="back_to_admin")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data == "admin_add_clicks")
async def admin_add_clicks_start(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет прав!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "💰 **Добавление кликов**\n\n"
        "Отправь ID пользователя и количество кликов через пробел.\n"
        "Пример: `123456789 1000`\n\n"
        "Для отмены отправь `/cancel`",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data == "admin_add_gems")
async def admin_add_gems_start(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет прав!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "💎 **Добавление алмазов**\n\n"
        "Отправь ID пользователя и количество алмазов через пробел.\n"
        "Пример: `123456789 50`\n\n"
        "Для отмены отправь `/cancel`",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.message(Command("cancel"))
async def cancel_action(message: types.Message):
    await message.answer("❌ Действие отменено.")


@dp.message(lambda message: message.from_user.id == ADMIN_ID and not message.text.startswith('/'))
async def admin_action_process(message: types.Message):
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
    
    # Проверяем, что добавляем (клики или алмазы)
    if "алмаз" in message.text.lower() or "gems" in message.text.lower():
        cursor.execute("UPDATE users SET gems = gems + ? WHERE user_id = ?", (amount, user_id))
        await message.answer(f"✅ Пользователю `{user_id}` начислено `{amount}` алмазов!", parse_mode="Markdown")
    else:
        cursor.execute("UPDATE users SET clicks = clicks + ?, total_clicks = total_clicks + ? WHERE user_id = ?", (amount, amount, user_id))
        await message.answer(f"✅ Пользователю `{user_id}` начислено `{amount}` кликов!", parse_mode="Markdown")
    
    conn.commit()
    conn.close()


@dp.callback_query(lambda c: c.data == "back_to_start")
async def back_to_start(callback: types.CallbackQuery):
    await callback.message.answer("🏠 **Главное меню**\n\nБот готов к работе!", parse_mode="Markdown")
    await callback.answer()


# ==================== ЗАПУСК ====================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())