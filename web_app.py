import os
import sqlite3
import random
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

app = FastAPI()

class ClickData(BaseModel):
    user_id: int
    clicks: int

DB_PATH = os.path.join(os.path.dirname(__file__), "zeta_clicker.db")

# ==================== ИНИЦИАЛИЗАЦИЯ БД ====================

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Основная таблица пользователей (добавляем алмазы)
    cursor.execute("ALTER TABLE users ADD COLUMN gems INTEGER DEFAULT 0")
    cursor.execute("ALTER TABLE users ADD COLUMN total_gems INTEGER DEFAULT 0")
    cursor.execute("ALTER TABLE users ADD COLUMN last_booster_time TIMESTAMP DEFAULT NULL")
    
    # Таблица достижений
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
    
    # Прогресс достижений пользователя
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
    
    # Таблица кейсов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
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
            description TEXT,
            effect_type TEXT,
            effect_value REAL,
            duration_minutes INTEGER,
            price_gems INTEGER,
            price_clicks INTEGER
        )
    """)
    
    # Активные бустеры пользователя
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
    
    # Добавляем стандартные достижения
    cursor.execute("SELECT COUNT(*) FROM achievements")
    if cursor.fetchone()[0] == 0:
        achievements = [
            ("Новичок", "Накликать 100 кликов", "clicks", 100, 1, 500, None),
            ("Серебряный палец", "Накликать 1000 кликов", "clicks", 1000, 2, 2000, None),
            ("Золотой палец", "Накликать 10000 кликов", "clicks", 10000, 5, 10000, None),
            ("Коллекционер", "Купить 1 скин", "skins", 1, 1, 500, None),
            ("Магнат", "Купить 3 скина", "skins", 3, 3, 2000, None),
            ("Реферал", "Пригласить 1 друга", "referrals", 1, 1, 1000, None),
            ("Популярный", "Пригласить 5 друзей", "referrals", 5, 5, 5000, None),
        ]
        cursor.executemany(
            "INSERT INTO achievements (name, description, condition_type, condition_value, reward_gems, reward_clicks, reward_skin_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            achievements
        )
    
    # Добавляем кейсы
    cursor.execute("SELECT COUNT(*) FROM cases")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO cases (name, price_gems, price_clicks) VALUES (?, ?, ?)", ("Обычный кейс", 0, 1000))
        case_id = cursor.lastrowid
        rewards = [
            (case_id, "clicks", 100, "100 кликов", 30),
            (case_id, "clicks", 500, "500 кликов", 20),
            (case_id, "clicks", 1000, "1000 кликов", 15),
            (case_id, "clicks", 5000, "5000 кликов", 5),
            (case_id, "gems", 1, "1 алмаз", 15),
            (case_id, "gems", 5, "5 алмазов", 8),
            (case_id, "booster", 1, "x2 клика (30 мин)", 5),
            (case_id, "skin", 2, "Золотая утка", 2),
        ]
        cursor.executemany(
            "INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance) VALUES (?, ?, ?, ?, ?)",
            rewards
        )
    
    # Добавляем бустеры
    cursor.execute("SELECT COUNT(*) FROM boosters")
    if cursor.fetchone()[0] == 0:
        boosters = [
            ("x2 Клики", "Удваивает силу клика на 30 минут", "tap_multiplier", 2, 30, 5, 5000),
            ("Автокликер", "Автоматически кликает 10 раз в секунду", "auto_click", 10, 30, 10, 10000),
            ("x2 Пассивка", "Удваивает пассивный доход на 1 час", "passive_multiplier", 2, 60, 3, 3000),
        ]
        cursor.executemany(
            "INSERT INTO boosters (name, description, effect_type, effect_value, duration_minutes, price_gems, price_clicks) VALUES (?, ?, ?, ?, ?, ?, ?)",
            boosters
        )
    
    conn.commit()
    conn.close()

init_db()

# ==================== ФУНКЦИИ ДЛЯ НОВЫХ ФИЧ ====================

def get_user_stats(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT clicks, level, tap_power, passive_income, current_skin, total_clicks, daily_streak, gems FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            "clicks": int(result[0]),
            "level": int(result[1]),
            "tap_power": int(result[2]),
            "passive_income": int(result[3]),
            "skin": str(result[4]) if result[4] else "🦆",
            "total_clicks": int(result[5]),
            "daily_streak": int(result[6]),
            "gems": int(result[7])
        }
    else:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (user_id, clicks, level, tap_power, passive_income, current_skin, total_clicks, daily_streak, gems) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, 0, 1, 1, 0, "🦆", 0, 0, 0)
        )
        conn.commit()
        conn.close()
        return {"clicks": 0, "level": 1, "tap_power": 1, "passive_income": 0, "skin": "🦆", "total_clicks": 0, "daily_streak": 0, "gems": 0}

def update_clicks(user_id: int, increment: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT clicks, total_clicks, level FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if result:
        new_clicks = result[0] + increment
        new_total = result[1] + increment
        new_level = 1 + new_total // 100
        cursor.execute("UPDATE users SET clicks = ?, total_clicks = ?, level = ? WHERE user_id = ?", (new_clicks, new_total, new_level, user_id))
        conn.commit()
        
        # Проверка достижений
        check_achievements(user_id, "clicks", new_total)
    conn.close()

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
    cursor.execute("SELECT id, condition_type, condition_value, reward_gems, reward_clicks FROM achievements WHERE condition_type = ?", (condition_type,))
    achievements = cursor.fetchall()
    
    for ach in achievements:
        ach_id, ach_type, ach_value, reward_gems, reward_clicks = ach
        cursor.execute("SELECT completed FROM user_achievements WHERE user_id = ? AND achievement_id = ?", (user_id, ach_id))
        result = cursor.fetchone()
        if not result or result[0] == 0:
            if current_value >= ach_value:
                cursor.execute("INSERT OR REPLACE INTO user_achievements (user_id, achievement_id, progress, completed, completed_at) VALUES (?, ?, ?, ?, ?)",
                               (user_id, ach_id, ach_value, 1, datetime.now().isoformat()))
                add_gems(user_id, reward_gems)
                cursor.execute("SELECT clicks FROM users WHERE user_id = ?", (user_id,))
                clicks = cursor.fetchone()[0]
                cursor.execute("UPDATE users SET clicks = ? WHERE user_id = ?", (clicks + reward_clicks, user_id))
    conn.commit()
    conn.close()

def open_case(user_id: int, case_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT price_gems, price_clicks FROM cases WHERE id = ?", (case_id,))
    price_gems, price_clicks = cursor.fetchone()
    
    cursor.execute("SELECT clicks, gems FROM users WHERE user_id = ?", (user_id,))
    clicks, gems = cursor.fetchone()
    
    if clicks >= price_clicks and price_clicks > 0:
        new_clicks = clicks - price_clicks
        cursor.execute("UPDATE users SET clicks = ? WHERE user_id = ?", (new_clicks, user_id))
    elif gems >= price_gems and price_gems > 0:
        new_gems = gems - price_gems
        cursor.execute("UPDATE users SET gems = ? WHERE user_id = ?", (new_gems, user_id))
    else:
        conn.close()
        return {"success": False, "message": "Не хватает ресурсов"}
    
    cursor.execute("SELECT reward_type, reward_value, reward_text FROM case_rewards WHERE case_id = ? ORDER BY random() LIMIT 1", (case_id,))
    reward_type, reward_value, reward_text = cursor.fetchone()
    
    result = {"success": True, "reward_text": reward_text}
    
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
        booster_id = reward_value
        expires_at = datetime.now() + timedelta(minutes=30)
        cursor.execute("INSERT OR REPLACE INTO user_boosters (user_id, booster_id, expires_at) VALUES (?, ?, ?)", (user_id, booster_id, expires_at.isoformat()))
        result["reward"] = reward_text
    elif reward_type == "skin":
        skin_id = reward_value
        cursor.execute("INSERT OR IGNORE INTO user_skins (user_id, skin_id) VALUES (?, ?)", (user_id, skin_id))
        result["reward"] = reward_text
    
    conn.commit()
    conn.close()
    return result

def get_active_boosters(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
        SELECT b.id, b.name, b.description, b.effect_type, b.effect_value, b.duration_minutes, 
               julianday(ub.expires_at) - julianday(?) as minutes_left
        FROM user_boosters ub
        JOIN boosters b ON ub.booster_id = b.id
        WHERE ub.user_id = ? AND ub.expires_at > ?
    """, (now, user_id, now))
    result = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "description": r[2], "effect_type": r[3], "effect_value": r[4], "minutes_left": int(r[6])} for r in result]

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

