import os
import sqlite3
import random
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

app = FastAPI()

class ClickData(BaseModel):
    user_id: int
    clicks: int

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
            daily_streak INTEGER DEFAULT 0,
            gems INTEGER DEFAULT 0,
            total_gems INTEGER DEFAULT 0
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
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_skins (
            user_id INTEGER,
            skin_id INTEGER,
            PRIMARY KEY (user_id, skin_id)
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
            reward_clicks INTEGER,
            reward_skin_id INTEGER DEFAULT NULL
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
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            emoji TEXT,
            price_gems INTEGER,
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
            price_gems INTEGER,
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
    
    conn.commit()
    
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
            (case_id, "gems", 5, "5 алмазов 💎", 15),
            (case_id, "gems", 10, "10 алмазов 💎", 10),
            (case_id, "booster", 2, "x2 клика (1 час)", 5),
            (case_id, "skin", 3, "Киберутка 🤖", 3),
        ]
        cursor.executemany(
            "INSERT INTO case_rewards (case_id, reward_type, reward_value, reward_text, chance) VALUES (?, ?, ?, ?, ?)",
            rewards
        )
    
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

def get_user_stats(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT clicks, level, energy, tap_power, passive_income, current_skin, total_clicks, daily_streak, gems FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            "clicks": result[0],
            "level": result[1],
            "energy": result[2],
            "tap_power": result[3],
            "passive_income": result[4],
            "skin": result[5] if result[5] else "🦆",
            "total_clicks": result[6],
            "daily_streak": result[7],
            "gems": result[8]
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

@app.get("/api/get_achievements")
async def get_achievements_list(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, condition_value, reward_gems, reward_clicks FROM achievements")
    achievements = cursor.fetchall()
    
    result = []
    for ach in achievements:
        ach_id, name, desc, condition, reward_gems, reward_clicks = ach
        cursor.execute("SELECT completed FROM user_achievements WHERE user_id = ? AND achievement_id = ?", (user_id, ach_id))
        completed = cursor.fetchone()
        result.append({
            "id": ach_id,
            "name": name,
            "description": desc,
            "condition": condition,
            "reward_gems": reward_gems,
            "reward_clicks": reward_clicks,
            "completed": completed[0] if completed else 0
        })
    conn.close()
    return {"achievements": result}

@app.get("/api/get_stats")
async def get_stats(user_id: int):
    stats = get_user_stats(user_id)
    boosters = get_active_boosters(user_id)
    tap_multiplier = get_booster_multiplier(user_id)
    return {
        "clicks": stats["clicks"],
        "level": stats["level"],
        "energy": stats["energy"],
        "tap_power": stats["tap_power"],
        "passive_income": stats["passive_income"],
        "skin": stats["skin"],
        "total_clicks": stats["total_clicks"],
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
        "energy": stats["energy"],
        "tap_power": stats["tap_power"],
        "passive_income": stats["passive_income"],
        "gems": stats["gems"]
    }

@app.get("/health")
async def health():
    return {"status": "ok"}

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
        .tap-value {{ position: fixed; pointer-events: none; font-size: 28px; font-weight: bold; color: #ffd700; animation: floatUp 0.6s ease-out forwards; z-index: 1000; }}
        @keyframes floatUp {{ 0% {{ opacity: 1; transform: translateY(0) scale(0.8); }} 100% {{ opacity: 0; transform: translateY(-80px) scale(1.2); }} }}
        .energy-bar {{ width: 100%; height: 12px; background: rgba(255,255,255,0.2); border-radius: 6px; margin: 10px 0; overflow: hidden; }}
        .energy-fill {{ height: 100%; background: linear-gradient(90deg, #00ff88, #00cc66); border-radius: 6px; transition: width 0.2s; }}
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
            </div>
            <div class="energy-bar"><div class="energy-fill" id="energyFill" style="width: {stats["energy"]/10}%"></div></div>
            <div class="duck-container"><div class="duck" id="duck">🦆</div></div>
            <div class="button-grid">
                <button class="action-btn" id="upgradeTapBtn">💪 Улучшить тап</button>
                <button class="action-btn" id="upgradePassiveBtn">💰 Улучшить пассивку</button>
                <button class="action-btn" id="collectPassiveBtn">💵 Собрать пассивку</button>
                <button class="action-btn" id="dailyBtn">🎁 Ежедневный</button>
                <button class="action-btn" id="openShopBtn">👕 Магазин</button>
                <button class="action-btn" id="openCasesBtn">📦 Кейсы</button>
                <button class="action-btn" id="openBoostersBtn">⚡ Бустеры</button>
                <button class="action-btn" id="openAchievementsBtn">🏆 Достижения</button>
                <button class="action-btn" id="openReferralBtn">👥 Рефералы</button>
                <button class="action-btn" id="profileBtn">📊 Профиль</button>
            </div>
            <button class="action-btn full-width" id="closeBtn">✖️ Закрыть</button>
        </div>
        
        <div id="profileScreen" class="screen">
            <h3 style="color: white; text-align: center; margin-bottom: 20px;">📊 ПРОФИЛЬ</h3>
            <div class="stats">
                <div class="stat-row"><span class="stat-label">🦆 Уровень</span><span class="stat-value" id="profileLevel">{stats["level"]}</span></div>
                <div class="stat-row"><span class="stat-label">💰 Всего кликов</span><span class="stat-value" id="profileTotalClicks">{stats["total_clicks"]}</span></div>
                <div class="stat-row"><span class="stat-label">💪 Сила клика</span><span class="stat-value" id="profileTapPower">+{stats["tap_power"]}</span></div>
                <div class="stat-row"><span class="stat-label">⏱️ Пассивный доход</span><span class="stat-value" id="profilePassive">{stats["passive_income"]}/час</span></div>
                <div class="stat-row"><span class="stat-label">💎 Алмазы</span><span class="stat-value" id="profileGems">{stats["gems"]}</span></div>
                <div class="stat-row"><span class="stat-label">📅 Серия входов</span><span class="stat-value" id="profileStreak">{stats["daily_streak"]}</span></div>
                <div class="stat-row"><span class="stat-label">🎨 Скин</span><span class="stat-value" id="profileSkin">{stats["skin"]}</span></div>
            </div>
            <button class="action-btn full-width back-btn" onclick="showScreen('mainScreen')">◀️ Назад</button>
        </div>
        
        <div id="shopScreen" class="screen">
            <h3 style="color: white; text-align: center; margin-bottom: 20px;">👕 МАГАЗИН СКИНОВ</h3>
            <div id="skinsList" class="skin-list">Загрузка...</div>
            <button class="action-btn full-width back-btn" onclick="showScreen('mainScreen')">◀️ Назад</button>
        </div>
        
        <div id="casesScreen" class="screen">
            <h3 style="color: white; text-align: center; margin-bottom: 20px;">📦 КЕЙСЫ</h3>
            <div id="casesList" class="case-list">Загрузка...</div>
            <button class="action-btn full-width back-btn" onclick="showScreen('mainScreen')">◀️ Назад</button>
        </div>
        
        <div id="boostersScreen" class="screen">
            <h3 style="color: white; text-align: center; margin-bottom: 20px;">⚡ БУСТЕРЫ</h3>
            <div id="activeBoostersList" class="booster-list">Загрузка...</div>
            <div id="shopBoostersList" class="booster-list">Загрузка...</div>
            <button class="action-btn full-width back-btn" onclick="showScreen('mainScreen')">◀️ Назад</button>
        </div>
        
        <div id="achievementsScreen" class="screen">
            <h3 style="color: white; text-align: center; margin-bottom: 20px;">🏆 ДОСТИЖЕНИЯ</h3>
            <div id="achievementsList" class="achievement-list">Загрузка...</div>
            <button class="action-btn full-width back-btn" onclick="showScreen('mainScreen')">◀️ Назад</button>
        </div>
        
        <div id="referralScreen" class="screen">
            <h3 style="color: white; text-align: center; margin-bottom: 20px;">👥 РЕФЕРАЛЫ</h3>
            <div class="stats">
                <div class="stat-row"><span class="stat-label">👥 Приглашено друзей</span><span class="stat-value" id="referralCount">0</span></div>
                <div class="stat-row"><span class="stat-label">🎁 Не получено наград</span><span class="stat-value" id="unclaimedRewards">0</span></div>
            </div>
            <div style="background: rgba(0,0,0,0.3); border-radius: 16px; padding: 12px; margin-bottom: 20px;">
                <div style="color: #aaa; font-size: 12px; margin-bottom: 8px;">🔗 Твоя реферальная ссылка:</div>
                <div id="referralLink" style="color: #ffd700; font-size: 12px; word-break: break-all;"></div>
                <button class="action-btn full-width" id="copyReferralBtn" style="margin-top: 10px; background: #4caf50;">📋 Копировать ссылку</button>
            </div>
            <button class="action-btn full-width" id="claimReferralBtn" style="margin-bottom: 10px;">🎁 Забрать награду</button>
            <button class="action-btn full-width back-btn" onclick="showScreen('mainScreen')">◀️ Назад</button>
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
            const screens = ['mainScreen', 'profileScreen', 'shopScreen', 'casesScreen', 'boostersScreen', 'achievementsScreen', 'referralScreen'];
            screens.forEach(s => document.getElementById(s).classList.remove('active'));
            document.getElementById(screenName).classList.add('active');
            
            if (screenName === 'shopScreen') loadSkins();
            if (screenName === 'casesScreen') loadCases();
            if (screenName === 'boostersScreen') loadBoosters();
            if (screenName === 'achievementsScreen') loadAchievements();
            if (screenName === 'referralScreen') loadReferralData();
        }}
        
        function updateUI() {{
            document.getElementById('clicksValue').innerText = clicks;
            document.getElementById('levelValue').innerText = level;
            document.getElementById('tapPowerValue').innerText = '+' + tapPower;
            document.getElementById('passiveValue').innerText = passiveIncome + '/час';
            document.getElementById('gemsValue').innerText = gems;
            document.getElementById('energyFill').style.width = (energy / 10) + '%';
            
            if (document.getElementById('profileLevel')) document.getElementById('profileLevel').innerText = level;
            if (document.getElementById('profileTapPower')) document.getElementById('profileTapPower').innerText = '+' + tapPower;
            if (document.getElementById('profilePassive')) document.getElementById('profilePassive').innerText = passiveIncome + '/час';
            if (document.getElementById('profileSkin')) document.getElementById('profileSkin').innerText = currentSkin;
            if (document.getElementById('profileGems')) document.getElementById('profileGems').innerText = gems;
            if (document.getElementById('profileTotalClicks')) document.getElementById('profileTotalClicks').innerText = '{stats["total_clicks"]}';
            if (document.getElementById('profileStreak')) document.getElementById('profileStreak').innerText = '{stats["daily_streak"]}';
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
                document.getElementById('duck').innerText = currentSkin;
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
                    div.innerHTML = 
                        '<div class="skin-info">' +
                            '<span class="skin-emoji">' + skin.emoji + '</span>' +
                            '<div>' +
                                '<div class="skin-name">' + skin.name + '</div>' +
                                '<div class="skin-price">+' + skin.bonus + ' к силе | ' + limitedText + '</div>' +
                            '</div>' +
                        '</div>' +
                        '<div>' + paymentOptions + '</div>';
                    skinsList.appendChild(div);
                }}
            }} catch(e) {{ console.error(e); }}
        }}
        
        async function loadCases() {{
            try {{
                const res = await fetch('/api/get_cases?user_id=' + userId);
                const data = await res.json();
                const casesList = document.getElementById('casesList');
                casesList.innerHTML = '';
                for (const caseItem of data.cases) {{
                    let priceText = caseItem.price_clicks > 0 ? caseItem.price_clicks + ' кликов' : caseItem.price_gems + ' алмазов';
                    const div = document.createElement('div');
                    div.className = 'case-container';
                    div.innerHTML = 
                        '<div class="case-box" onclick="openCase(' + caseItem.id + ')">' +
                            '<div class="case-emoji">' + caseItem.emoji + '</div>' +
                            '<div class="case-price">' + caseItem.name + '<br>' + priceText + '</div>' +
                        '</div>';
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
                    activeDiv.innerHTML = '<h4 style="color: #ffd700; margin-bottom: 10px;">⚡ АКТИВНЫЕ БУСТЕРЫ:</h4>';
                    for (const b of data.active_boosters) {{
                        activeDiv.innerHTML += 
                            '<div class="booster-item">' +
                                '<div class="booster-info">' +
                                    '<span class="booster-emoji">' + b.emoji + '</span>' +
                                    '<div>' +
                                        '<div class="booster-name">' + b.name + '</div>' +
                                        '<div class="booster-price">' + b.description + ' | Осталось: ' + b.minutes_left + ' мин</div>' +
                                    '</div>' +
                                '</div>' +
                            '</div>';
                    }}
                }} else {{
                    activeDiv.innerHTML = '<div style="text-align: center; padding: 20px; color: #aaa;">Нет активных бустеров</div>';
                }}
                const shopDiv = document.getElementById('shopBoostersList');
                shopDiv.innerHTML = '<h4 style="color: #ffd700; margin-bottom: 10px;">💎 ДОСТУПНЫЕ БУСТЕРЫ:</h4>';
                for (const b of data.shop_boosters) {{
                    let priceText = b.price_clicks > 0 ? b.price_clicks + ' кликов' : b.price_gems + ' алмазов';
                    shopDiv.innerHTML += 
                        '<div class="booster-item">' +
                            '<div class="booster-info">' +
                                '<span class="booster-emoji">' + b.emoji + '</span>' +
                                '<div>' +
                                    '<div class="booster-name">' + b.name + '</div>' +
                                    '<div class="booster-price">' + b.description + ' | Цена: ' + priceText + '</div>' +
                                '</div>' +
                            '</div>' +
                            '<button class="booster-btn" onclick="buyBooster(' + b.id + ')">💎 КУПИТЬ</button>' +
                        '</div>';
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
                    let statusText = ach.completed ? '<span class="achievement-completed">✅ ВЫПОЛНЕНО</span>' : '<span class="achievement-desc">📋 Не выполнено</span>';
                    div.innerHTML = 
                        '<div class="achievement-info">' +
                            '<span class="achievement-emoji">' + emoji + '</span>' +
                            '<div>' +
                                '<div class="achievement-name">' + ach.name + '</div>' +
                                '<div class="achievement-desc">' + ach.description + ' (' + ach.condition + ')</div>' +
                                '<div class="achievement-desc">🎁 Награда: +' + ach.reward_gems + '💎 +' + ach.reward_clicks + '💰</div>' +
                            '</div>' +
                        '</div>' +
                        statusText;
                    achievementsList.appendChild(div);
                }}
            }} catch(e) {{ console.error(e); }}
        }}
        
        async function loadReferralData() {{
            try {{
                const res = await fetch('/api/get_referrals?user_id=' + userId);
                const data = await res.json();
                document.getElementById('referralCount').innerText = data.count;
                document.getElementById('unclaimedRewards').innerText = data.unclaimed;
                const botUsername = tg.initDataUnsafe?.user?.username || 'ZetaClickerRobot';
                const referralLink = 'https://t.me/' + botUsername + '?start=ref_' + userId;
                document.getElementById('referralLink').innerText = referralLink;
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
            await sendClick();
        }};
        
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