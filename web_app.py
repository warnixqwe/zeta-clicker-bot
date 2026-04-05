import os
import sqlite3
import random
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ClickData(BaseModel):
    user_id: int
    clicks: int

DB_PATH = os.path.join(os.path.dirname(__file__), "zeta_clicker.db")

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT NULL,
            clicks INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            energy INTEGER DEFAULT 1000,
            tap_power INTEGER DEFAULT 1,
            passive_income INTEGER DEFAULT 0,
            current_skin TEXT DEFAULT '🦆',
            total_clicks INTEGER DEFAULT 0,
            last_daily TIMESTAMP DEFAULT NULL,
            daily_streak INTEGER DEFAULT 0,
            gems INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            emoji TEXT,
            price_clicks INTEGER,
            tap_bonus INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_skins (
            user_id INTEGER,
            skin_id INTEGER,
            PRIMARY KEY (user_id, skin_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            emoji TEXT,
            price_clicks INTEGER
        )
    """)
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS boosters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            emoji TEXT,
            description TEXT,
            effect_type TEXT,
            effect_value REAL,
            duration_minutes INTEGER,
            price_clicks INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_boosters (
            user_id INTEGER,
            booster_id INTEGER,
            expires_at TIMESTAMP,
            PRIMARY KEY (user_id, booster_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            condition_type TEXT,
            condition_value INTEGER,
            reward_gems INTEGER,
            reward_clicks INTEGER
        )
    """)
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
    conn.commit()
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN username TEXT DEFAULT NULL")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    
    cursor.execute("SELECT COUNT(*) FROM skins")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO skins (name, emoji, price_clicks, tap_bonus) VALUES (?, ?, ?, ?)", [
            ('Обычная утка', '🦆', 0, 0),
            ('Золотая утка', '🌟', 5000, 2),
            ('Киберутка', '🤖', 15000, 5),
            ('Утка-призрак', '👻', 30000, 10),
            ('Дьявольская утка', '😈', 50000, 15),
        ])
    
    cursor.execute("SELECT COUNT(*) FROM cases")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO cases (name, emoji, price_clicks) VALUES (?, ?, ?)", ("Обычный кейс", "📦", 1000))
        case_id = cursor.lastrowid
        cursor.executemany("INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance) VALUES (?, ?, ?, ?, ?)", [
            (case_id, "clicks", 100, "100 кликов", 30),
            (case_id, "clicks", 500, "500 кликов", 20),
            (case_id, "clicks", 1000, "1000 кликов", 15),
            (case_id, "clicks", 5000, "5000 кликов", 5),
            (case_id, "gems", 1, "1 алмаз 💎", 15),
            (case_id, "gems", 5, "5 алмазов 💎", 8),
            (case_id, "booster", 1, "x2 клика (30 мин)", 5),
            (case_id, "skin", 2, "Золотая утка 🌟", 2),
        ])
        
        cursor.execute("INSERT INTO cases (name, emoji, price_clicks) VALUES (?, ?, ?)", ("Серебряный кейс", "🥈", 5000))
        case_id = cursor.lastrowid
        cursor.executemany("INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance) VALUES (?, ?, ?, ?, ?)", [
            (case_id, "clicks", 1000, "1000 кликов", 25),
            (case_id, "clicks", 2500, "2500 кликов", 20),
            (case_id, "clicks", 5000, "5000 кликов", 15),
            (case_id, "gems", 2, "2 алмаза 💎", 15),
            (case_id, "gems", 5, "5 алмазов 💎", 10),
            (case_id, "booster", 1, "x2 клика (30 мин)", 8),
            (case_id, "skin", 3, "Киберутка 🤖", 5),
            (case_id, "skin", 4, "Утка-призрак 👻", 2),
        ])
        
        cursor.execute("INSERT INTO cases (name, emoji, price_clicks) VALUES (?, ?, ?)", ("Алмазный кейс", "💎", 15000))
        case_id = cursor.lastrowid
        cursor.executemany("INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance) VALUES (?, ?, ?, ?, ?)", [
            (case_id, "clicks", 5000, "5000 кликов", 20),
            (case_id, "clicks", 10000, "10000 кликов", 15),
            (case_id, "clicks", 25000, "25000 кликов", 10),
            (case_id, "gems", 5, "5 алмазов 💎", 15),
            (case_id, "gems", 10, "10 алмазов 💎", 10),
            (case_id, "gems", 25, "25 алмазов 💎", 5),
            (case_id, "booster", 1, "x2 клика (1 час)", 10),
            (case_id, "skin", 4, "Утка-призрак 👻", 4),
            (case_id, "skin", 5, "Дьявольская утка 😈", 3),
        ])
    
    cursor.execute("SELECT COUNT(*) FROM boosters")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO boosters (name, emoji, description, effect_type, effect_value, duration_minutes, price_clicks) VALUES (?, ?, ?, ?, ?, ?, ?)", [
            ("x2 Клики", "⚡", "Удваивает силу клика на 30 минут", "tap_multiplier", 2, 30, 5000),
            ("Энергетик", "🔋", "Восстанавливает 500 энергии", "energy", 500, 0, 2000),
        ])
    
    cursor.execute("SELECT COUNT(*) FROM achievements")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO achievements (name, description, condition_type, condition_value, reward_gems, reward_clicks) VALUES (?, ?, ?, ?, ?, ?)", [
            ("Новичок", "Накликать 100 кликов", "clicks", 100, 1, 500),
            ("Серебряный палец", "Накликать 1000 кликов", "clicks", 1000, 2, 2000),
            ("Золотой палец", "Накликать 10000 кликов", "clicks", 10000, 5, 10000),
            ("Коллекционер", "Купить 1 скин", "skins", 1, 1, 500),
            ("Магнат", "Купить 3 скина", "skins", 3, 3, 2000),
            ("Везунчик", "Открыть 5 кейсов", "cases", 5, 3, 3000),
            ("Азартный", "Открыть 20 кейсов", "cases", 20, 10, 10000),
        ])
    conn.commit()
    conn.close()