# ==================== API ====================

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
    cursor.execute("SELECT last_daily, daily_streak, clicks FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        return {"success": False, "message": "Пользователь не найден"}
    
    last_daily, daily_streak, clicks = result
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
    
    cursor.execute("UPDATE users SET clicks = ?, last_daily = ?, daily_streak = ? WHERE user_id = ?", 
                   (new_clicks, today.isoformat(), daily_streak, user_id))
    conn.commit()
    conn.close()
    
    return {"success": True, "bonus": bonus, "streak": daily_streak, "new_clicks": new_clicks}

@app.post("/api/buy_skin")
async def buy_skin(user_id: int, skin_id: int):
    skins = {2: {"price": 5000, "emoji": "🌟", "name": "Золотая утка", "bonus": 2},
             3: {"price": 15000, "emoji": "🤖", "name": "Киберутка", "bonus": 5},
             4: {"price": 30000, "emoji": "👻", "name": "Утка-призрак", "bonus": 10},
             5: {"price": 50000, "emoji": "😈", "name": "Дьявольская утка", "bonus": 15}}
    
    if skin_id not in skins:
        return {"success": False, "message": "Скин не найден"}
    
    price = skins[skin_id]["price"]
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT clicks FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        return {"success": False, "message": "Пользователь не найден"}
    
    clicks = result[0]
    
    if clicks >= price:
        new_clicks = clicks - price
        cursor.execute("UPDATE users SET clicks = ? WHERE user_id = ?", (new_clicks, user_id))
        cursor.execute("INSERT OR IGNORE INTO user_skins (user_id, skin_id) VALUES (?, ?)", (user_id, skin_id))
        conn.commit()
        conn.close()
        
        # Проверка достижения за покупку скинов
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM user_skins WHERE user_id = ?", (user_id,))
        skins_count = cursor.fetchone()[0]
        conn.close()
        check_achievements(user_id, "skins", skins_count)
        
        return {"success": True, "new_clicks": new_clicks, "skin_name": skins[skin_id]["name"]}
    else:
        conn.close()
        return {"success": False, "need": price, "clicks": clicks}

@app.post("/api/equip_skin")
async def equip_skin(user_id: int, skin_id: int):
    skins = {2: "🌟", 3: "🤖", 4: "👻", 5: "😈"}
    if skin_id not in skins:
        return {"success": False, "message": "Скин не найден"}
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM user_skins WHERE user_id = ? AND skin_id = ?", (user_id, skin_id))
    if not cursor.fetchone():
        conn.close()
        return {"success": False, "message": "Скин не куплен"}
    
    emoji = skins[skin_id]
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
    conn.close()
    
    all_skins = [
        {"id": 2, "name": "Золотая утка", "emoji": "🌟", "price": 5000, "bonus": 2},
        {"id": 3, "name": "Киберутка", "emoji": "🤖", "price": 15000, "bonus": 5},
        {"id": 4, "name": "Утка-призрак", "emoji": "👻", "price": 30000, "bonus": 10},
        {"id": 5, "name": "Дьявольская утка", "emoji": "😈", "price": 50000, "bonus": 15},
    ]
    
    for skin in all_skins:
        skin["owned"] = skin["id"] in owned
        skin["equipped"] = (skin["emoji"] == current)
    
    return {"skins": all_skins, "current_skin": current}

@app.get("/api/get_referrals")
async def get_referrals(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))
    count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND reward_claimed = 0", (user_id,))
    unclaimed = cursor.fetchone()[0]
    conn.close()
    
    # Проверка достижения за рефералов
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
async def open_case(user_id: int, case_id: int = 1):
    result = open_case(user_id, case_id)
    return result

