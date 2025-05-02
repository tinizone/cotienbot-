# File: /main.py
from fastapi import FastAPI
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from modules.chat.handler import start, handle_message, handle_media
from config.settings import settings
import asyncio
from threading import Thread

app = FastAPI()

def init_telegram_bot():
    try:
        telegram_app = Application.builder().token(settings.telegram_token).build()
        telegram_app.add_handler(CommandHandler("start", start))
        telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        telegram_app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.AUDIO, handle_media))
        return telegram_app
    except Exception as e:
        print(f"Failed to initialize Telegram Bot: {e}")
        raise

def run_bot(telegram_app):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(telegram_app.run_polling())
    except Exception as e:
        print(f"Error in bot polling: {e}")
    finally:
        loop.close()

@app.on_event("startup")
async def startup_event():
    telegram_app = init_telegram_bot()
    bot_thread = Thread(target=run_bot, args=(telegram_app,), daemon=True)
    bot_thread.start()

@app.on_event("shutdown")
async def shutdown_event():
    print("Shutting down CotienBot...")

@app.get("/")
async def root():
    return {"message": "CotienBot is running!"}
