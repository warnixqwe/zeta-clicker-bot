import asyncio
from datetime import datetime
from aiogram import Router, Bot, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.fsm.context import FSMContext

from database import *
from keyboards import *
from config import BOT_TOKEN, ADMIN_ID

router = Router()


# ==================== КОМАНДЫ ====================

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    
    # Проверяем реферальный параметр
    args = message.get_args()
    if args and args.startswith("ref_"):
        referrer_id = int(args.split("_")[1])
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
    args = message.get_args()
    if not args or not args.isdigit():
        await message.answer("❌ Используй: `/donate <количество звезд>`\nПример: `/donate 100`", parse_mode="Markdown")
        return
    
    amount = int(args)
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


# ==================== CALLBACK-ЗАПРОСЫ ====================

@router.callback_query(lambda c: c.data == "tap")
async def handle_tap(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    clicks, level, energy, tap_power, passive_income, _, current_skin, total_clicks, _ = get_user_stats(user_id)
    
    if energy <= 0:
        await callback.answer("😫 Нет энергии!", show_alert=True)
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


# ==================== ПЛАТЕЖИ (TELEGRAM STARS) ====================

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
    
    await message.bot.send_message(
        ADMIN_ID,
        f"🔔 Новый донат!\nПользователь: {user_id}\nСумма: {amount} ⭐️\nНачислено: {bonus_clicks} кликов"
    )


# ==================== ОСТАЛЬНЫЕ ОБРАБОТЧИКИ ====================

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