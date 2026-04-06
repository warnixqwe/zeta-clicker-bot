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
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            clicks BIGINT DEFAULT 0,
            level INTEGER DEFAULT 1,
            energy INTEGER DEFAULT 1000,
            tap_power INTEGER DEFAULT 1,
            current_skin TEXT DEFAULT '🦆',
            total_clicks BIGINT DEFAULT 0,
            gems INTEGER DEFAULT 0
        )
    """)
    await conn.close()

async def get_user_stats(user_id: int):
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow("SELECT clicks, level, energy, tap_power, current_skin, total_clicks, gems FROM users WHERE user_id = $1", user_id)
    if not row:
        await conn.execute("INSERT INTO users (user_id, clicks, level, energy, tap_power, current_skin, total_clicks, gems) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)", user_id, 0, 1, 1000, 1, '🦆', 0, 0)
        await conn.close()
        return {"clicks": 0, "level": 1, "energy": 1000, "tap_power": 1, "skin": "🦆", "total_clicks": 0, "gems": 0}
    await conn.close()
    return {"clicks": row["clicks"], "level": row["level"], "energy": row["energy"], "tap_power": row["tap_power"], "skin": row["current_skin"], "total_clicks": row["total_clicks"], "gems": row["gems"]}

async def update_clicks(user_id: int, increment: int):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("UPDATE users SET clicks = clicks + $1, total_clicks = total_clicks + $1, energy = energy - 1 WHERE user_id = $2", increment, user_id)
    await conn.close()

@app.post("/api/click")
async def handle_click(data: ClickData):
    await update_clicks(data.user_id, data.clicks)
    stats = await get_user_stats(data.user_id)
    return stats

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
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            padding: 16px;
        }}
        
        .container {{
            max-width: 500px;
            margin: 0 auto;
        }}
        
        /* Карточка профиля */
        .card {{
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 24px;
            padding: 20px;
            margin-bottom: 16px;
            border: 1px solid rgba(255,255,255,0.2);
        }}
        
        .stats-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}
        
        .stats-label {{
            color: rgba(255,255,255,0.7);
            font-size: 14px;
        }}
        
        .stats-value {{
            color: #ffd700;
            font-size: 20px;
            font-weight: bold;
        }}
        
        /* Энергия */
        .energy-container {{
            margin-top: 12px;
        }}
        
        .energy-bar {{
            width: 100%;
            height: 8px;
            background: rgba(255,255,255,0.2);
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }}
        
        .energy-fill {{
            height: 100%;
            background: linear-gradient(90deg, #00ff88, #00cc66);
            border-radius: 4px;
            transition: width 0.2s;
            width: {stats["energy"]/10}%;
        }}
        
        /* Утка */
        .duck-container {{
            display: flex;
            justify-content: center;
            margin: 30px 0;
        }}
        
        .duck {{
            font-size: 180px;
            cursor: pointer;
            transition: transform 0.1s ease;
            filter: drop-shadow(0 10px 20px rgba(0,0,0,0.3));
        }}
        
        .duck:active {{
            transform: scale(0.95);
        }}
        
        /* Сетка кнопок */
        .grid-2 {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-top: 20px;
        }}
        
        .btn {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 16px;
            padding: 16px;
            color: white;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.1s, opacity 0.2s;
            text-align: center;
        }}
        
        .btn:active {{
            transform: scale(0.96);
            opacity: 0.9;
        }}
        
        .btn-full {{
            width: 100%;
            margin-top: 12px;
            background: rgba(255,255,255,0.15);
        }}
        
        /* Всплывающие числа */
        .tap-value {{
            position: fixed;
            pointer-events: none;
            font-size: 32px;
            font-weight: bold;
            color: #ffd700;
            text-shadow: 0 0 10px rgba(0,0,0,0.5);
            z-index: 1000;
            animation: floatUp 0.8s ease-out forwards;
        }}
        
        @keyframes floatUp {{
            0% {{
                opacity: 1;
                transform: translateY(0) scale(0.8);
            }}
            100% {{
                opacity: 0;
                transform: translateY(-100px) scale(1.5);
            }}
        }}
        
        /* Адаптация под тёмную тему Telegram */
        @media (prefers-color-scheme: dark) {{
            body {{
                background: linear-gradient(135deg, #0a0a1a 0%, #0f0f1f 100%);
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Карточка статистики -->
        <div class="card">
            <div class="stats-row">
                <span class="stats-label">🦆 Уровень</span>
                <span class="stats-value" id="levelValue">{stats["level"]}</span>
            </div>
            <div class="stats-row">
                <span class="stats-label">💰 Клики</span>
                <span class="stats-value" id="clicksValue">{stats["clicks"]}</span>
            </div>
            <div class="stats-row">
                <span class="stats-label">💪 Сила клика</span>
                <span class="stats-value" id="tapPowerValue">+{stats["tap_power"]}</span>
            </div>
            <div class="stats-row">
                <span class="stats-label">💎 Алмазы</span>
                <span class="stats-value" id="gemsValue">{stats["gems"]}</span>
            </div>
            <div class="energy-container">
                <div class="stats-row">
                    <span class="stats-label">⚡ Энергия</span>
                    <span class="stats-value" id="energyValue">{stats["energy"]}/1000</span>
                </div>
                <div class="energy-bar">
                    <div class="energy-fill" id="energyFill"></div>
                </div>
            </div>
        </div>
        
        <!-- Утка -->
        <div class="duck-container">
            <div class="duck" id="duck">{stats["skin"]}</div>
        </div>
        
        <!-- Кнопки -->
        <div class="grid-2">
            <button class="btn" id="upgradeBtn">💪 Улучшить тап</button>
            <button class="btn" id="dailyBtn">🎁 Ежедневный</button>
            <button class="btn" id="shopBtn">👕 Магазин</button>
            <button class="btn" id="profileBtn">📊 Профиль</button>
        </div>
        
        <button class="btn btn-full" id="closeBtn">✖️ Закрыть</button>
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
        let gems = {stats["gems"]};
        let maxEnergy = 1000;
        
        function updateUI() {{
            document.getElementById('clicksValue').innerText = clicks;
            document.getElementById('levelValue').innerText = level;
            document.getElementById('tapPowerValue').innerText = '+' + tapPower;
            document.getElementById('energyValue').innerText = Math.floor(energy) + '/1000';
            document.getElementById('gemsValue').innerText = gems;
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
                gems = data.gems;
                updateUI();
            }} catch(e) {{
                console.error('Load stats error:', e);
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
                energy = data.energy;
                gems = data.gems;
                updateUI();
            }} catch(e) {{
                console.error('Click error:', e);
            }}
        }}
        
        function showFloatingNumber(x, y, value) {{
            const el = document.createElement('div');
            el.className = 'tap-value';
            el.textContent = '+' + value;
            el.style.left = x + 'px';
            el.style.top = y + 'px';
            document.body.appendChild(el);
            setTimeout(() => el.remove(), 800);
        }}
        
        document.getElementById('duck').onclick = async (e) => {{
            if (energy <= 0) {{
                tg.showPopup({{
                    title: '😫 Нет энергии!',
                    message: 'Подожди, энергия восстановится.',
                    buttons: [{{type: 'ok'}}]
                }});
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
        
        document.getElementById('upgradeBtn').onclick = async () => {{
            const price = tapPower * 100;
            if (clicks >= price) {{
                const res = await fetch('/api/upgrade_tap?user_id=' + userId, {{method: 'POST'}});
                const data = await res.json();
                if (data.success) {{
                    tg.showPopup({{
                        title: '✅ Улучшено!',
                        message: 'Сила клика: +' + data.new_tap_power,
                        buttons: [{{type: 'ok'}}]
                    }});
                    await loadStats();
                }}
            }} else {{
                tg.showPopup({{
                    title: '❌ Не хватает кликов',
                    message: 'Нужно: ' + price + ' кликов',
                    buttons: [{{type: 'ok'}}]
                }});
            }}
        }};
        
        document.getElementById('dailyBtn').onclick = async () => {{
            tg.showPopup({{
                title: '🎁 Ежедневный бонус',
                message: 'Скоро появится!',
                buttons: [{{type: 'ok'}}]
            }});
        }};
        
        document.getElementById('shopBtn').onclick = async () => {{
            tg.showPopup({{
                title: '👕 Магазин',
                message: 'Скоро тут будут скины!',
                buttons: [{{type: 'ok'}}]
            }});
        }};
        
        document.getElementById('profileBtn').onclick = async () => {{
            tg.showPopup({{
                title: '📊 Профиль',
                message: 'Клики: ' + clicks + '\\nУровень: ' + level + '\\nСила клика: +' + tapPower + '\\nАлмазы: ' + gems,
                buttons: [{{type: 'ok'}}]
            }});
        }};
        
        document.getElementById('closeBtn').onclick = () => tg.close();
        
        // Восстановление энергии (1 в секунду)
        setInterval(() => {{
            if (energy < maxEnergy) {{
                energy = Math.min(energy + 1, maxEnergy);
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