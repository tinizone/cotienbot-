# File: /main.py
import logging
import importlib
import os
import asyncio
from fastapi import FastAPI, Request, HTTPException
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update
from telegram.error import TelegramError
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from config.settings import settings
from database.firestore import FirestoreClient

logger = logging.getLogger(__name__)
logger.info("Bắt đầu import các module cơ bản...")

logger.info("Hoàn tất import các module cơ bản")

app = FastAPI()
app.telegram_app = None
app.initialized = False
app.firestore_client = None

# Hàm tải động các module từ thư mục modules/
def load_modules():
    module_handlers = []
    modules_dir = "modules"
    for filename in os.listdir(modules_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = filename[:-3]  # Loại bỏ .py
            try:
                module = importlib.import_module(f"{modules_dir}.{module_name}")
                logger.info(f"Đã tải module: {module_name}")
                if hasattr(module, "register_handlers"):
                    handlers = module.register_handlers()
                    module_handlers.extend(handlers)
            except Exception as e:
                logger.error(f"Lỗi khi tải module {module_name}: {str(e)}")
    return module_handlers

async def get_telegram_app():
    if app.telegram_app is None:
        logger.info("Đang khởi tạo ứng dụng Telegram...")
        try:
            if not settings.telegram_token:
                logger.error("TELEGRAM_TOKEN không được cung cấp")
                raise ValueError("TELEGRAM_TOKEN không được cung cấp")
            app.telegram_app = Application.builder().token(settings.telegram_token).read_timeout(30).write_timeout(30).build()
            # Đăng ký handlers từ các module
            handlers = load_modules()
            for handler in handlers:
                app.telegram_app.add_handler(handler)
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

        logger.info("Bước 4: Khởi tạo FirestoreClient...")
        get_firestore_client()
        logger.info("Bước 4 hoàn tất: FirestoreClient đã được khởi tạo")
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
        logger.info("Đang flush buffer Firestore...")
        db = get_firestore_client()
        # Flush chat buffer
        for user_id, chats in db.chat_buffer.items():
            if chats:
                doc_ref = db.client.collection("chat_history").document(user_id)
                current_chats = doc_ref.get().to_dict().get("chats", []) if doc_ref.get().exists else []
                current_chats.extend(chats)
                current_chats = current_chats[-db.MAX_CHATS:]
                doc_ref.set({"chats": current_chats})
                logger.info(f"Đã flush buffer trò chuyện cho user {user_id}")
        # Flush training buffer
        for user_id, training_data in db.training_buffer.items():
            if training_data:
                doc_ref = db.client.collection("users").document(user_id)
                current_training = doc_ref.get().to_dict().get("training_data", []) if doc_ref.get().exists else []
                current_training.extend(training_data)
                current_training = current_training[-db.MAX_TRAINING:]
                doc_ref.set({"training_data": current_training})
                logger.info(f"Đã flush buffer huấn luyện cho user {user_id}")
        logger.info("Đã xóa webhook và tắt ứng dụng")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
