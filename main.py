from fastapi import FastAPI, Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update
from config.settings import settings
from database.firestore import FirestoreClient
from modules.chat.handler import (
    start, help_command, train_command, create_quiz_command, take_quiz_command,
    create_course_command, crawl_command, list_courses_command, set_admin_command,
    get_id_command, handle_message, handle_media
)
from modules.learning.crawler import crawl_rss
import logging
import asyncio
import html
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

logger = logging.getLogger(__name__)

# Khởi tạo FastAPI và Limiter
app = FastAPI()
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Xử lý lỗi RateLimitExceeded
async def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return HTTPException(status_code=429, detail="Rate limit exceeded")

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Lưu telegram_app như thuộc tính của app
app.telegram_app = None
app.initialized = False

async def get_telegram_app():
    if app.telegram_app is None:
        logger.info("Đang khởi tạo ứng dụng Telegram...")
        app.telegram_app = Application.builder().token(settings.telegram_token).read_timeout(30).write_timeout(30).build()
        app.telegram_app.add_handler(CommandHandler("start", start))
        app.telegram_app.add_handler(CommandHandler("help", help_command))
        app.telegram_app.add_handler(CommandHandler("train", train_command))
        app.telegram_app.add_handler(CommandHandler("createquiz", create_quiz_command))
        app.telegram_app.add_handler(CommandHandler("takequiz", take_quiz_command))
        app.telegram_app.add_handler(CommandHandler("createcourse", create_course_command))
        app.telegram_app.add_handler(CommandHandler("crawl", crawl_command))
        app.telegram_app.add_handler(CommandHandler("listcourses", list_courses_command))
        app.telegram_app.add_handler(CommandHandler("setadmin", set_admin_command))
        app.telegram_app.add_handler(CommandHandler("getid", get_id_command))
        app.telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.telegram_app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.VOICE, handle_media))
        logger.info("Đã khởi tạo ứng dụng Telegram thành công")
    return app.telegram_app

# Route webhook cho Telegram
@app.post("/webhook")
@limiter.limit("10/minute")
async def webhook(request: Request):
    try:
        if not app.initialized or app.telegram_app is None:
            logger.error("Ứng dụng Telegram chưa được khởi tạo hoặc không sẵn sàng")
            raise HTTPException(status_code=500, detail="Ứng dụng chưa khởi tạo")
        update = Update.de_json(await request.json(), app.telegram_app.bot)
        if update is None:
            logger.error("Nhận được cập nhật không hợp lệ từ Telegram")
            raise HTTPException(status_code=400, detail="Cập nhật không hợp lệ")
        await app.telegram_app.process_update(update)
        logger.info("Xử lý webhook thành công")
        return {"status": "ok"}
    except RateLimitExceeded:
        raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lỗi khi xử lý webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Route gốc
@app.get("/")
async def root():
    return {"message": "CotienBot đang chạy!"}

# Retry logic cho set_webhook
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type(Exception))
async def set_webhook_with_retry(telegram_app, webhook_url):
    logger.info(f"Thử thiết lập webhook tới {webhook_url}")
    try:
        await telegram_app.bot.set_webhook(url=webhook_url)
        logger.info(f"Đã thiết lập webhook thành công tới {webhook_url}")
    except Exception as e:
        logger.error(f"Lỗi khi thiết lập webhook: {str(e)}")
        raise

# Sự kiện khởi động
@app.on_event("startup")
async def startup_event():
    logger.info("Bắt đầu sự kiện khởi động...")
    try:
        # Khởi tạo telegram_app
        await get_telegram_app()
        logger.info("Đang gọi Application.initialize()...")
        await app.telegram_app.initialize()
        logger.info("Application.initialize() hoàn tất")
        app.initialized = True

        # Thiết lập webhook với retry
        webhook_url = f"https://{settings.render_domain}/webhook"
        await set_webhook_with_retry(app.telegram_app, webhook_url)

        # Thiết lập admin
        db = FirestoreClient()
        admin_user_id = settings.admin_user_id
        if admin_user_id:
            logger.info(f"Đang đặt admin cho user {admin_user_id}")
            db.set_admin(admin_user_id, "Admin")
            logger.info(f"Đã đặt {admin_user_id} làm admin khi khởi động.")
    except Exception as e:
        logger.error(f"Lỗi nghiêm trọng trong startup_event: {str(e)}")
        app.initialized = False
        raise

# Sự kiện tắt
@app.on_event("shutdown")
async def shutdown_event():
    if app.telegram_app and app.initialized:
        logger.info("Đang xóa webhook và tắt ứng dụng...")
        await app.telegram_app.bot.delete_webhook()
        await app.telegram_app.shutdown()
        logger.info("Đã xóa webhook và tắt ứng dụng")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
