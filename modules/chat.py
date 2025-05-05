import logging
import time
import random
from telegram import Update
from telegram.ext import CallbackContext, CommandHandler, MessageHandler, filters
from database.firestore import FirestoreClient
from config.settings import settings
import google.generativeai as genai

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.gemini_api_key)
FALLBACK_RESPONSES = [
    "Xin lỗi, tôi không hiểu câu hỏi của bạn. Bạn có thể hỏi lại không?",
    "Hmm, tôi chưa biết cách trả lời câu này. Hãy thử hỏi theo cách khác nhé!",
    "Tôi đang gặp chút khó khăn. Bạn có thể cung cấp thêm thông tin không?",
]
GEMINI_RATE_LIMIT = 50
gemini_call_count = 0
last_reset_time = time.time()

async def start(update: Update, context: CallbackContext) -> None:
    try:
        welcome_message = (
            "Chào mừng bạn đến với CotienBot! 🤖\n"
            "Tôi là trợ lý cá nhân của bạn, có thể trò chuyện và học hỏi từ dữ liệu bạn cung cấp.\n"
            "Dùng /help để xem danh sách lệnh."
        )
        await update.message.reply_text(welcome_message)
        logger.info(f"Gửi tin nhắn chào mừng tới user {update.message.from_user.id}")
    except Exception as e:
        logger.error(f"Lỗi trong start: {str(e)}", exc_info=True)
        await update.message.reply_text("Xin lỗi, đã có lỗi xảy ra. Vui lòng thử lại!")

async def help_command(update: Update, context: CallbackContext) -> None:
    try:
        help_message = (
            "Danh sách lệnh:\n"
            "/start - Khởi động bot\n"
            "/help - Hiển thị trợ giúp\n"
            "/train <thông tin> - Huấn luyện bot với thông tin của bạn\n"
            "Hoặc bạn có thể trò chuyện tự nhiên với tôi!"
        )
        await update.message.reply_text(help_message)
        logger.info(f"Gửi tin nhắn trợ giúp tới user {update.message.from_user.id}")
    except Exception as e:
        logger.error(f"Lỗi trong help_command: {str(e)}", exc_info=True)
        await update.message.reply_text("Xin lỗi, đã có lỗi xảy ra. Vui lòng thử lại!")

async def train_command(update: Update, context: CallbackContext) -> None:
    try:
        user_id = str(update.message.from_user.id)
        info = " ".join(context.args) if context.args else None
        if not info:
            await update.message.reply_text("Vui lòng cung cấp thông tin để huấn luyện. Ví dụ: /train tôi tên là Vinh")
            logger.info(f"User {user_id} không cung cấp thông tin huấn luyện")
            return

        db = FirestoreClient()
        result = db.save_training_data(user_id, info)
        if result == "buffered":
            await update.message.reply_text(f"Đã lưu dữ liệu huấn luyện: {info} (ID: {result})")
            logger.info(f"Đã lưu dữ liệu huấn luyện cho user {user_id}: {info}")
        else:
            await update.message.reply_text("Đã lưu dữ liệu huấn luyện thành công!")
            logger.info(f"Đã lưu dữ liệu huấn luyện trực tiếp cho user {user_id}: {info}")
    except Exception as e:
        logger.error(f"Lỗi trong train_command: {str(e)}", exc_info=True)
        await update.message.reply_text("Xin lỗi, đã có lỗi khi lưu dữ liệu huấn luyện. Vui lòng thử lại!")

def get_gemini_model():
    return genai.GenerativeModel("gemini-1.5-flash")

