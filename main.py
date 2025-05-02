# File: /main.py
from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from modules.chat.handler import start, handle_message, handle_media
from config.settings import settings
import logging

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Khởi tạo Telegram Bot
telegram_app = Application.builder().token(settings.telegram_token).build()

# Thêm các handler
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
telegram_app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.AUDIO, handle_media))

# Endpoint để nhận webhook từ Telegram
@app.post("/webhook")
async def webhook(request: Request):
    try:
        update = Update.de_json(await request.json(), telegram_app.bot)
        await telegram_app.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint kiểm tra server
@app.get("/")
async def root():
    return {"message": "CotienBot is running!"}

# Thiết lập webhook khi server khởi động
@app.on_event("startup")
async def startup_event():
    webhook_url = f"https://{settings.render_domain}/webhook"
    logger.info(f"Attempting to set webhook to {webhook_url}")
    try:
        await telegram_app.bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook set successfully to {webhook_url}")
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")
        # Không raise exception để tránh crash, chỉ log lỗi
        return

@app.on_event("shutdown")
async def shutdown_event():
    await telegram_app.bot.delete_webhook()
    logger.info("Webhook removed")
