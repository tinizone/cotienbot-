from telegram import Update
from telegram.ext import CallbackContext
import html
import logging
from database.firestore import FirestoreClient
from modules.learning.quiz import QuizManager
from modules.learning.course import CourseManager
from modules.media.speech import SpeechProcessor

logger = logging.getLogger(__name__)
firestore_client = FirestoreClient()
quiz_manager = QuizManager()
course_manager = CourseManager()

async def start(update: Update, context: CallbackContext) -> None:
    """Xử lý lệnh /start."""
    try:
        user_id = str(update.message.from_user.id)
        user_data = firestore_client.get_user(user_id)
        if user_data is None:
            firestore_client.save_user(user_id, {
                "name": update.message.from_user.first_name,
                "created_at": firestore_client.SERVER_TIMESTAMP
            })
        await update.message.reply_text(
            "Chào mừng bạn đến với CotienBot! 🤖\n"
            "Tôi có thể giúp bạn trò chuyện, học tập, và hơn thế nữa.\n"
            "Dùng /help để xem danh sách lệnh."
        )
    except Exception as e:
        logger.error(f"Lỗi trong start: {str(e)}")
        await update.message.reply_text("Lỗi khi khởi động bot. Vui lòng thử lại.")

async def help_command(update: Update, context: CallbackContext) -> None:
    """Xử lý lệnh /help."""
    try:
        help_text = (
            "Danh sách lệnh:\n"
            "/start - Khởi động bot\n"
            "/help - Hiển thị trợ giúp\n"
            "/train - Huấn luyện bot với dữ liệu\n"
            "/createquiz - Tạo quiz\n"
            "/takequiz - Tham gia quiz\n"
            "/createcourse - Tạo khóa học\n"
            "/crawl - Crawl dữ liệu từ RSS\n"
            "/listcourses - Liệt kê khóa học\n"
            "/setadmin - Đặt admin (yêu cầu quyền)\n"
            "/getid - Lấy ID người dùng"
        )
        await update.message.reply_text(help_text)
    except Exception as e:
        logger.error(f"Lỗi trong help_command: {str(e)}")
        await update.message.reply_text("Lỗi khi hiển thị trợ giúp. Vui lòng thử lại.")

async def train_command(update: Update, context: CallbackContext) -> None:
    """Xử lý lệnh /train."""
    try:
        user_id = str(update.message.from_user.id)
        if not context.args:
            await update.message.reply_text("Vui lòng cung cấp dữ liệu để huấn luyện, ví dụ: /train Xin chào")
            return
        info = " ".join(context.args)
        doc_id = firestore_client.save_training_data(user_id, info, "general")
        await update.message.reply_text(f"Đã lưu dữ liệu huấn luyện: {html.escape(info)} (ID: {doc_id})")
    except Exception as e:
        logger.error(f"Lỗi trong train_command: {str(e)}")
        await update.message.reply_text("Lỗi khi huấn luyện. Vui lòng thử lại.")

async def create_quiz_command(update: Update, context: CallbackContext) -> None:
    """Xử lý lệnh /createquiz."""
    try:
        user_id = str(update.message.from_user.id)
        quiz_id = quiz_manager.create_quiz(user_id)
        await update.message.reply_text(f"Đã tạo quiz với ID: {quiz_id}\nSử dụng /takequiz để tham gia!")
    except Exception as e:
        logger.error(f"Lỗi trong create_quiz_command: {str(e)}")
        await update.message.reply_text("Lỗi khi tạo quiz. Vui lòng thử lại.")

async def take_quiz_command(update: Update, context: CallbackContext) -> None:
    """Xử lý lệnh /takequiz."""
    try:
        user_id = str(update.message.from_user.id)
        result = quiz_manager.take_quiz(user_id)
        await update.message.reply_text(result)
    except Exception as e:
        logger.error(f"Lỗi trong take_quiz_command: {str(e)}")
        await update.message.reply_text("Lỗi khi tham gia quiz. Vui lòng thử lại.")

async def create_course_command(update: Update, context: CallbackContext) -> None:
    """Xử lý lệnh /createcourse."""
    try:
        user_id = str(update.message.from_user.id)
        if not context.args:
            await update.message.reply_text("Vui lòng cung cấp tên khóa học, ví dụ: /createcourse Python Cơ Bản")
            return
        course_name = " ".join(context.args)
        course_id = course_manager.create_course(user_id, course_name)
        await update.message.reply_text(f"Đã tạo khóa học với ID: {course_id}\nTên: {course_name}")
    except Exception as e:
        logger.error(f"Lỗi trong create_course_command: {str(e)}")
        await update.message.reply_text("Lỗi khi tạo khóa học. Vui lòng thử lại.")

