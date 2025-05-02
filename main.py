import logging
from fastapi import FastAPI
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from modules.chat.handler import start, handle_message
from config.settings import settings

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

# Khởi tạo Telegram Bot
def init_telegram_bot():
    try:
        logger.info("Khởi tạo Telegram Bot...")
        telegram_app = Application.builder().token(settings.telegram_token).build()
        telegram_app.add_handler(CommandHandler("start", start))
        telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        logger.info("Telegram Bot đã được khởi tạo thành công.")
        return telegram_app
    except Exception as e:
        logger.error(f"Lỗi khi khởi tạo Telegram Bot: {str(e)}")
        raise

# Chạy bot khi server khởi động
@app.on_event("startup")
async def startup_event():
    try:
        logger.info("Bắt đầu chạy Telegram Bot...")
        telegram_app = init_telegram_bot()
        await telegram_app.initialize()
        await telegram_app.start()
        await telegram_app.updater.start_polling()
        logger.info("Telegram Bot đang chạy với polling.")
    except Exception as e:
        logger.error(f"Lỗi khi chạy Telegram Bot: {str(e)}")
        raise

# Endpoint kiểm tra server
@app.get("/")
async def root():
    return {"message": "CotienBot is running!"}
