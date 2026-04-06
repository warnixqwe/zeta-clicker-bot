import os
import asyncpg
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

app = FastAPI()

DATABASE_URL = os.getenv("DATABASE_URL")

class ClickData(BaseModel):
    user_id: int
    clicks: int

async def init_db():
    conn = await asyncpg.connect(DATABASE_URL)
    
    # Удаляем старую таблицу, если есть
    await conn.execute("DROP TABLE IF EXISTS users")
    
    # Создаём новую с правильными колонками
    await conn.execute("""
        CREATE TABLE users (
            user_id BIGINT PRIMARY KEY,
            balance BIGINT DEFAULT 0,
            profit_per_tap INTEGER DEFAULT 1,
            coins_for_upgrade BIGINT DEFAULT 50000000,
            profit_per_hour BIGINT DEFAULT 229150,
            level INTEGER DEFAULT 7,
            max_level INTEGER DEFAULT 10,
            boost_energy INTEGER DEFAULT 4500,
            max_energy INTEGER DEFAULT 4500
        )
    """)
    await conn.close()

async def get_user_stats(user_id: int):
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
    if not row:
        await conn.execute("""
            INSERT INTO users (user_id, balance, profit_per_tap, coins_for_upgrade, profit_per_hour, level, max_level, boost_energy, max_energy)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """, user_id, 0, 1, 50000000, 229150, 7, 10, 4500, 4500)
        await conn.close()
        return {
            "balance": 0,
            "profit_per_tap": 1,
            "coins_for_upgrade": 50000000,
            "profit_per_hour": 229150,
            "level": 7,
            "max_level": 10,
            "boost_energy": 4500,
            "max_energy": 4500
        }
    await conn.close()
    return {
        "balance": row["balance"],
        "profit_per_tap": row["profit_per_tap"],
        "coins_for_upgrade": row["coins_for_upgrade"],
        "profit_per_hour": row["profit_per_hour"],
        "level": row["level"],
        "max_level": row["max_level"],
        "boost_energy": row["boost_energy"],
        "max_energy": row["max_energy"]
    }

async def update_balance(user_id: int, increment: int):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("UPDATE users SET balance = balance + $1 WHERE user_id = $2", increment, user_id)
    await conn.close()

@app.post("/api/click")
async def handle_click(data: ClickData):
    await update_balance(data.user_id, data.clicks)
    stats = await get_user_stats(data.user_id)
    return stats

@app.get("/api/get_stats")
async def get_stats(user_id: int):
    return await get_user_stats(user_id)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.on_event("startup")
async def startup():
    await init_db()

