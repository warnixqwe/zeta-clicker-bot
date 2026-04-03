import sqlite3
import os
from datetime import datetime, timedelta
from typing import Tuple, List, Dict

DB_PATH = os.path.join(os.path.dirname(__file__), "zeta_clicker.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            clicks INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            energy INTEGER DEFAULT 1000,
            tap_power INTEGER DEFAULT 1,
            passive_income INTEGER DEFAULT 0,
            premium_until TIMESTAMP DEFAULT NULL,
            current_skin TEXT DEFAULT '🦆',
            total_clicks INTEGER DEFAULT 0,
            last_daily TIMESTAMP DEFAULT NULL,
            daily_streak INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            referrer_id INTEGER,
            referred_id INTEGER PRIMARY KEY,
            reward_claimed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            target_clicks INTEGER,
            reward_clicks INTEGER,
            reward_xp INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_quests (
            user_id INTEGER,
            quest_id INTEGER,
            progress INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0,
            date DATE DEFAULT CURRENT_DATE,
            PRIMARY KEY (user_id, quest_id, date)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            emoji TEXT,
            price_clicks INTEGER,
            tap_bonus INTEGER DEFAULT 0,
            is_limited INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_skins (
            user_id INTEGER,
            skin_id INTEGER,
            equipped INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, skin_id)
        )
    """)

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM skins")
    if cursor.fetchone()[0] == 0:
        default_skins = [
            ('Обычная утка', '🦆', 0, 0),
            ('Золотая утка', '🌟', 5000, 2),
            ('Киберутка', '🤖', 15000, 5),
            ('Утка-призрак', '👻', 30000, 10),
            ('Дьявольская утка', '😈', 50000, 15),
        ]
        cursor.executemany(
            "INSERT INTO skins (name, emoji, price_clicks, tap_bonus) VALUES (?, ?, ?, ?)",
            default_skins
        )
        conn.commit()

    cursor.execute("SELECT COUNT(*) FROM quests")
    if cursor.fetchone()[0] == 0:
        default_quests = [
            ('Кликер', 'Сделай 100 кликов', 100, 500),
            ('Энергетик', 'Восстанови энергию 3 раза', 3, 300),
            ('Спонсор', 'Прокачай силу тапа', 1, 400),
            ('Реферал', 'Пригласи 1 друга', 1, 1000),
            ('Стресс-тест', 'Сделай 500 кликов', 500, 2000),
        ]
        cursor.executemany(
            "INSERT INTO quests (name, description, target_clicks, reward_clicks) VALUES (?, ?, ?, ?)",
            default_quests
        )
        conn.commit()

    conn.close()

def get_user_stats(user_id: int) -> Tuple:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT clicks, level, energy, tap_power, passive_income, premium_until, current_skin, total_clicks, daily_streak FROM users WHERE user_id = ?",
        (user_id,)
    )
    result = cursor.fetchone()
    if not result:
        cursor.execute(
            "INSERT INTO users (user_id, clicks, level, energy, tap_power, passive_income, premium_until, current_skin, total_clicks, daily_streak) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, 0, 1, 1000, 1, 0, None, '🦆', 0, 0)
        )
        conn.commit()
        result = (0, 1, 1000, 1, 0, None, '🦆', 0, 0)
    conn.close()
    return result

def update_tap(user_id: int, energy_cost: int = 1, tap_bonus: int = 0) -> Tuple:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT clicks, level, energy, tap_power, total_clicks FROM users WHERE user_id = ?", (user_id,))
    clicks, level, energy, tap_power, total_clicks = cursor.fetchone()
    if energy < energy_cost:
        conn.close()
        return (clicks, level, energy)
    total_tap_power = tap_power + tap_bonus
    new_clicks = clicks + total_tap_power
    new_total_clicks = total_clicks + total_tap_power
    new_energy = energy - energy_cost
    new_level = 1 + new_total_clicks // 100
    cursor.execute(
        "UPDATE users SET clicks = ?, level = ?, energy = ?, total_clicks = ? WHERE user_id = ?",
        (new_clicks, new_level, new_energy, new_total_clicks, user_id)
    )
    conn.commit()
    conn.close()
    return (new_clicks, new_level, new_energy)

def collect_passive_income(user_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT clicks, passive_income, premium_until FROM users WHERE user_id = ?", (user_id,))
    clicks, passive_income, premium_until = cursor.fetchone()
    multiplier = 1.5 if premium_until and datetime.now() < datetime.fromisoformat(premium_until) else 1.0
    earned = int(passive_income * multiplier)
    new_clicks = clicks + earned
    cursor.execute("UPDATE users SET clicks = ? WHERE user_id = ?", (new_clicks, user_id))
    conn.commit()
    conn.close()
    return earned

def claim_daily_bonus(user_id: int) -> Tuple[int, int]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT last_daily, daily_streak, clicks FROM users WHERE user_id = ?", (user_id,))
    last_daily, daily_streak, clicks = cursor.fetchone()
    today = datetime.now().date()
    last_date = datetime.fromisoformat(last_daily).date() if last_daily else None
    if last_date == today:
        conn.close()
        return (0, daily_streak)
    if last_date == today - timedelta(days=1):
        daily_streak += 1
    else:
        daily_streak = 1
    bonus = min(100 + daily_streak * 50, 600)
    new_clicks = clicks + bonus
    cursor.execute(
        "UPDATE users SET clicks = ?, last_daily = ?, daily_streak = ? WHERE user_id = ?",
        (new_clicks, today.isoformat(), daily_streak, user_id)
    )
    conn.commit()
    conn.close()
    return (bonus, daily_streak)

def add_referral(referrer_id: int, referred_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (referrer_id, referred_id))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def claim_referral_reward(referrer_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND reward_claimed = 0", (referrer_id,))
    count = cursor.fetchone()[0]
    if count == 0:
        conn.close()
        return 0
    reward = count * 1000
    cursor.execute("SELECT clicks FROM users WHERE user_id = ?", (referrer_id,))
    clicks = cursor.fetchone()[0]
    cursor.execute("UPDATE users SET clicks = ? WHERE user_id = ?", (clicks + reward, referrer_id))
    cursor.execute("UPDATE referrals SET reward_claimed = 1 WHERE referrer_id = ? AND reward_claimed = 0", (referrer_id,))
    conn.commit()
    conn.close()
    return reward

def get_referral_count(user_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_daily_quests(user_id: int) -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    today = datetime.now().date().isoformat()
    cursor.execute("SELECT id, name, description, target_clicks, reward_clicks FROM quests")
    quests = cursor.fetchall()
    result = []
    for q_id, name, desc, target, reward in quests:
        cursor.execute("SELECT progress, completed FROM user_quests WHERE user_id = ? AND quest_id = ? AND date = ?", (user_id, q_id, today))
        progress_data = cursor.fetchone()
        if progress_data:
            progress, completed = progress_data
        else:
            progress, completed = 0, 0
        result.append({'id': q_id, 'name': name, 'description': desc, 'target': target, 'reward': reward, 'progress': progress, 'completed': completed})
    conn.close()
    return result

def get_skins_list() -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, emoji, price_clicks, tap_bonus FROM skins")
    skins = cursor.fetchall()
    conn.close()
    return [{'id': s[0], 'name': s[1], 'emoji': s[2], 'price': s[3], 'bonus': s[4]} for s in skins]

def get_user_skins(user_id: int) -> List[int]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT skin_id FROM user_skins WHERE user_id = ?", (user_id,))
    skins = cursor.fetchall()
    conn.close()
    return [s[0] for s in skins]

def buy_skin(user_id: int, skin_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM user_skins WHERE user_id = ? AND skin_id = ?", (user_id, skin_id))
    if cursor.fetchone():
        conn.close()
        return False
    cursor.execute("SELECT price_clicks FROM skins WHERE id = ?", (skin_id,))
    price = cursor.fetchone()[0]
    cursor.execute("SELECT clicks FROM users WHERE user_id = ?", (user_id,))
    clicks = cursor.fetchone()[0]
    if clicks < price:
        conn.close()
        return False
    cursor.execute("UPDATE users SET clicks = ? WHERE user_id = ?", (clicks - price, user_id))
    cursor.execute("INSERT INTO user_skins (user_id, skin_id) VALUES (?, ?)", (user_id, skin_id))
    conn.commit()
    conn.close()
    return True

def equip_skin(user_id: int, skin_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM user_skins WHERE user_id = ? AND skin_id = ?", (user_id, skin_id))
    if not cursor.fetchone():
        conn.close()
        return False
    cursor.execute("SELECT emoji FROM skins WHERE id = ?", (skin_id,))
    emoji = cursor.fetchone()[0]
    cursor.execute("UPDATE users SET current_skin = ? WHERE user_id = ?", (emoji, user_id))
    conn.commit()
    conn.close()
    return True

def is_premium(user_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT premium_until FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result and result[0]:
        return datetime.now() < datetime.fromisoformat(result[0])
    return False

def buy_premium(user_id: int, days: int = 30) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    price = days * 500
    cursor.execute("SELECT clicks FROM users WHERE user_id = ?", (user_id,))
    clicks = cursor.fetchone()[0]
    if clicks < price:
        conn.close()
        return False
    cursor.execute("SELECT premium_until FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    current_until = result[0] if result else None
    if current_until:
        new_date = datetime.fromisoformat(current_until) + timedelta(days=days)
    else:
        new_date = datetime.now() + timedelta(days=days)
    cursor.execute("UPDATE users SET clicks = ?, premium_until = ? WHERE user_id = ?", (clicks - price, new_date.isoformat(), user_id))
    conn.commit()
    conn.close()
    return True

def upgrade_tap_power(user_id: int) -> Tuple[bool, int, int]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT clicks, tap_power FROM users WHERE user_id = ?", (user_id,))
    clicks, tap_power = cursor.fetchone()
    price = tap_power * 100
    if clicks >= price:
        new_tap_power = tap_power + 1
        new_clicks = clicks - price
        cursor.execute("UPDATE users SET clicks = ?, tap_power = ? WHERE user_id = ?", (new_clicks, new_tap_power, user_id))
        conn.commit()
        conn.close()
        return (True, new_tap_power, price)
    conn.close()
    return (False, tap_power, price)

def upgrade_energy(user_id: int) -> Tuple[bool, int, int]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT clicks, energy FROM users WHERE user_id = ?", (user_id,))
    clicks, energy = cursor.fetchone()
    price = (energy // 100) * 100
    if clicks >= price:
        new_energy = energy + 100
        new_clicks = clicks - price
        cursor.execute("UPDATE users SET clicks = ?, energy = ? WHERE user_id = ?", (new_clicks, new_energy, user_id))
        conn.commit()
        conn.close()
        return (True, new_energy, price)
    conn.close()
    return (False, energy, price)

def upgrade_passive_income(user_id: int) -> Tuple[bool, int, int]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT clicks, passive_income FROM users WHERE user_id = ?", (user_id,))
    clicks, passive_income = cursor.fetchone()
    price = 500 + passive_income * 100
    if clicks >= price:
        new_passive = passive_income + 5
        new_clicks = clicks - price
        cursor.execute("UPDATE users SET clicks = ?, passive_income = ? WHERE user_id = ?", (new_clicks, new_passive, user_id))
        conn.commit()
        conn.close()
        return (True, new_passive, price)
    conn.close()
    return (False, passive_income, price)

def get_leaderboard(limit: int = 10) -> List[Tuple]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, total_clicks FROM users ORDER BY total_clicks DESC LIMIT ?", (limit,))
    result = cursor.fetchall()
    conn.close()
    return result

def add_clicks(user_id: int, amount: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET clicks = clicks + ?, total_clicks = total_clicks + ? WHERE user_id = ?", (amount, amount, user_id))
    conn.commit()
    conn.close()

def get_all_users() -> List[int]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()
    return [u[0] for u in users]

def reset_all_quests():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_quests")
    conn.commit()
    conn.close()

def get_top_donors(limit: int = 10) -> List[Tuple]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, total_clicks FROM users ORDER BY total_clicks DESC LIMIT ?", (limit,))
    result = cursor.fetchall()
    conn.close()
    return result