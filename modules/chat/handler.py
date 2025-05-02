import logging
from telegram import Update
from telegram.ext import ContextTypes
from modules.chat.gemini import get_gemini_response
from database.firestore import FirestoreClient

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Nhận lệnh /start từ user {update.message.from_user.id}")
    await update.message.reply_text("Chào mừng bạn đến với CotienBot! Gõ /help để xem hướng dẫn.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    message = update.message.text
    logger.info(f"Nhận tin nhắn từ user {user_id}: {message}")
    try:
        response = get_gemini_response(message)
        await update.message.reply_text(response)
        # Lưu lịch sử chat
        db = FirestoreClient()
        db.save_chat(user_id, message, response)
        logger.info(f"Đã trả lời user {user_id}: {response}")
    except Exception as e:
        logger.error(f"Lỗi khi xử lý tin nhắn từ user {user_id}: {str(e)}")
        await update.message.reply_text("Có lỗi xảy ra, vui lòng thử lại sau!")
