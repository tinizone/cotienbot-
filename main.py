from fastapi import FastAPI
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from modules.chat.handler import start, handle_message
from config.settings import settings
import asyncio
import threading

app = FastAPI()

# Khởi tạo Telegram Bot
def init_telegram_bot():
    telegram_app = Application.builder().token(settings.telegram_token).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return telegram_app

# Hàm chạy polling trong thread riêng
def run_polling(telegram_app):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    telegram_app.run_polling()

# Chạy bot khi server khởi động
@app.on_event("startup")
async def startup_event():
    telegram_app = init_telegram_bot()
    # Chạy polling trong thread riêng để tránh xung đột event loop
    polling_thread = threading.Thread(target=run_polling, args=(telegram_app,), daemon=True)
    polling_thread.start()

# Endpoint kiểm tra server
@app.get("/")
async def root():
    return {"message": "CotienBot is running!"}