@app.get("/api/get_boosters")
async def get_boosters(user_id: int):
    active = get_active_boosters(user_id)
    return {"boosters": active}

@app.get("/api/get_achievements")
async def get_achievements_list(user_id: int):
    achievements = get_achievements(user_id)
    return {"achievements": achievements}

@app.get("/api/get_stats")
async def get_stats(user_id: int):
    stats = get_user_stats(user_id)
    boosters = get_active_boosters(user_id)
    tap_multiplier = get_booster_multiplier(user_id)
    return {
        "clicks": stats["clicks"],
        "level": stats["level"],
        "tap_power": stats["tap_power"],
        "passive_income": stats["passive_income"],
        "skin": stats["skin"],
        "daily_streak": stats["daily_streak"],
        "gems": stats["gems"],
        "boosters": boosters,
        "tap_multiplier": tap_multiplier
    }

@app.post("/api/click")
async def handle_click(data: ClickData):
    multiplier = get_booster_multiplier(data.user_id)
    final_clicks = int(data.clicks * multiplier)
    update_clicks(data.user_id, final_clicks)
    stats = get_user_stats(data.user_id)
    return {
        "clicks": stats["clicks"],
        "level": stats["level"],
        "tap_power": stats["tap_power"],
        "passive_income": stats["passive_income"],
        "gems": stats["gems"]
    }

