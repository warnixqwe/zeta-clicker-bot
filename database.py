import asyncpg
import os
from datetime import datetime, timedelta
from typing import List, Tuple, Dict

DATABASE_URL = os.getenv("DATABASE_URL")

async def get_connection():
    return await asyncpg.connect(DATABASE_URL, statement_cache_size=0)

async def init_db():
    conn = await get_connection()
    
    await conn.execute("DROP TABLE IF EXISTS user_boosters")
    await conn.execute("DROP TABLE IF EXISTS user_skins")
    await conn.execute("DROP TABLE IF EXISTS case_rewards")
    await conn.execute("DROP TABLE IF EXISTS referrals")
    await conn.execute("DROP TABLE IF EXISTS achievements")
    await conn.execute("DROP TABLE IF EXISTS skins")
    await conn.execute("DROP TABLE IF EXISTS boosters")
    await conn.execute("DROP TABLE IF EXISTS cases")
    await conn.execute("DROP TABLE IF EXISTS users")
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            balance BIGINT DEFAULT 0,
            profit_per_tap INTEGER DEFAULT 1,
            profit_per_hour INTEGER DEFAULT 0,
            energy INTEGER DEFAULT 1000,
            max_energy INTEGER DEFAULT 1000,
            gems INTEGER DEFAULT 0,
            total_clicks BIGINT DEFAULT 0,
            daily_streak INTEGER DEFAULT 0,
            last_daily TIMESTAMP DEFAULT NULL,
            last_energy_update TIMESTAMP DEFAULT NULL,
            current_skin TEXT DEFAULT '🦆'
        )
    """)
    
    await conn.execute("""
        CREATE TABLE referrals (
            referrer_id BIGINT,
            referred_id BIGINT PRIMARY KEY,
            reward_claimed INTEGER DEFAULT 0,
            bonus_claimed INTEGER DEFAULT 0,
            referred_tap_power INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await conn.execute("""
        CREATE TABLE skins (
            id SERIAL PRIMARY KEY,
            name TEXT,
            emoji TEXT,
            price_clicks INTEGER,
            price_gems INTEGER DEFAULT 0,
            tap_bonus INTEGER DEFAULT 0
        )
    """)
    
    await conn.execute("""
        CREATE TABLE user_skins (
            user_id BIGINT,
            skin_id INTEGER,
            PRIMARY KEY (user_id, skin_id)
        )
    """)
    
    await conn.execute("""
        CREATE TABLE cases (
            id SERIAL PRIMARY KEY,
            name TEXT,
            emoji TEXT,
            price_clicks INTEGER,
            price_gems INTEGER DEFAULT 0
        )
    """)
    
    await conn.execute("""
        CREATE TABLE case_rewards (
            id SERIAL PRIMARY KEY,
            case_id INTEGER REFERENCES cases(id) ON DELETE CASCADE,
            reward_type TEXT,
            reward_value INTEGER,
            reward_text TEXT,
            chance INTEGER
        )
    """)
    
    await conn.execute("""
        CREATE TABLE boosters (
            id SERIAL PRIMARY KEY,
            name TEXT,
            emoji TEXT,
            description TEXT,
            effect_type TEXT,
            effect_value REAL,
            duration_minutes INTEGER,
            price_clicks INTEGER,
            price_gems INTEGER DEFAULT 0
        )
    """)
    
    await conn.execute("""
        CREATE TABLE user_boosters (
            user_id BIGINT,
            booster_id INTEGER,
            expires_at TIMESTAMP,
            PRIMARY KEY (user_id, booster_id)
        )
    """)
    
    # Добавляем скины
    await conn.executemany("""
        INSERT INTO skins (name, emoji, price_clicks, price_gems, tap_bonus) VALUES ($1, $2, $3, $4, $5)
    """, [
        ('Обычная утка', '🦆', 0, 0, 0),
        ('Золотая утка', '🌟', 5000, 0, 2),
        ('Киберутка', '🤖', 15000, 0, 5),
        ('Утка-призрак', '👻', 30000, 0, 10),
        ('Дьявольская утка', '😈', 50000, 0, 15),
    ])
    
    # Кейсы
    await conn.execute("INSERT INTO cases (name, emoji, price_clicks, price_gems) VALUES ($1, $2, $3, $4)", 'Обычный кейс', '📦', 1000, 0)
    await conn.execute("INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance) VALUES (1, 'clicks', 100, '100 монет', 30)")
    await conn.execute("INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance) VALUES (1, 'clicks', 500, '500 монет', 20)")
    await conn.execute("INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance) VALUES (1, 'clicks', 1000, '1000 монет', 15)")
    await conn.execute("INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance) VALUES (1, 'gems', 1, '1 алмаз 💎', 15)")
    await conn.execute("INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance) VALUES (1, 'gems', 5, '5 алмазов 💎', 8)")
    await conn.execute("INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance) VALUES (1, 'booster', 1, 'x2 прибыль (30 мин)', 5)")
    await conn.execute("INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance) VALUES (1, 'skin', 2, 'Золотая утка 🌟', 2)")
    
    await conn.execute("INSERT INTO cases (name, emoji, price_clicks, price_gems) VALUES ($1, $2, $3, $4)", 'Золотой кейс', '🎁', 10000, 10)
    await conn.execute("INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance) VALUES (2, 'clicks', 5000, '5000 монет', 25)")
    await conn.execute("INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance) VALUES (2, 'clicks', 10000, '10000 монет', 20)")
    await conn.execute("INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance) VALUES (2, 'gems', 5, '5 алмазов 💎', 15)")
    await conn.execute("INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance) VALUES (2, 'gems', 10, '10 алмазов 💎', 10)")
    await conn.execute("INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance) VALUES (2, 'gems', 25, '25 алмазов 💎', 5)")
    await conn.execute("INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance) VALUES (2, 'booster', 1, 'x2 прибыль (30 мин)', 5)")
    await conn.execute("INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance) VALUES (2, 'skin', 3, 'Киберутка 🤖', 3)")
    
    await conn.execute("INSERT INTO cases (name, emoji, price_clicks, price_gems) VALUES ($1, $2, $3, $4)", 'Алмазный кейс', '💎', 50000, 50)
    await conn.execute("INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance) VALUES (3, 'clicks', 25000, '25000 монет', 20)")
    await conn.execute("INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance) VALUES (3, 'clicks', 50000, '50000 монет', 15)")
    await conn.execute("INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance) VALUES (3, 'gems', 10, '10 алмазов 💎', 20)")
    await conn.execute("INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance) VALUES (3, 'gems', 25, '25 алмазов 💎', 15)")
    await conn.execute("INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance) VALUES (3, 'gems', 50, '50 алмазов 💎', 10)")
    await conn.execute("INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance) VALUES (3, 'skin', 4, 'Утка-призрак 👻', 5)")
    await conn.execute("INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance) VALUES (3, 'skin', 5, 'Дьявольская утка 😈', 3)")
    
    # Бустеры
    await conn.execute("INSERT INTO boosters (name, emoji, description, effect_type, effect_value, duration_minutes, price_clicks, price_gems) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)", 'x2 Прибыль', '⚡', 'Удваивает прибыль за тап на 30 минут', 'tap_multiplier', 2, 30, 5000, 0)
    await conn.execute("INSERT INTO boosters (name, emoji, description, effect_type, effect_value, duration_minutes, price_clicks, price_gems) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)", 'Энергетик', '🔋', 'Восстанавливает 500 энергии', 'energy', 500, 0, 2000, 0)
    
    await conn.close()

async def get_user_stats(user_id: int):
   # Таблица ежедневной статистики (топ)
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS daily_stats (
        user_id BIGINT NOT NULL,
        clicks_today BIGINT DEFAULT 0,
        date DATE DEFAULT CURRENT_DATE,
        PRIMARY KEY (user_id, date)
    )
""")
    
     # Индекс для быстрых запросов топа
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_stats_date_clicks ON daily_stats(date, clicks_today DESC)")
    
    await conn.close()

   # Таблица ежедневной статистики (топ)
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS daily_stats (
        user_id BIGINT NOT NULL,
        clicks_today BIGINT DEFAULT 0,
        date DATE DEFAULT CURRENT_DATE,
        PRIMARY KEY (user_id, date)
    )
""")
    
     # Индекс для быстрых запросов топа
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_stats_date_clicks ON daily_stats(date, clicks_today DESC)")
    
    await conn.close()

