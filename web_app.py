import os
import asyncpg
import random
import io
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel
import uvicorn
from PIL import Image, ImageDraw, ImageFont

app = FastAPI()

DATABASE_URL = os.getenv("DATABASE_URL")

class ClickData(BaseModel):
    user_id: int
    clicks: int

# ==================== ФУНКЦИИ БД ====================

async def get_connection():
    return await asyncpg.connect(DATABASE_URL, statement_cache_size=0)

async def init_db():
    conn = await get_connection()
    # Удаляем старые таблицы
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
        CREATE TABLE users (
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
    conn = await get_connection()
    await conn.execute("""
        UPDATE users 
        SET balance = balance + $1, 
            total_clicks = total_clicks + $1, 
            energy = energy - 1 
        WHERE user_id = $2
    """, increment, user_id)
    await conn.close()

async def get_active_boosters(user_id: int):
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

async def get_booster_multiplier(user_id: int):
    boosters = await get_active_boosters(user_id)
    multiplier = 1.0
    for b in boosters:
        if b["effect_type"] == "tap_multiplier":
            multiplier *= b["effect_value"]
    return multiplier

<<<<<<< HEAD
async def upgrade_tap_power(user_id: int):
=======
async def get_user_username(user_id: int):
    try:
        from aiogram import Bot
        bot = Bot(token=os.getenv("BOT_TOKEN"))
        user = await bot.get_chat(user_id)
        await bot.session.close()
        return user.username or str(user_id)
    except:
        return str(user_id)

@app.post("/api/click")
async def handle_click(data: ClickData):
    multiplier = await get_booster_multiplier(data.user_id)
    final_clicks = int(data.clicks * multiplier)
    await update_balance(data.user_id, final_clicks)
    stats = await get_user_stats(data.user_id)
    return stats
async def update_daily_clicks(user_id: int, increment: int):
    conn = await get_connection()
    today = datetime.now().date()
    await conn.execute("""
        INSERT INTO daily_stats (user_id, clicks_today, date)
        VALUES ($1, $2, $3)
        ON CONFLICT (user_id, date) DO UPDATE SET clicks_today = daily_stats.clicks_today + $2
    """, user_id, increment, today)
    await conn.close()

@app.post("/api/upgrade_tap")
async def upgrade_tap(user_id: int):
>>>>>>> 5d33dda (Финальная версия бота)
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

async def claim_daily(user_id: int):
    stats = await get_user_stats(user_id)
    today = datetime.now().date()
    last_date = stats.get("last_daily")
    if last_date:
        if isinstance(last_date, datetime):
            last_date = last_date.date()
        if last_date == today:
            return (False, 0, 0)
        streak = stats["daily_streak"] + 1 if last_date == today - timedelta(days=1) else 1
    else:
        streak = 1
    bonus = min(100 + streak * 50, 600)
    conn = await get_connection()
    await conn.execute("UPDATE users SET balance = balance + $1, daily_streak = $2, last_daily = $3 WHERE user_id = $4", bonus, streak, today, user_id)
    await conn.close()
    return (True, bonus, streak)

async def collect_passive(user_id: int):
    stats = await get_user_stats(user_id)
    if stats["profit_per_hour"] <= 0:
        return (False, 0)
    earned = stats["profit_per_hour"]
    conn = await get_connection()
    await conn.execute("UPDATE users SET balance = balance + $1 WHERE user_id = $2", earned, user_id)
    await conn.close()
    return (True, earned)

async def open_case(user_id: int, case_id: int):
    conn = await get_connection()
    case = await conn.fetchrow("SELECT name, emoji, price_clicks, price_gems FROM cases WHERE id = $1", case_id)
    if not case:
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

async def buy_booster(user_id: int):
    stats = await get_user_stats(user_id)
    price = 5000
    if stats["balance"] >= price:
        conn = await get_connection()
        new_balance = stats["balance"] - price
        await conn.execute("UPDATE users SET balance = $1 WHERE user_id = $2", new_balance, user_id)
        expires_at = datetime.now() + timedelta(minutes=30)
        await conn.execute("INSERT INTO user_boosters (user_id, booster_id, expires_at) VALUES ($1, $2, $3) ON CONFLICT (user_id, booster_id) DO UPDATE SET expires_at = EXCLUDED.expires_at", user_id, 1, expires_at)
        await conn.close()
        return (True, "x2 Прибыль", "⚡")
    return (False, None, None)

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

# ==================== API ЭНДПОИНТЫ ====================

@app.post("/api/click")
async def handle_click(data: ClickData):
    multiplier = await get_booster_multiplier(data.user_id)
    final_clicks = int(data.clicks * multiplier)
    await update_clicks(data.user_id, final_clicks)
    stats = await get_user_stats(data.user_id)
    return {
        "balance": stats["balance"],
        "profit_per_tap": stats["profit_per_tap"],
        "profit_per_hour": stats["profit_per_hour"],
        "energy": stats["energy"],
        "gems": stats["gems"],
        "current_skin": stats["current_skin"]
    }

@app.post("/api/upgrade_tap")
async def upgrade_tap(user_id: int):
    success, new_power, price = await upgrade_tap_power(user_id)
    if success:
        return {"success": True, "new_tap_power": new_power}
    return {"success": False, "need": price}

@app.post("/api/upgrade_hourly")
async def upgrade_hourly(user_id: int):
    success, new_hourly, price = await upgrade_hourly(user_id)
    if success:
        return {"success": True, "new_hourly": new_hourly}
    return {"success": False, "need": price}

@app.post("/api/claim_daily")
async def claim_daily(user_id: int):
    success, bonus, streak = await claim_daily(user_id)
    if success:
        return {"success": True, "bonus": bonus, "streak": streak}
    return {"success": False, "message": "Уже забирал сегодня"}

@app.post("/api/collect_passive")
async def collect_passive(user_id: int):
    success, earned = await collect_passive(user_id)
    if success:
        return {"success": True, "earned": earned}
    return {"success": False, "message": "Нет пассивного дохода"}

@app.post("/api/open_case")
async def open_case_api(user_id: int, case_id: int = 1):
    success, reward_text, case_emoji, _ = await open_case(user_id, case_id)
    if success:
        return {"success": True, "reward_text": reward_text, "case_emoji": case_emoji}
    return {"success": False, "need": 0, "currency": "монет"}

@app.get("/api/get_cases")
async def get_cases_api():
    cases = await get_cases()
    return {"cases": cases}

@app.post("/api/buy_booster")
async def buy_booster_api(user_id: int):
    success, name, emoji = await buy_booster(user_id)
    if success:
        return {"success": True, "booster_name": name, "booster_emoji": emoji}
    return {"success": False, "need": 5000}

@app.get("/api/get_boosters")
async def get_boosters_api(user_id: int):
    boosters = await get_active_boosters(user_id)
    return {"boosters": boosters}

@app.post("/api/buy_skin")
async def buy_skin_api(user_id: int, skin_id: int):
    success, name, emoji = await buy_skin(user_id, skin_id)
    if success:
        return {"success": True, "skin_name": name, "skin_emoji": emoji}
    return {"success": False, "need": 0}

@app.post("/api/equip_skin")
async def equip_skin_api(user_id: int, skin_id: int):
    success, emoji = await equip_skin(user_id, skin_id)
    if success:
        return {"success": True, "skin": emoji}
    return {"success": False, "message": "Скин не куплен"}

@app.get("/api/get_skins")
async def get_skins_api(user_id: int):
    skins = await get_skins(user_id)
    return {"skins": skins}

@app.get("/api/get_referrals")
async def get_referrals_api(user_id: int):
    count = await get_referrals(user_id)
    return {"count": count}

@app.post("/api/claim_referral")
async def claim_referral_api(user_id: int):
    reward = await claim_referral_reward(user_id)
    if reward > 0:
        return {"success": True, "reward": reward}
    return {"success": False, "message": "Нет новых рефералов"}

@app.get("/api/get_leaderboard")
async def get_leaderboard_api(limit: int = 10):
    leaderboard = await get_leaderboard(limit)
    return {"leaderboard": leaderboard}

@app.get("/api/get_stats")
async def get_stats_api(user_id: int):
    stats = await get_user_stats(user_id)
    boosters = await get_active_boosters(user_id)
    multiplier = await get_booster_multiplier(user_id)
    return {**stats, "boosters": boosters, "tap_multiplier": multiplier}

@app.get("/api/share_image")
async def share_image(user_id: int):
    stats = await get_user_stats(user_id)
    
    img = Image.new('RGB', (500, 500), color='#0a0f1e')
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except:
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Рисуем утку (эмодзи не отрисовать, пишем текст)
    draw.text((250, 100), "🦆", fill="white", anchor="mm", font=font)
    
    draw.text((250, 200), f"Баланс: {stats['balance']} монет", fill="#ffd700", anchor="mm", font=font_small)
    draw.text((250, 250), f"Сила тапа: +{stats['profit_per_tap']}", fill="#ffd700", anchor="mm", font=font_small)
    draw.text((250, 300), f"Скин: {stats['current_skin']}", fill="#ffd700", anchor="mm", font=font_small)
    draw.text((250, 400), "Zeta Clicker", fill="white", anchor="mm", font=font)
    
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    return Response(content=img_byte_arr.getvalue(), media_type="image/png")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.on_event("startup")
async def startup():
    await init_db()

@app.get("/", response_class=HTMLResponse)
async def mini_app(user_id: int = 1):
    stats = await get_user_stats(user_id)
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>Zeta Clicker</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; user-select: none; -webkit-tap-highlight-color: transparent; }}
        body {{ min-height: 100vh; background: radial-gradient(circle at 20% 30%, #0a0f1e, #03060c); font-family: "Segoe UI", Roboto, Helvetica, Arial, sans-serif; padding-bottom: 80px; }}
        .container {{ max-width: 450px; margin: 0 auto; padding: 20px; }}
        .card {{ background: rgba(20, 30, 45, 0.7); backdrop-filter: blur(12px); border-radius: 32px; padding: 20px; margin-bottom: 16px; border: 1px solid rgba(255, 215, 0, 0.2); box-shadow: 0 8px 32px rgba(0,0,0,0.3); }}
        .title {{ font-size: 28px; font-weight: bold; background: linear-gradient(135deg, #ffd700, #ff8c00); -webkit-background-clip: text; background-clip: text; color: transparent; text-align: center; margin-bottom: 20px; }}
        .balance-row {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 20px; }}
        .balance-label {{ color: rgba(255,255,255,0.6); font-size: 14px; }}
        .balance-value {{ font-size: 32px; font-weight: bold; color: #ffd700; }}
        .stats-grid {{ display: flex; flex-direction: column; gap: 12px; margin-bottom: 20px; }}
        .stat-item {{ display: flex; justify-content: space-between; align-items: center; }}
        .stat-label {{ color: rgba(255,255,255,0.5); font-size: 14px; }}
        .stat-value {{ color: white; font-size: 18px; font-weight: 600; }}
        .highlight {{ color: #ffd700; }}
        .energy-container {{ margin-top: 12px; }}
        .energy-bar {{ width: 100%; height: 8px; background: rgba(255,255,255,0.2); border-radius: 4px; overflow: hidden; margin-top: 8px; }}
        .energy-fill {{ height: 100%; background: linear-gradient(90deg, #00ff88, #00cc66); border-radius: 4px; transition: width 0.2s; width: {stats["energy"]/stats["max_energy"]*100}%; }}
        .tap-area {{ text-align: center; margin: 30px 0; }}
        .duck {{ font-size: 180px; cursor: pointer; transition: transform 0.1s ease; filter: drop-shadow(0 10px 20px rgba(0,0,0,0.3)); }}
        .duck:active {{ transform: scale(0.95); }}
        .tap-value {{ position: fixed; pointer-events: none; font-size: 28px; font-weight: bold; color: #ffd700; text-shadow: 0 0 10px rgba(0,0,0,0.5); z-index: 1000; animation: floatUp 0.6s ease-out forwards; }}
        @keyframes floatUp {{ 0% {{ opacity: 1; transform: translateY(0) scale(0.8); }} 100% {{ opacity: 0; transform: translateY(-80px) scale(1.2); }} }}
        .bottom-menu {{ position: fixed; bottom: 0; left: 0; right: 0; background: rgba(20, 30, 45, 0.95); backdrop-filter: blur(20px); border-top: 1px solid rgba(255,215,0,0.2); padding: 8px 10px; z-index: 100; overflow-x: auto; white-space: nowrap; }}
        .bottom-menu > div {{ display: flex; justify-content: space-around; min-width: 100%; }}
        .menu-item {{ display: inline-flex; flex-direction: column; align-items: center; gap: 4px; background: none; border: none; color: rgba(255,255,255,0.6); font-size: 11px; cursor: pointer; padding: 6px 8px; border-radius: 16px; white-space: nowrap; }}
        .menu-item.active {{ color: #ffd700; background: rgba(255,215,0,0.15); }}
        .menu-icon {{ font-size: 24px; }}
        .skins-list, .cases-list, .boosters-list, .leaderboard-list {{ margin: 20px 0; }}
        .skin-item, .booster-item, .leaderboard-item {{ background: rgba(0,0,0,0.3); border-radius: 16px; padding: 12px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }}
        .skin-info, .booster-info {{ display: flex; align-items: center; gap: 12px; }}
        .skin-emoji, .booster-emoji {{ font-size: 40px; }}
        .skin-name, .booster-name {{ font-size: 16px; font-weight: bold; color: white; }}
        .skin-price, .booster-price {{ font-size: 12px; color: #ffd700; }}
        .skin-btn, .booster-btn {{ background: linear-gradient(135deg, #667eea, #764ba2); border: none; border-radius: 12px; padding: 8px 16px; color: white; cursor: pointer; }}
        .skin-btn.owned {{ background: #4caf50; }}
        .case-item {{ background: linear-gradient(135deg, rgba(255,215,0,0.2), rgba(255,140,0,0.2)); border-radius: 20px; padding: 30px; text-align: center; cursor: pointer; margin-bottom: 20px; }}
        .case-emoji {{ font-size: 80px; }}
        .case-name {{ font-size: 20px; font-weight: bold; color: #ffd700; margin-top: 10px; }}
        .case-price {{ font-size: 14px; color: rgba(255,255,255,0.7); margin-top: 5px; }}
        .leaderboard-item {{ display: flex; justify-content: space-between; padding: 12px; }}
        .leaderboard-rank {{ font-weight: bold; color: #ffd700; width: 40px; }}
        .leaderboard-name {{ flex: 1; }}
        .leaderboard-clicks {{ color: #ffd700; }}
        .referral-link {{ background: rgba(0,0,0,0.3); border-radius: 16px; padding: 12px; margin-bottom: 20px; word-break: break-all; }}
        .referral-link-text {{ color: #ffd700; font-size: 12px; font-family: monospace; }}
        .referral-stats {{ display: flex; justify-content: space-between; margin-bottom: 20px; }}
        .referral-stat {{ text-align: center; flex: 1; }}
        .referral-stat-value {{ font-size: 24px; font-weight: bold; color: #ffd700; }}
        .copy-btn {{ background: #4caf50; border: none; border-radius: 12px; padding: 12px; color: white; cursor: pointer; width: 100%; margin-top: 10px; }}
        .channel-btn {{ background: rgba(255,215,0,0.15); border: 1px solid rgba(255,215,0,0.3); border-radius: 24px; padding: 12px; text-align: center; cursor: pointer; margin-top: 20px; }}
        .channel-text {{ color: #ffd700; font-size: 14px; font-weight: 600; }}
        .share-btn {{ background: linear-gradient(135deg, #ff8c00, #ff4500); }}
        .screen {{ display: none; }}
        .screen.active {{ display: block; }}
    </style>
</head>
<body>
    <div class="container">
        <!-- ГЛАВНЫЙ ЭКРАН -->
        <div id="mainScreen" class="screen active">
            <div class="card">
                <div class="title">Zeta Clicker</div>
                <div class="balance-row">
                    <span class="balance-label">💰 Баланс</span>
                    <span class="balance-value" id="balance">{stats["balance"]}</span>
                    <button class="copy-btn" id="donateBtn" style="background: linear-gradient(135deg, #f5af19, #f12711);">⭐ Поддержать (Telegram Stars)</button>
                </div>
                <div class="stats-grid">
                    <div class="stat-item">
                        <span class="stat-label">Прибыль за тап</span>
                        <span class="stat-value highlight" id="profitPerTap">+{stats["profit_per_tap"]}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Прибыль в час</span>
                        <span class="stat-value highlight" id="profitPerHour">+{stats["profit_per_hour"]}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">💎 Алмазы</span>
                        <span class="stat-value highlight" id="gemsValue">{stats["gems"]}</span>
                    </div>
                </div>
                <div class="energy-container">
                    <div class="stat-item">
                        <span class="stat-label">⚡ Энергия</span>
                        <span class="stat-value" id="energyValue">{stats["energy"]}/{stats["max_energy"]}</span>
                    </div>
                    <div class="energy-bar">
                        <div class="energy-fill" id="energyFill"></div>
                    </div>
                </div>
            </div>
            <div class="tap-area">
                <div class="duck" id="duck">{stats["current_skin"]}</div>
            </div>
            <div class="channel-btn" id="channelBtn">
                <span class="channel-text">📢 Канал ZetaClicker</span>
            </div>
            <button class="copy-btn share-btn" id="shareBtn" style="margin-top: 16px;">📤 Поделиться прогрессом</button>
        </div>
        
        <!-- КЕЙСЫ -->
        <div id="casesScreen" class="screen">
            <div class="card">
                <div class="title">📦 Кейсы</div>
                <div id="casesList" class="cases-list"></div>
            </div>
        </div>
        
        <!-- РЕФЕРАЛЫ -->
        <div id="referralScreen" class="screen">
            <div class="card">
                <div class="title">👥 Рефералы</div>
                <div class="referral-stats">
                    <div class="referral-stat">
                        <div class="referral-stat-value" id="referralCount">0</div>
                        <div style="color: rgba(255,255,255,0.6); font-size: 12px;">Приглашено</div>
                    </div>
                </div>
                <div class="referral-link">
                    <div style="color: rgba(255,255,255,0.6); margin-bottom: 8px;">🔗 Твоя реферальная ссылка:</div>
                    <div class="referral-link-text" id="referralLink"></div>
                    <button class="copy-btn" id="copyReferralBtn">📋 Копировать ссылку</button>
                </div>
                <button class="copy-btn" id="claimReferralBtn" style="background: linear-gradient(135deg, #ff8c00, #ff4500);">🎁 Забрать награду (1000 за реферала)</button>
            </div>
        </div>
        
        <!-- МАГАЗИН СКИНОВ -->
        <div id="shopScreen" class="screen">
            <div class="card">
                <div class="title">👕 Магазин скинов</div>
                <div id="skinsList" class="skins-list"></div>
            </div>
        </div>
        
        <!-- БУСТЕРЫ И УЛУЧШЕНИЯ -->
        <div id="boostersScreen" class="screen">
            <div class="card">
                <div class="title">⚡ Бустеры</div>
                <div id="activeBoostersList"></div>
                <div id="shopBoostersList"></div>
            </div>
            <div class="card" style="margin-top: 16px;">
                <div class="title">💪 Улучшения</div>
                <div class="stat-item" style="margin-bottom: 16px;">
                    <span class="stat-label">💪 Сила тапа</span>
                    <span class="stat-value highlight" id="upgradeTapValue">{stats["profit_per_tap"]}</span>
                </div>
                <button class="copy-btn" id="upgradeTapBtn" style="background: linear-gradient(135deg, #667eea, #764ba2); margin-bottom: 16px;">⬆️ Улучшить тап</button>
                <div class="stat-item" style="margin-bottom: 16px;">
                    <span class="stat-label">💰 Прибыль в час</span>
                    <span class="stat-value highlight" id="upgradeHourlyValue">{stats["profit_per_hour"]}</span>
                </div>
                <button class="copy-btn" id="upgradeHourlyBtn" style="background: linear-gradient(135deg, #667eea, #764ba2);">⬆️ Улучшить пассивку</button>
            </div>
        </div>
        
        <!-- ТОП ИГРОКОВ -->
        <div id="leaderboardScreen" class="screen">
            <div class="card">
                <div class="title">🏆 Топ игроков</div>
                <div id="leaderboardList" class="leaderboard-list"></div>
            </div>
        </div>
    </div>
    
    <!-- НИЖНЕЕ МЕНЮ -->
    <div class="bottom-menu">
        <div style="display: flex; justify-content: space-around; width: 100%; gap: 5px;">
            <button class="menu-item" data-screen="mainScreen"><span class="menu-icon">🦆</span><span>Кликер</span></button>
            <button class="menu-item" data-screen="casesScreen"><span class="menu-icon">📦</span><span>Кейсы</span></button>
            <button class="menu-item" data-screen="referralScreen"><span class="menu-icon">👥</span><span>Рефка</span></button>
            <button class="menu-item" data-screen="shopScreen"><span class="menu-icon">👕</span><span>Магазин</span></button>
            <button class="menu-item" data-screen="boostersScreen"><span class="menu-icon">⚡</span><span>Бустеры</span></button>
            <button class="menu-item" data-screen="leaderboardScreen"><span class="menu-icon">🏆</span><span>Топ</span></button>
        </div>
    </div>
    
    <script>
        var tg = window.Telegram.WebApp;
        tg.ready();
        tg.expand();
        
        var userId = new URLSearchParams(window.location.search).get('user_id') || 1;
        var balance = {stats["balance"]};
        var profitPerTap = {stats["profit_per_tap"]};
        var profitPerHour = {stats["profit_per_hour"]};
        var energy = {stats["energy"]};
        var maxEnergy = {stats["max_energy"]};
        var gems = {stats["gems"]};
        var currentSkin = "{stats["current_skin"]}" || '🦆';
        
        var menuItems = document.querySelectorAll('.menu-item');
        for (var i = 0; i < menuItems.length; i++) {{
            menuItems[i].addEventListener('click', function() {{
                var screenId = this.dataset.screen;
                var screens = document.querySelectorAll('.screen');
                for (var j = 0; j < screens.length; j++) {{
                    screens[j].classList.remove('active');
                }}
                document.getElementById(screenId).classList.add('active');
                var allMenuItems = document.querySelectorAll('.menu-item');
                for (var k = 0; k < allMenuItems.length; k++) {{
                    allMenuItems[k].classList.remove('active');
                }}
                this.classList.add('active');
                
                if (screenId === 'casesScreen') loadCases();
                if (screenId === 'shopScreen') loadSkins();
                if (screenId === 'boostersScreen') loadBoosters();
                if (screenId === 'referralScreen') loadReferralData();
                if (screenId === 'leaderboardScreen') loadLeaderboard();
            }});
        }}
        
        function updateUI() {{
            document.getElementById('balance').innerText = balance;
            document.getElementById('profitPerTap').innerText = '+' + profitPerTap;
            document.getElementById('profitPerHour').innerText = '+' + profitPerHour;
            document.getElementById('gemsValue').innerText = gems;
            document.getElementById('energyValue').innerText = energy + '/' + maxEnergy;
            document.getElementById('energyFill').style.width = (energy / maxEnergy * 100) + '%';
            document.getElementById('upgradeTapValue').innerText = profitPerTap;
            document.getElementById('upgradeHourlyValue').innerText = profitPerHour;
        }}
        
        async function loadStats() {{
            try {{
                var res = await fetch('/api/get_stats?user_id=' + userId);
                var data = await res.json();
                balance = data.balance;
                profitPerTap = data.profit_per_tap;
                profitPerHour = data.profit_per_hour;
                energy = data.energy;
                maxEnergy = data.max_energy;
                gems = data.gems;
                currentSkin = data.current_skin || '🦆';
                document.getElementById('duck').innerText = currentSkin;
                updateUI();
            }} catch(e) {{ console.error(e); }}
        }}
        
        async function sendClick() {{
            try {{
                var res = await fetch('/api/click', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ user_id: userId, clicks: profitPerTap }})
                }});
                var data = await res.json();
                balance = data.balance;
                profitPerTap = data.profit_per_tap;
                profitPerHour = data.profit_per_hour;
                energy = data.energy;
                gems = data.gems;
                updateUI();
            }} catch(e) {{ console.error(e); }}
        }}
        
        function showFloatingNumber(x, y, value) {{
            var el = document.createElement('div');
            el.className = 'tap-value';
            el.textContent = '+' + value;
            el.style.left = x + 'px';
            el.style.top = y + 'px';
            document.body.appendChild(el);
            setTimeout(function() {{ el.remove(); }}, 600);
        }}
        
        document.getElementById('duck').onclick = async function(e) {{
            if (energy <= 0) {{
                tg.showPopup({{ title: '😫 Нет энергии!', message: 'Подожди, энергия восстановится.', buttons: [{{type: 'ok'}}] }});
                return;
            }}
            var rect = e.target.getBoundingClientRect();
            var x = rect.left + rect.width / 2;
            var y = rect.top;
            showFloatingNumber(x, y, profitPerTap);
            energy -= 1;
            updateUI();
            await sendClick();
        }};
        
        document.getElementById('upgradeTapBtn').onclick = async function() {{
            var res = await fetch('/api/upgrade_tap?user_id=' + userId, {{ method: 'POST' }});
            var data = await res.json();
            if (data.success) {{
                tg.showPopup({{ title: '✅ Улучшено!', message: 'Сила тапа: +' + data.new_tap_power, buttons: [{{type: 'ok'}}] }});
                await loadStats();
            }} else {{
                tg.showPopup({{ title: '❌ Не хватает монет', message: 'Нужно: ' + data.need + ' монет', buttons: [{{type: 'ok'}}] }});
            }}
        }};
        
        document.getElementById('upgradeHourlyBtn').onclick = async function() {{
            var res = await fetch('/api/upgrade_hourly?user_id=' + userId, {{ method: 'POST' }});
            var data = await res.json();
            if (data.success) {{
                tg.showPopup({{ title: '✅ Улучшено!', message: 'Прибыль в час: +' + data.new_hourly, buttons: [{{type: 'ok'}}] }});
                await loadStats();
            }} else {{
                tg.showPopup({{ title: '❌ Не хватает монет', message: 'Нужно: ' + data.need + ' монет', buttons: [{{type: 'ok'}}] }});
            }}
        }};
        
        document.getElementById('channelBtn').onclick = function() {{
            tg.openTelegramLink('https://t.me/ZetaClicker');
        }};
        
        // Кнопка поделиться
        document.getElementById('shareBtn').onclick = async function() {{
            var imgUrl = '/api/share_image?user_id=' + userId;
            tg.showPopup({{
                title: '📤 Поделиться прогрессом',
                message: 'Нажми "Поделиться", чтобы отправить картинку другу!',
                buttons: [
                    {{type: 'default', text: '📤 Поделиться'}},
                    {{type: 'cancel', text: 'Отмена'}}
                ]
            }}, function(buttonId) {{
                if (buttonId === '0') {{
                    tg.sendData(JSON.stringify({{ action: 'share', user_id: userId }}));
                }}
            }});
        }};
        
        async function loadCases() {{
            var res = await fetch('/api/get_cases');
            var data = await res.json();
            var casesList = document.getElementById('casesList');
            casesList.innerHTML = '';
            for (var i = 0; i < data.cases.length; i++) {{
                var c = data.cases[i];
                var price = c.price_clicks > 0 ? c.price_clicks + ' монет' : c.price_gems + ' алмазов';
                var div = document.createElement('div');
                div.className = 'case-item';
                div.innerHTML = '<div class="case-emoji">' + c.emoji + '</div><div class="case-name">' + c.name + '</div><div class="case-price">Цена: ' + price + '</div>';
                div.onclick = (function(id) {{ return function() {{ openCase(id); }}; }})(c.id);
                casesList.appendChild(div);
            }}
        }}
        
        async function openCase(caseId) {{
            var res = await fetch('/api/open_case?user_id=' + userId + '&case_id=' + caseId, {{ method: 'POST' }});
            var data = await res.json();
            if (data.success) {{
                tg.showPopup({{ title: '🎁 Открытие кейса!', message: data.case_emoji + ' Вы получили: ' + data.reward_text, buttons: [{{type: 'ok'}}] }});
                await loadStats();
            }} else {{
                tg.showPopup({{ title: '❌ Не хватает ресурсов', message: 'Нужно больше монет или алмазов', buttons: [{{type: 'ok'}}] }});
            }}
        }}
        
        async function loadSkins() {{
            var res = await fetch('/api/get_skins?user_id=' + userId);
            var data = await res.json();
            var skinsList = document.getElementById('skinsList');
            skinsList.innerHTML = '';
            for (var i = 0; i < data.skins.length; i++) {{
                var skin = data.skins[i];
                var div = document.createElement('div');
                div.className = 'skin-item';
                div.innerHTML = '<div class="skin-info"><span class="skin-emoji">' + skin.emoji + '</span><div><div class="skin-name">' + skin.name + '</div><div class="skin-price">+' + skin.bonus + ' к силе | Цена: ' + skin.price + ' монет</div></div></div>';
                var btn = document.createElement('button');
                if (skin.owned) {{
                    btn.className = 'skin-btn owned';
                    btn.innerHTML = '✅ Куплен';
                    div.appendChild(btn);
                    var equipBtn = document.createElement('button');
                    equipBtn.className = 'skin-btn';
                    equipBtn.style.marginLeft = '8px';
                    equipBtn.style.background = '#ff9800';
                    equipBtn.innerHTML = '⚡ Экипировать';
                    equipBtn.onclick = (function(id) {{ return function() {{ equipSkin(id); }}; }})(skin.id);
                    div.appendChild(equipBtn);
                }} else {{
                    btn.className = 'skin-btn';
                    btn.innerHTML = '💎 Купить';
                    btn.onclick = (function(id) {{ return function() {{ buySkin(id); }}; }})(skin.id);
                    div.appendChild(btn);
                }}
                skinsList.appendChild(div);
            }}
        }}
        
        async function buySkin(skinId) {{
            var res = await fetch('/api/buy_skin?user_id=' + userId + '&skin_id=' + skinId, {{ method: 'POST' }});
            var data = await res.json();
            if (data.success) {{
                tg.showPopup({{ title: '✅ Покупка успешна!', message: 'Вы купили ' + data.skin_name + ' ' + data.skin_emoji, buttons: [{{type: 'ok'}}] }});
                await loadStats();
                await loadSkins();
            }} else {{
                tg.showPopup({{ title: '❌ Не хватает монет', message: 'Нужно больше монет', buttons: [{{type: 'ok'}}] }});
            }}
        }}
        
        async function equipSkin(skinId) {{
            var res = await fetch('/api/equip_skin?user_id=' + userId + '&skin_id=' + skinId, {{ method: 'POST' }});
            var data = await res.json();
            if (data.success) {{
                tg.showPopup({{ title: '✅ Скин экипирован!', message: 'Теперь ваша утка: ' + data.skin, buttons: [{{type: 'ok'}}] }});
                await loadStats();
                await loadSkins();
            }}
        }}
        
        async function loadBoosters() {{
            var res = await fetch('/api/get_boosters?user_id=' + userId);
            var data = await res.json();
            var activeDiv = document.getElementById('activeBoostersList');
            if (data.boosters && data.boosters.length > 0) {{
                activeDiv.innerHTML = '<h3 style="color: #ffd700; margin-bottom: 10px;">⚡ Активные бустеры:</h3>';
                for (var i = 0; i < data.boosters.length; i++) {{
                    var b = data.boosters[i];
                    activeDiv.innerHTML += '<div class="booster-item"><div class="booster-info"><span class="booster-emoji">' + b.emoji + '</span><div><div class="booster-name">' + b.name + '</div><div class="booster-price">' + b.description + ' | Осталось: ' + b.minutes_left + ' мин</div></div></div></div>';
                }}
            }} else {{
                activeDiv.innerHTML = '<div style="text-align: center; padding: 20px; color: rgba(255,255,255,0.5);">Нет активных бустеров</div>';
            }}
            var shopDiv = document.getElementById('shopBoostersList');
            shopDiv.innerHTML = '<h3 style="color: #ffd700; margin-bottom: 10px;">💎 Доступные бустеры:</h3>';
            shopDiv.innerHTML += '<div class="booster-item"><div class="booster-info"><span class="booster-emoji">⚡</span><div><div class="booster-name">x2 Прибыль</div><div class="booster-price">Удваивает прибыль за тап на 30 минут</div></div></div><button class="booster-btn" onclick="buyBooster()">Купить за 5000</button></div>';
        }}
        
        async function buyBooster() {{
            var res = await fetch('/api/buy_booster?user_id=' + userId, {{ method: 'POST' }});
            var data = await res.json();
            if (data.success) {{
                tg.showPopup({{ title: '✅ Бустер активирован!', message: data.booster_emoji + ' ' + data.booster_name + ' активирован!', buttons: [{{type: 'ok'}}] }});
                await loadStats();
                await loadBoosters();
            }} else {{
                tg.showPopup({{ title: '❌ Не хватает монет', message: 'Нужно: 5000 монет', buttons: [{{type: 'ok'}}] }});
            }}
        }}
        
        async function loadReferralData() {{
            var res = await fetch('/api/get_referrals?user_id=' + userId);
            var data = await res.json();
            document.getElementById('referralCount').innerText = data.count;
            var botUsername = 'ZetaClickerRobot';
            var referralLink = 'https://t.me/' + botUsername + '?start=ref_' + userId;
            document.getElementById('referralLink').innerText = referralLink;
            document.getElementById('copyReferralBtn').onclick = function() {{
                navigator.clipboard.writeText(referralLink);
                tg.showPopup({{ title: '✅ Скопировано!', message: 'Реферальная ссылка скопирована', buttons: [{{type: 'ok'}}] }});
            }};
            document.getElementById('claimReferralBtn').onclick = async function() {{
                var claimRes = await fetch('/api/claim_referral?user_id=' + userId, {{ method: 'POST' }});
                var claimData = await claimRes.json();
                if (claimData.success) {{
                    tg.showPopup({{ title: '🎉 Награда получена!', message: '+' + claimData.reward + ' монет!', buttons: [{{type: 'ok'}}] }});
                    await loadStats();
                    await loadReferralData();
                }} else {{
                    tg.showPopup({{ title: '❌ Нет новых рефералов', message: claimData.message, buttons: [{{type: 'ok'}}] }});
                }}
            }};
        }}
        
        async function loadLeaderboard() {{
            try {{
                var res = await fetch('/api/get_leaderboard?limit=10');
                var data = await res.json();
                var leaderboardList = document.getElementById('leaderboardList');
                leaderboardList.innerHTML = '';
                for (var i = 0; i < data.leaderboard.length; i++) {{
                    var player = data.leaderboard[i];
                    var div = document.createElement('div');
                    div.className = 'leaderboard-item';
                    div.innerHTML = '<span class="leaderboard-rank">' + (i+1) + '</span><span class="leaderboard-name">' + player.username + '</span><span class="leaderboard-clicks">' + player.balance + '💰</span>';
                    leaderboardList.appendChild(div);
                }}
            }} catch(e) {{
                console.error('Leaderboard error:', e);
            }}
        }}
        
        setInterval(function() {{
            if (energy < maxEnergy) {{
                energy = Math.min(energy + 1, maxEnergy);
                updateUI();
            }}
        }}, 2000);
        
        loadStats();
<<<<<<< HEAD
=======

                document.getElementById('shareBtn').onclick = async function() {{
            var imgUrl = '/api/share_image?user_id=' + userId;
            
            tg.showPopup({{
                title: '📤 Поделиться прогрессом',
                message: 'Нажми "Поделиться", чтобы отправить картинку другу!',
                buttons: [
                    {{type: 'default', text: '📤 Поделиться'}},
                    {{type: 'cancel', text: 'Отмена'}}
                ]
            }}, function(buttonId) {{
                if (buttonId === '0') {{
                    tg.sendData(JSON.stringify({{ action: 'share', user_id: userId }}));
                }}
            }});
        }};

                document.getElementById('donateBtn').onclick = function() {
            tg.showPopup({
                title: 'Поддержать проект',
                message: 'Выбери сумму в Telegram Stars:',
                buttons: [
                    {id: '10', type: 'default', text: '⭐ 10 Stars'},
                    {id: '50', type: 'default', text: '⭐ 50 Stars'},
                    {id: '100', type: 'default', text: '⭐ 100 Stars'},
                    {type: 'cancel', text: 'Отмена'}
                ]
            }, function(buttonId) {
                if (buttonId && buttonId !== 'cancel') {
                    tg.openInvoice({
                        title: 'Поддержка Zeta Clicker',
                        description: `Донат ${buttonId} Telegram Stars`,
                        payload: JSON.stringify({user_id: userId, stars: parseInt(buttonId)}),
                        provider_token: '',  // для Stars пустая строка
                        currency: 'XTR',
                        prices: [{label: 'Telegram Stars', amount: parseInt(buttonId)}]
                    });
                }
            });
        };

>>>>>>> 5d33dda (Финальная версия бота)
    </script>
</body>
</html>
"""
    
    return HTMLResponse(content=html)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