@app.get("/health")
async def health():
    return {"status": "ok"}

# ==================== HTML С ЭКРАНАМИ ====================

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
        
        .skin-list, .booster-list, .achievement-list {{ margin: 20px 0; }}
        .skin-item, .booster-item, .achievement-item {{ background: rgba(0,0,0,0.3); border-radius: 16px; padding: 12px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }}
        .skin-info, .booster-info, .achievement-info {{ display: flex; align-items: center; gap: 12px; }}
        .skin-emoji, .booster-emoji, .achievement-emoji {{ font-size: 40px; }}
        .skin-name, .booster-name, .achievement-name {{ font-size: 16px; font-weight: bold; }}
        .skin-price, .booster-price, .achievement-desc {{ font-size: 12px; color: #ffd700; }}
        .skin-btn, .booster-btn {{ background: #667eea; border: none; border-radius: 12px; padding: 8px 16px; color: white; cursor: pointer; }}
        .skin-btn.owned {{ background: #4caf50; }}
        .skin-btn.equipped {{ background: #ff9800; }}
        .achievement-completed {{ background: #4caf50; color: white; border-radius: 12px; padding: 4px 8px; font-size: 12px; }}
        
        .case-container {{ text-align: center; margin: 20px 0; }}
        .case-box {{ background: linear-gradient(135deg, #ffd700, #ff8c00); border-radius: 20px; padding: 30px; cursor: pointer; margin-bottom: 20px; }}
        .case-box:active {{ transform: scale(0.98); }}
        .case-emoji {{ font-size: 80px; }}
        .case-price {{ color: white; margin-top: 10px; }}
        
        .tap-value {{ position: fixed; pointer-events: none; font-size: 28px; font-weight: bold; color: #ffd700; animation: floatUp 0.6s ease-out forwards; z-index: 1000; }}
        @keyframes floatUp {{ 0% {{ opacity: 1; transform: translateY(0) scale(0.8); }} 100% {{ opacity: 0; transform: translateY(-80px) scale(1.2); }} }}
    </style>
</head>
<body>
    <div class="container">
        <!-- ГЛАВНЫЙ ЭКРАН -->
        <div id="mainScreen" class="screen active">
            <div class="stats">
                <div class="stat-row"><span class="stat-label">🦆 Уровень</span><