# ==================== ОСНОВНЫЕ ФУНКЦИИ ====================

async def get_user_stats(user_id: int) -> Tuple:
    conn = await get_connection()
    row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
    if not row:
        await conn.execute("""
            INSERT INTO users (user_id, balance, profit_per_tap, profit_per_hour, energy, max_energy, gems, total_clicks, daily_streak, last_daily, current_skin)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """, user_id, 0, 1, 0, 1000, 1000, 0, 0, 0, None, '🦆')
        await conn.close()
        return {
            "balance": 0, "profit_per_tap": 1, "profit_per_hour": 0, "energy": 1000,
            "max_energy": 1000, "gems": 0, "total_clicks": 0, "daily_streak": 0, "current_skin": "🦆"
        }
    await conn.close()
    return {
        "balance": row["balance"],
        "profit_per_tap": row["profit_per_tap"],
        "profit_per_hour": row["profit_per_hour"],
        "energy": row["energy"],
        "max_energy": row["max_energy"],
        "gems": row["gems"],
        "total_clicks": row["total_clicks"],
        "daily_streak": row["daily_streak"],
        "current_skin": row["current_skin"] if row["current_skin"] else "🦆"
    }

async def update_clicks(user_id: int, increment: int):
    """Обновляет баланс и энергию при клике"""
