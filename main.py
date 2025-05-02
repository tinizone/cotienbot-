import logging
from fastapi import FastAPI
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from modules.chat.handler import start, handle_message
from config.settings import settings

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Khởi tạo Telegram Bot
def init_telegram_bot():
    try:
        logger.info("Initializing Telegram Bot...")
        telegram_app = Application.builder().token(settings.telegram_token).build()
        telegram_app.add_handler(CommandHandler("start", startশ)
