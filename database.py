import asyncpg
import os
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Optional

DATABASE_URL = os.getenv("DATABASE_URL")

async def get_connection():
    """Возвращает соединение с БД"""
    return await asyncpg.connect(DATABASE_URL)

async def init_db():
    """Создаёт все таблицы, если их нет"""
    conn = await get_connection()
    
    # Таблица пользователей
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            clicks BIGINT DEFAULT 0,
            level INTEGER DEFAULT 1,
            energy INTEGER DEFAULT 1000,
            tap_power INTEGER DEFAULT 1,
            passive_income INTEGER DEFAULT 0,
            premium_until TIMESTAMP DEFAULT NULL,
            current_skin TEXT DEFAULT '🦆',
            total_clicks BIGINT DEFAULT 0,
            last_daily TIMESTAMP DEFAULT NULL,
            daily_streak INTEGER DEFAULT 0,
            gems INTEGER DEFAULT 0,
            total_gems INTEGER DEFAULT 0
        )
    """)
    
    # Таблица рефералов
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            referrer_id BIGINT,
            referred_id BIGINT PRIMARY KEY,
            reward_claimed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица скинов
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS skins (
            id SERIAL PRIMARY KEY,
            name TEXT,
            emoji TEXT,
            price_clicks INTEGER,
            price_gems INTEGER DEFAULT 0,
            tap_bonus INTEGER DEFAULT 0,
            is_limited INTEGER DEFAULT 0
        )
    """)
    
    # Купленные скины
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS user_skins (
            user_id BIGINT,
            skin_id INTEGER,
            PRIMARY KEY (user_id, skin_id)
        )
    """)
    
    # Достижения
    await conn.execute("DROP TABLE IF EXISTS achievements")
    await conn.execute("""
    CREATE TABLE achievements (
        id SERIAL PRIMARY KEY,
        name TEXT,
        description TEXT,
        condition_type TEXT,
        condition_value INTEGER,
        reward_gems INTEGER,
        reward_clicks INTEGER,
        reward_skin_id INTEGER DEFAULT NULL
        )
    """)
    # Добавляем колонку reward_skin_id
    await conn.execute("ALTER TABLE achievements ADD COLUMN reward_skin_id INTEGER DEFAULT NULL")
    
    # Прогресс достижений пользователей
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS user_achievements (
            user_id BIGINT,
            achievement_id INTEGER,
            progress INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0,
            completed_at TIMESTAMP DEFAULT NULL,
            PRIMARY KEY (user_id, achievement_id)
        )
    """)
    
    # Кейсы
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id SERIAL PRIMARY KEY,
            name TEXT,
            emoji TEXT,
            price_gems INTEGER,
            price_clicks INTEGER
        )
    """)
    
    # Награды из кейсов
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS case_rewards (
            id SERIAL PRIMARY KEY,
            case_id INTEGER REFERENCES cases(id),
            reward_type TEXT,
            reward_value INTEGER,
            reward_text TEXT,
            chance INTEGER
        )
    """)
    
    # Бустеры
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS boosters (
            id SERIAL PRIMARY KEY,
            name TEXT,
            emoji TEXT,
            description TEXT,
            effect_type TEXT,
            effect_value REAL,
            duration_minutes INTEGER,
            price_gems INTEGER,
            price_clicks INTEGER
        )
    """)
    
    # Активные бустеры пользователей
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS user_boosters (
            user_id BIGINT,
            booster_id INTEGER,
            expires_at TIMESTAMP,
            PRIMARY KEY (user_id, booster_id)
        )
    """)
    
    # Ежедневные задания
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS quests (
            id SERIAL PRIMARY KEY,
            name TEXT,
            description TEXT,
            target_clicks INTEGER,
            reward_clicks INTEGER,
            reward_xp INTEGER DEFAULT 0
        )
    """)
    
    # Прогресс заданий пользователей
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS user_quests (
            user_id BIGINT,
            quest_id INTEGER,
            progress INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0,
            date DATE DEFAULT CURRENT_DATE,
            PRIMARY KEY (user_id, quest_id, date)
        )
    """)
    
    # Добавляем скины по умолчанию
    result = await conn.fetchval("SELECT COUNT(*) FROM skins")
    if result == 0:
        await conn.executemany("""
            INSERT INTO skins (name, emoji, price_clicks, price_gems, tap_bonus, is_limited)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, [
            ('Обычная утка', '🦆', 0, 0, 0, 0),
            ('Золотая утка', '🌟', 5000, 0, 2, 0),
            ('Киберутка', '🤖', 15000, 0, 5, 0),
            ('Утка-призрак', '👻', 30000, 0, 10, 0),
            ('Дьявольская утка', '😈', 50000, 0, 15, 0),
            ('Алмазная утка', '💎', 0, 50, 20, 1),
        ])
    
    # Добавляем достижения по умолчанию
    result = await conn.fetchval("SELECT COUNT(*) FROM achievements")
    if result == 0:
        await conn.executemany("""
            INSERT INTO achievements (name, description, condition_type, condition_value, reward_gems, reward_clicks, reward_skin_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, [
            ("Новичок", "Накликать 100 кликов", "clicks", 100, 1, 500, None),
            ("Серебряный палец", "Накликать 1000 кликов", "clicks", 1000, 2, 2000, None),
            ("Золотой палец", "Накликать 10000 кликов", "clicks", 10000, 5, 10000, None),
            ("Коллекционер", "Купить 1 скин", "skins", 1, 1, 500, None),
            ("Магнат", "Купить 3 скина", "skins", 3, 3, 2000, None),
            ("Реферал", "Пригласить 1 друга", "referrals", 1, 1, 1000, None),
            ("Популярный", "Пригласить 5 друзей", "referrals", 5, 5, 5000, None),
        ])
    
    # Добавляем кейсы по умолчанию
    result = await conn.fetchval("SELECT COUNT(*) FROM cases")
    if result == 0:
        await conn.execute("""
            INSERT INTO cases (name, emoji, price_gems, price_clicks)
            VALUES ($1, $2, $3, $4)
        """, "Обычный кейс", "📦", 0, 1000)
        
        case_id = await conn.fetchval("SELECT lastval()")
        
        await conn.executemany("""
            INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance)
            VALUES ($1, $2, $3, $4, $5)
        """, [
            (case_id, "clicks", 100, "100 кликов", 30),
            (case_id, "clicks", 500, "500 кликов", 20),
            (case_id, "clicks", 1000, "1000 кликов", 15),
            (case_id, "clicks", 5000, "5000 кликов", 5),
            (case_id, "gems", 1, "1 алмаз 💎", 15),
            (case_id, "gems", 5, "5 алмазов 💎", 8),
            (case_id, "booster", 1, "x2 клика (30 мин)", 5),
            (case_id, "skin", 2, "Золотая утка 🌟", 2),
        ])
        
        await conn.execute("""
            INSERT INTO cases (name, emoji, price_gems, price_clicks)
            VALUES ($1, $2, $3, $4)
        """, "Золотой кейс", "🎁", 10, 10000)
        
        case_id = await conn.fetchval("SELECT lastval()")
        
        await conn.executemany("""
            INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance)
            VALUES ($1, $2, $3, $4, $5)
        """, [
            (case_id, "clicks", 5000, "5000 кликов", 25),
            (case_id, "clicks", 10000, "10000 кликов", 20),
            (case_id, "gems", 5, "5 алмазов 💎", 15),
            (case_id, "gems", 10, "10 алмазов 💎", 10),
            (case_id, "booster", 2, "x2 клика (1 час)", 5),
            (case_id, "skin", 3, "Киберутка 🤖", 3),
        ])
    
    # Добавляем бустеры по умолчанию
    result = await conn.fetchval("SELECT COUNT(*) FROM boosters")
    if result == 0:
        await conn.executemany("""
            INSERT INTO boosters (name, emoji, description, effect_type, effect_value, duration_minutes, price_gems, price_clicks)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, [
            ("x2 Клики", "⚡", "Удваивает силу клика на 30 минут", "tap_multiplier", 2, 30, 5, 5000),
            ("Автокликер", "🤖", "Автоматически кликает 10 раз в секунду", "auto_click", 10, 30, 10, 10000),
            ("x2 Пассивка", "💰", "Удваивает пассивный доход на 1 час", "passive_multiplier", 2, 60, 3, 3000),
            ("Энергетик", "🔋", "Восстанавливает 500 энергии мгновенно", "energy", 500, 0, 2, 2000),
        ])
    
    # Добавляем задания по умолчанию
    result = await conn.fetchval("SELECT COUNT(*) FROM quests")
    if result == 0:
        await conn.executemany("""
            INSERT INTO quests (name, description, target_clicks, reward_clicks)
            VALUES ($1, $2, $3, $4)
        """, [
            ('Кликер', 'Сделай 100 кликов', 100, 500),
            ('Энергетик', 'Восстанови энергию 3 раза', 3, 300),
            ('Спонсор', 'Прокачай силу тапа', 1, 400),
            ('Реферал', 'Пригласи 1 друга', 1, 1000),
            ('Стресс-тест', 'Сделай 500 кликов', 500, 2000),
        ])
    
    await conn.close()

# ==================== ОСНОВНЫЕ ФУНКЦИИ ====================

async def get_user_stats(user_id: int) -> Tuple:
    conn = await get_connection()
    row = await conn.fetchrow("""
        SELECT clicks, level, energy, tap_power, passive_income, premium_until, current_skin, total_clicks, daily_streak, gems
        FROM users WHERE user_id = $1
    """, user_id)
    
    if not row:
        await conn.execute("""
            INSERT INTO users (user_id, clicks, level, energy, tap_power, passive_income, premium_until, current_skin, total_clicks, daily_streak, gems)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """, user_id, 0, 1, 1000, 1, 0, None, '🦆', 0, 0, 0)
        await conn.close()
        return (0, 1, 1000, 1, 0, None, '🦆', 0, 0, 0)
    
    await conn.close()
    return (row['clicks'], row['level'], row['energy'], row['tap_power'], row['passive_income'], 
            row['premium_until'], row['current_skin'], row['total_clicks'], row['daily_streak'], row['gems'])

async def update_tap(user_id: int, energy_cost: int = 1, tap_bonus: int = 0) -> Tuple:
    conn = await get_connection()
    
    row = await conn.fetchrow("""
        SELECT clicks, level, energy, tap_power, total_clicks FROM users WHERE user_id = $1
    """, user_id)
    
    if row['energy'] < energy_cost:
        await conn.close()
        return (row['clicks'], row['level'], row['energy'])
    
    total_tap_power = row['tap_power'] + tap_bonus
    new_clicks = row['clicks'] + total_tap_power
    new_total_clicks = row['total_clicks'] + total_tap_power
    new_energy = row['energy'] - energy_cost
    new_level = 1 + new_total_clicks // 100
    
    await conn.execute("""
        UPDATE users SET clicks = $1, level = $2, energy = $3, total_clicks = $4
        WHERE user_id = $5
    """, new_clicks, new_level, new_energy, new_total_clicks, user_id)
    
    await conn.close()
    return (new_clicks, new_level, new_energy)

async def add_clicks(user_id: int, amount: int):
    conn = await get_connection()
    await conn.execute("""
        UPDATE users SET clicks = clicks + $1, total_clicks = total_clicks + $1
        WHERE user_id = $2
    """, amount, user_id)
    await conn.close()

async def add_gems(user_id: int, amount: int):
    conn = await get_connection()
    await conn.execute("""
        UPDATE users SET gems = gems + $1, total_gems = total_gems + $1
        WHERE user_id = $2
    """, amount, user_id)
    await conn.close()

async def collect_passive_income(user_id: int) -> int:
    conn = await get_connection()
    row = await conn.fetchrow("""
        SELECT clicks, passive_income, premium_until FROM users WHERE user_id = $1
    """, user_id)
    
    multiplier = 1.5 if row['premium_until'] and datetime.now() < row['premium_until'] else 1.0
    earned = int(row['passive_income'] * multiplier)
    new_clicks = row['clicks'] + earned
    
    await conn.execute("UPDATE users SET clicks = $1 WHERE user_id = $2", new_clicks, user_id)
    await conn.close()
    return earned

async def claim_daily_bonus(user_id: int) -> Tuple[int, int]:
    conn = await get_connection()
    row = await conn.fetchrow("""
        SELECT last_daily, daily_streak, clicks FROM users WHERE user_id = $1
    """, user_id)
    
    today = datetime.now().date()
    last_date = row['last_daily'].date() if row['last_daily'] else None
    
    if last_date == today:
        await conn.close()
        return (0, row['daily_streak'])
    
    if last_date == today - timedelta(days=1):
        daily_streak = row['daily_streak'] + 1
    else:
        daily_streak = 1
    
    bonus = min(100 + daily_streak * 50, 600)
    new_clicks = row['clicks'] + bonus
    
    await conn.execute("""
        UPDATE users SET clicks = $1, last_daily = $2, daily_streak = $3
        WHERE user_id = $4
    """, new_clicks, today.isoformat(), daily_streak, user_id)
    
    await conn.close()
    return (bonus, daily_streak)

async def add_referral(referrer_id: int, referred_id: int) -> bool:
    conn = await get_connection()
    try:
        await conn.execute("""
            INSERT INTO referrals (referrer_id, referred_id) VALUES ($1, $2)
        """, referrer_id, referred_id)
        await conn.close()
        return True
    except:
        await conn.close()
        return False

async def claim_referral_reward(referrer_id: int) -> int:
    conn = await get_connection()
    count = await conn.fetchval("""
        SELECT COUNT(*) FROM referrals WHERE referrer_id = $1 AND reward_claimed = 0
    """, referrer_id)
    
    if count == 0:
        await conn.close()
        return 0
    
    reward = count * 1000
    await conn.execute("UPDATE users SET clicks = clicks + $1 WHERE user_id = $2", reward, referrer_id)
    await conn.execute("UPDATE referrals SET reward_claimed = 1 WHERE referrer_id = $1 AND reward_claimed = 0", referrer_id)
    
    await conn.close()
    return reward

async def get_referral_count(user_id: int) -> int:
    conn = await get_connection()
    count = await conn.fetchval("SELECT COUNT(*) FROM referrals WHERE referrer_id = $1", user_id)
    await conn.close()
    return count

async def get_skins_list() -> List[Dict]:
    conn = await get_connection()
    rows = await conn.fetch("SELECT id, name, emoji, price_clicks, price_gems, tap_bonus, is_limited FROM skins")
    await conn.close()
    return [{'id': r['id'], 'name': r['name'], 'emoji': r['emoji'], 'price': r['price_clicks'], 
             'price_gems': r['price_gems'], 'bonus': r['tap_bonus'], 'limited': r['is_limited']} for r in rows]

async def get_user_skins(user_id: int) -> List[int]:
    conn = await get_connection()
    rows = await conn.fetch("SELECT skin_id FROM user_skins WHERE user_id = $1", user_id)
    await conn.close()
    return [r['skin_id'] for r in rows]

async def buy_skin(user_id: int, skin_id: int) -> bool:
    conn = await get_connection()
    
    # Проверяем, есть ли уже такой скин
    exists = await conn.fetchval("SELECT 1 FROM user_skins WHERE user_id = $1 AND skin_id = $2", user_id, skin_id)
    if exists:
        await conn.close()
        return False
    
    # Получаем цену
    price = await conn.fetchval("SELECT price_clicks FROM skins WHERE id = $1", skin_id)
    
    # Проверяем баланс
    clicks = await conn.fetchval("SELECT clicks FROM users WHERE user_id = $1", user_id)
    
    if clicks < price:
        await conn.close()
        return False
    
    # Покупаем
    await conn.execute("UPDATE users SET clicks = clicks - $1 WHERE user_id = $2", price, user_id)
    await conn.execute("INSERT INTO user_skins (user_id, skin_id) VALUES ($1, $2)", user_id, skin_id)
    
    await conn.close()
    return True

async def equip_skin(user_id: int, skin_id: int) -> bool:
    conn = await get_connection()
    
    # Проверяем, есть ли скин у пользователя
    exists = await conn.fetchval("SELECT 1 FROM user_skins WHERE user_id = $1 AND skin_id = $2", user_id, skin_id)
    if not exists:
        await conn.close()
        return False
    
    # Получаем эмодзи скина
    emoji = await conn.fetchval("SELECT emoji FROM skins WHERE id = $1", skin_id)
    
    # Обновляем текущий скин
    await conn.execute("UPDATE users SET current_skin = $1 WHERE user_id = $2", emoji, user_id)
    
    await conn.close()
    return True

async def upgrade_tap_power(user_id: int) -> Tuple[bool, int, int]:
    conn = await get_connection()
    row = await conn.fetchrow("SELECT clicks, tap_power FROM users WHERE user_id = $1", user_id)
    
    price = row['tap_power'] * 100
    
    if row['clicks'] >= price:
        new_tap_power = row['tap_power'] + 1
        new_clicks = row['clicks'] - price
        await conn.execute("""
            UPDATE users SET clicks = $1, tap_power = $2 WHERE user_id = $3
        """, new_clicks, new_tap_power, user_id)
        await conn.close()
        return (True, new_tap_power, price)
    
    await conn.close()
    return (False, row['tap_power'], price)

async def upgrade_passive_income(user_id: int) -> Tuple[bool, int, int]:
    conn = await get_connection()
    row = await conn.fetchrow("SELECT clicks, passive_income FROM users WHERE user_id = $1", user_id)
    
    price = 500 + row['passive_income'] * 100
    
    if row['clicks'] >= price:
        new_passive = row['passive_income'] + 5
        new_clicks = row['clicks'] - price
        await conn.execute("""
            UPDATE users SET clicks = $1, passive_income = $2 WHERE user_id = $3
        """, new_clicks, new_passive, user_id)
        await conn.close()
        return (True, new_passive, price)
    
    await conn.close()
    return (False, row['passive_income'], price)

async def get_daily_quests(user_id: int) -> List[Dict]:
    conn = await get_connection()
    today = datetime.now().date().isoformat()
    
    quests = await conn.fetch("SELECT id, name, description, target_clicks, reward_clicks FROM quests")
    
    result = []
    for q in quests:
        progress_data = await conn.fetchrow("""
            SELECT progress, completed FROM user_quests
            WHERE user_id = $1 AND quest_id = $2 AND date = $3
        """, user_id, q['id'], today)
        
        if progress_data:
            progress, completed = progress_data['progress'], progress_data['completed']
        else:
            progress, completed = 0, 0
        
        result.append({
            'id': q['id'],
            'name': q['name'],
            'description': q['description'],
            'target': q['target_clicks'],
            'reward': q['reward_clicks'],
            'progress': progress,
            'completed': completed
        })
    
    await conn.close()
    return result

async def get_leaderboard(limit: int = 10) -> List[Tuple]:
    conn = await get_connection()
    rows = await conn.fetch("""
        SELECT user_id, total_clicks FROM users ORDER BY total_clicks DESC LIMIT $1
    """, limit)
    await conn.close()
    return [(r['user_id'], r['total_clicks']) for r in rows]

async def get_user_rank(user_id: int) -> int:
    conn = await get_connection()
    total_clicks = await conn.fetchval("SELECT total_clicks FROM users WHERE user_id = $1", user_id)
    rank = await conn.fetchval("SELECT COUNT(*) + 1 FROM users WHERE total_clicks > $1", total_clicks)
    await conn.close()
    return rank

async def is_premium(user_id: int) -> bool:
    conn = await get_connection()
    premium_until = await conn.fetchval("SELECT premium_until FROM users WHERE user_id = $1", user_id)
    await conn.close()
    if premium_until:
        return datetime.now() < premium_until
    return False

async def buy_premium(user_id: int, days: int = 30) -> bool:
    conn = await get_connection()
    price = days * 500
    
    clicks = await conn.fetchval("SELECT clicks FROM users WHERE user_id = $1", user_id)
    
    if clicks < price:
        await conn.close()
        return False
    
    current_until = await conn.fetchval("SELECT premium_until FROM users WHERE user_id = $1", user_id)
    
    if current_until:
        new_date = current_until + timedelta(days=days)
    else:
        new_date = datetime.now() + timedelta(days=days)
    
    await conn.execute("""
        UPDATE users SET clicks = clicks - $1, premium_until = $2 WHERE user_id = $3
    """, price, new_date, user_id)
    
    await conn.close()
    return True