async def regenerate_energy(user_id: int):
    conn = await get_connection()
    row = await conn.fetchrow("SELECT energy, max_energy, last_energy_update FROM users WHERE user_id = $1", user_id)
    now = datetime.now()
    last = row["last_energy_update"] or now
    seconds_passed = (now - last).total_seconds()
    if seconds_passed > 0:
        new_energy = min(row["energy"] + int(seconds_passed / 2), row["max_energy"])  # 1 энергия за 2 секунды
        await conn.execute("UPDATE users SET energy = $1, last_energy_update = $2 WHERE user_id = $3",
                           new_energy, now, user_id)
    await conn.close()

async def regenerate_energy(user_id: int):
    conn = await get_connection()
    row = await conn.fetchrow("SELECT energy, max_energy, last_energy_update FROM users WHERE user_id = $1", user_id)
    now = datetime.now()
    last = row["last_energy_update"] or now
    seconds_passed = (now - last).total_seconds()
    if seconds_passed > 0:
        new_energy = min(row["energy"] + int(seconds_passed / 2), row["max_energy"])  # 1 энергия за 2 секунды
        await conn.execute("UPDATE users SET energy = $1, last_energy_update = $2 WHERE user_id = $3",
                           new_energy, now, user_id)
    await conn.close()

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
        UPDATE users 
        SET balance = balance + $1, 
            total_clicks = total_clicks + $1, 
            energy = energy - 1 
        WHERE user_id = $2
    """, increment, user_id)
    await conn.close()

async def add_referral(referrer_id: int, referred_id: int) -> bool:
    if referrer_id == referred_id:
        pass
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

async def claim_daily_bonus(user_id: int):
    conn = await get_connection()
    row = await conn.fetchrow("SELECT last_daily, daily_streak, balance FROM users WHERE user_id = $1", user_id)
    today = datetime.now().date()
    last = row["last_daily"].date() if row["last_daily"] else None
    if last == today:
        await conn.close()
        return (False, 0, 0)
    if last == today - timedelta(days=1):
        streak = row["daily_streak"] + 1
    else:
        streak = 1
    bonus = 100 + streak * 50   # например, 150, 200, 250...
    new_balance = row["balance"] + bonus
    await conn.execute("UPDATE users SET balance = $1, daily_streak = $2, last_daily = $3 WHERE user_id = $4",
                       new_balance, streak, today, user_id)
    await conn.close()
    return (True, bonus, streak)

async def add_referral(user_id: int, referrer_id: int) -> bool:
    if user_id == referrer_id:
        return False
    conn = await get_connection()
    try:
        await conn.execute("""
            INSERT INTO referrals (referrer_id, referred_id, referred_tap_power) 
            VALUES ($1, $2, $3)
        """, referrer_id, referred_id, 1)
        await conn.execute("UPDATE users SET balance = balance + 1000 WHERE user_id = $1", referrer_id)
        await conn.close()
        return True
    except:
        await conn.close()
        return False

async def check_referral_bonus(user_id: int, new_tap_power: int):
    """Проверяем, не прокачал ли реферал силу тапа до 10 уровня"""
    conn = await get_connection()
    referrer = await conn.fetchval("""
        SELECT referrer_id FROM referrals WHERE referred_id = $1 AND bonus_claimed = 0
    """, user_id)
    if referrer and new_tap_power >= 10:
        await conn.execute("UPDATE users SET balance = balance + 5000 WHERE user_id = $1", referrer)
        await conn.execute("UPDATE referrals SET bonus_claimed = 1 WHERE referred_id = $1", user_id)
    await conn.close()

async def get_referrals(user_id: int) -> int:
    conn = await get_connection()
    count = await conn.fetchval("SELECT COUNT(*) FROM referrals WHERE referrer_id = $1", user_id)
    await conn.close()
    return count

async def claim_referral_reward(user_id: int) -> int:
    conn = await get_connection()
    count = await conn.fetchval("SELECT COUNT(*) FROM referrals WHERE referrer_id = $1 AND reward_claimed = 0", user_id)
    if count == 0:
        await conn.close()
        return 0
    reward = count * 1000
    await conn.execute("UPDATE users SET balance = balance + $1 WHERE user_id = $2", reward, user_id)
    await conn.execute("UPDATE referrals SET reward_claimed = 1 WHERE referrer_id = $1 AND reward_claimed = 0", user_id)
    await conn.close()
    return reward

async def upgrade_tap_power(user_id: int):
    stats = await get_user_stats(user_id)
    price = stats["profit_per_tap"] * 100
    if stats["balance"] >= price:
        conn = await get_connection()
        new_balance = stats["balance"] - price
        new_profit = stats["profit_per_tap"] + 1
        await conn.execute("UPDATE users SET balance = $1, profit_per_tap = $2 WHERE user_id = $3", new_balance, new_profit, user_id)
        await conn.close()
        return (True, new_profit, price)
    return (False, stats["profit_per_tap"], price)

async def upgrade_hourly(user_id: int):
    stats = await get_user_stats(user_id)
    price = 500 + stats["profit_per_hour"] * 100
    if stats["balance"] >= price:
        conn = await get_connection()
        new_balance = stats["balance"] - price
        new_hourly = stats["profit_per_hour"] + 5
        await conn.execute("UPDATE users SET balance = $1, profit_per_hour = $2 WHERE user_id = $3", new_balance, new_hourly, user_id)
        await conn.close()
        return (True, new_hourly, price)
    return (False, stats["profit_per_hour"], price)

async def get_skins(user_id: int):
    conn = await get_connection()
    rows = await conn.fetch("SELECT skin_id FROM user_skins WHERE user_id = $1", user_id)
    owned = [row["skin_id"] for row in rows]
    skins_rows = await conn.fetch("SELECT id, name, emoji, price_clicks, tap_bonus FROM skins")
    await conn.close()
    return [{"id": r["id"], "name": r["name"], "emoji": r["emoji"], "price": r["price_clicks"], "bonus": r["tap_bonus"], "owned": r["id"] in owned} for r in skins_rows]

async def buy_skin(user_id: int, skin_id: int):
    stats = await get_user_stats(user_id)
    conn = await get_connection()
    price = await conn.fetchval("SELECT price_clicks FROM skins WHERE id = $1", skin_id)
    if stats["balance"] >= price:
        new_balance = stats["balance"] - price
        await conn.execute("UPDATE users SET balance = $1 WHERE user_id = $2", new_balance, user_id)
        await conn.execute("INSERT INTO user_skins (user_id, skin_id) VALUES ($1, $2) ON CONFLICT DO NOTHING", user_id, skin_id)
        skin = await conn.fetchrow("SELECT name, emoji FROM skins WHERE id = $1", skin_id)
        await conn.close()
        return (True, skin["name"], skin["emoji"])
    await conn.close()
    return (False, None, None)

async def equip_skin(user_id: int, skin_id: int):
    conn = await get_connection()
    owned = await conn.fetchval("SELECT 1 FROM user_skins WHERE user_id = $1 AND skin_id = $2", user_id, skin_id)
    if not owned:
        await conn.close()
        return (False, None)
    emoji = await conn.fetchval("SELECT emoji FROM skins WHERE id = $1", skin_id)
    await conn.execute("UPDATE users SET current_skin = $1 WHERE user_id = $2", emoji, user_id)
    await conn.close()
    return (True, emoji)

async def open_case(user_id: int, case_id: int):
    conn = await get_connection()
    case = await conn.fetchrow("SELECT name, emoji, price_clicks, price_gems FROM cases WHERE id = $1", case_id)
    if not case:
        row = await conn.fetchrow("SELECT clicks, tap_power FROM users WHERE user_id = $1", user_id)
    
    price = row['tap_power'] * 100
    
    if row['clicks'] >= price:
        new_tap_power = row['tap_power'] + 1
        new_clicks = row['clicks'] - price
        await conn.execute("""
            UPDATE users SET clicks = $1, tap_power = $2 WHERE user_id = $3
        """, new_clicks, new_tap_power, user_id)
        await check_referral_activity(user_id, new_profit)

        await conn.close()
        return (False, None, None, None)
    stats = await get_user_stats(user_id)
    if case["price_clicks"] > 0 and stats["balance"] >= case["price_clicks"]:
        new_balance = stats["balance"] - case["price_clicks"]
        await conn.execute("UPDATE users SET balance = $1 WHERE user_id = $2", new_balance, user_id)
    elif case["price_gems"] > 0 and stats["gems"] >= case["price_gems"]:
        new_gems = stats["gems"] - case["price_gems"]
        await conn.execute("UPDATE users SET gems = $1 WHERE user_id = $2", new_gems, user_id)
    else:
        await conn.close()
        return (False, None, None, None)
    rewards = await conn.fetch("SELECT reward_type, reward_value, reward_text FROM case_rewards WHERE case_id = $1", case_id)
    import random
    selected = random.choice(rewards)
    if selected["reward_type"] == "clicks":
        await conn.execute("UPDATE users SET balance = balance + $1 WHERE user_id = $2", selected["reward_value"], user_id)
    elif selected["reward_type"] == "gems":
        await conn.execute("UPDATE users SET gems = gems + $1 WHERE user_id = $2", selected["reward_value"], user_id)
    elif selected["reward_type"] == "booster":
        expires_at = datetime.now() + timedelta(minutes=30)
        await conn.execute("INSERT INTO user_boosters (user_id, booster_id, expires_at) VALUES ($1, $2, $3) ON CONFLICT (user_id, booster_id) DO UPDATE SET expires_at = EXCLUDED.expires_at", user_id, 1, expires_at)
    elif selected["reward_type"] == "skin":
        await conn.execute("INSERT INTO user_skins (user_id, skin_id) VALUES ($1, $2) ON CONFLICT DO NOTHING", user_id, selected["reward_value"])
    await conn.close()
    return (True, selected["reward_text"], case["emoji"], None)

async def get_cases():
    conn = await get_connection()
    cases = await conn.fetch("SELECT id, name, emoji, price_clicks, price_gems FROM cases")
    await conn.close()
    return [{"id": c["id"], "name": c["name"], "emoji": c["emoji"], "price_clicks": c["price_clicks"], "price_gems": c["price_gems"]} for c in cases]

async def get_boosters(user_id: int):
    conn = await get_connection()
    now = datetime.now()
    rows = await conn.fetch("""
        SELECT b.id, b.name, b.emoji, b.description, b.effect_type, b.effect_value, 
               (EXTRACT(EPOCH FROM (ub.expires_at - $1)) / 60)::INT as minutes_left
        FROM user_boosters ub
        JOIN boosters b ON ub.booster_id = b.id
        WHERE ub.user_id = $2 AND ub.expires_at > $1
    """, now, user_id)
    await conn.close()
    return [dict(row) for row in rows]

async def buy_booster(user_id: int, booster_id: int):
    stats = await get_user_stats(user_id)
    price = 5000
    if stats["balance"] >= price:
        conn = await get_connection()
        new_balance = stats["balance"] - price
        await conn.execute("UPDATE users SET balance = $1 WHERE user_id = $2", new_balance, user_id)
        expires_at = datetime.now() + timedelta(minutes=30)
        await conn.execute("INSERT INTO user_boosters (user_id, booster_id, expires_at) VALUES ($1, $2, $3) ON CONFLICT (user_id, booster_id) DO UPDATE SET expires_at = EXCLUDED.expires_at", user_id, booster_id, expires_at)
        await conn.close()
        return (True, "x2 Прибыль", "⚡")
    return (False, None, None)

async def get_leaderboard(limit: int = 10):
    conn = await get_connection()
    rows = await conn.fetch("SELECT user_id, balance, total_clicks FROM users ORDER BY balance DESC LIMIT $1", limit)
    await conn.close()
    leaderboard = []
    for row in rows:
        user_id = row["user_id"]
        username = str(user_id)
        try:
            from aiogram import Bot
            bot = Bot(token=os.getenv("BOT_TOKEN"))
            user = await bot.get_chat(user_id)
            await bot.session.close()
            if user.username:
                username = f"@{user.username}"
            elif user.first_name:
                username = user.first_name
        except:
            pass
        leaderboard.append({"user_id": user_id, "username": username, "balance": row["balance"], "clicks": row["total_clicks"]})
    return leaderboard     
    return True

async def check_referral_activity(referred_id: int, new_tap_power: int):
    """Если реферал достиг силы тапа 10, наградить пригласившего"""
    conn = await get_connection()
    row = await conn.fetchrow("SELECT referrer_id, bonus_claimed FROM referrals WHERE referred_id = $1", referred_id)
    if row and not row["bonus_claimed"] and new_tap_power >= 10:
        referrer = row["referrer_id"]
        await conn.execute("UPDATE users SET balance = balance + 5000 WHERE user_id = $1", referrer)
        await conn.execute("UPDATE referrals SET bonus_claimed = TRUE WHERE referred_id = $1", referred_id)
    await conn.close()

async def check_and_notify_passive(user_id: int):
    """Проверяет, не накопилось ли 1000 пассивного дохода, и отправляет уведомление"""
    conn = await get_connection()
    row = await conn.fetchrow("SELECT passive_income, last_passive_notify FROM users WHERE user_id = $1", user_id)
    if not row:
        await conn.close()
        return
    passive = row["passive_income"]
    last_notify = row["last_passive_notify"]
    if passive >= 1000 and (last_notify is None or (datetime.now() - last_notify).total_seconds() > 3600):
        await conn.execute("UPDATE users SET last_passive_notify = $1 WHERE user_id = $2", datetime.now(), user_id)
        await bot.send_message(user_id, f"💰 **Внимание!** Твой пассивный доход накопил {passive} монет! Забери их в игре.", parse_mode="Markdown")
    await conn.close()

async def award_daily_top():
    """Раз в сутки начисляет награды топ-3 игроков по кликам за день"""
    conn = await get_connection()
    yesterday = (datetime.now() - timedelta(days=1)).date()
    rows = await conn.fetch("""
        SELECT user_id, clicks_today FROM daily_stats
        WHERE date = $1
        ORDER BY clicks_today DESC LIMIT 3
    """, yesterday)
    rewards = [5000, 3000, 1000]
    for i, row in enumerate(rows):
        bonus = rewards[i] if i < len(rewards) else 0
        if bonus:
            await conn.execute("UPDATE users SET balance = balance + $1 WHERE user_id = $2", bonus, row["user_id"])
            await bot.send_message(row["user_id"], f"🏆 **Топ дня!** Ты занял {i+1} место и получил {bonus} монет!")
    await conn.close()