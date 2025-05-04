# UPDATE: /app/main.py
from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from modules.chat.handler import start, handle_message, handle_media, help_command, train_command, create_quiz_command, take_quiz_command, create_course_command, list_courses_command, set_admin_command, crawl_command, get_id_command
from config.settings import settings
import logging
from database.firestore import FirestoreClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

async def get_telegram_app():
    """Create and configure Telegram Application."""
    app = Application.builder().token(settings.telegram_token).read_timeout(30).write_timeout(30).connection_retries(3).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("train", train_command))
    app.add_handler(CommandHandler("createquiz", create_quiz_command))
    app.add_handler(CommandHandler("takequiz", take_quiz_command))
    app.add_handler(CommandHandler("createcourse", create_course_command))
    app.add_handler(CommandHandler("crawl", crawl_command))
    app.add_handler(CommandHandler("listcourses", list_courses_command))
    app.add_handler(CommandHandler("setadmin", set_admin_command))
    app.add_handler(CommandHandler("getid", get_id_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.VOICE, handle_media))
    return app

@app.post("/webhook")
@limiter.limit("10/minute")  # Limit webhook requests
async def webhook(request: Request):
    """Handle Telegram webhook updates."""
    try:
        telegram_app = await get_telegram_app()
        update = Update.de_json(await request.json(), telegram_app.bot)
        if update is None:
            logger.error("Received invalid update from Telegram")
            raise HTTPException(status_code=400, detail="Invalid update")
        await telegram_app.process_update(update)
        return {"status": "ok"}
    except RateLimitExceeded:
        raise
    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "CotienBot is running!"}

@app.on_event("startup")
async def startup_event():
    """Initialize Telegram application and set webhook."""
    telegram_app = await get_telegram_app()
    await telegram_app.initialize()
    logger.info("Telegram Application initialized")
    webhook_url = f"https://{settings.render_domain}/webhook"
    logger.info(f"Attempting to set webhook to {webhook_url}")
    try:
        await telegram_app.bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook set successfully to {webhook_url}")
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")
        raise

    # Set admin from environment variable
    db = FirestoreClient()
    admin_user_id = settings.admin_user_id  # Load from .env
    if admin_user_id:
        db.set_admin(admin_user_id, "Admin")
        logger.info(f"Set {admin_user_id} as admin on startup.")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up webhook and shutdown application."""
    telegram_app = await get_telegram_app()
    await telegram_app.bot.delete_webhook()
    await telegram_app.shutdown()
    logger.info("Webhook removed and application shutdown")
