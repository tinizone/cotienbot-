# File: /modules/chat/handler.py
from telegram import Update
from telegram.ext import CallbackContext
from modules.chat.gemini import get_gemini_response
import logging

logger = logging.getLogger(__name__)

async def start(update: Update, context: CallbackContext) -> None:
    welcome_message = "Chào mừng bạn đến với CotienBot!\nGõ /help để xem hướng dẫn."
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: CallbackContext) -> None:
    try:
        help_message = "Đây là hướng dẫn sử dụng CotienBot:\n" \
                       "- Gõ /start để bắt đầu.\n" \
                       "- Gõ /help để xem hướng dẫn.\n" \
                       "- Gửi tin nhắn để trò chuyện với bot.\n" \
                       "- Gửi ảnh, video, hoặc âm thanh để bot xử lý."
        # Gọi Gemini AI để tạo thêm hướng dẫn (nếu cần)
        gemini_response = get_gemini_response("Cung cấp hướng dẫn ngắn gọn để sử dụng bot Telegram")
        full_message = f"{help_message}\n\nHướng dẫn từ AI:\n{gemini_response}"
        await update.message.reply_text(full_message)
    except Exception as e:
        logger.error(f"Error in help_command: {str(e)}")
        await update.message.reply_text(f"Lỗi khi xử lý /help: {str(e)}")

async def handle_message(update: Update, context: CallbackContext) -> None:
    try:
        user_message = update.message.text
        response = get_gemini_response(user_message)
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error in handle_message: {str(e)}")
        await update.message.reply_text(f"Lỗi: {str(e)}")

async def handle_media(update: Update, context: CallbackContext) -> None:
    try:
        media_type = "photo" if update.message.photo else "video" if update.message.video else "audio"
        await update.message.reply_text(f"Tôi đã nhận được {media_type} của bạn. Tính năng xử lý đang phát triển!")
    except Exception as e:
        logger.error(f"Error in handle_media: {str(e)}")
        await update.message.reply_text(f"Lỗi: {str(e)}")
