# File: /modules/chat/handler.py
from telegram import Update
from telegram.ext import CallbackContext
from modules.chat.gemini import get_gemini_response
from modules.learning.quiz import QuizManager
from modules.media.speech import SpeechProcessor
from database.firestore import FirestoreClient
import logging
from modules.learning.crawler import crawl_rss

logger = logging.getLogger(__name__)
firestore = FirestoreClient()
quiz_manager = QuizManager()

async def start(update: Update, context: CallbackContext) -> None:
    user_id = str(update.message.from_user.id)
    welcome_message = f"Chào {update.message.from_user.first_name}!\nGõ /help để xem hướng dẫn."
    await update.message.reply_text(welcome_message)
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
                       "- /createquiz <question> | <correct> | <wrong1> | <wrong2> | <wrong3>: Tạo quiz (admin).\n" \
                       "- /takequiz <quiz_id> <answer>: Trả lời quiz.\n" \
                       "- Gửi tin nhắn để trò chuyện.\n" \
                       "- Gửi giọng nói để lưu thông tin."
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

async def create_quiz_command(update: Update, context: CallbackContext) -> None:
    try:
        if not context.args:
            await update.message.reply_text("Vui lòng nhập: /createquiz <question> | <correct> | <wrong1> | <wrong2> | <wrong3>")
            return
        args = " ".join(context.args).split("|")
        if len(args) != 5:
            await update.message.reply_text("Cần đúng 5 phần: câu hỏi, đáp án đúng, 3 đáp án sai.")
            return
        question, correct, *wrong_answers = [arg.strip() for arg in args]
        user_id = str(update.message.from_user.id)
        quiz_id = quiz_manager.create_quiz(user_id, question, correct, wrong_answers)
        await update.message.reply_text(f"Quiz created! ID: {quiz_id}")
    except ValueError as e:
        await update.message.reply_text(f"Lỗi: {str(e)}")
    except Exception as e:
        logger.error(f"Error in create_quiz_command: {str(e)}")
        await update.message.reply_text(f"Lỗi: {str(e)}")

async def take_quiz_command(update: Update, context: CallbackContext) -> None:
    try:
        if len(context.args) < 2:
            await update.message.reply_text("Vui lòng nhập: /takequiz <quiz_id> <answer>")
            return
        quiz_id, answer = context.args[0], " ".join(context.args[1:])
        result = quiz_manager.check_answer(quiz_id, answer)
        await update.message.reply_text(result["message"])
    except Exception as e:
        logger.error(f"Error in take_quiz_command: {str(e)}")
        await update.message.reply_text(f"Lỗi: {str(e)}")

async def handle_message(update: Update, context: CallbackContext) -> None:
    try:
        user_id = str(update.message.from_user.id)
        user_message = update.message.text

        # Tìm trong dữ liệu đào tạo
        training_data = firestore.get_training_data(user_id, user_message)
        if training_data:
            response = training_data[0]["info"]
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
        user_id = str(update.message.from_user.id)
        if update.message.photo:
            await update.message.reply_text("Tính năng xử lý ảnh đang phát triển!")
        elif update.message.video:
            await update.message.reply_text("Tính năng xử lý video đang phát triển!")
        elif update.message.voice:
            voice = update.message.voice
            file = await voice.get_file()
            audio_data = await file.download_as_bytearray()
            speech = SpeechProcessor()
            result = await speech.speech_to_text(audio_data)
            if result["status"] == "success":
                text = result["text"]
                doc_id = firestore.save_training_data(user_id, text, "general")
                await update.message.reply_text(f"Đã lưu giọng nói: {text} (ID: {doc_id})")
            else:
                await update.message.reply_text(f"Lỗi: {result['message']}")
    except Exception as e:
        logger.error(f"Error in handle_media: {str(e)}")
        await update.message.reply_text(f"Lỗi: {str(e)}")
async def create_course_command(update: Update, context: CallbackContext) -> None:
    try:
        if not context.args:
            await update.message.reply_text("Vui lòng nhập: /createcourse <title> | <description>")
            return
        args = " ".join(context.args).split("|")
        if len(args) != 2:
            await update.message.reply_text("Cần đúng 2 phần: tiêu đề, mô tả.")
            return
        title, description = [arg.strip() for arg in args]
        user_id = str(update.message.from_user.id)
        course_manager = CourseManager()
        course_manager.create_course(title, description, user_id)
        await update.message.reply_text(f"Khóa học '{title}' đã được tạo!")
    except ValueError as e:
        await update.message.reply_text(f"Lỗi: {str(e)}")
    except Exception as e:
        logger.error(f"Error in create_course_command: {str(e)}")
        await update.message.reply_text(f"Lỗi: {str(e)}")
# Thêm vào /modules/chat/handler.py

async def crawl_command(update: Update, context: CallbackContext) -> None:
    try:
        if not context.args:
            await update.message.reply_text("Vui lòng cung cấp URL: /crawl <url>")
            return
        url = context.args[0]
        result = crawl_rss(url)
        if "error" in result:
            await update.message.reply_text(f"Lỗi: {result['error']}")
        else:
            await update.message.reply_text(f"Đã crawl {len(result)} bài từ {url}")
    except Exception as e:
        logger.error(f"Error in crawl_command: {str(e)}")
        await update.message.reply_text(f"Lỗi: {str(e)}")
