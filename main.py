from fastapi import FastAPI
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from modules.chat.handler import start, handle_message
from config.settings import settings

app = FastAPI()

# Khởi tạo Telegram Bot
def init_telegram_bot():
    telegram_app = Application.builder().token(settings.telegram_token).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return telegram_app

# Chạy bot khi server khởi động
@app.on_event("startup")
async def startup_event():
    telegram_app = init_telegram_bot()
    telegram_app.run_polling()

# Endpoint kiểm tra server
@app.get("/")
async def root():
    return {"message": "CotienBot is running!"}
