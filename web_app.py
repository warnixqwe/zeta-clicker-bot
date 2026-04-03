import os
import sqlite3
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Dict, Tuple

app = FastAPI()

# Настройка шаблонов
templates = Jinja2Templates(directory="templates")

# Модели данных
class ClickData(BaseModel):
    user_id: int
    clicks: int

class UserIdData(BaseModel):
    user_id: int

class SkinData(BaseModel):
    user_id: int
    skin_id: int

# База данных
DB_PATH = os.path.join(os.path.dirname(__file__), "zeta_clicker.db")

# ==================== ФУНКЦИИ РАБОТЫ С БАЗОЙ ДАННЫХ ====================

def get_user_stats(user_id: int) -> dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT clicks, level, energy, tap_power, passive_income, premium_until, current_skin, total_clicks, daily_streak FROM users WHERE user_id = ?",
        (user_id,)
    )
    result = cursor.fetchone()
    conn.close()
    
    if result:
        premium = result[5] and datetime.now() < datetime.fromisoformat(result[5])
        return {
            "clicks": result[0],
            "level": result[1],
            "energy": result[2],
            "tap_power": result[3],
            "passive_income": result[4],
            "premium": premium,
            "skin": result[6] if result[6] else "🦆",
            "total_clicks": result[7],
            "daily_streak": result[8] if result[8] else 0
        }
    else:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (user_id, clicks, level, energy, tap_power, passive_income, premium_until, current_skin, total_clicks, daily_streak) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, 0, 1, 1000, 1, 0, None, "🦆", 0, 0)
        )
        conn.commit()
        conn.close()
        return {
            "clicks": 0,
            "level": 1,
            "energy": 1000,
            "tap_power": 1,
            "passive_income": 0,
            "premium": False,
            "skin": "🦆",
            "total_clicks": 0,
            "daily_streak": 0
        }

