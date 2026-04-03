from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура"""
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
        InlineKeyboardButton(text="💰 Собрать пассивку", callback_data="collect_passive")
    )
    return keyboard

def get_back_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой назад"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="◀️ На главную", callback_data="main_menu"))
    return keyboard

def get_shop_keyboard(skins: list, user_skins: list, current_skin_emoji: str) -> InlineKeyboardMarkup:
    """Клавиатура магазина скинов"""
    keyboard = InlineKeyboardMarkup(row_width=1)
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
        
        keyboard.add(InlineKeyboardButton(text=btn_text, callback_data=callback))
    
    keyboard.add(InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu"))
    return keyboard

def get_upgrades_keyboard(tap_price: int, energy_price: int, passive_price: int) -> InlineKeyboardMarkup:
    """Клавиатура прокачки"""
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(text=f"💪 Улучшить силу тапа ({tap_price} кликов)", callback_data="upgrade_tap"),
        InlineKeyboardButton(text=f"🔋 Улучшить энергию ({energy_price} кликов)", callback_data="upgrade_energy"),
        InlineKeyboardButton(text=f"💰 Улучшить пассивный доход ({passive_price} кликов)", callback_data="upgrade_passive"),
        InlineKeyboardButton(text="◀️ На главную", callback_data="main_menu")
    )
    return keyboard

def get_quests_keyboard(quests: list) -> InlineKeyboardMarkup:
    """Клавиатура заданий"""
    keyboard = InlineKeyboardMarkup(row_width=1)
    for quest in quests:
        status = "✅" if quest['completed'] else "🔄"
        btn_text = f"{status} {quest['name']} — {quest['progress']}/{quest['target']}"
        keyboard.add(InlineKeyboardButton(text=btn_text, callback_data=f"quest_{quest['id']}"))
    keyboard.add(InlineKeyboardButton(text="◀️ На главную", callback_data="main_menu"))
    return keyboard

def get_referral_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура рефералов"""
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(text="🎁 Забрать награду", callback_data="claim_referral"),
        InlineKeyboardButton(text="◀️ На главную", callback_data="main_menu")
    )
    return keyboard