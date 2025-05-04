# File: /modules/chat/handler.py
from telegram import Update
from telegram.ext import CallbackContext
from modules.chat.gemini import get_gemini_response
from database.firestore import FirestoreClient
import logging

logger = logging.getLogger(__name__)
firestore = FirestoreClient()

async def start(update: Update, context: CallbackContext) -> None:
    user_id = str(update.message.from_user.id)
    welcome_message = f"Chào {update.message.from_user.first_name}!\nGõ /help để xem hướng dẫn."
    await update.message.reply_text(welcome_message)
    # Lưu thông tin người dùng
    firestore.save_user(user_id, {
        "name": update.message.from_user.first_name,
        "created_at": firestore.SERVER_TIMESTAMP
    })

async def help_command(update: Update, context: CallbackContext) -> None:
    try:
        help_message = "Hướng dẫn sử dụng CotienBot:\n" \
                       "- /start: Bắt đầu.\n" \
                       "- /help: Xem hướng dẫn.\n" \
                       "- /train <info>: Lưu thông tin (VD: Tôi tên Vinh).\n" \
                       "- Gửi tin nhắn để trò chuyện.\n" \
                       "- Gửi ảnh, video, hoặc âm thanh để xử lý."
        await update.message.reply_text(help_message)
    except Exception as e:
        logger.error(f"Error in help_command: {str(e)}")
        await update.message.reply_text(f"Lỗi: {str(e)}")

async def train_command(update: Update, context: CallbackContext) -> None:
    try:
        if not context.args:
            await update.message.reply_text("Vui lòng cung cấp thông tin: /train <info>")
            return
        user_id = str(update.message.from_user.id)
        info = " ".join(context.args)
        data_type = "name" if info.lower().startswith("tôi tên") else "general"
        doc_id = firestore.save_training_data(user_id, info, data_type)
        await update.message.reply_text(f"Đã lưu thông tin: {info} (ID: {doc_id})")
    except Exception as e:
        logger.error(f"Error in train_command: {str(e)}")
        await update.message.reply_text(f"Lỗi: {str(e)}")

async def handle_message(update: Update, context: CallbackContext) -> None:
    try:
        user_id = str(update.message.from_user.id)
        user_message = update.message.text

        # Tìm trong dữ liệu đào tạo
        training_data = firestore.get_training_data(user_id, user_message)
        if training_data:
            response = training_data[0]["info"]  # Lấy kết quả tương đồng cao nhất
            await update.message.reply_text(response)
            firestore.save_chat(user_id, user_message, response)
            return

        # Nếu không tìm thấy, gọi Gemini
        response = get_gemini_response(user_message)
        await update.message.reply_text(response)
        firestore.save_chat(user_id, user_message, response)
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
