import os
import json
import sqlite3
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

app = FastAPI()

# Настройка шаблонов
templates = Jinja2Templates(directory="templates")

# Модель для данных от Mini App
class ClickData(BaseModel):
    user_id: int
    clicks: int

# База данных
DB_PATH = "zeta_clicker.db"

def get_user_stats(user_id: int):
    """Получает статистику пользователя из БД"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT clicks, level, tap_power, current_skin FROM users WHERE user_id = ?",
        (user_id,)
    )
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            "clicks": result[0],
            "level": result[1],
            "tap_power": result[2],
            "skin": result[3] if result[3] else "🦆"
        }
    else:
        # Создаём нового пользователя, если его нет
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
    """Обновляет клики пользователя"""
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

# ==================== РОУТЫ ====================

@app.get("/", response_class=HTMLResponse)
async def mini_app(request: Request, user_id: int = None):
    """
    Главная страница Mini App.
    Получает user_id из параметра запроса (Telegram подставляет initData)
    """
    if not user_id:
        # Пробуем получить из initData (заглушка для тестов)
        user_id = 1
    
    stats = get_user_stats(user_id)
    
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
    """
    API для сохранения клика от Mini App
    """
    success = update_clicks(data.user_id, data.clicks)
    if success:
        stats = get_user_stats(data.user_id)
        return JSONResponse(content=stats)
    else:
        raise HTTPException(status_code=500, detail="Failed to update clicks")

@app.get("/api/stats/{user_id}")
async def get_stats(user_id: int):
    """
    API для получения статистики пользователя
    """
    stats = get_user_stats(user_id)
    return JSONResponse(content=stats)

@app.get("/health")
async def health_check():
    """
    Проверка работоспособности для Railway
    """
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

# ==================== ЗАПУСК ====================

if __name__ == "__main__":
    # Берём порт из переменной окружения Railway, если нет — ставим 8000
    port = int(os.environ.get("PORT", 8000))
    # Хост обязательно 0.0.0.0, чтобы Railway мог подключиться
    uvicorn.run(app, host="0.0.0.0", port=port)