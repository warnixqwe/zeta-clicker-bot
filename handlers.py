import sqlite3
import os
from datetime import datetime
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.exceptions import TelegramBadRequest

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

# ==================== АДМИН-ПАНЕЛЬ ====================

@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа к админ-панели!")
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Все пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="💰 Топ-10 донатеров", callback_data="admin_top_donors")],
        [InlineKeyboardButton(text="📨 Рассылка", callback_data="admin_mailing")],
        [InlineKeyboardButton(text="🎁 Выдать клики", callback_data="admin_give_clicks")],
        [InlineKeyboardButton(text="⭐ Выдать премиум", callback_data="admin_give_premium")],
        [InlineKeyboardButton(text="📋 Посмотреть логи", callback_data="admin_logs")],
        [InlineKeyboardButton(text="🔄 Сбросить задания всем", callback_data="admin_reset_quests")],
        [InlineKeyboardButton(text="◀️ На главную", callback_data="main_menu")]
    ])
    await message.answer("👑 **Админ-панель Zeta Clicker**\n\nВыбери действие:", reply_markup=keyboard, parse_mode="Markdown")

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
        "1. Зай