# app.py
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging
import os
from telegram.ext import Application
from modules.chat import start, help_command, train_command, handle_message
from config.settings import settings
import psutil
import time

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Khởi tạo FastAPI app
app = FastAPI()

# Khởi tạo bot Telegram
try:
    application = Application.builder().token(settings.telegram_token).build()
except Exception as e:
    logger.error(f"Không thể khởi tạo bot Telegram: {str(e)}")
    raise

# Đăng ký các handler
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("train", train_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Biến toàn cục cho giới hạn Gemini API
GEMINI_RATE_LIMIT = 50
gemini_call_count = 0
last_reset_time = time.time()

# Webhook endpoint
@app.post("/webhook")
async def webhook(request: Request):
    global gemini_call_count, last_reset_time
    current_time = time.time()
    if current_time - last_reset_time >= 60:
        gemini_call_count = 0
        last_reset_time = current_time

    try:
        # Log tài nguyên
        try:
            memory = psutil.virtual_memory()
            logger.info(f"RAM sử dụng: {memory.percent}% (tổng: {memory.total / 1024 / 1024:.2f}MB, còn lại: {memory.available / 1024 / 1024:.2f}MB)")
            cpu = psutil.cpu_percent()
            logger.info(f"CPU sử dụng: {cpu}%")
        except Exception as e:
            logger.warning(f"Không thể kiểm tra tài nguyên: {str(e)}")

        data = await request.json()
        update = data
        await application.process_update(update)
        return JSONResponse({"status": "ok"})
    except Exception as e:
        logger.error(f"Lỗi trong webhook: {str(e)}", exc_info=True)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

# Khởi động bot
async def startup_event():
    logger.info("Đang khởi động bot...")
    try:
        await application.bot.set_webhook(url=f"{settings.render_domain}/webhook")
        logger.info(f"Webhook đã được đăng ký tại: {settings.render_domain}/webhook")
    except Exception as e:
        logger.error(f"Lỗi khi đăng ký webhook: {str(e)}", exc_info=True)
    logger.info("Bot đã khởi động thành công!")

@app.on_event("startup")
async def startup():
    await startup_event()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    uvicorn.run(app, host="0.0.0.0", port=7860)  # Spaces dùng port 7860 mặc định
