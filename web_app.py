import os
import sqlite3
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

app = FastAPI()
templates = Jinja2Templates(directory="templates")

class ClickData(BaseModel):
    user_id: int
    clicks: int

DB_PATH = os.path.join(os.path.dirname(__file__), "zeta_clicker.db")

def get_user_stats(user_id: int):
    """Возвращает простой словарь с числами и строками"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT clicks, level, tap_power, current_skin FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        # Принудительно преобразуем всё в простые типы
        return {
            "clicks": int(result[0]),
            "level": int(result[1]),
            "tap_power": int(result[2]),
            "skin": str(result[3]) if result[3] else "🦆"
        }
    else:
        # Создаём пользователя, если его нет
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

@app.get("/", response_class=HTMLResponse)
async def mini_app(request: Request, user_id: int = 1):
    stats = get_user_stats(user_id)
    
    # Явно передаём каждый параметр, никаких словарей внутри словаря
    return templates.TemplateResponse(
        "game.html",
        {
            "request": request,
            "user_id": user_id,
            "clicks": stats["clicks"],
            "level": stats["level"],
            "tap_power": stats["tap_power"],
            "skin": stats["skin"]
        }
    )

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