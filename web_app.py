import os
import sqlite3
import random
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

app = FastAPI()
templates = Jinja2Templates(directory="templates")

class ClickData(BaseModel):
    user_id: int
    clicks: int

DB_PATH = os.path.join(os.path.dirname(__file__), "zeta_clicker.db")

# ==================== ИНИЦИАЛИЗАЦИЯ БД ====================

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Основная таблица пользователей (расширенная)
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
            daily_streak INTEGER DEFAULT 0,
            gems INTEGER DEFAULT 0,
            total_gems INTEGER DEFAULT 0
        )
    """)
    
    # Таблица рефералов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            referrer_id INTEGER,
            referred_id INTEGER PRIMARY KEY,
            reward_claimed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица скинов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            emoji TEXT,
            price_clicks INTEGER,
            price_gems INTEGER DEFAULT 0,
            tap_bonus INTEGER DEFAULT 0,
            is_limited INTEGER DEFAULT 0
        )
    """)
    
    # Купленные скины
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_skins (
            user_id INTEGER,
            skin_id INTEGER,
            PRIMARY KEY (user_id, skin_id)
        )
    """)
    
    # Достижения
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            condition_type TEXT,
            condition_value INTEGER,
            reward_gems INTEGER,
            reward_clicks INTEGER,
            reward_skin_id INTEGER DEFAULT NULL
        )
    """)
    
    # Прогресс достижений
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_achievements (
            user_id INTEGER,
            achievement_id INTEGER,
            progress INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0,
            completed_at TIMESTAMP DEFAULT NULL,
            PRIMARY KEY (user_id, achievement_id)
        )
    """)
    
    # Кейсы
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            emoji TEXT,
            price_gems INTEGER,
            price_clicks INTEGER
        )
    """)
    
    # Награды из кейсов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS case_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER,
            reward_type TEXT,
            reward_value INTEGER,
            reward_text TEXT,
            chance INTEGER
        )
    """)
    
    # Бустеры
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS boosters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    
    # Активные бустеры
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_boosters (
            user_id INTEGER,
            booster_id INTEGER,
            expires_at TIMESTAMP,
            PRIMARY KEY (user_id, booster_id)
        )
    """)
    
    # Турниры
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tournaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            reward_gems INTEGER,
            reward_clicks INTEGER,
            reward_skin_id INTEGER DEFAULT NULL
        )
    """)
    
    # Участники турниров
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tournament_participants (
            user_id INTEGER,
            tournament_id INTEGER,
            score INTEGER DEFAULT 0,
            rank INTEGER DEFAULT NULL,
            reward_claimed INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, tournament_id)
        )
    """)
    
    conn.commit()
    
    # Добавляем скины
    cursor.execute("SELECT COUNT(*) FROM skins")
    if cursor.fetchone()[0] == 0:
        default_skins = [
            ('Обычная утка', '🦆', 0, 0, 0, 0),
            ('Золотая утка', '🌟', 5000, 0, 2, 0),
            ('Киберутка', '🤖', 15000, 0, 5, 0),
            ('Утка-призрак', '👻', 30000, 0, 10, 0),
            ('Дьявольская утка', '😈', 50000, 0, 15, 0),
            ('Алмазная утка', '💎', 0, 50, 20, 1),
        ]
        cursor.executemany(
            "INSERT INTO skins (name, emoji, price_clicks, price_gems, tap_bonus, is_limited) VALUES (?, ?, ?, ?, ?, ?)",
            default_skins
        )
    
    # Добавляем достижения
    cursor.execute("SELECT COUNT(*) FROM achievements")
    if cursor.fetchone()[0] == 0:
        achievements = [
            ("Новичок", "Накликать 100 кликов", "clicks", 100, 1, 500, None),
            ("Серебряный палец", "Накликать 1000 кликов", "clicks", 1000, 2, 2000, None),
            ("Золотой палец", "Накликать 10000 кликов", "clicks", 10000, 5, 10000, None),
            ("Легенда", "Накликать 100000 кликов", "clicks", 100000, 10, 50000, None),
            ("Коллекционер", "Купить 1 скин", "skins", 1, 1, 500, None),
            ("Магнат", "Купить 3 скина", "skins", 3, 3, 2000, None),
            ("Реферал", "Пригласить 1 друга", "referrals", 1, 1, 1000, None),
            ("Популярный", "Пригласить 5 друзей", "referrals", 5, 5, 5000, None),
            ("Мастер рефералов", "Пригласить 20 друзей", "referrals", 20, 20, 20000, None),
            ("Улучшатель", "Улучшить силу тапа до 10", "tap_power", 10, 2, 2000, None),
            ("Гуру", "Улучшить силу тапа до 50", "tap_power", 50, 5, 10000, None),
        ]
        cursor.executemany(
            "INSERT INTO achievements (name, description, condition_type, condition_value, reward_gems, reward_clicks, reward_skin_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            achievements
        )
    
    # Добавляем кейсы
    cursor.execute("SELECT COUNT(*) FROM cases")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO cases (name, emoji, price_gems, price_clicks) VALUES (?, ?, ?, ?)", ("Обычный кейс", "📦", 0, 1000))
        case_id = cursor.lastrowid
        rewards = [
            (case_id, "clicks", 100, "100 кликов", 30),
            (case_id, "clicks", 500, "500 кликов", 20),
            (case_id, "clicks", 1000, "1000 кликов", 15),
            (case_id, "clicks", 5000, "5000 кликов", 5),
            (case_id, "gems", 1, "1 алмаз 💎", 15),
            (case_id, "gems", 5, "5 алмазов 💎", 8),
            (case_id, "gems", 10, "10 алмазов 💎", 3),
            (case_id, "booster", 1, "x2 клика (30 мин)", 5),
            (case_id, "skin", 2, "Золотая утка 🌟", 2),
        ]
        cursor.executemany(
            "INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance) VALUES (?, ?, ?, ?, ?)",
            rewards
        )
        
        cursor.execute("INSERT INTO cases (name, emoji, price_gems, price_clicks) VALUES (?, ?, ?, ?)", ("Золотой кейс", "🎁", 10, 10000))
        case_id = cursor.lastrowid
        rewards = [
            (case_id, "clicks", 5000, "5000 кликов", 25),
            (case_id, "clicks", 10000, "10000 кликов", 20),
            (case_id, "clicks", 25000, "25000 кликов", 15),
            (case_id, "gems", 5, "5 алмазов 💎", 15),
            (case_id, "gems", 10, "10 алмазов 💎", 10),
            (case_id, "gems", 25, "25 алмазов 💎", 5),
            (case_id, "booster", 2, "x2 клика (1 час)", 5),
            (case_id, "skin", 3, "Киберутка 🤖", 3),
            (case_id, "skin", 4, "Утка-призрак 👻", 2),
        ]
        cursor.executemany(
            "INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance) VALUES (?, ?, ?, ?, ?)",
            rewards
        )
    
    # Добавляем бустеры
    cursor.execute("SELECT COUNT(*) FROM boosters")
    if cursor.fetchone()[0] == 0:
        boosters = [
            ("x2 Клики", "⚡", "Удваивает силу клика на 30 минут", "tap_multiplier", 2, 30, 5, 5000),
            ("Автокликер", "🤖", "Автоматически кликает 10 раз в секунду", "auto_click", 10, 30, 10, 10000),
            ("x2 Пассивка", "💰", "Удваивает пассивный доход на 1 час", "passive_multiplier", 2, 60, 3, 3000),
            ("Энергетик", "🔋", "Восстанавливает 500 энергии мгновенно", "energy", 500, 0, 2, 2000),
        ]
        cursor.executemany(
            "INSERT INTO boosters (name, emoji, description, effect_type, effect_value, duration_minutes, price_gems, price_clicks) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            boosters
        )
    
    conn.commit()
    conn.close()

