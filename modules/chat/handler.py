# File: /modules/chat/handler.py
from telegram import Update
from telegram.ext import ContextTypes
from modules.chat.gemini import get_gemini_response
from database.firestore import FirestoreClient
from modules.media.ocr import extract_text_from_image

db = FirestoreClient()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Chào mừng bạn đến với CotienBot! Gõ /help để xem hướng dẫn.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    message = update.message.text
    response = get_gemini_response(message)
    await update.message.reply_text(response)
    db.save_chat(user_id, message, response)

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if update.message.photo:
        file = await update.message.photo[-1].get_file()
        image_bytes = await file.download_as_bytearray()
        text = extract_text_from_image(image_bytes)
        await update.message.reply_text(f"Extracted text: {text}")
        db.save_chat(user_id, "photo", text)
    elif update.message.video:
        await update.message.reply_text("Video received! Processing not yet implemented.")
    elif update.message.audio:
        await update.message.reply_text("Audio received! Processing not yet implemented.")
