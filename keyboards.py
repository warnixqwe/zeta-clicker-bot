from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура для обычных пользователей"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🦆 КВАК!", callback_data="tap"), InlineKeyboardButton(text="📊 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🎁 Ежедневный бонус", callback_data="daily"), InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals")],
        [InlineKeyboardButton(text="📋 Задания", callback_data="quests"), InlineKeyboardButton(text="🏆 Лидерборд", callback_data="leaderboard")],
        [InlineKeyboardButton(text="👕 Магазин скинов", callback_data="shop"), InlineKeyboardButton(text="💎 Прокачка", callback_data="upgrades")],
        [InlineKeyboardButton(text="⭐ Премиум", callback_data="premium"), InlineKeyboardButton(text="💰 Собрать пассивку", callback_data="collect_passive")]
    ])
    return keyboard

def get_back_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой 'На главную'"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ На главную", callback_data="main_menu")]
    ])
    return keyboard

def get_shop_keyboard(skins: list, user_skins: list, current_skin_emoji: str) -> InlineKeyboardMarkup:
    """Клавиатура магазина скинов"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for skin in skins:
        emoji = skin['emoji']
        name = skin['name']
        price = skin['price']
        skin_id = skin['id']
        
        if skin_id in user_skins:
            if current_skin_emoji == emoji:
                btn_text = f"{emoji} {name} — ЭКИПИРОВАН"
                callback = "noop"
            else:
                btn_text = f"{emoji} {name} — ЭКИПИРОВАТЬ"
                callback = f"equip_skin_{skin_id}"
        else:
            btn_text = f"{emoji} {name} — {price} кликов"
            callback = f"buy_skin_{skin_id}"
        
        keyboard.inline_keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=callback)])
    
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")])
    return keyboard

def get_upgrades_keyboard(tap_price: int, energy_price: int, passive_price: int) -> InlineKeyboardMarkup:
    """Клавиатура для прокачки"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💪 Улучшить силу тапа ({tap_price} кликов)", callback_data="upgrade_tap")],
        [InlineKeyboardButton(text=f"⚡ Улучшить энергию ({energy_price} кликов)", callback_data="upgrade_energy")],
        [InlineKeyboardButton(text=f"💰 Улучшить пассивный доход ({passive_price} кликов)", callback_data="upgrade_passive")],
        [InlineKeyboardButton(text="◀️ На главную", callback_data="main_menu")]
    ])
    return keyboard

def get_referral_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для реферальной системы"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Забрать награду", callback_data="claim_referral")],
        [InlineKeyboardButton(text="◀️ На главную", callback_data="main_menu")]
    ])
    return keyboard

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура админ-панели"""
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
    return keyboard

def get_confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения действия"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}"),
         InlineKeyboardButton(text="❌ Нет", callback_data="cancel")]
    ])
    return keyboard