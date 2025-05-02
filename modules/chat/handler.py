from telegram import Update
from telegram.ext import ContextTypes
from modules.chat.gemini import get_gemini_response
from database.firestore import FirestoreClient

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Chào mừng bạn đến với CotienBot! Gõ /help để xem hướng dẫn.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    message = update.message.text
    response = get_gemini_response(message)
    await update.message.reply_text(response)
    
    # Lưu lịch sử chat
    db = FirestoreClient()
    db.save_chat(user_id, message, response)
