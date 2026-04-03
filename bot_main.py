import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from config import BOT_TOKEN

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    base_url = os.environ.get("PUBLIC_URL", "https://твой-адрес.up.railway.app")
    web_app_url = f"{base_url}/?user_id={user_id}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🦆 Играть в Zeta Clicker!", web_app=WebAppInfo(url=web_app_url))]
    ])
    
    await message.answer(
        "🦆 **Добро пожаловать в Zeta Clicker!**\n\n"
        "Нажми на кнопку ниже, чтобы открыть игру.\n\n"
        "✨ **В игре тебя ждут:**\n"
        "• Кликай по утке и зарабатывай клики\n"
        "• Прокачивай силу клика и энергию\n"
        "• Покупай скины и получай бонусы\n"
        "• Выполняй ежедневные задания\n"
        "• Приглашай друзей и получай награды\n"
        "• Соревнуйся в топе игроков\n\n"
        "Погнали! 🚀",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def main():
    print("🦆 Бот Zeta Clicker запущен (только Mini App)!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())