@app.get("/", response_class=HTMLResponse)
async def mini_app(user_id: int = 1):
    stats = await get_user_stats(user_id)
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>OTMeta Clicker</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; user-select: none; -webkit-tap-highlight-color: transparent; }}
        body {{ min-height: 100vh; background: radial-gradient(circle at 20% 30%, #0a0f1e, #03060c); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; padding: 20px; }}
        .container {{ max-width: 450px; margin: 0 auto; }}
        .card {{ background: rgba(20, 30, 45, 0.7); backdrop-filter: blur(12px); border-radius: 32px; padding: 20px; margin-bottom: 16px; border: 1px solid rgba(255, 215, 0, 0.2); box-shadow: 0 8px 32px rgba(0,0,0,0.3); }}
        .card-header {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 16px; }}
        .title {{ font-size: 24px; font-weight: bold; background: linear-gradient(135deg, #ffd700, #ff8c00); -webkit-background-clip: text; background-clip: text; color: transparent; }}
        .badge {{ background: rgba(0,0,0,0.5); padding: 4px 12px; border-radius: 20px; font-size: 12px; color: #ffd700; }}
        .balance-row {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 20px; }}
        .balance-label {{ color: rgba(255,255,255,0.6); font-size: 14px; }}
        .balance-value {{ font-size: 32px; font-weight: bold; color: #ffd700; }}
        .stats-grid {{ display: flex; flex-direction: column; gap: 12px; margin-bottom: 20px; }}
        .stat-item {{ display: flex; justify-content: space-between; align-items: center; }}
        .stat-label {{ color: rgba(255,255,255,0.5); font-size: 14px; }}
        .stat-value {{ color: white; font-size: 18px; font-weight: 600; }}
        .highlight {{ color: #ffd700; }}
        .level-container {{ display: flex; justify-content: space-between; align-items: center; margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.1); }}
        .level-text {{ color: #ffd700; font-weight: bold; }}
        .legendary {{ color: #ff8c00; font-weight: bold; }}
        .energy-container {{ margin-top: 12px; }}
        .energy-bar {{ width: 100%; height: 8px; background: rgba(255,255,255,0.2); border-radius: 4px; overflow: hidden; margin-top: 8px; }}
        .energy-fill {{ height: 100%; background: linear-gradient(90deg, #00ff88, #00cc66); border-radius: 4px; transition: width 0.2s; width: {stats["boost_energy"]/stats["max_energy"]*100}%; }}
        .tap-area {{ text-align: center; margin: 30px 0; }}
        .coin {{ width: 200px; height: 200px; background: radial-gradient(circle at 30% 30%, #ffd700, #b8860b); border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 80px; font-weight: bold; color: #fff; text-shadow: 0 4px 10px rgba(0,0,0,0.3); cursor: pointer; transition: transform 0.1s ease; box-shadow: 0 20px 30px rgba(0,0,0,0.3); }}
        .coin:active {{ transform: scale(0.95); }}
        .button-group {{ display: flex; gap: 12px; margin: 20px 0; }}
        .btn {{ flex: 1; background: linear-gradient(135deg, #2a3a5a, #1a2a4a); border: none; border-radius: 24px; padding: 14px; color: white; font-size: 14px; font-weight: 600; cursor: pointer; text-align: center; }}
        .btn:active {{ transform: scale(0.96); }}
        .btn-boost {{ background: linear-gradient(135deg, #ff8c00, #ff4500); }}
        .btn-secret {{ background: rgba(255,255,255,0.1); width: 100%; margin-top: 12px; }}
        .tap-value {{ position: fixed; pointer-events: none; font-size: 28px; font-weight: bold; color: #ffd700; text-shadow: 0 0 10px rgba(0,0,0,0.5); z-index: 1000; animation: floatUp 0.6s ease-out forwards; }}
        @keyframes floatUp {{ 0% {{ opacity: 1; transform: translateY(0) scale(0.8); }} 100% {{ opacity: 0; transform: translateY(-80px) scale(1.2); }} }}
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <div class="card-header">
                <span class="title">OTMeta</span>
                <span class="badge">60T</span>
            </div>
            <div class="balance-row">
                <span class="balance-label">💰 Баланс</span>
                <span class="balance-value" id="balance">{stats["balance"]}</span>
            </div>
            <div class="stats-grid">
                <div class="stat-item">
                    <span class="stat-label">Прибыль за тап</span>
                    <span class="stat-value highlight" id="profitPerTap">+{stats["profit_per_tap"]}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Монет для апа</span>
                    <span class="stat-value" id="upgradeCost">{stats["coins_for_upgrade"]}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Прибыль в час</span>
                    <span class="stat-value highlight" id="profitPerHour">+{stats["profit_per_hour"]}K</span>
                </div>
            </div>
            <div class="level-container">
                <span class="level-text">Legendary</span>
                <span class="legendary">Level {stats["level"]}/{stats["max_level"]}</span>
            </div>
            <div class="energy-container">
                <div class="stat-item">
                    <span class="stat-label">Boost Energy</span>
                    <span class="stat-value" id="energyValue">{stats["boost_energy"]} / {stats["max_energy"]}</span>
                </div>
                <div class="energy-bar">
                    <div class="energy-fill" id="energyFill"></div>
                </div>
            </div>
        </div>
        
        <div class="tap-area">
            <div class="coin" id="coin">💰</div>
        </div>
        
        <div class="button-group">
            <button class="btn" id="upgradeBtn">⬆️ Улучшить</button>
            <button class="btn btn-boost" id="boostBtn">⚡ Boost</button>
        </div>
        <button class="btn btn-secret" id="secretBtn">❓ как забрать секретный</button>
    </div>
    
    <script>
        const tg = window.Telegram.WebApp;
        tg.ready();
        tg.expand();
        
        const userId = new URLSearchParams(window.location.search).get('user_id') || 1;
        let balance = {stats["balance"]};
        let profitPerTap = {stats["profit_per_tap"]};
        let upgradeCost = {stats["coins_for_upgrade"]};
        let profitPerHour = {stats["profit_per_hour"]};
        let level = {stats["level"]};
        let maxLevel = {stats["max_level"]};
        let boostEnergy = {stats["boost_energy"]};
        let maxEnergy = {stats["max_energy"]};
        
        function updateUI() {{
            document.getElementById('balance').innerText = balance;
            document.getElementById('profitPerTap').innerText = '+' + profitPerTap;
            document.getElementById('upgradeCost').innerText = upgradeCost;
            document.getElementById('profitPerHour').innerText = '+' + profitPerHour + 'K';
            document.getElementById('energyValue').innerText = boostEnergy + ' / ' + maxEnergy;
            document.getElementById('energyFill').style.width = (boostEnergy / maxEnergy * 100) + '%';
        }}
        
        async function loadStats() {{
            try {{
                const res = await fetch('/api/get_stats?user_id=' + userId);
                const data = await res.json();
                balance = data.balance;
                profitPerTap = data.profit_per_tap;
                upgradeCost = data.coins_for_upgrade;
                profitPerHour = data.profit_per_hour;
                level = data.level;
                maxLevel = data.max_level;
                boostEnergy = data.boost_energy;
                maxEnergy = data.max_energy;
                updateUI();
            }} catch(e) {{ console.error(e); }}
        }}
        
        async function sendClick() {{
            try {{
                const res = await fetch('/api/click', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ user_id: userId, clicks: profitPerTap }})
                }});
                const data = await res.json();
                balance = data.balance;
                profitPerTap = data.profit_per_tap;
                upgradeCost = data.coins_for_upgrade;
                profitPerHour = data.profit_per_hour;
                boostEnergy = data.boost_energy;
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
        
        document.getElementById('coin').onclick = async (e) => {{
            if (boostEnergy <= 0) {{
                tg.showPopup({{ title: '😫 Нет энергии!', message: 'Подожди, энергия восстановится.', buttons: [{{type: 'ok'}}] }});
                return;
            }}
            const rect = e.target.getBoundingClientRect();
            const x = rect.left + rect.width / 2;
            const y = rect.top;
            showFloatingNumber(x, y, profitPerTap);
            boostEnergy -= 1;
            updateUI();
            await sendClick();
        }};
        
        document.getElementById('upgradeBtn').onclick = () => tg.showPopup({{ title: '⬆️ Улучшение', message: 'Скоро будет!', buttons: [{{type: 'ok'}}] }});
        document.getElementById('boostBtn').onclick = () => tg.showPopup({{ title: '⚡ Boost', message: 'Скоро будет!', buttons: [{{type: 'ok'}}] }});
        document.getElementById('secretBtn').onclick = () => tg.showPopup({{ title: '❓ Секретный бонус', message: 'Следи за новостями в канале!', buttons: [{{type: 'ok'}}] }});
        
        setInterval(() => {{
            if (boostEnergy < maxEnergy) {{
                boostEnergy = Math.min(boostEnergy + 1, maxEnergy);
                updateUI();
            }}
        }}, 1000);
        
        loadStats();
    </script>
</body>
</html>'''
    
    return HTMLResponse(content=html)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)