from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(text="🦆 КВАК!", callback_data="tap"),
        InlineKeyboardButton(text="📊 Профиль", callback_data="profile")
    )
    keyboard.add(
        InlineKeyboardButton(text="🎁 Ежедневный бонус", callback_data="daily"),
        InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals")
    )
    keyboard.add(
        InlineKeyboardButton(text="📋 Задания", callback_data="quests"),
        InlineKeyboardButton(text="🏆 Лидерборд", callback_data="leaderboard")
    )
    keyboard.add(
        InlineKeyboardButton(text="👕 Магазин скинов", callback_data="shop"),
        InlineKeyboardButton(text="💎 Прокачка", callback_data="upgrades")
    )
    keyboard.add(
        InlineKeyboardButton(text="⭐ Премиум", callback_data="premium"),
        InlineKeyboardButton(text="💰 Пассивка", callback_data="collect_passive")
    )
    return keyboard

def get_back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ На главную", callback_data="main_menu")]
    ])

def get_shop_keyboard(skins, user_skins, current_skin_emoji):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for skin in skins:
        if skin['id'] in user_skins:
            if current_skin_emoji == skin['emoji']:
                btn_text = f"{skin['emoji']} {skin['name']} — ЭКИПИРОВАН"
                callback = "noop"
            else:
                btn_text = f"{skin['emoji']} {skin['name']} — ЭКИПИРОВАТЬ"
                callback = f"equip_skin_{skin['id']}"
        else:
            btn_text = f"{skin['emoji']} {skin['name']} — {skin['price']} кликов"
            callback = f"buy_skin_{skin['id']}"
        keyboard.inline_keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=callback)])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")])
    return keyboard

def get_upgrades_keyboard(tap_price, passive_price):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💪 Улучшить силу тапа ({tap_price})", callback_data="upgrade_tap")],
        [InlineKeyboardButton(text=f"💰 Улучшить пассивный доход ({passive_price})", callback_data="upgrade_passive")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    ])

def get_referral_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Забрать награду", callback_data="claim_referral")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    ])