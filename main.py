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
import logging
import asyncio
import html

logger = logging.getLogger(__name__)

# Khởi tạo FastAPI và Limiter
app = FastAPI()
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Xử lý lỗi RateLimitExceeded
async def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return HTTPException(status_code=429, detail="Rate limit exceeded")

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Khởi tạo ứng dụng Telegram
async def get_telegram_app():
    app = Application.builder().token(settings.telegram_token).read_timeout(30).write_timeout(30).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("train", train_command))
    app.add_handler(CommandHandler("createquiz", create_quiz_command))
    app.add_handler(CommandHandler("takequiz", take_quiz_command))
    app.add_handler(CommandHandler("createcourse", create_course_command))
    app.add_handler(CommandHandler("crawl", crawl_command))
    app.add_handler(CommandHandler("listcourses", list_courses_command))
    app.add_handler(CommandHandler("setadmin", set_admin_command))
    app.add_handler(CommandHandler("getid", get_id_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.VOICE, handle_media))
    return app

# Route webhook cho Telegram
@app.post("/webhook")
@limiter.limit("10/minute")
async def webhook(request: Request):
    try:
        telegram_app = await get_telegram_app()
        update = Update.de_json(await request.json(), telegram_app.bot)
        if update is None:
            logger.error("Nhận được cập nhật không hợp lệ từ Telegram")
            raise HTTPException(status_code=400, detail="Cập nhật không hợp lệ")
        await telegram_app.process_update(update)
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

# Sự kiện khởi động
@app.on_event("startup")
async def startup_event():
    telegram_app = await get_telegram_app()
    await telegram_app.initialize()
    logger.info("Đã khởi tạo ứng dụng Telegram")
    webhook_url = f"https://{settings.render_domain}/webhook"
    logger.info(f"Đang thiết lập webhook tới {webhook_url}")
    try:
        await telegram_app.bot.set_webhook(url=webhook_url)
        logger.info(f"Đã thiết lập webhook thành công tới {webhook_url}")
    except Exception as e:
        logger.error(f"Lỗi khi thiết lập webhook: {e}")
        raise

    db = FirestoreClient()
    admin_user_id = settings.admin_user_id
    if admin_user_id:
        db.set_admin(admin_user_id, "Admin")
        logger.info(f"Đã đặt {admin_user_id} làm admin khi khởi động.")

# Sự kiện tắt
@app.on_event("shutdown")
async def shutdown_event():
    telegram_app = await get_telegram_app()
    await telegram_app.bot.delete_webhook()
    await telegram_app.shutdown()
    logger.info("Đã xóa webhook và tắt ứng dụng")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
