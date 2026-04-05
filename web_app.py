import os
import asyncpg
import random
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

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

DATABASE_URL = os.environ.get("DATABASE_URL", "")

async def init_db():
    conn = await asyncpg.connect(DATABASE_URL)
    
    # Создание таблиц (без изменений)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT DEFAULT NULL,
            clicks BIGINT DEFAULT 0,
            level INTEGER DEFAULT 1,
            energy INTEGER DEFAULT 1000,
            tap_power INTEGER DEFAULT 1,
            passive_income INTEGER DEFAULT 0,
            current_skin TEXT DEFAULT '🦆',
            total_clicks BIGINT DEFAULT 0,
            last_daily TIMESTAMP DEFAULT NULL,
            daily_streak INTEGER DEFAULT 0,
            gems INTEGER DEFAULT 0
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS skins (
            id SERIAL PRIMARY KEY,
            name TEXT,
            emoji TEXT,
            price_clicks INTEGER,
            tap_bonus INTEGER DEFAULT 0
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS user_skins (
            user_id BIGINT,
            skin_id INTEGER,
            PRIMARY KEY (user_id, skin_id)
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id SERIAL PRIMARY KEY,
            name TEXT,
            emoji TEXT,
            price_clicks INTEGER
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS case_rewards (
            id SERIAL PRIMARY KEY,
            case_id INTEGER,
            reward_type TEXT,
            reward_value INTEGER,
            reward_text TEXT,
            chance INTEGER
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS boosters (
            id SERIAL PRIMARY KEY,
            name TEXT,
            emoji TEXT,
            description TEXT,
            effect_type TEXT,
            effect_value REAL,
            duration_minutes INTEGER,
            price_clicks INTEGER
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS user_boosters (
            user_id BIGINT,
            booster_id INTEGER,
            expires_at TIMESTAMP,
            PRIMARY KEY (user_id, booster_id)
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            id SERIAL PRIMARY KEY,
            name TEXT,
            description TEXT,
            condition_type TEXT,
            condition_value INTEGER,
            reward_gems INTEGER,
            reward_clicks INTEGER
        )
    """)
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
    
        # Исправленные INSERT (без ON CONFLICT, так как таблица новая)
    # Сначала проверяем, есть ли данные
    count = await conn.fetchval("SELECT COUNT(*) FROM skins")
    if count == 0:
        await conn.execute("INSERT INTO skins (name, emoji, price_clicks, tap_bonus) VALUES ($1, $2, $3, $4)",
                           'Обычная утка', '🦆', 0, 0)
        await conn.execute("INSERT INTO skins (name, emoji, price_clicks, tap_bonus) VALUES ($1, $2, $3, $4)",
                           'Золотая утка', '🌟', 5000, 2)
        await conn.execute("INSERT INTO skins (name, emoji, price_clicks, tap_bonus) VALUES ($1, $2, $3, $4)",
                           'Киберутка', '🤖', 15000, 5)
        await conn.execute("INSERT INTO skins (name, emoji, price_clicks, tap_bonus) VALUES ($1, $2, $3, $4)",
                           'Утка-призрак', '👻', 30000, 10)
        await conn.execute("INSERT INTO skins (name, emoji, price_clicks, tap_bonus) VALUES ($1, $2, $3, $4)",
                           'Дьявольская утка', '😈', 50000, 15)
    
    count = await conn.fetchval("SELECT COUNT(*) FROM cases")
    if count == 0:
        await conn.execute("INSERT INTO cases (name, emoji, price_clicks) VALUES ($1, $2, $3)",
                           'Обычный кейс', '📦', 1000)
        await conn.execute("INSERT INTO cases (name, emoji, price_clicks) VALUES ($1, $2, $3)",
                           'Серебряный кейс', '🥈', 5000)
        await conn.execute("INSERT INTO cases (name, emoji, price_clicks) VALUES ($1, $2, $3)",
                           'Алмазный кейс', '💎', 15000)
    
    count = await conn.fetchval("SELECT COUNT(*) FROM boosters")
    if count == 0:
        await conn.execute("INSERT INTO boosters (name, emoji, description, effect_type, effect_value, duration_minutes, price_clicks) VALUES ($1, $2, $3, $4, $5, $6, $7)",
                           'x2 Клики', '⚡', 'Удваивает силу клика на 30 минут', 'tap_multiplier', 2, 30, 5000)
        await conn.execute("INSERT INTO boosters (name, emoji, description, effect_type, effect_value, duration_minutes, price_clicks) VALUES ($1, $2, $3, $4, $5, $6, $7)",
                           'Энергетик', '🔋', 'Восстанавливает 500 энергии', 'energy', 500, 0, 2000)
    
    count = await conn.fetchval("SELECT COUNT(*) FROM achievements")
    if count == 0:
        await conn.execute("INSERT INTO achievements (name, description, condition_type, condition_value, reward_gems, reward_clicks) VALUES ($1, $2, $3, $4, $5, $6)",
                           'Новичок', 'Накликать 100 кликов', 'clicks', 100, 1, 500)
        await conn.execute("INSERT INTO achievements (name, description, condition_type, condition_value, reward_gems, reward_clicks) VALUES ($1, $2, $3, $4, $5, $6)",
                           'Серебряный палец', 'Накликать 1000 кликов', 'clicks', 1000, 2, 2000)
        await conn.execute("INSERT INTO achievements (name, description, condition_type, condition_value, reward_gems, reward_clicks) VALUES ($1, $2, $3, $4, $5, $6)",
                           'Золотой палец', 'Накликать 10000 кликов', 'clicks', 10000, 5, 10000)
        await conn.execute("INSERT INTO achievements (name, description, condition_type, condition_value, reward_gems, reward_clicks) VALUES ($1, $2, $3, $4, $5, $6)",
                           'Коллекционер', 'Купить 1 скин', 'skins', 1, 1, 500)
        await conn.execute("INSERT INTO achievements (name, description, condition_type, condition_value, reward_gems, reward_clicks) VALUES ($1, $2, $3, $4, $5, $6)",
                           'Магнат', 'Купить 3 скина', 'skins', 3, 3, 2000)
        await conn.execute("INSERT INTO achievements (name, description, condition_type, condition_value, reward_gems, reward_clicks) VALUES ($1, $2, $3, $4, $5, $6)",
                           'Везунчик', 'Открыть 5 кейсов', 'cases', 5, 3, 3000)
        await conn.execute("INSERT INTO achievements (name, description, condition_type, condition_value, reward_gems, reward_clicks) VALUES ($1, $2, $3, $4, $5, $6)",
                           'Азартный', 'Открыть 20 кейсов', 'cases', 20, 10, 10000)
    
    await conn.close()

async def get_user_stats(user_id: int, username: str = None):
    conn = await asyncpg.connect(DATABASE_URL)
    result = await conn.fetchrow("SELECT clicks, level, energy, tap_power, passive_income, current_skin, total_clicks, daily_streak, gems, username FROM users WHERE user_id = $1", user_id)
    if result:
        if username and result['username'] != username:
            await conn.execute("UPDATE users SET username = $1 WHERE user_id = $2", username, user_id)
        await conn.close()
        return {
            "clicks": result['clicks'], "level": result['level'], "energy": result['energy'],
            "tap_power": result['tap_power'], "passive_income": result['passive_income'],
            "skin": result['current_skin'], "total_clicks": result['total_clicks'],
            "daily_streak": result['daily_streak'], "gems": result['gems'],
            "username": result['username'] or str(user_id)
        }
    else:
        await conn.execute("INSERT INTO users (user_id, username, clicks, level, energy, tap_power, passive_income, current_skin, total_clicks, daily_streak, gems) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)",
                           user_id, username or str(user_id), 0, 1, 1000, 1, 0, "🦆", 0, 0, 0)
        await conn.close()
        return {"clicks": 0, "level": 1, "energy": 1000, "tap_power": 1, "passive_income": 0, "skin": "🦆", "total_clicks": 0, "daily_streak": 0, "gems": 0, "username": username or str(user_id)}

async def update_clicks(user_id: int, increment: int):
    conn = await asyncpg.connect(DATABASE_URL)
    result = await conn.fetchrow("SELECT clicks, total_clicks, level, energy FROM users WHERE user_id = $1", user_id)
    if result:
        new_clicks = result['clicks'] + increment
        new_total = result['total_clicks'] + increment
        new_energy = result['energy'] - 1 if result['energy'] > 0 else 0
        new_level = 1 + new_total // 100
        await conn.execute("UPDATE users SET clicks = $1, total_clicks = $2, level = $3, energy = $4 WHERE user_id = $5",
                           new_clicks, new_total, new_level, new_energy, user_id)
    await conn.close()

async def add_gems(user_id: int, amount: int):
    conn = await asyncpg.connect(DATABASE_URL)
    result = await conn.fetchrow("SELECT gems FROM users WHERE user_id = $1", user_id)
    if result:
        await conn.execute("UPDATE users SET gems = $1 WHERE user_id = $2", result['gems'] + amount, user_id)
    await conn.close()

async def get_active_boosters(user_id: int):
    conn = await asyncpg.connect(DATABASE_URL)
    now = datetime.now()  # ← объект datetime, а не строка!
    result = await conn.fetch("""
        SELECT b.id, b.name, b.emoji, b.description, b.effect_type, b.effect_value, b.duration_minutes,
               EXTRACT(EPOCH FROM (ub.expires_at - $1::timestamp)) / 60 as minutes_left
        FROM user_boosters ub
        JOIN boosters b ON ub.booster_id = b.id
        WHERE ub.user_id = $2 AND ub.expires_at > $1
    """, now, user_id)
    await conn.close()
    return [{"id": r['id'], "name": r['name'], "emoji": r['emoji'], "description": r['description'],
             "effect_type": r['effect_type'], "effect_value": r['effect_value'], "minutes_left": int(r['minutes_left'] or 0)} for r in result]

async def get_booster_multiplier(user_id: int):
    boosters = await get_active_boosters(user_id)
    multiplier = 1.0
    for b in boosters:
        if b["effect_type"] == "tap_multiplier":
            multiplier *= b["effect_value"]
    return multiplier

async def check_achievements(user_id: int, condition_type: str, current_value: int):
    conn = await asyncpg.connect(DATABASE_URL)
    achievements = await conn.fetch("SELECT id, condition_value, reward_gems, reward_clicks FROM achievements WHERE condition_type = $1", condition_type)
    for ach in achievements:
        completed = await conn.fetchval("SELECT completed FROM user_achievements WHERE user_id = $1 AND achievement_id = $2", user_id, ach['id'])
        if not completed and current_value >= ach['condition_value']:
            await conn.execute("INSERT INTO user_achievements (user_id, achievement_id, progress, completed, completed_at) VALUES ($1, $2, $3, $4, $5)",
                               user_id, ach['id'], ach['condition_value'], 1, datetime.now())
            if ach['reward_gems'] > 0:
                await add_gems(user_id, ach['reward_gems'])
            if ach['reward_clicks'] > 0:
                await conn.execute("UPDATE users SET clicks = clicks + $1 WHERE user_id = $2", ach['reward_clicks'], user_id)
    await conn.close()

@app.on_event("startup")
async def startup():
    await init_db()

@app.post("/api/click")
async def handle_click(data: ClickData):
    multiplier = await get_booster_multiplier(data.user_id)
    final_clicks = int(data.clicks * multiplier)
    await update_clicks(data.user_id, final_clicks)
    stats = await get_user_stats(data.user_id)
    await check_achievements(data.user_id, "clicks", stats["total_clicks"])
    return {
        "clicks": stats["clicks"], "level": stats["level"], "energy": stats["energy"],
        "tap_power": stats["tap_power"], "passive_income": stats["passive_income"], "gems": stats["gems"]
    }

@app.post("/api/upgrade_tap")
async def upgrade_tap(user_id: int):
    stats = await get_user_stats(user_id)
    price = stats["tap_power"] * 100
    if stats["clicks"] >= price:
        conn = await asyncpg.connect(DATABASE_URL)
        new_clicks = stats["clicks"] - price
        new_tap_power = stats["tap_power"] + 1
        await conn.execute("UPDATE users SET clicks = $1, tap_power = $2 WHERE user_id = $3", new_clicks, new_tap_power, user_id)
        await conn.close()
        return {"success": True, "new_tap_power": new_tap_power}
    return {"success": False, "need": price}

@app.post("/api/upgrade_passive")
async def upgrade_passive(user_id: int):
    stats = await get_user_stats(user_id)
    price = 500 + stats["passive_income"] * 100
    if stats["clicks"] >= price:
        conn = await asyncpg.connect(DATABASE_URL)
        new_clicks = stats["clicks"] - price
        new_passive = stats["passive_income"] + 5
        await conn.execute("UPDATE users SET clicks = $1, passive_income = $2 WHERE user_id = $3", new_clicks, new_passive, user_id)
        await conn.close()
        return {"success": True, "new_passive": new_passive}
    return {"success": False, "need": price}

@app.post("/api/collect_passive")
async def collect_passive(user_id: int):
    stats = await get_user_stats(user_id)
    if stats["passive_income"] > 0:
        conn = await asyncpg.connect(DATABASE_URL)
        new_clicks = stats["clicks"] + stats["passive_income"]
        await conn.execute("UPDATE users SET clicks = $1 WHERE user_id = $2", new_clicks, user_id)
        await conn.close()
        return {"success": True, "earned": stats["passive_income"]}
    return {"success": False, "message": "Нет пассивного дохода"}

@app.post("/api/claim_daily")
async def claim_daily(user_id: int):
    stats = await get_user_stats(user_id)
    today = datetime.now().date()
    last_date = datetime.fromisoformat(stats.get("last_daily", "")).date() if stats.get("last_daily") else None
    if last_date == today:
        return {"success": False, "message": "Уже забирал сегодня"}
    streak = stats["daily_streak"] + 1 if last_date == today - timedelta(days=1) else 1
    bonus = min(100 + streak * 50, 600)
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("UPDATE users SET clicks = clicks + $1, daily_streak = $2, last_daily = $3 WHERE user_id = $4",
                       bonus, streak, today, user_id)
    await conn.close()
    return {"success": True, "bonus": bonus, "streak": streak}

@app.post("/api/buy_skin")
async def buy_skin(user_id: int, skin_id: int):
    conn = await asyncpg.connect(DATABASE_URL)
    skin = await conn.fetchrow("SELECT name, emoji, price_clicks FROM skins WHERE id = $1", skin_id)
    if not skin:
        await conn.close()
        return {"success": False, "message": "Скин не найден"}
    stats = await get_user_stats(user_id)
    if stats["clicks"] >= skin['price_clicks']:
        new_clicks = stats["clicks"] - skin['price_clicks']
        await conn.execute("UPDATE users SET clicks = $1 WHERE user_id = $2", new_clicks, user_id)
        await conn.execute("INSERT INTO user_skins (user_id, skin_id) VALUES ($1, $2) ON CONFLICT DO NOTHING", user_id, skin_id)
        skins_count = await conn.fetchval("SELECT COUNT(*) FROM user_skins WHERE user_id = $1", user_id)
        await conn.close()
        await check_achievements(user_id, "skins", skins_count)
        return {"success": True, "skin_name": skin['name'], "skin_emoji": skin['emoji']}
    await conn.close()
    return {"success": False, "need": skin['price_clicks']}

@app.post("/api/equip_skin")
async def equip_skin(user_id: int, skin_id: int):
    conn = await asyncpg.connect(DATABASE_URL)
    owned = await conn.fetchval("SELECT 1 FROM user_skins WHERE user_id = $1 AND skin_id = $2", user_id, skin_id)
    if not owned:
        await conn.close()
        return {"success": False, "message": "Скин не куплен"}
    emoji = await conn.fetchval("SELECT emoji FROM skins WHERE id = $1", skin_id)
    await conn.execute("UPDATE users SET current_skin = $1 WHERE user_id = $2", emoji, user_id)
    await conn.close()
    return {"success": True, "skin": emoji}

@app.get("/api/get_skins")
async def get_skins(user_id: int):
    conn = await asyncpg.connect(DATABASE_URL)
    owned = [row['skin_id'] for row in await conn.fetch("SELECT skin_id FROM user_skins WHERE user_id = $1", user_id)]
    current = await conn.fetchval("SELECT current_skin FROM users WHERE user_id = $1", user_id)
    skins = await conn.fetch("SELECT id, name, emoji, price_clicks, tap_bonus FROM skins")
    await conn.close()
    return {"skins": [{"id": s['id'], "name": s['name'], "emoji": s['emoji'], "price": s['price_clicks'], "bonus": s['tap_bonus'], "owned": s['id'] in owned, "equipped": s['emoji'] == current} for s in skins], "current_skin": current}

@app.post("/api/open_case")
async def open_case(user_id: int, case_id: int = 1):
    conn = await asyncpg.connect(DATABASE_URL)
    case = await conn.fetchrow("SELECT name, emoji, price_clicks FROM cases WHERE id = $1", case_id)
    if not case:
        await conn.close()
        return {"success": False, "message": "Кейс не найден"}
    stats = await get_user_stats(user_id)
    if stats["clicks"] >= case['price_clicks']:
        new_clicks = stats["clicks"] - case['price_clicks']
        await conn.execute("UPDATE users SET clicks = $1 WHERE user_id = $2", new_clicks, user_id)
        rewards = await conn.fetch("SELECT reward_type, reward_value, reward_text, chance FROM case_rewards WHERE case_id = $1", case_id)
        total_chance = sum(r['chance'] for r in rewards)
        rand = random.randint(1, total_chance)
        cumulative = 0
        selected = None
        for reward in rewards:
            cumulative += reward['chance']
            if rand <= cumulative:
                selected = reward
                break
        if selected['reward_type'] == "clicks":
            await conn.execute("UPDATE users SET clicks = clicks + $1 WHERE user_id = $2", selected['reward_value'], user_id)
        elif selected['reward_type'] == "gems":
            await conn.execute("UPDATE users SET gems = gems + $1 WHERE user_id = $2", selected['reward_value'], user_id)
        elif selected['reward_type'] == "booster":
            expires_at = datetime.now() + timedelta(minutes=30)
            await conn.execute("INSERT INTO user_boosters (user_id, booster_id, expires_at) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
                               user_id, selected['reward_value'], expires_at
        elif selected['reward_type'] == "skin":
            await conn.execute("INSERT INTO user_skins (user_id, skin_id) VALUES ($1, $2) ON CONFLICT DO NOTHING", user_id, selected['reward_value'])
        cases_opened = await conn.fetchval("SELECT COUNT(*) FROM user_achievements WHERE user_id = $1 AND achievement_id IN (6,7) AND completed = 1", user_id)
        await conn.close()
        await check_achievements(user_id, "cases", cases_opened + 1)
        return {"success": True, "reward_text": selected['reward_text'], "case_emoji": case['emoji']}
    await conn.close()
    return {"success": False, "need": case['price_clicks']}

@app.get("/api/get_cases")
async def get_cases():
    conn = await asyncpg.connect(DATABASE_URL)
    cases = await conn.fetch("SELECT id, name, emoji, price_clicks FROM cases")
    await conn.close()
    return {"cases": [{"id": c['id'], "name": c['name'], "emoji": c['emoji'], "price": c['price_clicks']} for c in cases]}

@app.get("/api/get_boosters")
async def get_boosters(user_id: int):
    conn = await asyncpg.connect(DATABASE_URL)
    shop_boosters = await conn.fetch("SELECT id, name, emoji, description, price_clicks FROM boosters")
    active = await get_active_boosters(user_id)
    await conn.close()
    return {"shop_boosters": [{"id": b['id'], "name": b['name'], "emoji": b['emoji'], "description": b['description'], "price": b['price_clicks']} for b in shop_boosters],
            "active_boosters": active}

@app.post("/api/buy_booster")
async def buy_booster(user_id: int, booster_id: int):
    conn = await asyncpg.connect(DATABASE_URL)
    booster = await conn.fetchrow("SELECT name, emoji, price_clicks, duration_minutes, effect_type, effect_value FROM boosters WHERE id = $1", booster_id)
    if not booster:
        await conn.close()
        return {"success": False, "message": "Бустер не найден"}
    stats = await get_user_stats(user_id)
    if stats["clicks"] >= booster['price_clicks']:
        new_clicks = stats["clicks"] - booster['price_clicks']
        await conn.execute("UPDATE users SET clicks = $1 WHERE user_id = $2", new_clicks, user_id)
        expires_at = datetime.now() + timedelta(minutes=booster['duration_minutes'])
        await conn.execute("INSERT INTO user_boosters (user_id, booster_id, expires_at) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
                           user_id, booster_id, expires_at
        if booster['effect_type'] == "energy":
            new_energy = min(stats["energy"] + int(booster['effect_value']), 1000)
            await conn.execute("UPDATE users SET energy = $1 WHERE user_id = $2", new_energy, user_id)
        await conn.close()
        return {"success": True, "booster_name": booster['name'], "booster_emoji": booster['emoji']}
    await conn.close()
    return {"success": False, "need": booster['price_clicks']}

@app.get("/api/get_achievements")
async def get_achievements(user_id: int):
    conn = await asyncpg.connect(DATABASE_URL)
    achievements = await conn.fetch("SELECT id, name, description, condition_value, reward_gems, reward_clicks FROM achievements")
    result = []
    for ach in achievements:
        completed = await conn.fetchval("SELECT completed FROM user_achievements WHERE user_id = $1 AND achievement_id = $2", user_id, ach['id'])
        result.append({
            "id": ach['id'], "name": ach['name'], "description": ach['description'], "condition": ach['condition_value'],
            "reward_gems": ach['reward_gems'], "reward_clicks": ach['reward_clicks'], "completed": completed or 0
        })
    await conn.close()
    return {"achievements": result}

@app.get("/api/get_leaderboard")
async def get_leaderboard(limit: int = 10):
    conn = await asyncpg.connect(DATABASE_URL)
    result = await conn.fetch("SELECT user_id, username, total_clicks FROM users ORDER BY total_clicks DESC LIMIT $1", limit)
    await conn.close()
    return {"leaderboard": [{"user_id": r['user_id'], "username": r['username'] or str(r['user_id']), "clicks": r['total_clicks']} for r in result]}

@app.get("/api/get_stats")
async def get_stats(user_id: int, username: str = None):
    stats = await get_user_stats(user_id, username)
    boosters = await get_active_boosters(user_id)
    tap_multiplier = await get_booster_multiplier(user_id)
    return {**stats, "boosters": boosters, "tap_multiplier": tap_multiplier}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
async def mini_app(user_id: int = 1, username: str = None):
    stats = await get_user_stats(user_id, username)
    
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
        
        let clicks = {stats["clicks"]};
        let level = {stats["level"]};
        let tapPower = {stats["tap_power"]};
        let passiveIncome = {stats["passive_income"]};
        let energy = {stats["energy"]};
        let gems = {stats["gems"]};
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
            document.getElementById('clicksValue').textContent = clicks;
            document.getElementById('levelValue').textContent = level;
            document.getElementById('tapPowerValue').textContent = '+' + tapPower;
            document.getElementById('passiveValue').textContent = passiveIncome + '/час';
            document.getElementById('gemsValue').textContent = gems;
            document.getElementById('energyValue').textContent = Math.floor(energy) + '/1000';
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
                document.getElementById('duck').textContent = currentSkin;
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