init_db()

def get_user_stats(user_id: int, username: str = None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT clicks, level, energy, tap_power, passive_income, current_skin, total_clicks, daily_streak, gems, username FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        if username and result[9] != username:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
            conn.commit()
            conn.close()
        return {
            "clicks": result[0], "level": result[1], "energy": result[2],
            "tap_power": result[3], "passive_income": result[4], "skin": result[5],
            "total_clicks": result[6], "daily_streak": result[7], "gems": result[8],
            "username": result[9] or str(user_id)
        }
    else:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (user_id, username, clicks, level, energy, tap_power, passive_income, current_skin, total_clicks, daily_streak, gems) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (user_id, username or str(user_id), 0, 1, 1000, 1, 0, "🦆", 0, 0, 0))
        conn.commit()
        conn.close()
        return {"clicks": 0, "level": 1, "energy": 1000, "tap_power": 1, "passive_income": 0, "skin": "🦆", "total_clicks": 0, "daily_streak": 0, "gems": 0, "username": username or str(user_id)}

def update_clicks(user_id: int, increment: int):
    for attempt in range(3):
        try:
            conn = get_db()
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
            conn.close()
            return True
        except sqlite3.OperationalError as e:
            if "locked" in str(e) and attempt < 2:
                time.sleep(0.1)
                continue
            raise e
    return False

def add_gems(user_id: int, amount: int):
    for attempt in range(3):
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT gems FROM users WHERE user_id = ?", (user_id,))
            gems = cursor.fetchone()[0]
            cursor.execute("UPDATE users SET gems = ? WHERE user_id = ?", (gems + amount, user_id))
            conn.commit()
            conn.close()
            return True
        except sqlite3.OperationalError as e:
            if "locked" in str(e) and attempt < 2:
                time.sleep(0.1)
                continue
            raise e
    return False

def get_active_boosters(user_id: int):
    conn = get_db()
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

def check_achievements(user_id: int, condition_type: str, current_value: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, condition_value, reward_gems, reward_clicks FROM achievements WHERE condition_type = ?", (condition_type,))
    achievements = cursor.fetchall()
    for ach in achievements:
        ach_id, ach_value, reward_gems, reward_clicks = ach
        cursor.execute("SELECT completed FROM user_achievements WHERE user_id = ? AND achievement_id = ?", (user_id, ach_id))
        result = cursor.fetchone()
        if not result or result[0] == 0:
            if current_value >= ach_value:
                cursor.execute("INSERT INTO user_achievements (user_id, achievement_id, progress, completed, completed_at) VALUES (?, ?, ?, ?, ?)",
                               (user_id, ach_id, ach_value, 1, datetime.now().isoformat()))
                if reward_gems > 0:
                    add_gems(user_id, reward_gems)
                if reward_clicks > 0:
                    cursor.execute("UPDATE users SET clicks = clicks + ? WHERE user_id = ?", (reward_clicks, user_id))
    conn.commit()
    conn.close()

@app.post("/api/click")
async def handle_click(data: ClickData):
    multiplier = get_booster_multiplier(data.user_id)
    final_clicks = int(data.clicks * multiplier)
    update_clicks(data.user_id, final_clicks)
    stats = get_user_stats(data.user_id)
    check_achievements(data.user_id, "clicks", stats["total_clicks"])
    return {
        "clicks": stats["clicks"], "level": stats["level"], "energy": stats["energy"],
        "tap_power": stats["tap_power"], "passive_income": stats["passive_income"], "gems": stats["gems"]
    }

@app.post("/api/upgrade_tap")
async def upgrade_tap(user_id: int):
    stats = get_user_stats(user_id)
    price = stats["tap_power"] * 100
    if stats["clicks"] >= price:
        conn = get_db()
        cursor = conn.cursor()
        new_clicks = stats["clicks"] - price
        new_tap_power = stats["tap_power"] + 1
        cursor.execute("UPDATE users SET clicks = ?, tap_power = ? WHERE user_id = ?", (new_clicks, new_tap_power, user_id))
        conn.commit()
        conn.close()
        return {"success": True, "new_tap_power": new_tap_power}
    return {"success": False, "need": price}

@app.post("/api/upgrade_passive")
async def upgrade_passive(user_id: int):
    stats = get_user_stats(user_id)
    price = 500 + stats["passive_income"] * 100
    if stats["clicks"] >= price:
        conn = get_db()
        cursor = conn.cursor()
        new_clicks = stats["clicks"] - price
        new_passive = stats["passive_income"] + 5
        cursor.execute("UPDATE users SET clicks = ?, passive_income = ? WHERE user_id = ?", (new_clicks, new_passive, user_id))
        conn.commit()
        conn.close()
        return {"success": True, "new_passive": new_passive}
    return {"success": False, "need": price}

@app.post("/api/collect_passive")
async def collect_passive(user_id: int):
    stats = get_user_stats(user_id)
    if stats["passive_income"] > 0:
        conn = get_db()
        cursor = conn.cursor()
        new_clicks = stats["clicks"] + stats["passive_income"]
        cursor.execute("UPDATE users SET clicks = ? WHERE user_id = ?", (new_clicks, user_id))
        conn.commit()
        conn.close()
        return {"success": True, "earned": stats["passive_income"]}
    return {"success": False, "message": "Нет пассивного дохода"}

@app.post("/api/claim_daily")
async def claim_daily(user_id: int):
    stats = get_user_stats(user_id)
    today = datetime.now().date()
    last_date = datetime.fromisoformat(stats.get("last_daily", "")).date() if stats.get("last_daily") else None
    if last_date == today:
        return {"success": False, "message": "Уже забирал сегодня"}
    streak = stats["daily_streak"] + 1 if last_date == today - timedelta(days=1) else 1
    bonus = min(100 + streak * 50, 600)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET clicks = clicks + ?, daily_streak = ?, last_daily = ? WHERE user_id = ?",
                   (bonus, streak, today.isoformat(), user_id))
    conn.commit()
    conn.close()
    return {"success": True, "bonus": bonus, "streak": streak}

