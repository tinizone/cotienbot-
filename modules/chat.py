# File: /modules/chat.py
from telegram.ext import CommandHandler, MessageHandler, filters
from telegram import Update
from telegram.ext import CallbackContext
import logging
import google.generativeai as genai
from config.settings import settings
from database.firestore import FirestoreClient
import time

logger = logging.getLogger(__name__)

# Cấu hình Gemini API
genai.configure(api_key=settings.gemini_api_key)
model = None
gemini_call_count = 0
last_reset_time = time.time()
GEMINI_RATE_LIMIT = 50
FALLBACK_RESPONSES = [
    "Xin lỗi, tôi đang gặp chút vấn đề. Bạn có thể hỏi lại không? 😊",
    "Tôi không hiểu câu hỏi này, bạn có thể giải thích thêm không?",
    "Có vẻ tôi cần thêm thông tin để trả lời. Bạn có thể dùng /train để huấn luyện tôi không?"
]

def get_gemini_model():
    global model
    if model is None:
        logger.info("Đang khởi tạo mô hình Gemini...")
        model = genai.GenerativeModel("gemini-1.5-flash")
    return model

async def start(update: Update, context: CallbackContext) -> None:
    logger.info(f"Received /start command from user {update.message.from_user.id}")
    await update.message.reply_text(
        "Chào mừng bạn đến với CotienBot! 🤖\n"
        "Tôi là trợ lý cá nhân của bạn, có thể trò chuyện và học hỏi từ dữ liệu bạn cung cấp.\n"
        "Dùng /help để xem danh sách lệnh."
    )
    logger.info(f"Đã phản hồi /start cho user {update.message.from_user.id}")

async def help_command(update: Update, context: CallbackContext) -> None:
    logger.info(f"Received /help command from user {update.message.from_user.id}")
    await update.message.reply_text(
        "Danh sách lệnh:\n"
        "/start - Bắt đầu trò chuyện\n"
        "/help - Hiển thị danh sách lệnh\n"
        "/train <text> - Huấn luyện bot với dữ liệu cá nhân\n"
        "/getid - Lấy ID người dùng\n"
        "Gửi tin nhắn bất kỳ để trò chuyện!"
    )
    logger.info(f"Đã phản hồi /help cho user {update.message.from_user.id}")

async def get_id_command(update: Update, context: CallbackContext) -> None:
    user_id = str(update.message.from_user.id)
    logger.info(f"Received /getid command from user {user_id}")
    await update.message.reply_text(f"ID của bạn là: {user_id}")
    logger.info(f"Đã phản hồi /getid cho user {user_id}")

async def handle_message(update: Update, context: CallbackContext) -> None:
    try:
        user_id = str(update.message.from_user.id)
        message = update.message.text
        logger.info(f"Received message from user {user_id}: {message}")

        db = FirestoreClient()

        # Kiểm tra lịch sử trò chuyện
        similar_chat = db.get_similar_chat(user_id, message)
        if similar_chat:
            response = similar_chat["response"]
            await update.message.reply_text(response)
            logger.info(f"Trả lời từ lịch sử trò chuyện cho user {user_id}: {response}")
            return

        # Tìm trong dữ liệu huấn luyện cá nhân
        training_data = db.get_training_data(user_id, message)
        if training_data:
            response = training_data[0]["info"]
            await update.message.reply_text(f"Dựa trên dữ liệu huấn luyện: {response}")
            db.save_chat(user_id, message, response)
            logger.info(f"Trả lời từ dữ liệu huấn luyện cho user {user_id}: {response}")
            return

        # Kiểm tra giới hạn Gemini API
        global gemini_call_count, last_reset_time
        current_time = time.time()
        if current_time - last_reset_time >= 60:
            gemini_call_count = 0
            last_reset_time = current_time
        if gemini_call_count >= GEMINI_RATE_LIMIT:
            await update.message.reply_text("Đã đạt giới hạn yêu cầu Gemini. Vui lòng thử lại sau!")
            logger.warning(f"Đã đạt giới hạn Gemini API cho user {user_id}")
            return

        # Gọi Gemini nếu không tìm thấy dữ liệu
        logger.info(f"Không tìm thấy dữ liệu huấn luyện, gọi Gemini cho user {user_id}")
        gemini_model = get_gemini_model()
        response = gemini_model.generate_content(message).text
        gemini_call_count += 1
        await update.message.reply_text(f"[Gemini] {response}")
        db.save_chat(user_id, message, response, is_gemini=True)
        logger.info(f"Trả lời từ Gemini cho user {user_id}: {response}")
    except Exception as e:
        logger.error(f"Lỗi trong handle_message: {str(e)}")
        import random
        fallback_response = random.choice(FALLBACK_RESPONSES)
        await update.message.reply_text(fallback_response)

async def handle_media(update: Update, context: CallbackContext) -> None:
    logger.info(f"Received media from user {update.message.from_user.id}")
    await update.message.reply_text("Tôi đã nhận được media! Tôi sẽ cố gắng xử lý nó.")
    logger.info(f"Đã phản hồi media cho user {update.message.from_user.id}")

def register_handlers():
    logger.info("Đăng ký các handler trong chat.py...")
    handlers = [
        CommandHandler("start", start),
        CommandHandler("help", help_command),
        CommandHandler("getid", get_id_command),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message),
        MessageHandler(filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.VOICE, handle_media)
    ]
    logger.info(f"Đã đăng ký {len(handlers)} handler trong chat.py")
    return handlers
