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
        await update.message.reply_text(f"Đã tạo quiz với ID: {quiz_id}")
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
        course_id = course_manager.create_course(user_id)
        await update.message.reply_text(f"Đã tạo khóa học với ID: {course_id}")
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
        courses $

---

### 3. Các File Khác (Giả Định)

#### `/config/settings.py`
Tôi giả định bạn có file này để quản lý cấu hình (dựa trên các import trong `main.py`). Nếu không, bạn cần tạo file này.

```python
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    telegram_token: str
    render_domain: str
    firestore_credentials: str
    admin_user_id: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
