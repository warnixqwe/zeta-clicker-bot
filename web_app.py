import os
import sqlite3
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
            current_skin TEXT DEFAULT '🦆',
            total_clicks INTEGER DEFAULT 0,
            last_daily TIMESTAMP DEFAULT NULL,
            daily_streak INTEGER DEFAULT 0,
            gems INTEGER DEFAULT 0
        )
    """)
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
            "clicks": result[0], "level": result[1], "energy": result[2], "tap_power": result[3],
            "passive_income": result[4], "skin": result[5], "total_clicks": result[6],
            "daily_streak": result[7], "gems": result[8]
        }
    else:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (user_id, clicks, level, energy, tap_power, passive_income, current_skin, total_clicks, daily_streak, gems) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (user_id, 0, 1, 1000, 1, 0, "🦆", 0, 0, 0))
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

@app.post("/api/click")
async def handle_click(data: ClickData):
    update_clicks(data.user_id, data.clicks)
    stats = get_user_stats(data.user_id)
    return {
        "clicks": stats["clicks"],
        "level": stats["level"],
        "energy": stats["energy"],
        "tap_power": stats["tap_power"],
        "passive_income": stats["passive_income"],
        "gems": stats["gems"]
    }

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

@app.get("/api/get_stats")
async def get_stats(user_id: int):
    return get_user_stats(user_id)

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
        body {{ min-height: 100vh; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); font-family: Arial, sans-serif; padding: 20px; display: flex; justify-content: center; align-items: center; }}
        .container {{ max-width: 500px; width: 100%; background: rgba(255,255,255,0.05); border-radius: 32px; padding: 20px; }}
        .stats {{ background: rgba(0,0,0,0.3); border-radius: 24px; padding: 16px; margin-bottom: 24px; }}
        .stat-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.1); }}
        .stat-row:last-child {{ border-bottom: none; }}
        .stat-label {{ color: #aaa; font-size: 14px; }}
        .stat-value {{ color: #ffd700; font-size: 20px; font-weight: bold; }}
        .duck-container {{ display: flex; justify-content: center; margin: 20px 0; }}
        .duck {{ font-size: 180px; cursor: pointer; transition: transform 0.1s; }}
        .duck:active {{ transform: scale(0.94); }}
        .button-grid {{ display: flex; flex-direction: column; gap: 12px; margin: 24px 0; }}
        .action-btn {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none; border-radius: 16px; padding: 14px; color: white; font-size: 16px; font-weight: 600; cursor: pointer; text-align: center; }}
        .action-btn:active {{ transform: scale(0.96); }}
        .energy-bar {{ width: 100%; height: 12px; background: rgba(255,255,255,0.2); border-radius: 6px; margin: 10px 0; overflow: hidden; }}
        .energy-fill {{ height: 100%; background: linear-gradient(90deg, #00ff88, #00cc66); border-radius: 6px; transition: width 0.2s; }}
        .tap-value {{ position: fixed; pointer-events: none; font-size: 28px; font-weight: bold; color: #ffd700; animation: floatUp 0.6s ease-out forwards; z-index: 1000; }}
        @keyframes floatUp {{ 0% {{ opacity: 1; transform: translateY(0) scale(0.8); }} 100% {{ opacity: 0; transform: translateY(-80px) scale(1.2); }} }}
    </style>
</head>
<body>
    <div class="container">
        <div class="stats">
            <div class="stat-row"><span class="stat-label">🦆 Уровень</span><span class="stat-value" id="levelValue">{stats["level"]}</span></div>
            <div class="stat-row"><span class="stat-label">💰 Клики</span><span class="stat-value" id="clicksValue">{stats["clicks"]}</span></div>
            <div class="stat-row"><span class="stat-label">💪 Сила клика</span><span class="stat-value" id="tapPowerValue">+{stats["tap_power"]}</span></div>
            <div class="stat-row"><span class="stat-label">⚡ Энергия</span><span class="stat-value" id="energyValue">{stats["energy"]}/1000</span></div>
        </div>
        <div class="energy-bar"><div class="energy-fill" id="energyFill" style="width: {stats["energy"]/10}%"></div></div>
        <div class="duck-container"><div class="duck" id="duck">🦆</div></div>
        <div class="button-grid">
            <button class="action-btn" id="upgradeTapBtn">💪 Улучшить тап</button>
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
        let energy = {stats["energy"]};
        let maxEnergy = 1000;
        
        function updateUI() {{
            document.getElementById('clicksValue').innerText = clicks;
            document.getElementById('levelValue').innerText = level;
            document.getElementById('tapPowerValue').innerText = '+' + tapPower;
            document.getElementById('energyValue').innerText = Math.floor(energy) + '/1000';
            document.getElementById('energyFill').style.width = (energy / 10) + '%';
        }}
        
        async function loadStats() {{
            try {{
                const res = await fetch('/api/get_stats?user_id=' + userId);
                const data = await res.json();
                clicks = data.clicks;
                level = data.level;
                tapPower = data.tap_power;
                energy = data.energy;
                updateUI();
            }} catch(e) {{ console.error('Load stats error:', e); }}
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
                energy = data.energy;
                updateUI();
            }} catch(e) {{ console.error('Click error:', e); }}
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
                }} else {{
                    tg.showPopup({{title: '❌ Ошибка', message: data.message, buttons: [{{type: 'ok'}}]}});
                }}
            }} else {{
                tg.showPopup({{title: '❌ Не хватает кликов', message: 'Нужно: ' + price + ' кликов', buttons: [{{type: 'ok'}}]}});
            }}
        }};
        
        setInterval(() => {{
            if (energy < maxEnergy) {{
                energy = Math.min(energy + 5, maxEnergy);
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