async def handle_message(update: Update, context: CallbackContext) -> None:
    try:
        start_time = time.time()
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
            logger.info(f"Thời gian xử lý: {time.time() - start_time:.2f} giây")
            return

        # Lấy dữ liệu huấn luyện đã lọc
        training_data = db.get_training_data(user_id, message)
        training_context = []
        if training_data:
            training_context = [item["info"] for item in training_data]
        training_context_str = "\n".join([f"Người dùng đã huấn luyện: {info}" for info in training_context])

        # Kiểm tra giới hạn Gemini API
        global gemini_call_count, last_reset_time
        current_time = time.time()
        if current_time - last_reset_time >= 60:
            gemini_call_count = 0
            last_reset_time = current_time
        if gemini_call_count >= GEMINI_RATE_LIMIT:
            await update.message.reply_text("Đã đạt giới hạn yêu cầu Gemini. Vui lòng thử lại sau!")
            logger.warning(f"Đã đạt giới hạn Gemini API cho user {user_id}")
            logger.info(f"Thời gian xử lý: {time.time() - start_time:.2f} giây")
            return

        # Kiểm tra cache Gemini
        gemini_cache_key = f"{user_id}:{message}"
        if hasattr(db, "gemini_cache") and gemini_cache_key in db.gemini_cache:
            response = db.gemini_cache[gemini_cache_key]
            await update.message.reply_text(f"[Gemini] {response}")
            logger.info(f"Trả lời từ cache Gemini cho user {user_id}: {response}")
            logger.info(f"Thời gian xử lý: {time.time() - start_time:.2f} giây")
            return

        # Lấy ngữ cảnh từ lịch sử trò chuyện gần đây
        doc = db.client.collection("chat_history").document(user_id).get()
        context_messages = []
        if doc.exists:
            chats = doc.to_dict().get("chats", [])
            context_messages = [f"User: {chat['message']}\nBot: {chat['response']}" for chat in chats[-3:]]
        context_str = "\n".join(context_messages)

        # Gọi Gemini với dữ liệu đã lọc
        logger.info(f"Gọi Gemini cho user {user_id} với dữ liệu đã lọc")
        gemini_model = get_gemini_model()
        prompt = (
            "Bạn là một trợ lý thông minh. Dựa trên dữ liệu huấn luyện và lịch sử trò chuyện, hãy trả lời câu hỏi của người dùng một cách tự nhiên và chính xác.\n\n"
            f"Dữ liệu huấn luyện:\n{training_context_str}\n\n"
            f"Lịch sử trò chuyện:\n{context_str}\n\n"
            f"Câu hỏi: {message}\n\n"
            "Trả lời:"
        )
        from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_fixed(2),
            retry=retry_if_exception_type(Exception),
            before_sleep=lambda retry_state: logger.info(f"Retry Gemini API: attempt {retry_state.attempt_number}")
        )
        def call_gemini_with_timeout():
            import signal
            def timeout_handler(signum, frame):
                raise TimeoutError("Timeout of 10s exceeded")
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(10)
            try:
                return gemini_model.generate_content(prompt).text
            finally:
                signal.alarm(0)

        try:
            response = call_gemini_with_timeout()
        except Exception as e:
            logger.error(f"Lỗi khi gọi Gemini API: {str(e)}")
            response = "Xin lỗi, tôi không thể trả lời ngay bây giờ. Hãy thử lại sau!"
            await update.message.reply_text(response)
            logger.info(f"Thời gian xử lý: {time.time() - start_time:.2f} giây")
            return
        gemini_call_count += 1

        # Cache kết quả Gemini
        if not hasattr(db, "gemini_cache"):
            db.gemini_cache = {}
            db.gemini_cache_max_size = 1000
        if len(db.gemini_cache) >= db.gemini_cache_max_size:
            db.gemini_cache.clear()
        db.gemini_cache[gemini_cache_key] = response

        await update.message.reply_text(f"[Gemini] {response}")
        db.save_chat(user_id, message, response, is_gemini=True)
        logger.info(f"Trả lời từ Gemini cho user {user_id}: {response}")
        logger.info(f"Thời gian xử lý: {time.time() - start_time:.2f} giây")
    except Exception as e:
        logger.error(f"Lỗi trong handle_message: {str(e)}", exc_info=True)
        fallback_response = random.choice(FALLBACK_RESPONSES)
        await update.message.reply_text(fallback_response)
        logger.info(f"Thời gian xử lý: {time.time() - start_time:.2f} giây")