init_db()

# ==================== ФУНКЦИИ ДЛЯ НОВЫХ ФИЧ ====================

def get_user_stats(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT clicks, level, energy, tap_power, passive_income, current_skin, total_clicks, daily_streak, gems FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            "clicks": int(result[0]),
            "level": int(result[1]),
            "energy": int(result[2]),
            "tap_power": int(result[3]),
            "passive_income": int(result[4]),
            "skin": str(result[5]) if result[5] else "🦆",
            "total_clicks": int(result[6]),
            "daily_streak": int(result[7]),
            "gems": int(result[8])
        }
    else:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (user_id, clicks, level, energy, tap_power, passive_income, current_skin, total_clicks, daily_streak, gems) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, 0, 1, 1000, 1, 0, "🦆", 0, 0, 0)
        )
        conn.commit()
        conn.close()
        return {"clicks": 0, "level": 1, "energy": 1000, "tap_power": 1, "passive_income": 0, "skin": "🦆", "total_clicks": 0, "daily_streak": 0, "gems": 0}

def update_clicks(user_id: int, increment: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT clicks, total_clicks, level, energy FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if result:
        new_clicks = result[0] + increment
        new_total = result[1] + increment
        new_energy = result[3] - 1 if result[3] > 0 else 0
        new_level = 1 + new_total // 100
        cursor.execute("UPDATE users SET clicks = ?, total_clicks = ?, level = ?, energy = ? WHERE user_id = ?", 
                       (new_clicks, new_total, new_level, new_energy, user_id))
        conn.commit()
        
        # Проверка достижений
        check_achievements(user_id, "clicks", new_total)
        check_achievements(user_id, "tap_power", result[2])
    conn.close()
    return True

def add_gems(user_id: int, amount: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT gems, total_gems FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if result:
        new_gems = result[0] + amount
        new_total = result[1] + amount
        cursor.execute("UPDATE users SET gems = ?, total_gems = ? WHERE user_id = ?", (new_gems, new_total, user_id))
        conn.commit()
    conn.close()

def check_achievements(user_id: int, condition_type: str, current_value: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, condition_type, condition_value, reward_gems, reward_clicks, reward_skin_id FROM achievements WHERE condition_type = ?", (condition_type,))
    achievements = cursor.fetchall()
    
    for ach in achievements:
        ach_id, ach_type, ach_value, reward_gems, reward_clicks, reward_skin = ach
        cursor.execute("SELECT completed FROM user_achievements WHERE user_id = ? AND achievement_id = ?", (user_id, ach_id))
        result = cursor.fetchone()
        if not result or result[0] == 0:
            if current_value >= ach_value:
                cursor.execute("INSERT OR REPLACE INTO user_achievements (user_id, achievement_id, progress, completed, completed_at) VALUES (?, ?, ?, ?, ?)",
                               (user_id, ach_id, ach_value, 1, datetime.now().isoformat()))
                if reward_gems > 0:
                    add_gems(user_id, reward_gems)
                if reward_clicks > 0:
                    cursor.execute("SELECT clicks FROM users WHERE user_id = ?", (user_id,))
                    clicks = cursor.fetchone()[0]
                    cursor.execute("UPDATE users SET clicks = ? WHERE user_id = ?", (clicks + reward_clicks, user_id))
                if reward_skin:
                    cursor.execute("INSERT OR IGNORE INTO user_skins (user_id, skin_id) VALUES (?, ?)", (user_id, reward_skin))
    conn.commit()
    conn.close()

def open_case(user_id: int, case_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, emoji, price_gems, price_clicks FROM cases WHERE id = ?", (case_id,))
    case_name, case_emoji, price_gems, price_clicks = cursor.fetchone()
    
    cursor.execute("SELECT clicks, gems FROM users WHERE user_id = ?", (user_id,))
    clicks, gems = cursor.fetchone()
    
    if price_clicks > 0 and clicks >= price_clicks:
        new_clicks = clicks - price_clicks
        cursor.execute("UPDATE users SET clicks = ? WHERE user_id = ?", (new_clicks, user_id))
    elif price_gems > 0 and gems >= price_gems:
        new_gems = gems - price_gems
        cursor.execute("UPDATE users SET gems = ? WHERE user_id = ?", (new_gems, user_id))
    else:
        conn.close()
        return {"success": False, "message": "Не хватает ресурсов"}
    
    # Выбор награды с учётом шансов
    cursor.execute("SELECT reward_type, reward_value, reward_text, chance FROM case_rewards WHERE case_id = ?", (case_id,))
    rewards = cursor.fetchall()
    
    total_chance = sum(r[3] for r in rewards)
    rand = random.randint(1, total_chance)
    cumulative = 0
    selected = None
    for reward in rewards:
        cumulative += reward[3]
        if rand <= cumulative:
            selected = reward
            break
    
    reward_type, reward_value, reward_text, chance = selected
    result = {"success": True, "reward_text": reward_text, "case_emoji": case_emoji}
    
    if reward_type == "clicks":
        cursor.execute("SELECT clicks FROM users WHERE user_id = ?", (user_id,))
        current_clicks = cursor.fetchone()[0]
        cursor.execute("UPDATE users SET clicks = ? WHERE user_id = ?", (current_clicks + reward_value, user_id))
        result["reward"] = f"{reward_value} кликов"
    elif reward_type == "gems":
        cursor.execute("SELECT gems FROM users WHERE user_id = ?", (user_id,))
        current_gems = cursor.fetchone()[0]
        cursor.execute("UPDATE users SET gems = ? WHERE user_id = ?", (current_gems + reward_value, user_id))
        result["reward"] = f"{reward_value} алмазов"
    elif reward_type == "booster":
        expires_at = datetime.now() + timedelta(minutes=30 if reward_value == 1 else 60)
        cursor.execute("INSERT OR REPLACE INTO user_boosters (user_id, booster_id, expires_at) VALUES (?, ?, ?)", 
                       (user_id, reward_value, expires_at.isoformat()))
        result["reward"] = reward_text
    elif reward_type == "skin":
        cursor.execute("INSERT OR IGNORE INTO user_skins (user_id, skin_id) VALUES (?, ?)", (user_id, reward_value))
        result["reward"] = reward_text
    
    conn.commit()
    conn.close()
    return result

def get_active_boosters(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
        SELECT b.id, b.name, b.emoji, b.description, b.effect_type, b.effect_value, b.duration_minutes, 
               (julianday(ub.expires_at) - julianday(?)) * 24 * 60 as minutes_left
        FROM user_boosters ub
        JOIN boosters b ON ub.booster_id = b.id
        WHERE ub.user_id = ? AND ub.expires_at > ?
    """, (now, user_id, now))
    result = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "emoji": r[2], "description": r[3], "effect_type": r[4], 
             "effect_value": r[5], "minutes_left": int(r[7])} for r in result]

def get_booster_multiplier(user_id: int):
    boosters = get_active_boosters(user_id)
    multiplier = 1.0
    for b in boosters:
        if b["effect_type"] == "tap_multiplier":
            multiplier *= b["effect_value"]
    return multiplier

def get_achievements(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, condition_value, reward_gems, reward_clicks FROM achievements")
    all_achievements = cursor.fetchall()
    
    result = []
    for ach in all_achievements:
        ach_id, name, desc, condition, reward_gems, reward_clicks = ach
        cursor.execute("SELECT completed, completed_at FROM user_achievements WHERE user_id = ? AND achievement_id = ?", (user_id, ach_id))
        progress_data = cursor.fetchone()
        completed = progress_data[0] if progress_data else 0
        completed_at = progress_data[1] if progress_data else None
        result.append({
            "id": ach_id,
            "name": name,
            "description": desc,
            "condition": condition,
            "reward_gems": reward_gems,
            "reward_clicks": reward_clicks,
            "completed": completed,
            "completed_at": completed_at
        })
    conn.close()
    return result

def get_tournaments(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    
    # Активные турниры
    cursor.execute("SELECT id, name, description, end_date, reward_gems, reward_clicks FROM tournaments WHERE start_date <= ? AND end_date >= ?", (now, now))
    active = cursor.fetchall()
    
    # Текущий рейтинг
    tournaments_data = []
    for t in active:
        t_id, name, desc, end_date, reward_gems, reward_clicks = t
        cursor.execute("SELECT user_id, score FROM tournament_participants WHERE tournament_id = ? ORDER BY score DESC LIMIT 10", (t_id,))
        leaders = cursor.fetchall()
        cursor.execute("SELECT score FROM tournament_participants WHERE tournament_id = ? AND user_id = ?", (t_id, user_id))
        my_score = cursor.fetchone()
        tournaments_data.append({
            "id": t_id,
            "name": name,
            "description": desc,
            "end_date": end_date,
            "reward_gems": reward_gems,
            "reward_clicks": reward_clicks,
            "leaders": [{"user_id": l[0], "score": l[1]} for l in leaders],
            "my_score": my_score[0] if my_score else 0
        })
    conn.close()
    return tournaments_data
# ==================== API ЭНДПОИНТЫ ====================

@app.post("/api/upgrade_tap")
async def upgrade_tap(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT clicks, tap_power FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        return {"success": False, "message": "Пользователь не найден"}
    
    clicks, tap_power = result
    price = tap_power * 100
    
    if clicks >= price:
        new_tap_power = tap_power + 1
        new_clicks = clicks - price
        cursor.execute("UPDATE users SET clicks = ?, tap_power = ? WHERE user_id = ?", (new_clicks, new_tap_power, user_id))
        conn.commit()
        conn.close()
        check_achievements(user_id, "tap_power", new_tap_power)
        return {"success": True, "new_tap_power": new_tap_power, "new_clicks": new_clicks}
    else:
        conn.close()
        return {"success": False, "need": price, "clicks": clicks}

@app.post("/api/upgrade_passive")
async def upgrade_passive(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT clicks, passive_income FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        return {"success": False, "message": "Пользователь не найден"}
    
    clicks, passive_income = result
    price = 500 + passive_income * 100
    
    if clicks >= price:
        new_passive = passive_income + 5
        new_clicks = clicks - price
        cursor.execute("UPDATE users SET clicks = ?, passive_income = ? WHERE user_id = ?", (new_clicks, new_passive, user_id))
        conn.commit()
        conn.close()
        return {"success": True, "new_passive": new_passive, "new_clicks": new_clicks}
    else:
        conn.close()
        return {"success": False, "need": price, "clicks": clicks}

@app.post("/api/collect_passive")
async def collect_passive(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT clicks, passive_income FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        return {"success": False, "message": "Пользователь не найден"}
    
    clicks, passive_income = result
    if passive_income > 0:
        earned = passive_income
        new_clicks = clicks + earned
        cursor.execute("UPDATE users SET clicks = ? WHERE user_id = ?", (new_clicks, user_id))
        conn.commit()
        conn.close()
        return {"success": True, "earned": earned, "new_clicks": new_clicks}
    else:
        conn.close()
        return {"success": False, "message": "Пассивный доход не накоплен"}

@app.post("/api/claim_daily")
async def claim_daily(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT last_daily, daily_streak, clicks, gems FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        return {"success": False, "message": "Пользователь не найден"}
    
    last_daily, daily_streak, clicks, gems = result
    today = datetime.now().date()
    last_date = datetime.fromisoformat(last_daily).date() if last_daily else None
    
    if last_date == today:
        conn.close()
        return {"success": False, "message": "Уже забирал сегодня"}
    
    if last_date == today - timedelta(days=1):
        daily_streak += 1
    else:
        daily_streak = 1
    
    bonus = min(100 + daily_streak * 50, 600)
    new_clicks = clicks + bonus
    
    # Бонусные алмазы за серию
    gem_bonus = 0
    if daily_streak == 7:
        gem_bonus = 5
        new_gems = gems + gem_bonus
    else:
        new_gems = gems
    
    cursor.execute("UPDATE users SET clicks = ?, last_daily = ?, daily_streak = ?, gems = ? WHERE user_id = ?", 
                   (new_clicks, today.isoformat(), daily_streak, new_gems, user_id))
    conn.commit()
    conn.close()
    
    return {"success": True, "bonus": bonus, "gem_bonus": gem_bonus, "streak": daily_streak, "new_clicks": new_clicks}

@app.post("/api/buy_skin")
async def buy_skin(user_id: int, skin_id: int, payment: str = "clicks"):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, emoji, price_clicks, price_gems, tap_bonus FROM skins WHERE id = ?", (skin_id,))
    skin = cursor.fetchone()
    if not skin:
        conn.close()
        return {"success": False, "message": "Скин не найден"}
    
    skin_name, skin_emoji, price_clicks, price_gems, tap_bonus = skin
    
    if payment == "clicks" and price_clicks > 0:
        cursor.execute("SELECT clicks FROM users WHERE user_id = ?", (user_id,))
        clicks = cursor.fetchone()[0]
        if clicks >= price_clicks:
            new_clicks = clicks - price_clicks
            cursor.execute("UPDATE users SET clicks = ? WHERE user_id = ?", (new_clicks, user_id))
        else:
            conn.close()
            return {"success": False, "need": price_clicks, "type": "clicks"}
    elif payment == "gems" and price_gems > 0:
        cursor.execute("SELECT gems FROM users WHERE user_id = ?", (user_id,))
        gems = cursor.fetchone()[0]
        if gems >= price_gems:
            new_gems = gems - price_gems
            cursor.execute("UPDATE users SET gems = ? WHERE user_id = ?", (new_gems, user_id))
        else:
            conn.close()
            return {"success": False, "need": price_gems, "type": "gems"}
    else:
        conn.close()
        return {"success": False, "message": "Способ оплаты недоступен"}
    
    cursor.execute("INSERT OR IGNORE INTO user_skins (user_id, skin_id) VALUES (?, ?)", (user_id, skin_id))
    conn.commit()
    
    # Проверка достижения за покупку скинов
    cursor.execute("SELECT COUNT(*) FROM user_skins WHERE user_id = ?", (user_id,))
    skins_count = cursor.fetchone()[0]
    conn.close()
    check_achievements(user_id, "skins", skins_count)
    
    return {"success": True, "skin_name": skin_name, "skin_emoji": skin_emoji}

@app.post("/api/equip_skin")
async def equip_skin(user_id: int, skin_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM user_skins WHERE user_id = ? AND skin_id = ?", (user_id, skin_id))
    if not cursor.fetchone():
        conn.close()
        return {"success": False, "message": "Скин не куплен"}
    
    cursor.execute("SELECT emoji FROM skins WHERE id = ?", (skin_id,))
    emoji = cursor.fetchone()[0]
    cursor.execute("UPDATE users SET current_skin = ? WHERE user_id = ?", (emoji, user_id))
    conn.commit()
    conn.close()
    
    return {"success": True, "skin": emoji}

@app.get("/api/get_skins")
async def get_skins(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT skin_id FROM user_skins WHERE user_id = ?", (user_id,))
    owned = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT current_skin FROM users WHERE user_id = ?", (user_id,))
    current = cursor.fetchone()[0]
    cursor.execute("SELECT id, name, emoji, price_clicks, price_gems, tap_bonus, is_limited FROM skins")
    all_skins = cursor.fetchall()
    conn.close()
    
    result = []
    for skin in all_skins:
        result.append({
            "id": skin[0],
            "name": skin[1],
            "emoji": skin[2],
            "price_clicks": skin[3],
            "price_gems": skin[4],
            "bonus": skin[5],
            "limited": skin[6],
            "owned": skin[0] in owned,
            "equipped": skin[2] == current
        })
    
    return {"skins": result, "current_skin": current}

@app.get("/api/get_referrals")
async def get_referrals(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))
    count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND reward_claimed = 0", (user_id,))
    unclaimed = cursor.fetchone()[0]
    conn.close()
    
    check_achievements(user_id, "referrals", count)
    
    return {"count": count, "unclaimed": unclaimed}

@app.post("/api/claim_referral")
async def claim_referral(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND reward_claimed = 0", (user_id,))
    count = cursor.fetchone()[0]
    
    if count == 0:
        conn.close()
        return {"success": False, "message": "Нет неполученных наград"}
    
    reward = count * 1000
    cursor.execute("SELECT clicks FROM users WHERE user_id = ?", (user_id,))
    clicks = cursor.fetchone()[0]
    cursor.execute("UPDATE users SET clicks = ? WHERE user_id = ?", (clicks + reward, user_id))
    cursor.execute("UPDATE referrals SET reward_claimed = 1 WHERE referrer_id = ? AND reward_claimed = 0", (user_id,))
    conn.commit()
    conn.close()
    
    return {"success": True, "reward": reward}

@app.post("/api/open_case")
async def open_case_api(user_id: int, case_id: int = 1):
    result = open_case(user_id, case_id)
    return result

@app.get("/api/get_cases")
async def get_cases(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, emoji, price_gems, price_clicks FROM cases")
    cases = cursor.fetchall()
    conn.close()
    return {"cases": [{"id": c[0], "name": c[1], "emoji": c[2], "price_gems": c[3], "price_clicks": c[4]} for c in cases]}

@app.get("/api/get_boosters")
async def get_boosters_list(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, emoji, description, price_gems, price_clicks FROM boosters WHERE price_gems > 0 OR price_clicks > 0")
    shop_boosters = cursor.fetchall()
    
    active = get_active_boosters(user_id)
    conn.close()
    
    return {"shop_boosters": [{"id": b[0], "name": b[1], "emoji": b[2], "description": b[3], "price_gems": b[4], "price_clicks": b[5]} for b in shop_boosters],
            "active_boosters": active}
@app.get("/", response_class=HTMLResponse)
async def mini_app(user_id: int = 1):
    stats = get_user_stats(user_id)
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>Zeta Clicker</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; user-select: none; -webkit-tap-highlight-color: transparent; }}
        body {{ min-height: 100vh; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; padding: 20px; display: flex; justify-content: center; align-items: center; }}
        .container {{ max-width: 500px; width: 100%; background: rgba(255,255,255,0.05); border-radius: 32px; backdrop-filter: blur(10px); padding: 20px; }}
        
        .screen {{ display: none; }}
        .screen.active {{ display: block; }}
        
        .stats {{ background: rgba(0,0,0,0.3); border-radius: 24px; padding: 16px; margin-bottom: 24px; }}
        .stat-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.1); }}
        .stat-row:last-child {{ border-bottom: none; }}
        .stat-label {{ color: #aaa; font-size: 14px; }}
        .stat-value {{ color: #ffd700; font-size: 20px; font-weight: bold; }}
        
        .duck-container {{ display: flex; justify-content: center; margin: 20px 0; }}
        .duck {{ font-size: 180px; cursor: pointer; transition: transform 0.1s; filter: drop-shadow(0 10px 20px rgba(0,0,0,0.3)); }}
        .duck:active {{ transform: scale(0.94); }}
        
        .button-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 24px 0; }}
        .action-btn {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none; border-radius: 16px; padding: 14px 8px; color: white; font-size: 14px; font-weight: 600; cursor: pointer; text-align: center; }}
        .action-btn:active {{ transform: scale(0.96); opacity: 0.9; }}
        .back-btn {{ background: rgba(255,255,255,0.1); margin-top: 20px; }}
        .full-width {{ width: 100%; }}
        
        .skin-list, .booster-list, .achievement-list, .case-list {{ margin: 20px 0; }}
        .skin-item, .booster-item, .achievement-item {{ background: rgba(0,0,0,0.3); border-radius: 16px; padding: 12px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }}
        .skin-info, .booster-info, .achievement-info {{ display: flex; align-items: center; gap: 12px; flex: 1; }}
        .skin-emoji, .booster-emoji, .achievement-emoji {{ font-size: 40px; }}
        .skin-name, .booster-name, .achievement-name {{ font-size: 16px; font-weight: bold; }}
        .skin-price, .booster-price, .achievement-desc {{ font-size: 12px; color: #ffd700; }}
        .skin-btn, .booster-btn {{ background: #667eea; border: none; border-radius: 12px; padding: 8px 16px; color: white; cursor: pointer; }}
        .skin-btn.owned {{ background: #4caf50; }}
        .skin-btn.equipped {{ background: #ff9800; }}
        .achievement-completed {{ background: #4caf50; color: white; border-radius: 12px; padding: 4px 8px; font-size: 12px; }}
        
        .case-container {{ text-align: center; margin: 20px 0; }}
        .case-box {{ background: linear-gradient(135deg, #ffd700, #ff8c00); border-radius: 20px; padding: 30px; cursor: pointer; margin-bottom: 20px; transition: transform 0.1s; }}
        .case-box:active {{ transform: scale(0.98); }}
        .case-emoji {{ font-size: 80px; }}
        .case-price {{ color: white; margin-top: 10px; font-weight: bold; }}
        
        .tournament-card {{ background: rgba(0,0,0,0.3); border-radius: 16px; padding: 15px; margin-bottom: 15px; }}
        .tournament-name {{ font-size: 18px; font-weight: bold; color: #ffd700; margin-bottom: 10px; }}
        .tournament-desc {{ font-size: 12px; color: #aaa; margin-bottom: 10px; }}
        .leader-list {{ margin-top: 10px; padding-left: 15px; }}
        .leader-item {{ display: flex; justify-content: space-between; font-size: 12px; margin: 5px 0; }}
        
        .tap-value {{ position: fixed; pointer-events: none; font-size: 28px; font-weight: bold; color: #ffd700; animation: floatUp 0.6s ease-out forwards; z-index: 1000; }}
        @keyframes floatUp {{ 0% {{ opacity: 1; transform: translateY(0) scale(0.8); }} 100% {{ opacity: 0; transform: translateY(-80px) scale(1.2); }} }}
        
        .energy-bar {{ width: 100%; height: 12px; background: rgba(255,255,255,0.2); border-radius: 6px; margin: 10px 0; overflow: hidden; }}
        .energy-fill {{ height: 100%; background: linear-gradient(90deg, #00ff88, #00cc66); border-radius: 6px; transition: width 0.2s; }}
        .gems-badge {{ background: rgba(0,0,0,0.5); border-radius: 20px; padding: 5px 12px; display: inline-flex; align-items: center; gap: 5px; margin-left: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <!-- ЭКРАН 1: ГЛАВНЫЙ -->
        <div id="mainScreen" class="screen active">
            <div class="stats">
                <div class="stat-row"><span class="stat-label">🦆 Уровень</span><span class="stat-value" id="levelValue">{stats["level"]}</span></div>
                <div class="stat-row"><span class="stat-label">💰 Клики</span><span class="stat-value" id="clicksValue">{stats["clicks"]}</span></div>
                <div class="stat-row"><span class="stat-label">💪 Сила клика</span><span class="stat-value" id="tapPowerValue">+{stats["tap_power"]}</span></div>
                <div class="stat-row"><span class="stat-label">⏱️ Пассивный доход</span><span class="stat-value" id="passiveValue">{stats["passive_income"]}/час</span></div>
                <div class="stat-row"><span class="stat-label">💎 Алмазы</span><span class="stat-value" id="gemsValue">{stats["gems"]}</span></div>
            </div>
            <div class="energy-bar"><div class="energy-fill" id="energyFill" style="width: {stats["energy"]/10}%"></div></div>
            <div class="duck-container"><div class="duck" id="duck">{stats["skin"]}</div></div>
            <div class="button-grid">
                <button class="action-btn" id="upgradeTapBtn">💪 Улучшить тап</button>
                <button class="action-btn" id="upgradePassiveBtn">💰 Улучшить пассивку</button>
                <button class="action-btn" id="collectPassiveBtn">💵 Собрать пассивку</button>
                <button class="action-btn" id="dailyBtn">🎁 Ежедневный</button>
                <button class="action-btn" id="openShopBtn">👕 Магазин</button>
                <button class="action-btn" id="openCasesBtn">📦 Кейсы</button>
                <button class="action-btn" id="openBoostersBtn">⚡ Бустеры</button>
                <button class="action-btn" id="openAchievementsBtn">🏆 Достижения</button>
                <button class="action-btn" id="openTournamentsBtn">🎯 Турниры</button>
                <button class="action-btn" id="openReferralBtn">👥 Рефералы</button>
                <button class="action-btn" id="profileBtn">📊 Профиль</button>
            </div>
            <button class="action-btn full-width" id="closeBtn">✖️ Закрыть</button>
        </div>
        
        <!-- ЭКРАН 2: ПРОФИЛЬ -->
        <div id="profileScreen" class="screen">
            <h3 style="color: white; text-align: center; margin-bottom: 20px;">📊 ПРОФИЛЬ</h3>
            <div class="stats">
                <div class="stat-row"><span class="stat-label">🦆 Уровень</span><span class="stat-value" id="profileLevel">{stats["level"]}</span></div>
                <div class="stat-row"><span class="stat-label">💰 Всего кликов</span><span class="stat-value" id="profileTotalClicks">{stats["total_clicks"]}</span></div>
                <div class="stat-row"><span class="stat-label">💪 Сила клика</span><span class="stat-value" id="profileTapPower">+{stats["tap_power"]}</span></div>
                <div class="stat-row"><span class="stat-label">⏱️ Пассивный доход</span><span class="stat-value" id="profilePassive">{stats["passive_income"]}/час</span></div>
                <div class="stat-row"><span class="stat-label">💎 Всего алмазов</span><span class="stat-value" id="profileTotalGems">{stats["gems"]}</span></div>
                <div class="stat-row"><span class="stat-label">📅 Серия входов</span><span class="stat-value" id="profileStreak">{stats["daily_streak"]}</span></div>
                <div class="stat-row"><span class="stat-label">🎨 Скин</span><span class="stat-value" id="profileSkin">{stats["skin"]}</span></div>
            </div>
            <button class="action-btn full-width back-btn" onclick="showScreen('main')">◀️ Назад</button>
        </div>
        
        <!-- ЭКРАН 3: МАГАЗИН СКИНОВ -->
        <div id="shopScreen" class="screen">
            <h3 style="color: white; text-align: center; margin-bottom: 20px;">👕 МАГАЗИН СКИНОВ</h3>
            <div id="skinsList" class="skin-list">Загрузка...</div>
            <button class="action-btn full-width back-btn" onclick="showScreen('main')">◀️ Назад</button>
        </div>
        
        <!-- ЭКРАН 4: КЕЙСЫ -->
        <div id="casesScreen" class="screen">
            <h3 style="color: white; text-align: center; margin-bottom: 20px;">📦 КЕЙСЫ</h3>
            <div id="casesList" class="case-list">Загрузка...</div>
            <button class="action-btn full-width back-btn" onclick="showScreen('main')">◀️ Назад</button>
        </div>
        
        <!-- ЭКРАН 5: БУСТЕРЫ -->
        <div id="boostersScreen" class="screen">
            <h3 style="color: white; text-align: center; margin-bottom: 20px;">⚡ БУСТЕРЫ</h3>
            <div id="activeBoostersList" class="booster-list">Активные бустеры: загрузка...</div>
            <div id="shopBoostersList" class="booster-list">Доступные бустеры: загрузка...</div>
            <button class="action-btn full-width back-btn" onclick="showScreen('main')">◀️ Назад</button>
        </div>
        
        <!-- ЭКРАН 6: ДОСТИЖЕНИЯ -->
        <div id="achievementsScreen" class="screen">
            <h3 style="color: white; text-align: center; margin-bottom: 20px;">🏆 ДОСТИЖЕНИЯ</h3>
            <div id="achievementsList" class="achievement-list">Загрузка...</div>
            <button class="action-btn full-width back-btn" onclick="showScreen('main')">◀️ Назад</button>
        </div>
        
        <!-- ЭКРАН 7: ТУРНИРЫ -->
        <div id="tournamentsScreen" class="screen">
            <h3 style="color: white; text-align: center; margin-bottom: 20px;">🎯 ТУРНИРЫ</h3>
            <div id="tournamentsList">Загрузка...</div>
            <button class="action-btn full-width back-btn" onclick="showScreen('main')">◀️ Назад</button>
        </div>
        
        <!-- ЭКРАН 8: РЕФЕРАЛЫ -->
        <div id="referralScreen" class="screen">
            <h3 style="color: white; text-align: center; margin-bottom: 20px;">👥 РЕФЕРАЛЫ</h3>
            <div class="stats" style="margin-bottom: 20px;">
                <div class="stat-row"><span class="stat-label">👥 Приглашено друзей</span><span class="stat-value" id="referralCount">0</span></div>
                <div class="stat-row"><span class="stat-label">🎁 Не получено наград</span><span class="stat-value" id="unclaimedRewards">0</span></div>
            </div>
            <div id="referralLinkBox" style="background: rgba(0,0,0,0.3); border-radius: 16px; padding: 12px; margin-bottom: 20px;">
                <div style="color: #aaa; font-size: 12px; margin-bottom: 8px;">🔗 Твоя реферальная ссылка:</div>
                <div id="referralLink" style="color: #ffd700; font-size: 12px; word-break: break-all; font-family: monospace;"></div>
                <button class="action-btn full-width" id="copyReferralBtn" style="margin-top: 10px; background: #4caf50;">📋 Копировать ссылку</button>
            </div>
            <button class="action-btn full-width" id="claimReferralBtn" style="margin-bottom: 10px;">🎁 Забрать награду</button>
            <button class="action-btn full-width back-btn" onclick="showScreen('main')">◀️ Назад</button>
        </div>
    </div>
            <script>
        const tg = window.Telegram.WebApp;
        tg.ready();
        tg.expand();
        
        const userId = new URLSearchParams(window.location.search).get('user_id') || 1;
        let clicks = {stats["clicks"]};
        let level = {stats["level"]};
        let tapPower = {stats["tap_power"]};
        let passiveIncome = {stats["passive_income"]};
        let currentSkin = "{stats["skin"]}";
        let gems = {stats["gems"]};
        let energy = {stats["energy"]};
        let maxEnergy = 1000;
        
        function showScreen(screenName) {{
            const screens = ['mainScreen', 'profileScreen', 'shopScreen', 'casesScreen', 'boostersScreen', 'achievementsScreen', 'tournamentsScreen', 'referralScreen'];
            screens.forEach(s => document.getElementById(s).classList.remove('active'));
            document.getElementById(screenName).classList.add('active');
            
            if (screenName === 'shopScreen') loadSkins();
            if (screenName === 'casesScreen') loadCases();
            if (screenName === 'boostersScreen') loadBoosters();
            if (screenName === 'achievementsScreen') loadAchievements();
            if (screenName === 'tournamentsScreen') loadTournaments();
            if (screenName === 'referralScreen') loadReferralData();
        }}
        
        function updateUI() {{
            document.getElementById('clicksValue').textContent = clicks;
            document.getElementById('levelValue').textContent = level;
            document.getElementById('tapPowerValue').textContent = '+' + tapPower;
            document.getElementById('passiveValue').textContent = passiveIncome + '/час';
            document.getElementById('gemsValue').textContent = gems;
            document.getElementById('energyFill').style.width = (energy / 10) + '%';
            
            if (document.getElementById('profileLevel')) {{
                document.getElementById('profileLevel').textContent = level;
                document.getElementById('profileTapPower').textContent = '+' + tapPower;
                document.getElementById('profilePassive').textContent = passiveIncome + '/час';
                document.getElementById('profileSkin').textContent = currentSkin;
            }}
        }}
        
        async function loadStats() {{
            try {{
                const res = await fetch('/api/get_stats?user_id=' + userId);
                const data = await res.json();
                clicks = data.clicks;
                level = data.level;
                tapPower = data.tap_power;
                passiveIncome = data.passive_income;
                currentSkin = data.skin;
                gems = data.gems;
                energy = data.energy;
                updateUI();
                document.getElementById('duck').textContent = currentSkin;
                if (document.getElementById('profileTotalClicks')) document.getElementById('profileTotalClicks').textContent = data.total_clicks;
                if (document.getElementById('profileStreak')) document.getElementById('profileStreak').textContent = data.daily_streak;
                if (document.getElementById('profileTotalGems')) document.getElementById('profileTotalGems').textContent = data.gems;
            }} catch(e) {{ console.error(e); }}
        }}
        
        async function loadSkins() {{
    try {{
        const res = await fetch('/api/get_skins?user_id=' + userId);
        const data = await res.json();
        const skinsList = document.getElementById('skinsList');
        skinsList.innerHTML = '';
        
        for (const skin of data.skins) {{
            const div = document.createElement('div');
            div.className = 'skin-item';
            let paymentOptions = '';
            if (skin.price_clicks > 0) paymentOptions += '<button class="skin-btn" onclick="buySkin(' + skin.id + ', \'clicks\')">💎 ' + skin.price_clicks + ' кликов</button>';
            if (skin.price_gems > 0) paymentOptions += '<button class="skin-btn" onclick="buySkin(' + skin.id + ', \'gems\')">💎 ' + skin.price_gems + ' алмазов</button>';
            
            if (skin.owned && skin.equipped) {{
                paymentOptions = '<span class="skin-btn equipped">✅ ЭКИПИРОВАН</span>';
            }} else if (skin.owned) {{
                paymentOptions = '<button class="skin-btn owned" onclick="equipSkin(' + skin.id + ')">⚡ ЭКИПИРОВАТЬ</button>';
            }}
            
            let limitedText = skin.limited ? '🌟 Лимитированный' : 'Обычный';
            
            div.innerHTML = `
                <div class="skin-info">
                    <span class="skin-emoji">${skin.emoji}</span>
                    <div>
                        <div class="skin-name">${skin.name}</div>
                        <div class="skin-price">+${skin.bonus} к силе | ${limitedText}</div>
                    </div>
                </div>
                <div>${paymentOptions}</div>
            `;
            skinsList.appendChild(div);
        }}
    }} catch(e) {{ console.error(e); }}
}}
        
        async function buySkin(skinId, payment) {{
            const res = await fetch('/api/buy_skin?user_id=' + userId + '&skin_id=' + skinId + '&payment=' + payment, {{method: 'POST'}});
            const data = await res.json();
            if (data.success) {{
                tg.showPopup({{title: '✅ Покупка успешна!', message: 'Вы купили ' + data.skin_name + ' ' + data.skin_emoji, buttons: [{{type: 'ok'}}]}});
                await loadStats();
                await loadSkins();
            }} else {{
                let currency = data.type === 'clicks' ? 'кликов' : 'алмазов';
                tg.showPopup({{title: '❌ Не хватает ресурсов', message: 'Нужно: ' + data.need + ' ' + currency, buttons: [{{type: 'ok'}}]}});
            }}
        }}
        
        async function equipSkin(skinId) {{
            const res = await fetch('/api/equip_skin?user_id=' + userId + '&skin_id=' + skinId, {{method: 'POST'}});
            const data = await res.json();
            if (data.success) {{
                tg.showPopup({{title: '✅ Скин экипирован!', message: 'Теперь ваша утка: ' + data.skin, buttons: [{{type: 'ok'}}]}});
                await loadStats();
                await loadSkins();
            }} else {{
                tg.showPopup({{title: '❌ Ошибка', message: data.message, buttons: [{{type: 'ok'}}]}});
            }}
        }}
        
        async function loadCases() {{
            try {{
                const res = await fetch('/api/get_cases?user_id=' + userId);
                const data = await res.json();
                const casesList = document.getElementById('casesList');
                casesList.innerHTML = '';
                
                for (const caseItem of data.cases) {{
                    let priceText = '';
                    if (caseItem.price_clicks > 0) {{
                        priceText = caseItem.price_clicks + ' кликов';
                    }} else {{
                        priceText = caseItem.price_gems + ' алмазов';
                    }}
                    
                    const div = document.createElement('div');
                    div.className = 'case-container';
                    div.innerHTML = `
                        <div class="case-box" onclick="openCase(${caseItem.id})">
                            <div class="case-emoji">${caseItem.emoji}</div>
                            <div class="case-price">${caseItem.name}<br>${priceText}</div>
                        </div>
                    `;
                    casesList.appendChild(div);
                }}
            }} catch(e) {{ console.error(e); }}
        }}
        
        async function openCase(caseId) {{
            const res = await fetch('/api/open_case?user_id=' + userId + '&case_id=' + caseId, {{method: 'POST'}});
            const data = await res.json();
            if (data.success) {{
                tg.showPopup({{title: '🎁 Открытие кейса!', message: data.case_emoji + ' Вы получили: ' + data.reward_text, buttons: [{{type: 'ok'}}]}});
                await loadStats();
            }} else {{
                tg.showPopup({{title: '❌ Ошибка', message: data.message, buttons: [{{type: 'ok'}}]}});
            }}
        }}
        
        async function loadBoosters() {{
            try {{
                const res = await fetch('/api/get_boosters?user_id=' + userId);
                const data = await res.json();
                
                const activeDiv = document.getElementById('activeBoostersList');
                if (data.active_boosters.length > 0) {{
                    activeDiv.innerHTML = '<h4 style="color: #ffd700; margin-bottom: 10px;">⚡ АКТИВНЫЕ БУСТЕРЫ:</h4>';
                    for (const b of data.active_boosters) {{
                        activeDiv.innerHTML += `
                            <div class="booster-item">
                                <div class="booster-info">
                                    <span class="booster-emoji">${b.emoji}</span>
                                    <div>
                                        <div class="booster-name">${b.name}</div>
                                        <div class="booster-price">${b.description} | Осталось: ${b.minutes_left} мин</div>
                                    </div>
                                </div>
                            </div>
                        `;
                    }}
                }} else {{
                    activeDiv.innerHTML = '<div style="text-align: center; padding: 20px; color: #aaa;">Нет активных бустеров</div>';
                }}
                
                const shopDiv = document.getElementById('shopBoostersList');
                shopDiv.innerHTML = '<h4 style="color: #ffd700; margin-bottom: 10px;">💎 ДОСТУПНЫЕ БУСТЕРЫ:</h4>';
                for (const b of data.shop_boosters) {{
                    let priceText = '';
                    if (b.price_clicks > 0) priceText = b.price_clicks + ' кликов';
                    if (b.price_gems > 0) priceText = b.price_gems + ' алмазов';
                    shopDiv.innerHTML += `
                        <div class="booster-item">
                            <div class="booster-info">
                                <span class="booster-emoji">${b.emoji}</span>
                                <div>
                                    <div class="booster-name">${b.name}</div>
                                    <div class="booster-price">${b.description} | Цена: ${priceText}</div>
                                </div>
                            </div>
                            <button class="booster-btn" onclick="buyBooster(${b.id})">💎 КУПИТЬ</button>
                        </div>
                    `;
                }}
            }} catch(e) {{ console.error(e); }}
        }}
        
        async function buyBooster(boosterId) {{
            const payment = confirm('Оплатить кликами? (Отмена — алмазами)') ? 'clicks' : 'gems';
            const res = await fetch('/api/buy_booster?user_id=' + userId + '&booster_id=' + boosterId + '&payment=' + payment, {{method: 'POST'}});
            const data = await res.json();
            if (data.success) {{
                tg.showPopup({{title: '✅ Бустер активирован!', message: data.booster_emoji + ' ' + data.booster_name + ' активирован!', buttons: [{{type: 'ok'}}]}});
                await loadStats();
                await loadBoosters();
            }} else {{
                let currency = data.type === 'clicks' ? 'кликов' : 'алмазов';
                tg.showPopup({{title: '❌ Не хватает ресурсов', message: 'Нужно: ' + data.need + ' ' + currency, buttons: [{{type: 'ok'}}]}});
            }}
        }}
        
        async function loadAchievements() {{
    try {{
        const res = await fetch('/api/get_achievements?user_id=' + userId);
        const data = await res.json();
        const achievementsList = document.getElementById('achievementsList');
        achievementsList.innerHTML = '';
        
        for (const ach of data.achievements) {{
            const div = document.createElement('div');
            div.className = 'achievement-item';
            
            let emoji = ach.completed ? '🏆' : '🔒';
            let statusText = ach.completed ? '<span class="achievement-completed">✅ ВЫПОЛНЕНО</span>' : '<span class="achievement-desc">📋 Не выполнено</span>';
            
            div.innerHTML = `
                <div class="achievement-info">
                    <span class="achievement-emoji">${emoji}</span>
                    <div>
                        <div class="achievement-name">${ach.name}</div>
                        <div class="achievement-desc">${ach.description} (${ach.condition})</div>
                        <div class="achievement-desc">🎁 Награда: +${ach.reward_gems}💎 +${ach.reward_clicks}💰</div>
                    </div>
                </div>
                ${statusText}
            `;
            achievementsList.appendChild(div);
        }}
    }} catch(e) {{ console.error(e); }}
}}
        
        async function loadTournaments() {{
            try {{
                const res = await fetch('/api/get_tournaments?user_id=' + userId);
                const data = await res.json();
                const tournamentsList = document.getElementById('tournamentsList');
                tournamentsList.innerHTML = '';
                
                if (data.tournaments.length === 0) {{
                    tournamentsList.innerHTML = '<div style="text-align: center; padding: 20px; color: #aaa;">Активных турниров нет</div>';
                }} else {{
                    for (const t of data.tournaments) {{
                        let leadersHtml = '<div class="leader-list"><strong>🏆 Топ-10:</strong>';
                        for (let i = 0; i < Math.min(t.leaders.length, 10); i++) {{
                            leadersHtml += '<div class="leader-item"><span>' + (i+1) + '. Пользователь ' + t.leaders[i].user_id + '</span><span>' + t.leaders[i].score + ' кликов</span></div>';
                        }}
                        leadersHtml += '</div>';
                        
                        const div = document.createElement('div');
                        div.className = 'tournament-card';
                        div.innerHTML = `
                            <div class="tournament-name">🎯 ${t.name}</div>
                            <div class="tournament-desc">${t.description}</div>
                            <div class="tournament-desc">📅 До: ${new Date(t.end_date).toLocaleString()}</div>
                            <div class="tournament-desc">🎁 Награда: +${t.reward_gems}💎 +${t.reward_clicks}💰</div>
                            <div class="tournament-desc">📊 Твой счёт: ${t.my_score} кликов</div>
                            ${leadersHtml}
                        `;
                        tournamentsList.appendChild(div);
                    }}
                }}
            }} catch(e) {{ console.error(e); }}
        }}
        
        async function loadReferralData() {{
            try {{
                const res = await fetch('/api/get_referrals?user_id=' + userId);
                const data = await res.json();
                document.getElementById('referralCount').textContent = data.count;
                document.getElementById('unclaimedRewards').textContent = data.unclaimed;
                
                const botUsername = tg.initDataUnsafe?.user?.username || 'ZetaClickerRobot';
                const referralLink = 'https://t.me/' + botUsername + '?start=ref_' + userId;
                document.getElementById('referralLink').textContent = referralLink;
                
                document.getElementById('copyReferralBtn').onclick = () => {{
                    navigator.clipboard.writeText(referralLink);
                    tg.showPopup({{title: '✅ Скопировано!', message: 'Реферальная ссылка скопирована', buttons: [{{type: 'ok'}}]}});
                }};
                
                document.getElementById('claimReferralBtn').onclick = async () => {{
                    const claimRes = await fetch('/api/claim_referral?user_id=' + userId, {{method: 'POST'}});
                    const claimData = await claimRes.json();
                    if (claimData.success) {{
                        tg.showPopup({{title: '🎉 Награда получена!', message: '+' + claimData.reward + ' кликов!', buttons: [{{type: 'ok'}}]}});
                        await loadStats();
                        await loadReferralData();
                    }} else {{
                        tg.showPopup({{title: '❌ Нет наград', message: claimData.message, buttons: [{{type: 'ok'}}]}});
                    }}
                }};
            }} catch(e) {{ console.error(e); }}
        }}
        
        async function sendClick(increment) {{
            try {{
                const res = await fetch('/api/click', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ user_id: userId, clicks: increment }})
                }});
                const data = await res.json();
                clicks = data.clicks;
                level = data.level;
                tapPower = data.tap_power;
                passiveIncome = data.passive_income;
                gems = data.gems;
                energy = data.energy;
                updateUI();
            }} catch(e) {{ console.error(e); }}
        }}
        
        function showFloatingNumber(x, y, value) {{
            const el = document.createElement('div');
            el.className = 'tap-value';
            el.textContent = '+' + value;
            el.style.left = x + 'px';
            el.style.top = y + 'px';
            document.body.appendChild(el);
            setTimeout(() => el.remove(), 600);
        }}
        
        document.getElementById('duck').onclick = async (e) => {{
            if (energy <= 0) {{
                tg.showPopup({{title: '😫 Нет энергии!', message: 'Подожди, энергия восстановится.', buttons: [{{type: 'ok'}}]}});
                return;
            }}
            const rect = e.target.getBoundingClientRect();
            const x = rect.left + rect.width / 2;
            const y = rect.top;
            showFloatingNumber(x, y, tapPower);
            energy -= 1;
            updateUI();
            await sendClick(tapPower);
        }};
        
        document.getElementById('upgradeTapBtn').onclick = async () => {{
            const res = await fetch('/api/upgrade_tap?user_id=' + userId, {{method: 'POST'}});
            const data = await res.json();
            if (data.success) {{
                tg.showPopup({{title: '✅ Улучшено!', message: 'Сила клика: +' + data.new_tap_power, buttons: [{{type: 'ok'}}]}});
                await loadStats();
            }} else {{
                tg.showPopup({{title: '❌ Не хватает кликов', message: 'Нужно: ' + data.need + ' кликов', buttons: [{{type: 'ok'}}]}});
            }}
        }};
        
        document.getElementById('upgradePassiveBtn').onclick = async () => {{
            const res = await fetch('/api/upgrade_passive?user_id=' + userId, {{method: 'POST'}});
            const data = await res.json();
            if (data.success) {{
                tg.showPopup({{title: '✅ Пассивный доход улучшен!', message: 'Теперь +' + data.new_passive + '/час', buttons: [{{type: 'ok'}}]}});
                await loadStats();
            }} else {{
                tg.showPopup({{title: '❌ Не хватает кликов', message: 'Нужно: ' + data.need + ' кликов', buttons: [{{type: 'ok'}}]}});
            }}
        }};
        
        document.getElementById('collectPassiveBtn').onclick = async () => {{
            const res = await fetch('/api/collect_passive?user_id=' + userId, {{method: 'POST'}});
            const data = await res.json();
            if (data.success) {{
                tg.showPopup({{title: '💰 Получено!', message: '+' + data.earned + ' кликов!', buttons: [{{type: 'ok'}}]}});
                await loadStats();
            }} else {{
                tg.showPopup({{title: '😴 Нет дохода', message: data.message, buttons: [{{type: 'ok'}}]}});
            }}
        }};
        
        document.getElementById('dailyBtn').onclick = async () => {{
            const res = await fetch('/api/claim_daily?user_id=' + userId, {{method: 'POST'}});
            const data = await res.json();
            if (data.success) {{
                let gemMsg = data.gem_bonus ? ' +' + data.gem_bonus + '💎' : '';
                tg.showPopup({{title: '🎁 Бонус получен!', message: '+' + data.bonus + ' кликов!' + gemMsg + ' Серия: ' + data.streak, buttons: [{{type: 'ok'}}]}});
                await loadStats();
            }} else {{
                tg.showPopup({{title: '❌ Уже забирал', message: data.message, buttons: [{{type: 'ok'}}]}});
            }}
        }};
        
        document.getElementById('openShopBtn').onclick = () => showScreen('shopScreen');
        document.getElementById('openCasesBtn').onclick = () => showScreen('casesScreen');
        document.getElementById('openBoostersBtn').onclick = () => showScreen('boostersScreen');
        document.getElementById('openAchievementsBtn').onclick = () => showScreen('achievementsScreen');
        document.getElementById('openTournamentsBtn').onclick = () => showScreen('tournamentsScreen');
        document.getElementById('openReferralBtn').onclick = () => showScreen('referralScreen');
        document.getElementById('profileBtn').onclick = () => showScreen('profileScreen');
        document.getElementById('closeBtn').onclick = () => tg.close();
        
        loadStats();
        
        setInterval(() => {{
            if (energy < maxEnergy) {{
                energy = Math.min(energy + 5, maxEnergy);
                updateUI();
            }}
        }}, 1000);
    </script>
</body>
</html>'''
    
    return HTMLResponse(content=html)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)                           