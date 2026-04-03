from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🦆 КВАК!", callback_data="tap"), InlineKeyboardButton(text="📊 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🎁 Ежедневный бонус", callback_data="daily"), InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals")],
        [InlineKeyboardButton(text="📋 Задания", callback_data="quests"), InlineKeyboardButton(text="🏆 Лидерборд", callback_data="leaderboard")],
        [InlineKeyboardButton(text="👕 Магазин скинов", callback_data="shop"), InlineKeyboardButton(text="💎 Прокачка", callback_data="upgrades")],
        [InlineKeyboardButton(text="⭐ Премиум", callback_data="premium"), InlineKeyboardButton(text="💰 Собрать пассивку", callback_data="collect_passive")]
    ])
    return keyboard

def get_back_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ На главную", callback_data="main_menu")]
    ])
    return keyboard

def get_shop_keyboard(skins: list, user_skins: list, current_skin_emoji: str) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for skin in skins:
        emoji = skin['emoji']
        name = skin['name']
        price = skin['price']
        skin_id = skin['id']
        
        if skin_id in user_skins:
            if current_skin_emoji == emoji:
                btn_text = f"{emoji} {name} — ЭКИПИРОВАН"
                callback = f"noop"
            else:
                btn_text = f"{emoji} {name} — ЭКИПИРОВАТЬ"
                callback = f"equip_skin_{skin_id}"
        else:
            btn_text = f"{emoji} {name} — {price} кликов"
            callback = f"buy_skin_{skin_id}"
        
        keyboard.inline_keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=callback)])
    
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")])
    return keyboard

def get_upgrades_keyboard(tap_price: int, passive_price: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💪 Улучшить силу тапа ({tap_price} кликов)", callback_data="upgrade_tap")],
        [InlineKeyboardButton(text=f"💰 Улучшить пассивный доход ({passive_price} кликов)", callback_data="upgrade_passive")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    ])
    return keyboard

def get_referral_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Забрать награду", callback_data="claim_referral")],
        [InlineKeyboardButton(text="◀️ На главную", callback_data="main_menu")]
    ])
    return keyboard