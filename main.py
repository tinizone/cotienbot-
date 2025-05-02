from fastapi import FastAPI
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from modules.chat.handler import start, handle_message
from config.settings import settings
import threading
import asyncio

app = FastAPI()

# Khởi tạo Telegram Bot
def init_telegram_bot():
    telegram_app = Application.builder().token(settings.telegram_token).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return telegram_app

# Hàm chạy bot trong thread riêng
def run_bot_in_thread():
    telegram_app = init_telegram_bot()
    # Tạo event loop mới cho thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    telegram_app.run_polling()

# Chạy bot khi server khởi động
@app.on_event("startup")
async def startup_event():
    # Khởi động bot trong thread riêng
    bot_thread = threading.Thread(target=run_bot_in_thread, daemon=True)
    bot_thread.start()

# Endpoint kiểm tra server
@app.get("/")
async def root():
    return {"message": "CotienBot is running!"}