async def crawl_command(update: Update, context: CallbackContext) -> None:
    """Xử lý lệnh /crawl."""
    try:
        await update.message.reply_text("Tính năng crawl RSS sẽ sớm ra mắt! 🕷️")
    except Exception as e:
        logger.error(f"Lỗi trong crawl_command: {str(e)}")
        await update.message.reply_text("Lỗi khi crawl dữ liệu. Vui lòng thử lại.")

async def list_courses_command(update: Update, context: CallbackContext) -> None:
    """Xử lý lệnh /listcourses."""
    try:
        user_id = str(update.message.from_user.id)
        courses = course_manager.list_courses(user_id)
        if not courses:
            await update.message.reply_text("Chưa có khóa học nào. Tạo mới bằng /createcourse!")
            return
        await update.message.reply_text("Danh sách khóa học:\n" + "\n".join(courses))
    except Exception as e:
        logger.error(f"Lỗi trong list_courses_command: {str(e)}")
        await update.message.reply_text("Lỗi khi liệt kê khóa học. Vui lòng thử lại.")

async def set_admin_command(update: Update, context: CallbackContext) -> None:
    """Xử lý lệnh /setadmin."""
    try:
        user_id = str(update.message.from_user.id)
        user_data = firestore_client.get_user(user_id)
        if not user_data or user_data.get("role") != "admin":
            await update.message.reply_text("Bạn không có quyền thực hiện lệnh này!")
            return
        if not context.args:
            await update.message.reply_text("Vui lòng cung cấp ID người dùng để đặt làm admin, ví dụ: /setadmin 123456789")
            return
        target_user_id = context.args[0]
        firestore_client.set_admin(target_user_id, "Admin")
        await update.message.reply_text(f"Đã đặt người dùng {target_user_id} làm admin!")
    except Exception as e:
        logger.error(f"Lỗi trong set_admin_command: {str(e)}")
        await update.message.reply_text("Lỗi khi đặt admin. Vui lòng thử lại.")

async def get_id_command(update: Update, context: CallbackContext) -> None:
    """Xử lý lệnh /getid."""
    try:
        user_id = str(update.message.from_user.id)
        await update.message.reply_text(f"ID của bạn là: {user_id}")
    except Exception as e:
        logger.error(f"Lỗi trong get_id_command: {str(e)}")
        await update.message.reply_text("Lỗi khi lấy ID. Vui lòng thử lại.")

async def handle_message(update: Update, context: CallbackContext) -> None:
    """Xử lý tin nhắn văn bản."""
    try:
        user_id = str(update.message.from_user.id)
        message = html.escape(update.message.text)
        response = f"Echo: {message}"  # Thay thế bằng logic xử lý AI nếu cần
        firestore_client.save_chat(user_id, message, response)
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Lỗi trong handle_message: {str(e)}")
        await update.message.reply_text("Lỗi khi xử lý tin nhắn. Vui lòng thử lại.")

async def handle_media(update: Update, context: CallbackContext) -> None:
    """Xử lý tin nhắn media (giọng nói, ảnh, video)."""
    try:
        user_id = str(update.message.from_user.id)
        if update.message.photo:
            await update.message.reply_text("Tính năng xử lý ảnh sẽ sớm ra mắt! 📸")
        elif update.message.video:
            await update.message.reply_text("Tính năng xử lý video sẽ sớm ra mắt! 🎥")
        elif update.message.voice:
            voice = update.message.voice
            file = await voice.get_file()
            audio_data = await file.download_as_bytearray()
            speech = SpeechProcessor()
            result = await speech.speech_to_text(audio_data)
            if result["status"] == "success":
                text = html.escape(result["text"])
                doc_id = firestore_client.save_training_data(user_id, text, "speech")
                await update.message.reply_text(f"Đã lưu giọng nói: {text} (ID: {doc_id})")
            else:
                await update.message.reply_text(f"Lỗi: {result['message']}")
    except Exception as e:
        logger.error(f"Lỗi trong handle_media: {str(e)}")
        await update.message.reply_text("Lỗi khi xử lý media. Vui lòng thử lại.")
