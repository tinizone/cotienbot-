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
        telegram_app.add_handler(CommandHandler("start", start))
        telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        logger.info("Telegram Bot initialized successfully")
        return telegram_app
    except Exception as e:
        logger.error(f"Failed to initialize Telegram Bot: {str(e)}")
        raise

# Chạy bot khi server khởi động
@app.on_event("startup")
async def startup_event():
    try:
        logger.info("Setting up Telegram Bot webhook...")
        telegram_app = init_telegram_bot()
        await telegram_app.initialize()
        await telegram_app.start()
        # Cấu hình webhook
        webhook_url = f"https://{settings.render_domain}/webhook"  # Thay bằng domain của Render
        await telegram_app.bot.set_webhook(url=webhook_url)
        logger.info("Telegram Bot webhook set")
    except Exception as e:
        logger.error(f"Error setting Telegram Bot webhook: {str(e)}")
        raise

# Endpoint cho webhook
@app.post("/webhook")
async def webhook(update: dict):
    telegram_app = init_telegram_bot()
    await telegram_app.process_update(update)
    return {"status": "ok"}

# Endpoint kiểm tra server
@app.get("/")
async def root():
    return {"message": "CotienBot is running!"}
