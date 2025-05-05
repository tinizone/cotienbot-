import logging
logger = logging.getLogger(__name__)
logger.info("Bắt đầu import các module cơ bản...")

import asyncio
import html
from fastapi import FastAPI, Request, HTTPException

logger.info("Hoàn tất import các module cơ bản")

# Trì hoãn import các thư viện nặng
def import_telegram_libs():
    logger.info("Đang import các thư viện Telegram...")
    from telegram.ext import Application, CommandHandler, MessageHandler, filters
    from telegram import Update
    from telegram.error import TelegramError
    from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
    logger.info("Hoàn tất import các thư viện Telegram")
    return Application, CommandHandler, MessageHandler, filters, Update, TelegramError, retry, stop_after_attempt, wait_fixed, retry_if_exception_type

def import_app_libs():
    logger.info("Đang import các thư viện ứng dụng...")
    from config.settings import settings
    from database.firestore import FirestoreClient
    from modules.chat.handler import (
        start, help_command, train_command, create_quiz_command, take_quiz_command,
        create_course_command, crawl_command, list_courses_command, set_admin_command,
        get_id_command, handle_message, handle_media
    )
    from modules.learning.crawler import crawl_rss
    logger.info("Hoàn tất import các thư viện ứng dụng")
    return settings, FirestoreClient, (start, help_command, train_command, create_quiz_command, take_quiz_command,
                                      create_course_command, crawl_command, list_courses_command, set_admin_command,
                                      get_id_command, handle_message, handle_media), crawl_rss

app = FastAPI()
app.telegram_app = None
app.initialized = False
app.firestore_client = None

# Import các thư viện sau khi FastAPI khởi tạo
Application, CommandHandler, MessageHandler, filters, Update, TelegramError, retry, stop_after_attempt, wait_fixed, retry_if_exception_type = import_telegram_libs()
settings, FirestoreClient, (start, help_command, train_command, create_quiz_command, take_quiz_command,
                           create_course_command, crawl_command, list_courses_command, set_admin_command,
                           get_id_command, handle_message, handle_media), crawl_rss = import_app_libs()

async def get_telegram_app():
    if app.telegram_app is None:
        logger.info("Đang khởi tạo ứng dụng Telegram...")
        try:
            if not settings.telegram_token:
                logger.error("TELEGRAM_TOKEN không được cung cấp")
                raise ValueError("TELEGRAM_TOKEN không được cung cấp")
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
        except TelegramError as e:
            logger.error(f"Lỗi Telegram khi khởi tạo telegram_app: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Lỗi không xác định khi khởi tạo telegram_app: {str(e)}")
            raise
    return app.telegram_app

def get_firestore_client():
    if app.firestore_client is None:
        logger.info("Đang khởi tạo FirestoreClient...")
        try:
            app.firestore_client = FirestoreClient()
            logger.info("Đã khởi tạo FirestoreClient thành công")
        except Exception as e:
            logger.error(f"Lỗi khi khởi tạo FirestoreClient: {str(e)}")
            raise
    return app.firestore_client

@app.post("/webhook")
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lỗi khi xử lý webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "CotienBot đang chạy!"}

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type(Exception))
async def set_webhook_with_retry(telegram_app, webhook_url):
    logger.info(f"Thử thiết lập webhook tới {webhook_url}")
    try:
        await telegram_app.bot.set_webhook(url=webhook_url)
        logger.info(f"Đã thiết lập webhook thành công tới {webhook_url}")
    except TelegramError as e:
        logger.error(f"Lỗi Telegram khi thiết lập webhook: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Lỗi không xác định khi thiết lập webhook: {str(e)}")
        raise

@app.on_event("startup")
async def startup_event():
    logger.info("Bắt đầu sự kiện khởi động...")
    try:
        logger.info("Bước 1: Khởi tạo telegram_app...")
        await get_telegram_app()
        logger.info("Bước 1 hoàn tất: telegram_app đã được khởi tạo")

        logger.info("Bước 2: Đang gọi Application.initialize()...")
        await app.telegram_app.initialize()
        logger.info("Bước 2 hoàn tất: Application.initialize() thành công")
        app.initialized = True

        logger.info("Bước 3: Thiết lập webhook...")
        webhook_url = f"https://{settings.render_domain}/webhook"
        await set_webhook_with_retry(app.telegram_app, webhook_url)
        logger.info("Bước 3 hoàn tất: Webhook đã được thiết lập")

        try:
            logger.info("Bước 4: Khởi tạo FirestoreClient...")
            db = get_firestore_client()
            logger.info("Bước 4.1: FirestoreClient đã được khởi tạo")

            admin_user_id = settings.admin_user_id
            if admin_user_id:
                logger.info(f"Đang đặt admin cho user {admin_user_id}")
                db.set_admin(admin_user_id, "Admin")
                logger.info(f"Đã đặt {admin_user_id} làm admin khi khởi động.")
            else:
                logger.info("Không có admin_user_id, bỏ qua bước đặt admin")
        except Exception as e:
            logger.error(f"Lỗi khi khởi tạo FirestoreClient hoặc đặt admin: {str(e)}")
        logger.info("Bước 4 hoàn tất (tùy chọn)")
    except TelegramError as e:
        logger.error(f"Lỗi Telegram trong startup_event: {str(e)}")
        app.initialized = False
        raise
    except Exception as e:
        logger.error(f"Lỗi nghiêm trọng trong startup_event: {str(e)}")
        app.initialized = False
        raise

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
