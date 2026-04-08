import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import init_db
from handlers import router

logging.basicConfig(level=logging.INFO)

async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    print("🦆 Бот Zeta Clicker запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

    async def daily_reward_job():
    while True:
        now = datetime.now()
        # ждём до 00:05
        next_run = now.replace(hour=0, minute=5, second=0, microsecond=0)
        if now >= next_run:
            next_run += timedelta(days=1)
        await asyncio.sleep((next_run - now).total_seconds())
        
        # Вычисляем топ за вчера
        yesterday = (datetime.now() - timedelta(days=1)).date()
        conn = await get_connection()
        rows = await conn.fetch("""
            SELECT user_id, clicks_today FROM daily_stats
            WHERE date = $1
            ORDER BY clicks_today DESC LIMIT 3
        """, yesterday)
        rewards = [5000, 3000, 1000]
        for i, row in enumerate(rows):
            bonus = rewards[i] if i < len(rewards) else 0
            if bonus:
                await conn.execute("UPDATE users SET balance = balance + $1 WHERE user_id = $2", bonus, row["user_id"])
                await bot.send_message(row["user_id"], f"🏆 Вы вошли в топ-3 за вчера! Награда: {bonus} монет.")
        await conn.close()

async def main():
    asyncio.create_task(daily_reward_job())
    await dp.start_polling(bot)