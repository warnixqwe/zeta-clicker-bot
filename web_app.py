import os
import sqlite3
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

app = FastAPI()

class ClickData(BaseModel):
    user_id: int
    clicks: int

DB_PATH = os.path.join(os.path.dirname(__file__), "zeta_clicker.db")

def get_user_stats(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT clicks, level, tap_power, current_skin FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            "clicks": int(result[0]),
            "level": int(result[1]),
            "tap_power": int(result[2]),
            "skin": str(result[3]) if result[3] else "🦆"
        }
    else:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (user_id, clicks, level, tap_power, current_skin, total_clicks, daily_streak) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, 0, 1, 1, "🦆", 0, 0)
        )
        conn.commit()
        conn.close()
        return {"clicks": 0, "level": 1, "tap_power": 1, "skin": "🦆"}

def update_clicks(user_id: int, increment: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT clicks, total_clicks FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if result:
        new_clicks = result[0] + increment
        new_total = result[1] + increment
        cursor.execute("UPDATE users SET clicks = ?, total_clicks = ? WHERE user_id = ?", (new_clicks, new_total, user_id))
        conn.commit()
    conn.close()

def generate_html(clicks: int, level: int, tap_power: int, skin: str) -> str:
    """Генерирует HTML-страницу с подставленными значениями"""
    return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>Zeta Clicker</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            user-select: none;
            -webkit-tap-highlight-color: transparent;
        }}
        body {{
            min-height: 100vh;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        .container {{
            max-width: 500px;
            width: 100%;
            background: rgba(255,255,255,0.05);
            border-radius: 32px;
            backdrop-filter: blur(10px);
            padding: 20px;
        }}
        .stats {{
            background: rgba(0,0,0,0.3);
            border-radius: 24px;
            padding: 16px;
            margin-bottom: 24px;
        }}
        .stat-row {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        .stat-row:last-child {{ border-bottom: none; }}
        .stat-label {{ color: #aaa; font-size: 14px; }}
        .stat-value {{ color: #ffd700; font-size: 20px; font-weight: bold; }}
        .duck-container {{ display: flex; justify-content: center; margin: 20px 0; }}
        .duck {{ font-size: 180px; cursor: pointer; transition: transform 0.1s; filter: drop-shadow(0 10px 20px rgba(0,0,0,0.3)); }}
        .duck:active {{ transform: scale(0.94); }}
        .energy-section {{ margin: 20px 0; }}
        .energy-label {{ display: flex; justify-content: space-between; font-size: 12px; color: #aaa; margin-bottom: 6px; }}
        .energy-bar-bg {{ background: rgba(255,255,255,0.15); border-radius: 12px; height: 12px; overflow: hidden; }}
        .energy-fill {{ width: 100%; height: 100%; background: linear-gradient(90deg, #00c6ff, #0072ff); border-radius: 12px; transition: width 0.2s; }}
        .button-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 24px 0; }}
        .action-btn {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 16px;
            padding: 14px 8px;
            color: white;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            text-align: center;
        }}
        .action-btn:active {{ transform: scale(0.96); opacity: 0.9; }}
        .full-width {{ width: 100%; background: rgba(255,255,255,0.1); }}
        .tap-value {{
            position: fixed;
            pointer-events: none;
            font-size: 28px;
            font-weight: bold;
            color: #ffd700;
            animation: floatUp 0.6s ease-out forwards;
            z-index: 1000;
        }}
        @keyframes floatUp {{
            0% {{ opacity: 1; transform: translateY(0) scale(0.8); }}
            100% {{ opacity: 0; transform: translateY(-80px) scale(1.2); }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="stats">
            <div class="stat-row"><span class="stat-label">🦆 Уровень</span><span class="stat-value" id="levelValue">{level}</span></div>
            <div class="stat-row"><span class="stat-label">💰 Клики</span><span class="stat-value" id="clicksValue">{clicks}</span></div>
            <div class="stat-row"><span class="stat-label">💪 Сила клика</span><span class="stat-value" id="tapPowerValue">+{tap_power}</span></div>
        </div>
        <div class="duck-container"><div class="duck" id="duck">{skin}</div></div>
        <div class="energy-section">
            <div class="energy-label"><span>⚡ Энергия</span><span id="energyText">1000/1000</span></div>
            <div class="energy-bar-bg"><div class="energy-fill" id="energyFill" style="width: 100%"></div></div>
        </div>
        <div class="button-grid">
            <button class="action-btn" id="profileBtn">📊 Профиль</button>
            <button class="action-btn" id="shopBtn">👕 Магазин</button>
            <button class="action-btn" id="upgradeBtn">💎 Прокачка</button>
            <button class="action-btn" id="questsBtn">📋 Задания</button>
            <button class="action-btn" id="leaderboardBtn">🏆 Топ</button>
            <button class="action-btn" id="friendsBtn">👥 Друзья</button>
            <button class="action-btn" id="passiveBtn">💰 Пассивка</button>
            <button class="action-btn" id="dailyBtn">🎁 Ежедневный</button>
        </div>
        <button class="action-btn full-width" id="closeBtn">✖️ Закрыть</button>
    </div>
    <script>
        const tg = window.Telegram.WebApp;
        tg.ready();
        tg.expand();
        
        const userId = new URLSearchParams(window.location.search).get('user_id') || 1;
        let clicks = {clicks};
        let level = {level};
        let tapPower = {tap_power};
        let energy = 1000;
        let maxEnergy = 1000;
        let regenInterval = null;
        
        const duck = document.getElementById('duck');
        const clicksSpan = document.getElementById('clicksValue');
        const levelSpan = document.getElementById('levelValue');
        const tapPowerSpan = document.getElementById('tapPowerValue');
        const energyFill = document.getElementById('energyFill');
        const energyText = document.getElementById('energyText');
        
        function updateUI() {{
            clicksSpan.textContent = clicks;
            levelSpan.textContent = level;
            tapPowerSpan.textContent = `+${{tapPower}}`;
            energyFill.style.width = `${{(energy / maxEnergy) * 100}}%`;
            energyText.textContent = `${{Math.floor(energy)}}/${{maxEnergy}}`;
        }}
        
        function showFloatingNumber(x, y, value) {{
            const el = document.createElement('div');
            el.className = 'tap-value';
            el.textContent = `+${{value}}`;
            el.style.left = `${{x}}px`;
            el.style.top = `${{y}}px`;
            document.body.appendChild(el);
            setTimeout(() => el.remove(), 600);
        }}
        
        async function sendClick(increment) {{
            try {{
                const response = await fetch('/api/click', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ user_id: userId, clicks: increment }})
                }});
                const data = await response.json();
                clicks = data.clicks;
                level = data.level;
                tapPower = data.tap_power;
                updateUI();
            }} catch(e) {{ console.error('Click error:', e); }}
        }}
        
        function startEnergyRegen() {{
            if (regenInterval) clearInterval(regenInterval);
            regenInterval = setInterval(() => {{
                if (energy < maxEnergy) {{
                    energy = Math.min(energy + 5, maxEnergy);
                    updateUI();
                }} else if (energy >= maxEnergy && regenInterval) {{
                    clearInterval(regenInterval);
                    regenInterval = null;
                }}
            }}, 1000);
        }}
        
        duck.addEventListener('click', async (e) => {{
            if (energy <= 0) {{
                tg.showPopup({{ title: '😫 Нет энергии!', message: 'Подожди, энергия восстановится.', buttons: [{{type: 'ok'}}] }});
                return;
            }}
            const rect = duck.getBoundingClientRect();
            const x = rect.left + rect.width / 2;
            const y = rect.top;
            showFloatingNumber(x, y, tapPower);
            energy = Math.max(0, energy - 1);
            updateUI();
            await sendClick(tapPower);
            if (energy < maxEnergy) startEnergyRegen();
        }});
        
        async function loadStats() {{
            try {{
                const response = await fetch(`/api/stats/${{userId}}`);
                const data = await response.json();
                clicks = data.clicks;
                level = data.level;
                tapPower = data.tap_power;
                updateUI();
            }} catch(e) {{ console.error('Load error:', e); }}
        }}
        
        document.getElementById('profileBtn').onclick = () => tg.showPopup({{title: 'Профиль', message: `Клики: ${{clicks}}\\nУровень: ${{level}}\\nСила: +${{tapPower}}`, buttons: [{{type: 'ok'}}]}});
        document.getElementById('shopBtn').onclick = () => tg.showPopup({{title: 'Магазин', message: 'Скоро тут будут скины!', buttons: [{{type: 'ok'}}]}});
        document.getElementById('upgradeBtn').onclick = () => tg.showPopup({{title: 'Прокачка', message: 'Улучшай силу клика!', buttons: [{{type: 'ok'}}]}});
        document.getElementById('questsBtn').onclick = () => tg.showPopup({{title: 'Задания', message: 'Ежедневные задания', buttons: [{{type: 'ok'}}]}});
        document.getElementById('leaderboardBtn').onclick = () => tg.showPopup({{title: 'Топ игроков', message: 'Скоро появится', buttons: [{{type: 'ok'}}]}});
        document.getElementById('friendsBtn').onclick = () => tg.showPopup({{title: 'Друзья', message: 'Реферальная система', buttons: [{{type: 'ok'}}]}});
        document.getElementById('passiveBtn').onclick = () => tg.showPopup({{title: 'Пассивный доход', message: 'Доход будет начисляться', buttons: [{{type: 'ok'}}]}});
        document.getElementById('dailyBtn').onclick = () => tg.showPopup({{title: 'Ежедневный бонус', message: 'Заходи каждый день!', buttons: [{{type: 'ok'}}]}});
        document.getElementById('closeBtn').onclick = () => tg.close();
        
        loadStats();
        startEnergyRegen();
    </script>
</body>
</html>'''

@app.get("/", response_class=HTMLResponse)
async def mini_app(user_id: int = 1):
    stats = get_user_stats(user_id)
    html = generate_html(
        clicks=stats["clicks"],
        level=stats["level"],
        tap_power=stats["tap_power"],
        skin=stats["skin"]
    )
    return HTMLResponse(content=html)

@app.post("/api/click")
async def handle_click(data: ClickData):
    update_clicks(data.user_id, data.clicks)
    stats = get_user_stats(data.user_id)
    return JSONResponse(content={
        "clicks": stats["clicks"],
        "level": stats["level"],
        "tap_power": stats["tap_power"]
    })

@app.get("/api/stats/{user_id}")
async def get_stats(user_id: int):
    stats = get_user_stats(user_id)
    return JSONResponse(content={
        "clicks": stats["clicks"],
        "level": stats["level"],
        "tap_power": stats["tap_power"],
        "skin": stats["skin"]
    })

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)