def update_clicks(user_id: int, increment: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT clicks, total_clicks, level FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    if result:
        new_clicks = result[0] + increment
        new_total = result[1] + increment
        new_level = 1 + new_total // 100
        cursor.execute(
            "UPDATE users SET clicks = ?, total_clicks = ?, level = ? WHERE user_id = ?",
            (new_clicks, new_total, new_level, user_id)
        )
        conn.commit()
    conn.close()
    return True

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

def claim_daily_bonus(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT last_daily, daily_streak, clicks FROM users WHERE user_id = ?", (user_id,))
    last_daily, daily_streak, clicks = cursor.fetchone()
    today = datetime.now().date()
    last_date = datetime.fromisoformat(last_daily).date() if last_daily else None
    
    if last_date == today:
        conn.close()
        return (0, daily_streak, clicks)
    
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
    return (bonus, daily_streak, new_clicks)

def get_skins_list() -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, emoji, price_clicks, tap_bonus FROM skins")
    skins = cursor.fetchall()
    conn.close()
    return [{"id": s[0], "name": s[1], "emoji": s[2], "price": s[3], "bonus": s[4]} for s in skins]

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

def equip_skin(user_id: int, skin_id: int) -> str:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM user_skins WHERE user_id = ? AND skin_id = ?", (user_id, skin_id))
    if not cursor.fetchone():
        conn.close()
        return None
    cursor.execute("SELECT emoji FROM skins WHERE id = ?", (skin_id,))
    emoji = cursor.fetchone()[0]
    cursor.execute("UPDATE users SET current_skin = ? WHERE user_id = ?", (emoji, user_id))
    conn.commit()
    conn.close()
    return emoji

def upgrade_tap_power(user_id: int):
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
        return (True, new_tap_power, price, new_clicks)
    conn.close()
    return (False, tap_power, price, clicks)

def upgrade_energy(user_id: int):
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
        return (True, new_energy, price, new_clicks)
    conn.close()
    return (False, energy, price, clicks)

def upgrade_passive_income(user_id: int):
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
        return (True, new_passive, price, new_clicks)
    conn.close()
    return (False, passive_income, price, clicks)

def buy_premium(user_id: int, days: int = 30) -> bool:
    from datetime import timedelta
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
        result.append({"id": q_id, "name": name, "description": desc, "target": target, "reward": reward, "progress": progress, "completed": completed})
    conn.close()
    return result

def get_leaderboard(limit: int = 20) -> List[Tuple]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, total_clicks FROM users ORDER BY total_clicks DESC LIMIT ?", (limit,))
    result = cursor.fetchall()
    conn.close()
    return result

def get_referral_count(user_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def claim_referral_reward(user_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND reward_claimed = 0", (user_id,))
    count = cursor.fetchone()[0]
    if count == 0:
        conn.close()
        return 0
    reward = count * 1000
    cursor.execute("SELECT clicks FROM users WHERE user_id = ?", (user_id,))
    clicks = cursor.fetchone()[0]
    cursor.execute("UPDATE users SET clicks = ? WHERE user_id = ?", (clicks + reward, user_id))
    cursor.execute("UPDATE referrals SET reward_claimed = 1 WHERE referrer_id = ? AND reward_claimed = 0", (user_id,))
    conn.commit()
    conn.close()
    return reward

# ==================== API РОУТЫ ====================

@app.get("/", response_class=HTMLResponse)
async def mini_app(request: Request, user_id: int = None):
    if not user_id:
        user_id = 1
    return templates.TemplateResponse("game.html", {"request": request, "user_id": user_id})

@app.post("/api/click")
async def api_click(data: ClickData):
    success = update_clicks(data.user_id, data.clicks)
    if success:
        stats = get_user_stats(data.user_id)
        return JSONResponse(content=stats)
    raise HTTPException(status_code=500, detail="Failed to update clicks")

@app.get("/api/stats/{user_id}")
async def api_stats(user_id: int):
    return JSONResponse(content=get_user_stats(user_id))

@app.post("/api/collect_passive")
async def api_collect_passive(data: UserIdData):
    earned = collect_passive_income(data.user_id)
    stats = get_user_stats(data.user_id)
    return {"earned": earned, "clicks": stats["clicks"]}

@app.post("/api/daily")
async def api_daily(data: UserIdData):
    bonus, streak, clicks = claim_daily_bonus(data.user_id)
    return {"bonus": bonus, "streak": streak, "clicks": clicks}

@app.get("/api/skins/{user_id}")
async def api_skins(user_id: int):
    skins = get_skins_list()
    user_skins = get_user_skins(user_id)
    stats = get_user_stats(user_id)
    result = []
    for s in skins:
        owned = s["id"] in user_skins
        result.append({
            "id": s["id"],
            "name": s["name"],
            "emoji": s["emoji"],
            "price": s["price"],
            "bonus": s["bonus"],
            "owned": owned,
            "equipped": stats["skin"] == s["emoji"] if owned else False
        })
    return result

@app.post("/api/buy_skin")
async def api_buy_skin(data: SkinData):
    success = buy_skin(data.user_id, data.skin_id)
    stats = get_user_stats(data.user_id)
    user_skins = get_user_skins(data.user_id)
    return {"success": success, "clicks": stats["clicks"], "user_skins": user_skins}

@app.post("/api/equip_skin")
async def api_equip_skin(data: SkinData):
    emoji = equip_skin(data.user_id, data.skin_id)
    stats = get_user_stats(data.user_id)
    return {"success": emoji is not None, "skin": stats["skin"]}

@app.get("/api/upgrades/{user_id}")
async def api_upgrades(user_id: int):
    stats = get_user_stats(user_id)
    tap_price = stats["tap_power"] * 100
    energy_price = (stats["energy"] // 100) * 100
    passive_price = 500 + stats["passive_income"] * 100
    return {"tap_price": tap_price, "energy_price": energy_price, "passive_price": passive_price}

@app.post("/api/upgrade_tap")
async def api_upgrade_tap(data: UserIdData):
    success, new_value, price, new_clicks = upgrade_tap_power(data.user_id)
    stats = get_user_stats(data.user_id)
    return {"success": success, "new_value": new_value, "price": price, "clicks": new_clicks if success else stats["clicks"]}

@app.post("/api/upgrade_energy")
async def api_upgrade_energy(data: UserIdData):
    success, new_value, price, new_clicks = upgrade_energy(data.user_id)
    stats = get_user_stats(data.user_id)
    return {"success": success, "new_value": new_value, "price": price, "clicks": new_clicks if success else stats["clicks"]}

@app.post("/api/upgrade_passive")
async def api_upgrade_passive(data: UserIdData):
    success, new_value, price, new_clicks = upgrade_passive_income(data.user_id)
    stats = get_user_stats(data.user_id)
    return {"success": success, "new_value": new_value, "price": price, "clicks": new_clicks if success else stats["clicks"]}

@app.post("/api/buy_premium")
async def api_buy_premium(data: UserIdData):
    success = buy_premium(data.user_id, 30)
    stats = get_user_stats(data.user_id)
    return {"success": success, "clicks": stats["clicks"]}

@app.get("/api/quests/{user_id}")
async def api_quests(user_id: int):
    return get_daily_quests(user_id)

@app.get("/api/leaderboard")
async def api_leaderboard():
    leaderboard = get_leaderboard(20)
    return [{"user_id": uid, "total_clicks": clicks} for uid, clicks in leaderboard]

@app.get("/api/referrals/{user_id}")
async def api_referrals(user_id: int):
    count = get_referral_count(user_id)
    return {"count": count}

@app.post("/api/claim_referral")
async def api_claim_referral(data: UserIdData):
    reward = claim_referral_reward(data.user_id)
    stats = get_user_stats(data.user_id)
    return {"reward": reward, "clicks": stats["clicks"]}

@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

# Импорт timedelta для daily_bonus
from datetime import timedelta