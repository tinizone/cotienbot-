# File: /modules/train.py
from telegram.ext import CommandHandler
from telegram import Update
from telegram.ext import CallbackContext
import logging
from database.firestore import FirestoreClient

logger = logging.getLogger(__name__)

async def train_command(update: Update, context: CallbackContext) -> None:
    try:
        logger.info("Bắt đầu xử lý lệnh /train")
        user_id = str(update.message.from_user.id)
        if not context.args:
            logger.warning("Không có tham số được cung cấp cho /train")
            await update.message.reply_text("Vui lòng cung cấp dữ liệu để huấn luyện, ví dụ: /train Tôi tên là Vinh")
            return
        info = " ".join(context.args)
        logger.info(f"Đang lưu dữ liệu huấn luyện: {info} cho user {user_id}")
        db = FirestoreClient()
        doc_id = db.save_training_data(user_id, info)
        logger.info(f"Lưu dữ liệu huấn luyện thành công: ID {doc_id}")
        await update.message.reply_text(f"Đã lưu dữ liệu huấn luyện: {info} (ID: {doc_id})")
    except Exception as e:
        logger.error(f"Lỗi trong train_command: {str(e)}")
        await update.message.reply_text("Lỗi khi huấn luyện. Vui lòng thử lại.")

def register_handlers():
    return [
        CommandHandler("train", train_command)
    ]
