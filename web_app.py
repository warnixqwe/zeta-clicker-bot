import os
import sqlite3
from datetime import datetime, timedelta
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
    cursor.execute("SELECT clicks, level, tap_power, passive_income, current_skin, total_clicks, daily_streak FROM users WHERE user_id = ?", (user_id,))
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
            "daily_streak": int(result[6])
        }
    else:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (user_id, clicks, level, tap_power, passive_income, current_skin, total_clicks, daily_streak) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, 0, 1, 1, 0, "🦆", 0, 0)
        )
        conn.commit()
        conn.close()
        return {"clicks": 0, "level": 1, "tap_power": 1, "passive_income": 0, "skin": "🦆", "total_clicks": 0, "daily_streak": 0}

def update_clicks(user_id: int, increment: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT clicks, total_clicks FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if result:
        new_clicks = result[0] + increment
        new_total = result[1] + increment
        new_level = 1 + new_total // 100
        cursor.execute("UPDATE users SET clicks = ?, total_clicks = ?, level = ? WHERE user_id = ?", (new_clicks, new_total, new_level, user_id))
        conn.commit()
    conn.close()

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
    
    return {"count": count, "unclaimed": unclaimed}

@app.get("/api/stats/{user_id}")
async def get_stats(user_id: int):
    stats = get_user_stats(user_id)
    return JSONResponse(content={
        "clicks": stats["clicks"],
        "level": stats["level"],
        "tap_power": stats["tap_power"],
        "passive_income": stats["passive_income"],
        "skin": stats["skin"],
        "daily_streak": stats["daily_streak"]
    })

@app.post("/api/click")
async def handle_click(data: ClickData):
    update_clicks(data.user_id, data.clicks)
    stats = get_user_stats(data.user_id)
    return JSONResponse(content={
        "clicks": stats["clicks"],
        "level": stats["level"],
        "tap_power": stats["tap_power"],
        "passive_income": stats["passive_income"]
    })

@app.get("/health")
async def health():
    return {"status": "ok"}

# ==================== HTML С МНОГОЭКРАННЫМ МЕНЮ ====================

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
        
        /* Экраны */
        .screen {{ display: none; }}
        .screen.active {{ display: block; }}
        
        /* Статистика */
        .stats {{ background: rgba(0,0,0,0.3); border-radius: 24px; padding: 16px; margin-bottom: 24px; }}
        .stat-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.1); }}
        .stat-row:last-child {{ border-bottom: none; }}
        .stat-label {{ color: #aaa; font-size: 14px; }}
        .stat-value {{ color: #ffd700; font-size: 20px; font-weight: bold; }}
        
        /* Утка */
        .duck-container {{ display: flex; justify-content: center; margin: 20px 0; }}
        .duck {{ font-size: 180px; cursor: pointer; transition: transform 0.1s; filter: drop-shadow(0 10px 20px rgba(0,0,0,0.3)); }}
        .duck:active {{ transform: scale(0.94); }}
        
        /* Кнопки */
        .button-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 24px 0; }}
        .action-btn {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none; border-radius: 16px; padding: 14px 8px; color: white; font-size: 14px; font-weight: 600; cursor: pointer; text-align: center; }}
        .action-btn:active {{ transform: scale(0.96); opacity: 0.9; }}
        .back-btn {{ background: rgba(255,255,255,0.1); margin-top: 20px; }}
        .full-width {{ width: 100%; }}
        
        /* Список скинов */
        .skin-list {{ margin: 20px 0; }}
        .skin-item {{ background: rgba(0,0,0,0.3); border-radius: 16px; padding: 12px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }}
        .skin-info {{ display: flex; align-items: center; gap: 12px; }}
        .skin-emoji {{ font-size: 40px; }}
        .skin-name {{ font-size: 16px; font-weight: bold; }}
        .skin-price {{ font-size: 12px; color: #ffd700; }}
        .skin-btn {{ background: #667eea; border: none; border-radius: 12px; padding: 8px 16px; color: white; cursor: pointer; }}
        .skin-btn.owned {{ background: #4caf50; }}
        .skin-btn.equipped {{ background: #ff9800; }}
        
        .tap-value {{ position: fixed; pointer-events: none; font-size: 28px; font-weight: bold; color: #ffd700; animation: floatUp 0.6s ease-out forwards; z-index: 1000; }}
        @keyframes floatUp {{ 0% {{ opacity: 1; transform: translateY(0) scale(0.8); }} 100% {{ opacity: 0; transform: translateY(-80px) scale(1.2); }} }}
    </style>
</head>
<body>
    <div class="container">
        <!-- ЭКРАН 1: ГЛАВНЫЙ -->
        <div id="mainScreen" class="screen active">
            <div class="stats">
                <div class="stat-row"><span class="stat-label">🦆 Уровень</span><span class="stat-value" id="levelValue">{stats["level"]}</span></div>
                <div class="stat-row"><span class="stat-label">💰 Клики</span><span class="stat-value" id="clicksValue">{stats["clicks"]}</span></div>
                <div class="stat-row"><span class="stat-label">💪 Сила клика</span><span class="stat-value" id="tapPowerValue">+{stats["tap_power"]}</span></div>
                <div class="stat-row"><span class="stat-label">⏱️ Пассивный доход</span><span class="stat-value" id="passiveValue">{stats["passive_income"]}/час</span></div>
            </div>
            <div class="duck-container"><div class="duck" id="duck">{stats["skin"]}</div></div>
            <div class="button-grid">
                <button class="action-btn" id="upgradeTapBtn">💪 Улучшить тап</button>
                <button class="action-btn" id="upgradePassiveBtn">💰 Улучшить пассивку</button>
                <button class="action-btn" id="collectPassiveBtn">💵 Собрать пассивку</button>
                <button class="action-btn" id="dailyBtn">🎁 Ежедневный</button>
                <button class="action-btn" id="openShopBtn">👕 Магазин</button>
                <button class="action-btn" id="referralBtn">👥 Рефералы</button>
                <button class="action-btn" id="profileBtn">📊 Профиль</button>
            </div>
            <button class="action-btn full-width" id="closeBtn">✖️ Закрыть</button>
        </div>
        
        <!-- ЭКРАН 2: МАГАЗИН -->
        <div id="shopScreen" class="screen">
            <h3 style="color: white; text-align: center; margin-bottom: 20px;">👕 МАГАЗИН СКИНОВ</h3>
            <div id="skinsList" class="skin-list">Загрузка...</div>
            <button class="action-btn full-width back-btn" onclick="showScreen('main')">◀️ Назад</button>
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
        
        function showScreen(screenName) {{
            document.getElementById('mainScreen').classList.remove('active');
            document.getElementById('shopScreen').classList.remove('active');
            if (screenName === 'main') document.getElementById('mainScreen').classList.add('active');
            if (screenName === 'shop') {{
                document.getElementById('shopScreen').classList.add('active');
                loadSkins();
            }}
        }}
        
        function updateStats() {{
            document.getElementById('clicksValue').textContent = clicks;
            document.getElementById('levelValue').textContent = level;
            document.getElementById('tapPowerValue').textContent = `+${{tapPower}}`;
            document.getElementById('passiveValue').textContent = `${{passiveIncome}}/час`;
        }}
        
        async function loadStats() {{
            try {{
                const res = await fetch(`/api/stats/${{userId}}`);
                const data = await res.json();
                clicks = data.clicks;
                level = data.level;
                tapPower = data.tap_power;
                passiveIncome = data.passive_income;
                currentSkin = data.skin;
                updateStats();
                document.getElementById('duck').textContent = currentSkin;
            }} catch(e) {{ console.error(e); }}
        }}
        
        async function loadSkins() {{
            try {{
                const res = await fetch(`/api/get_skins?user_id=${{userId}}`);
                const data = await res.json();
                const skinsList = document.getElementById('skinsList');
                skinsList.innerHTML = '';
                
                for (const skin of data.skins) {{
                    const div = document.createElement('div');
                    div.className = 'skin-item';
                    div.innerHTML = `
                        <div class="skin-info">
                            <span class="skin-emoji">${{skin.emoji}}</span>
                            <div>
                                <div class="skin-name">${{skin.name}}</div>
                                <div class="skin-price">+${{skin.bonus}} к силе | ${'{:.0f}'.format(skin.price)} кликов</div>
                            </div>
                        </div>
                    `;
                    
                    const btn = document.createElement('button');
                    if (skin.owned && skin.equipped) {{
                        btn.textContent = '✅ ЭКИПИРОВАН';
                        btn.className = 'skin-btn equipped';
                        btn.disabled = true;
                    }} else if (skin.owned) {{
                        btn.textContent = '⚡ ЭКИПИРОВАТЬ';
                        btn.className = 'skin-btn';
                        btn.onclick = () => equipSkin(skin.id);
                    }} else {{
                        btn.textContent = `💎 КУПИТЬ (${'{:.0f}'.format(skin.price)})`;
                        btn.className = 'skin-btn';
                        btn.onclick = () => buySkin(skin.id);
                    }}
                    div.appendChild(btn);
                    skinsList.appendChild(div);
                }}
            }} catch(e) {{ console.error(e); }}
        }}
        
        async function buySkin(skinId) {{
            const res = await fetch(`/api/buy_skin?user_id=${{userId}}&skin_id=${{skinId}}`, {{method: 'POST'}});
            const data = await res.json();
            if (data.success) {{
                tg.showPopup({{title: '✅ Покупка успешна!', message: `Вы купили ${{data.skin_name}}`, buttons: [{{type: 'ok'}}]}});
                await loadStats();
                await loadSkins();
            }} else {{
                tg.showPopup({{title: '❌ Не хватает кликов', message: `Нужно: ${{data.need}} кликов`, buttons: [{{type: 'ok'}}]}});
            }}
        }}
        
        async function equipSkin(skinId) {{
            const res = await fetch(`/api/equip_skin?user_id=${{userId}}&skin_id=${{skinId}}`, {{method: 'POST'}});
            const data = await res.json();
            if (data.success) {{
                tg.showPopup({{title: '✅ Скин экипирован!', message: `Теперь ваша утка: ${{data.skin}}`, buttons: [{{type: 'ok'}}]}});
                await loadStats();
                await loadSkins();
            }} else {{
                tg.showPopup({{title: '❌ Ошибка', message: data.message, buttons: [{{type: 'ok'}}]}});
            }}
        }}
        
        async function sendClick(increment) {{
            try {{
                await fetch('/api/click', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ user_id: userId, clicks: increment }})
                }});
                await loadStats();
            }} catch(e) {{ console.error(e); }}
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
        
        // Обработчики кнопок
        document.getElementById('duck').onclick = async (e) => {{
            const rect = e.target.getBoundingClientRect();
            const x = rect.left + rect.width / 2;
            const y = rect.top;
            showFloatingNumber(x, y, tapPower);
            clicks += tapPower;
            updateStats();
            await sendClick(tapPower);
        }};
        
        document.getElementById('upgradeTapBtn').onclick = async () => {{
            const res = await fetch(`/api/upgrade_tap?user_id=${{userId}}`, {{method: 'POST'}});
            const data = await res.json();
            if (data.success) {{
                tg.showPopup({{title: '✅ Улучшено!', message: `Сила клика: +${{data.new_tap_power}}`, buttons: [{{type: 'ok'}}]}});
                await loadStats();
            }} else {{
                tg.showPopup({{title: '❌ Не хватает кликов', message: `Нужно: ${{data.need}} кликов`, buttons: [{{type: 'ok'}}]}});
            }}
        }};
        
        document.getElementById('upgradePassiveBtn').onclick = async () => {{
            const res = await fetch(`/api/upgrade_passive?user_id=${{userId}}`, {{method: 'POST'}});
            const data = await res.json();
            if (data.success) {{
                tg.showPopup({{title: '✅ Пассивный доход улучшен!', message: `Теперь +${{data.new_passive}}/час`, buttons: [{{type: 'ok'}}]}});
                await loadStats();
            }} else {{
                tg.showPopup({{title: '❌ Не хватает кликов', message: `Нужно: ${{data.need}} кликов`, buttons: [{{type: 'ok'}}]}});
            }}
        }};
        
        document.getElementById('collectPassiveBtn').onclick = async () => {{
            const res = await fetch(`/api/collect_passive?user_id=${{userId}}`, {{method: 'POST'}});
            const data = await res.json();
            if (data.success) {{
                tg.showPopup({{title: '💰 Получено!', message: `+${{data.earned}} кликов!`, buttons: [{{type: 'ok'}}]}});
                await loadStats();
            }} else {{
                tg.showPopup({{title: '😴 Нет дохода', message: data.message, buttons: [{{type: 'ok'}}]}});
            }}
        }};
        
        document.getElementById('dailyBtn').onclick = async () => {{
            const res = await fetch(`/api/claim_daily?user_id=${{userId}}`, {{method: 'POST'}});
            const data = await res.json();
            if (data.success) {{
                tg.showPopup({{title: '🎁 Бонус получен!', message: `+${{data.bonus}} кликов! Серия: ${{data.streak}}`, buttons: [{{type: 'ok'}}]}});
                await loadStats();
            }} else {{
                tg.showPopup({{title: '❌ Уже забирал', message: data.message, buttons: [{{type: 'ok'}}]}});
            }}
        }};
        
        document.getElementById('openShopBtn').onclick = () => showScreen('shop');
        
        document.getElementById('referralBtn').onclick = async () => {{
            const res = await fetch(`/api/get_referrals?user_id=${{userId}}`);
            const data = await res.json();
            tg.showPopup({{title: '👥 Рефералы', message: `Приглашено друзей: ${{data.count}}\\nНе получено наград: ${{data.unclaimed}}`, buttons: [{{type: 'ok'}}]}});
        }};
        
        document.getElementById('profileBtn').onclick = async () => {{
            const res = await fetch(`/api/stats/${{userId}}`);
            const data = await res.json();
            tg.showPopup({{title: '📊 Профиль', message: `Клики: ${{data.clicks}}\\nУровень: ${{data.level}}\\nСила клика: +${{data.tap_power}}\\nПассивный доход: ${{data.passive_income}}/час`, buttons: [{{type: 'ok'}}]}});
        }};
        
        document.getElementById('closeBtn').onclick = () => tg.close();
        
        loadStats();
    </script>
</body>
</html>'''
    
    return HTMLResponse(content=html)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)