@app.post("/api/buy_skin")
async def buy_skin(user_id: int, skin_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name, emoji, price_clicks FROM skins WHERE id = ?", (skin_id,))
    skin = cursor.fetchone()
    if not skin:
        conn.close()
        return {"success": False, "message": "Скин не найден"}
    skin_name, skin_emoji, price = skin
    stats = get_user_stats(user_id)
    if stats["clicks"] >= price:
        new_clicks = stats["clicks"] - price
        cursor.execute("UPDATE users SET clicks = ? WHERE user_id = ?", (new_clicks, user_id))
        cursor.execute("INSERT OR IGNORE INTO user_skins (user_id, skin_id) VALUES (?, ?)", (user_id, skin_id))
        cursor.execute("SELECT COUNT(*) FROM user_skins WHERE user_id = ?", (user_id,))
        skins_count = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        check_achievements(user_id, "skins", skins_count)
        return {"success": True, "skin_name": skin_name, "skin_emoji": skin_emoji}
    conn.close()
    return {"success": False, "need": price}

@app.post("/api/equip_skin")
async def equip_skin(user_id: int, skin_id: int):
    conn = get_db()
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
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT skin_id FROM user_skins WHERE user_id = ?", (user_id,))
    owned = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT current_skin FROM users WHERE user_id = ?", (user_id,))
    current = cursor.fetchone()[0]
    cursor.execute("SELECT id, name, emoji, price_clicks, tap_bonus FROM skins")
    skins = cursor.fetchall()
    conn.close()
    return {"skins": [{"id": s[0], "name": s[1], "emoji": s[2], "price": s[3], "bonus": s[4], "owned": s[0] in owned, "equipped": s[2] == current} for s in skins], "current_skin": current}

@app.post("/api/open_case")
async def open_case(user_id: int, case_id: int = 1):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name, emoji, price_clicks FROM cases WHERE id = ?", (case_id,))
    case = cursor.fetchone()
    if not case:
        conn.close()
        return {"success": False, "message": "Кейс не найден"}
    case_name, case_emoji, price = case
    stats = get_user_stats(user_id)
    if stats["clicks"] >= price:
        new_clicks = stats["clicks"] - price
        cursor.execute("UPDATE users SET clicks = ? WHERE user_id = ?", (new_clicks, user_id))
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
        reward_type, reward_value, reward_text, _ = selected
        if reward_type == "clicks":
            cursor.execute("UPDATE users SET clicks = clicks + ? WHERE user_id = ?", (reward_value, user_id))
        elif reward_type == "gems":
            cursor.execute("UPDATE users SET gems = gems + ? WHERE user_id = ?", (reward_value, user_id))
        elif reward_type == "booster":
            expires_at = datetime.now() + timedelta(minutes=30 if reward_value == 1 else 60)
            cursor.execute("INSERT OR REPLACE INTO user_boosters (user_id, booster_id, expires_at) VALUES (?, ?, ?)",
                           (user_id, reward_value, expires_at.isoformat()))
        elif reward_type == "skin":
            cursor.execute("INSERT OR IGNORE INTO user_skins (user_id, skin_id) VALUES (?, ?)", (user_id, reward_value))
        cursor.execute("SELECT COUNT(*) FROM user_achievements WHERE user_id = ? AND achievement_id IN (6,7) AND completed = 1", (user_id,))
        cases_opened = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        check_achievements(user_id, "cases", cases_opened + 1)
        return {"success": True, "reward_text": reward_text, "case_emoji": case_emoji}
    conn.close()
    return {"success": False, "need": price}

@app.get("/api/get_cases")
async def get_cases():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, emoji, price_clicks FROM cases")
    cases = cursor.fetchall()
    conn.close()
    return {"cases": [{"id": c[0], "name": c[1], "emoji": c[2], "price": c[3]} for c in cases]}

@app.get("/api/get_boosters")
async def get_boosters(user_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, emoji, description, price_clicks FROM boosters")
    shop_boosters = cursor.fetchall()
    active = get_active_boosters(user_id)
    conn.close()
    return {"shop_boosters": [{"id": b[0], "name": b[1], "emoji": b[2], "description": b[3], "price": b[4]} for b in shop_boosters],
            "active_boosters": active}

@app.post("/api/buy_booster")
async def buy_booster(user_id: int, booster_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name, emoji, price_clicks, duration_minutes, effect_type, effect_value FROM boosters WHERE id = ?", (booster_id,))
    booster = cursor.fetchone()
    if not booster:
        conn.close()
        return {"success": False, "message": "Бустер не найден"}
    booster_name, booster_emoji, price, duration, effect_type, effect_value = booster
    stats = get_user_stats(user_id)
    if stats["clicks"] >= price:
        new_clicks = stats["clicks"] - price
        cursor.execute("UPDATE users SET clicks = ? WHERE user_id = ?", (new_clicks, user_id))
        expires_at = datetime.now() + timedelta(minutes=duration)
        cursor.execute("INSERT OR REPLACE INTO user_boosters (user_id, booster_id, expires_at) VALUES (?, ?, ?)",
                       (user_id, booster_id, expires_at.isoformat()))
        if effect_type == "energy":
            new_energy = min(stats["energy"] + int(effect_value), 1000)
            cursor.execute("UPDATE users SET energy = ? WHERE user_id = ?", (new_energy, user_id))
        conn.commit()
        conn.close()
        return {"success": True, "booster_name": booster_name, "booster_emoji": booster_emoji}
    conn.close()
    return {"success": False, "need": price}

@app.get("/api/get_achievements")
async def get_achievements(user_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, condition_value, reward_gems, reward_clicks FROM achievements")
    achievements = cursor.fetchall()
    result = []
    for ach in achievements:
        ach_id, name, desc, condition, reward_gems, reward_clicks = ach
        cursor.execute("SELECT completed FROM user_achievements WHERE user_id = ? AND achievement_id = ?", (user_id, ach_id))
        completed = cursor.fetchone()
        result.append({
            "id": ach_id, "name": name, "description": desc, "condition": condition,
            "reward_gems": reward_gems, "reward_clicks": reward_clicks,
            "completed": completed[0] if completed else 0
        })
    conn.close()
    return {"achievements": result}

@app.get("/api/get_leaderboard")
async def get_leaderboard(limit: int = 10):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, total_clicks FROM users ORDER BY total_clicks DESC LIMIT ?", (limit,))
    result = cursor.fetchall()
    conn.close()
    return {"leaderboard": [{"user_id": r[0], "username": r[1] or str(r[0]), "clicks": r[2]} for r in result]}

@app.get("/api/get_stats")
async def get_stats(user_id: int, username: str = None):
    stats = get_user_stats(user_id, username)
    boosters = get_active_boosters(user_id)
    tap_multiplier = get_booster_multiplier(user_id)
    return {**stats, "boosters": boosters, "tap_multiplier": tap_multiplier}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
async def mini_app(user_id: int = 1, username: str = None):
    stats = get_user_stats(user_id, username)
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>Zeta Clicker</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; user-select: none; }}
        body {{ min-height: 100vh; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); font-family: Arial, sans-serif; padding: 20px; display: flex; justify-content: center; align-items: center; }}
        .container {{ max-width: 500px; width: 100%; background: rgba(255,255,255,0.05); border-radius: 32px; padding: 20px; }}
        .screen {{ display: none; }}
        .screen.active {{ display: block; }}
        .stats {{ background: rgba(0,0,0,0.3); border-radius: 24px; padding: 16px; margin-bottom: 24px; }}
        .stat-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.1); }}
        .stat-row:last-child {{ border-bottom: none; }}
        .stat-label {{ color: #aaa; font-size: 14px; }}
        .stat-value {{ color: #ffd700; font-size: 20px; font-weight: bold; }}
        .duck-container {{ display: flex; justify-content: center; margin: 20px 0; }}
        .duck {{ font-size: 180px; cursor: pointer; transition: transform 0.1s; }}
        .duck:active {{ transform: scale(0.94); }}
        .btn {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none; border-radius: 16px; padding: 14px; color: white; font-size: 16px; font-weight: 600; cursor: pointer; width: 100%; margin-top: 12px; }}
        .back-btn {{ background: rgba(255,255,255,0.15); }}
        .energy-bar {{ width: 100%; height: 12px; background: rgba(255,255,255,0.2); border-radius: 6px; margin: 10px 0; overflow: hidden; }}
        .energy-fill {{ height: 100%; background: linear-gradient(90deg, #00ff88, #00cc66); border-radius: 6px; transition: width 0.2s; }}
        .tap-value {{ position: fixed; pointer-events: none; font-size: 28px; font-weight: bold; color: #ffd700; animation: floatUp 0.6s ease-out forwards; z-index: 1000; }}
        @keyframes floatUp {{ 0% {{ opacity: 1; transform: translateY(0) scale(0.8); }} 100% {{ opacity: 0; transform: translateY(-80px) scale(1.2); }} }}
        .skin-list, .booster-list, .case-list, .achievement-list, .leaderboard-list {{ margin: 20px 0; }}
        .skin-item, .booster-item, .case-item, .achievement-item, .leaderboard-item {{ background: rgba(0,0,0,0.3); border-radius: 16px; padding: 12px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }}
        .skin-info, .booster-info, .achievement-info {{ display: flex; align-items: center; gap: 12px; }}
        .skin-emoji, .booster-emoji, .case-emoji, .achievement-emoji {{ font-size: 40px; }}
        .skin-name, .booster-name, .achievement-name {{ font-size: 16px; font-weight: bold; }}
        .skin-price, .booster-price, .case-price, .achievement-desc {{ font-size: 12px; color: #ffd700; }}
        .skin-buy-btn, .booster-buy-btn, .case-open-btn {{ background: #667eea; border: none; border-radius: 12px; padding: 8px 16px; color: white; cursor: pointer; }}
        .case-open-btn {{ background: linear-gradient(135deg, #ffd700, #ff8c00); color: #333; font-weight: bold; }}
        .achievement-completed {{ background: #4caf50; color: white; border-radius: 12px; padding: 4px 12px; font-size: 12px; }}
        .button-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 24px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div id="mainScreen" class="screen active">
            <div class="stats">
                <div class="stat-row"><span class="stat-label">🦆 Уровень</span><span class="stat-value" id="levelValue">{stats["level"]}</span></div>
                <div class="stat-row"><span class="stat-label">💰 Клики</span><span class="stat-value" id="clicksValue">{stats["clicks"]}</span></div>
                <div class="stat-row"><span class="stat-label">💪 Сила клика</span><span class="stat-value" id="tapPowerValue">+{stats["tap_power"]}</span></div>
                <div class="stat-row"><span class="stat-label">⏱️ Пассивный доход</span><span class="stat-value" id="passiveValue">{stats["passive_income"]}/час</span></div>
                <div class="stat-row"><span class="stat-label">💎 Алмазы</span><span class="stat-value" id="gemsValue">{stats["gems"]}</span></div>
                <div class="stat-row"><span class="stat-label">⚡ Энергия</span><span class="stat-value" id="energyValue">{stats["energy"]}/1000</span></div>
            </div>
            <div class="energy-bar"><div class="energy-fill" id="energyFill" style="width: {stats["energy"]/10}%"></div></div>
            <div class="duck-container"><div class="duck" id="duck">{stats["skin"]}</div></div>
            <div class="button-grid">
                <button class="btn" id="upgradeTapBtn">💪 Улучшить тап</button>
                <button class="btn" id="upgradePassiveBtn">💰 Улучшить пассивку</button>
                <button class="btn" id="collectPassiveBtn">💵 Собрать пассивку</button>
                <button class="btn" id="dailyBtn">🎁 Ежедневный</button>
                <button class="btn" id="openShopBtn">👕 Магазин</button>
                <button class="btn" id="openCasesBtn">📦 Кейсы</button>
                <button class="btn" id="openBoostersBtn">⚡ Бустеры</button>
                <button class="btn" id="openAchievementsBtn">🏆 Достижения</button>
                <button class="btn" id="openLeaderboardBtn">🏆 Топ</button>
            </div>
        </div>
        
        <div id="shopScreen" class="screen">
            <h3 style="color: white; text-align: center;">👕 МАГАЗИН СКИНОВ</h3>
            <div id="skinsList" class="skin-list">Загрузка...</div>
            <button class="btn back-btn" onclick="showScreen('mainScreen')">◀️ Назад</button>
        </div>
        
        <div id="casesScreen" class="screen">
            <h3 style="color: white; text-align: center;">📦 КЕЙСЫ</h3>
            <div id="casesList" class="case-list">Загрузка...</div>
            <button class="btn back-btn" onclick="showScreen('mainScreen')">◀️ Назад</button>
        </div>
        
        <div id="boostersScreen" class="screen">
            <h3 style="color: white; text-align: center;">⚡ БУСТЕРЫ</h3>
            <div id="activeBoostersList" class="booster-list">Активные бустеры: загрузка...</div>
            <div id="shopBoostersList" class="booster-list">Доступные бустеры: загрузка...</div>
            <button class="btn back-btn" onclick="showScreen('mainScreen')">◀️ Назад</button>
        </div>
        
        <div id="achievementsScreen" class="screen">
            <h3 style="color: white; text-align: center;">🏆 ДОСТИЖЕНИЯ</h3>
            <div id="achievementsList" class="achievement-list">Загрузка...</div>
            <button class="btn back-btn" onclick="showScreen('mainScreen')">◀️ Назад</button>
        </div>
        
        <div id="leaderboardScreen" class="screen">
            <h3 style="color: white; text-align: center;">🏆 ТОП ИГРОКОВ</h3>
            <div id="leaderboardList" class="leaderboard-list">Загрузка...</div>
            <button class="btn back-btn" onclick="showScreen('mainScreen')">◀️ Назад</button>
        </div>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.ready();
        tg.expand();
        
        const userId = new URLSearchParams(window.location.search).get('user_id') || 1;
        let username = tg.initDataUnsafe?.user?.username || null;
        
        let clicks = parseInt('{stats["clicks"]}');
        let level = parseInt('{stats["level"]}');
        let tapPower = parseInt('{stats["tap_power"]}');
        let passiveIncome = parseInt('{stats["passive_income"]}');
        let energy = parseInt('{stats["energy"]}');
        let gems = parseInt('{stats["gems"]}');
        let maxEnergy = 1000;
        let currentSkin = "{stats["skin"]}";
        
        function showScreen(screenName) {{
            const screens = ['mainScreen', 'shopScreen', 'casesScreen', 'boostersScreen', 'achievementsScreen', 'leaderboardScreen'];
            screens.forEach(s => document.getElementById(s).classList.remove('active'));
            document.getElementById(screenName).classList.add('active');
            if (screenName === 'shopScreen') loadSkins();
            if (screenName === 'casesScreen') loadCases();
            if (screenName === 'boostersScreen') loadBoosters();
            if (screenName === 'achievementsScreen') loadAchievements();
            if (screenName === 'leaderboardScreen') loadLeaderboard();
        }}
        
        function updateUI() {{
            document.getElementById('clicksValue').innerText = clicks;
            document.getElementById('levelValue').innerText = level;
            document.getElementById('tapPowerValue').innerText = '+' + tapPower;
            document.getElementById('passiveValue').innerText = passiveIncome + '/час';
            document.getElementById('gemsValue').innerText = gems;
            document.getElementById('energyValue').innerText = Math.floor(energy) + '/1000';
            document.getElementById('energyFill').style.width = (energy / 10) + '%';
        }}
        
        async function loadStats() {{
            try {{
                let url = '/api/get_stats?user_id=' + userId;
                if (username) url += '&username=' + encodeURIComponent(username);
                const res = await fetch(url);
                const data = await res.json();
                clicks = data.clicks;
                level = data.level;
                tapPower = data.tap_power;
                passiveIncome = data.passive_income;
                energy = data.energy;
                gems = data.gems;
                currentSkin = data.skin;
                updateUI();
                document.getElementById('duck').innerText = currentSkin;
            }} catch(e) {{ console.error(e); }}
        }}
        
        async function loadLeaderboard() {{
            try {{
                const res = await fetch('/api/get_leaderboard?limit=10');
                const data = await res.json();
                const leaderboardList = document.getElementById('leaderboardList');
                leaderboardList.innerHTML = '';
                for (let i = 0; i < data.leaderboard.length; i++) {{
                    const player = data.leaderboard[i];
                    const div = document.createElement('div');
                    div.className = 'leaderboard-item';
                    const medal = i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : '📊';
                    const displayName = player.username && player.username !== String(player.user_id) ? '@' + player.username : '👤 Пользователь ' + player.user_id;
                    div.innerHTML = '<span>' + medal + ' ' + (i+1) + '. ' + displayName + '</span><span>' + player.clicks + ' кликов</span>';
                    leaderboardList.appendChild(div);
                }}
            }} catch(e) {{ console.error(e); }}
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
                    div.innerHTML = 
                        '<div class="achievement-info">' +
                            '<span class="achievement-emoji">' + emoji + '</span>' +
                            '<div><div class="achievement-name">' + ach.name + '</div><div class="achievement-desc">' + ach.description + ' | Награда: +' + ach.reward_gems + '💎 +' + ach.reward_clicks + '💰</div></div>' +
                        '</div>' +
                        (ach.completed ? '<span class="achievement-completed">✅ ВЫПОЛНЕНО</span>' : '<span class="achievement-desc">📋 Не выполнено</span>');
                    achievementsList.appendChild(div);
                }}
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
                    if (skin.owned && skin.equipped) {{
                        div.innerHTML = 
                            '<div class="skin-info">' +
                                '<span class="skin-emoji">' + skin.emoji + '</span>' +
                                '<div><div class="skin-name">' + skin.name + '</div><div class="skin-price">+' + skin.bonus + ' к силе ✅ ЭКИПИРОВАН</div></div>' +
                            '</div>';
                    }} else if (skin.owned) {{
                        div.innerHTML = 
                            '<div class="skin-info">' +
                                '<span class="skin-emoji">' + skin.emoji + '</span>' +
                                '<div><div class="skin-name">' + skin.name + '</div><div class="skin-price">+' + skin.bonus + ' к силе (КУПЛЕН)</div></div>' +
                            '</div>' +
                            '<button class="skin-buy-btn" onclick="equipSkin(' + skin.id + ')">⚡ ЭКИПИРОВАТЬ</button>';
                    }} else {{
                        div.innerHTML = 
                            '<div class="skin-info">' +
                                '<span class="skin-emoji">' + skin.emoji + '</span>' +
                                '<div><div class="skin-name">' + skin.name + '</div><div class="skin-price">+' + skin.bonus + ' к силе | Цена: ' + skin.price + ' кликов</div></div>' +
                            '</div>' +
                            '<button class="skin-buy-btn" onclick="buySkin(' + skin.id + ')">💎 КУПИТЬ</button>';
                    }}
                    skinsList.appendChild(div);
                }}
            }} catch(e) {{ console.error(e); }}
        }}
        
        async function loadCases() {{
            try {{
                const res = await fetch('/api/get_cases');
                const data = await res.json();
                const casesList = document.getElementById('casesList');
                casesList.innerHTML = '';
                for (const caseItem of data.cases) {{
                    const div = document.createElement('div');
                    div.className = 'case-item';
                    div.innerHTML = 
                        '<div class="skin-info">' +
                            '<span class="case-emoji">' + caseItem.emoji + '</span>' +
                            '<div><div class="skin-name">' + caseItem.name + '</div><div class="case-price">Цена: ' + caseItem.price + ' кликов</div></div>' +
                        '</div>' +
                        '<button class="case-open-btn" onclick="openCase(' + caseItem.id + ')">🎲 ОТКРЫТЬ</button>';
                    casesList.appendChild(div);
                }}
            }} catch(e) {{ console.error(e); }}
        }}
        
        async function loadBoosters() {{
            try {{
                const res = await fetch('/api/get_boosters?user_id=' + userId);
                const data = await res.json();
                
                const activeDiv = document.getElementById('activeBoostersList');
                if (data.active_boosters.length > 0) {{
                    activeDiv.innerHTML = '<h4 style="color: #ffd700;">⚡ АКТИВНЫЕ БУСТЕРЫ:</h4>';
                    for (const b of data.active_boosters) {{
                        activeDiv.innerHTML += 
                            '<div class="booster-item">' +
                                '<div class="booster-info">' +
                                    '<span class="booster-emoji">' + b.emoji + '</span>' +
                                    '<div><div class="booster-name">' + b.name + '</div><div class="booster-price">' + b.description + ' | Осталось: ' + b.minutes_left + ' мин</div></div>' +
                                '</div>' +
                            '</div>';
                    }}
                }} else {{
                    activeDiv.innerHTML = '<div style="text-align: center; padding: 20px; color: #aaa;">Нет активных бустеров</div>';
                }}
                
                const shopDiv = document.getElementById('shopBoostersList');
                shopDiv.innerHTML = '<h4 style="color: #ffd700;">💎 ДОСТУПНЫЕ БУСТЕРЫ:</h4>';
                for (const b of data.shop_boosters) {{
                    shopDiv.innerHTML += 
                        '<div class="booster-item">' +
                            '<div class="booster-info">' +
                                '<span class="booster-emoji">' + b.emoji + '</span>' +
                                '<div><div class="booster-name">' + b.name + '</div><div class="booster-price">' + b.description + ' | Цена: ' + b.price + ' кликов</div></div>' +
                            '</div>' +
                            '<button class="booster-buy-btn" onclick="buyBooster(' + b.id + ')">💎 КУПИТЬ</button>' +
                        '</div>';
                }}
            }} catch(e) {{ console.error(e); }}
        }}
        
        async function buySkin(skinId) {{
            const res = await fetch('/api/buy_skin?user_id=' + userId + '&skin_id=' + skinId, {{method: 'POST'}});
            const data = await res.json();
            if (data.success) {{
                tg.showPopup({{title: '✅ Покупка успешна!', message: 'Вы купили ' + data.skin_name + ' ' + data.skin_emoji, buttons: [{{type: 'ok'}}]}});
                await loadStats();
                await loadSkins();
            }} else {{
                tg.showPopup({{title: '❌ Не хватает кликов', message: 'Нужно: ' + data.need + ' кликов', buttons: [{{type: 'ok'}}]}});
            }}
        }}
        
        async function equipSkin(skinId) {{
            const res = await fetch('/api/equip_skin?user_id=' + userId + '&skin_id=' + skinId, {{method: 'POST'}});
            const data = await res.json();
            if (data.success) {{
                tg.showPopup({{title: '✅ Скин экипирован!', message: 'Теперь ваша утка: ' + data.skin, buttons: [{{type: 'ok'}}]}});
                await loadStats();
                await loadSkins();
            }}
        }}
        
        async function openCase(caseId) {{
            const res = await fetch('/api/open_case?user_id=' + userId + '&case_id=' + caseId, {{method: 'POST'}});
            const data = await res.json();
            if (data.success) {{
                tg.showPopup({{title: '🎁 Открытие кейса!', message: data.case_emoji + ' Вы получили: ' + data.reward_text, buttons: [{{type: 'ok'}}]}});
                await loadStats();
            }} else {{
                tg.showPopup({{title: '❌ Не хватает кликов', message: 'Нужно: ' + data.need + ' кликов', buttons: [{{type: 'ok'}}]}});
            }}
        }}
        
        async function buyBooster(boosterId) {{
            const res = await fetch('/api/buy_booster?user_id=' + userId + '&booster_id=' + boosterId, {{method: 'POST'}});
            const data = await res.json();
            if (data.success) {{
                tg.showPopup({{title: '✅ Бустер активирован!', message: data.booster_emoji + ' ' + data.booster_name + ' активирован!', buttons: [{{type: 'ok'}}]}});
                await loadStats();
                await loadBoosters();
            }} else {{
                tg.showPopup({{title: '❌ Не хватает кликов', message: 'Нужно: ' + data.need + ' кликов', buttons: [{{type: 'ok'}}]}});
            }}
        }}
        
        async function sendClick() {{
            try {{
                const res = await fetch('/api/click', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ user_id: userId, clicks: tapPower }})
                }});
                const data = await res.json();
                clicks = data.clicks;
                level = data.level;
                tapPower = data.tap_power;
                passiveIncome = data.passive_income;
                energy = data.energy;
                gems = data.gems;
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
            await sendClick();
        }};
        
        document.getElementById('upgradeTapBtn').onclick = async () => {{
            const price = tapPower * 100;
            if (clicks >= price) {{
                const res = await fetch('/api/upgrade_tap?user_id=' + userId, {{method: 'POST'}});
                const data = await res.json();
                if (data.success) {{
                    tg.showPopup({{title: '✅ Улучшено!', message: 'Сила клика: +' + data.new_tap_power, buttons: [{{type: 'ok'}}]}});
                    await loadStats();
                }}
            }} else {{
                tg.showPopup({{title: '❌ Не хватает кликов', message: 'Нужно: ' + price + ' кликов', buttons: [{{type: 'ok'}}]}});
            }}
        }};
        
        document.getElementById('upgradePassiveBtn').onclick = async () => {{
            const price = 500 + passiveIncome * 100;
            if (clicks >= price) {{
                const res = await fetch('/api/upgrade_passive?user_id=' + userId, {{method: 'POST'}});
                const data = await res.json();
                if (data.success) {{
                    tg.showPopup({{title: '✅ Пассивный доход улучшен!', message: 'Теперь +' + data.new_passive + '/час', buttons: [{{type: 'ok'}}]}});
                    await loadStats();
                }}
            }} else {{
                tg.showPopup({{title: '❌ Не хватает кликов', message: 'Нужно: ' + price + ' кликов', buttons: [{{type: 'ok'}}]}});
            }}
        }};
        
        document.getElementById('collectPassiveBtn').onclick = async () => {{
            if (passiveIncome > 0) {{
                const res = await fetch('/api/collect_passive?user_id=' + userId, {{method: 'POST'}});
                const data = await res.json();
                if (data.success) {{
                    tg.showPopup({{title: '💰 Получено!', message: '+' + data.earned + ' кликов!', buttons: [{{type: 'ok'}}]}});
                    await loadStats();
                }}
            }} else {{
                tg.showPopup({{title: '😴 Нет дохода', message: 'Сначала улучши пассивный доход', buttons: [{{type: 'ok'}}]}});
            }}
        }};
        
        document.getElementById('dailyBtn').onclick = async () => {{
            const res = await fetch('/api/claim_daily?user_id=' + userId, {{method: 'POST'}});
            const data = await res.json();
            if (data.success) {{
                tg.showPopup({{title: '🎁 Бонус получен!', message: '+' + data.bonus + ' кликов! Серия: ' + data.streak, buttons: [{{type: 'ok'}}]}});
                await loadStats();
            }} else {{
                tg.showPopup({{title: '❌ Уже забирал', message: data.message, buttons: [{{type: 'ok'}}]}});
            }}
        }};
        
        document.getElementById('openShopBtn').onclick = () => showScreen('shopScreen');
        document.getElementById('openCasesBtn').onclick = () => showScreen('casesScreen');
        document.getElementById('openBoostersBtn').onclick = () => showScreen('boostersScreen');
        document.getElementById('openAchievementsBtn').onclick = () => showScreen('achievementsScreen');
        document.getElementById('openLeaderboardBtn').onclick = () => showScreen('leaderboardScreen');
        
        setInterval(() => {{
            if (energy < maxEnergy) {{
                energy = Math.min(energy + 1, maxEnergy);
                updateUI();
            }}
        }}, 2000);
        
        loadStats();
    </script>
</body>
</html>'''
    
    return HTMLResponse(content=html)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)