# File: /app/main.py
from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from modules.chat.handler import start, handle_message, handle_media, help_command, train_command, create_quiz_command, take_quiz_command
from config.settings import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
telegram_app = Application.builder().token(settings.telegram_token).build()

# Thêm các handler
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("help", help_command))
telegram_app.add_handler(CommandHandler("train", train_command))
telegram_app.add_handler(CommandHandler("createquiz", create_quiz_command))
telegram_app.add_handler(CommandHandler("takequiz", take_quiz_command))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
telegram_app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.VOICE, handle_media))
telegram_app.add_handler(CommandHandler("createcourse", create_course_command))
telegram_app.add_handler(CommandHandler("crawl", crawl_command))

@app.post("/webhook")
async def webhook(request: Request):
    try:
        update = Update.de_json(await request.json(), telegram_app.bot)
        if update is None:
            logger.error("Received invalid update from Telegram")
            return {"status": "invalid update"}
        await telegram_app.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "CotienBot is running!"}

@app.on_event("startup")
async def startup_event():
    await telegram_app.initialize()
    logger.info("Telegram Application initialized")
    webhook_url = f"https://{settings.render_domain}/webhook"
    logger.info(f"Attempting to set webhook to {webhook_url}")
    try:
        await telegram_app.bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook set successfully to {webhook_url}")
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    await telegram_app.bot.delete_webhook()
    await telegram_app.shutdown()
    logger.info("Webhook removed and application shutdown")
